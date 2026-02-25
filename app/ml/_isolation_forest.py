# isolation forest implementation
# data from the db team:
# bucket_timestamp, publisher_id, impression_count, click_count, conversion_count

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import psycopg2
from psycopg2 import sql
import joblib


# db settings - from db pod
DB_CONFIG = {
    'host': 'db',       
    'database': 'ad_metrics',   
    'user': 'postgres',        
    'password': '123456789', 
    'port': 5432                
}


def fetch_raw_data(start_date, end_date, publisher_id=None):
    """
    fetching raw metrics from the database.
    Batch Generator has inserted data into raw_metrics table
    using pandas read_sql() to get it
    
    visualisation :
    batch generator
          |
          v
postgres raw_metrics table
          |
          v
     pandas read_sql()
          |
          v
  isolation forest fit()

    Arguments:
        start_date = start timestamp
        end_date = end timestamp 
        publisher_id = optional (filter by specific publisher)
    

        It's returning DataFrame with columns: bucket_timestamp, publisher_id, 
                                impression_count, click_count, conversion_count
    """
    # connecting to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    
    # building SQL query
    if publisher_id is None:
        # get data for all publishers
        query = """
            SELECT bucket_timestamp, publisher_id, impression_count, 
                   click_count, conversion_count
            FROM raw_metrics
            WHERE bucket_timestamp >= %s AND bucket_timestamp < %s
            ORDER BY publisher_id, bucket_timestamp
        """
        params = (start_date, end_date)
    else:
        # get data for specific publisher
        query = """
            SELECT bucket_timestamp, publisher_id, impression_count, 
                   click_count, conversion_count
            FROM raw_metrics
            WHERE bucket_timestamp >= %s AND bucket_timestamp < %s
              AND publisher_id = %s
            ORDER BY bucket_timestamp
        """
        params = (start_date, end_date, publisher_id)
    
    # use pandas to read SQL query into DataFrame
    df = pd.read_sql(query, conn, params=params)
    
    # closing connection
    conn.close()
    
    return df


def log_results_to_db(predictions, model_name="isolation_forest_v1"):
    """
    logs model predictions back to the database
    inserts into model_logs table
    
    Arguments:
        predictions = DataFrame with columns including bucket_timestamp, 
                     publisher_id, trust_score
        model_name = name of the model (default: "isolation_forest_v1")
    """
    # connecting to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # preparing data for insertion and converting DataFrame to list of tuples
    records = []
    for _, row in predictions.iterrows():
        records.append((
            row['bucket_timestamp'],
            int(row['publisher_id']),
            model_name,
            float(row['trust_score'])
        ))
    
    # inserting into model_logs table
    insert_query = """
        INSERT INTO model_logs (timestamp, publisher_id, model_name, score)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (publisher_id, timestamp) 
        DO UPDATE SET score = EXCLUDED.score, model_name = EXCLUDED.model_name
    """
    
    # executing batch insert
    cur.executemany(insert_query, records)
    
    # committing changes
    conn.commit()
    
    # closing connection
    cur.close()
    conn.close()
    


def ctr_calculation(clicks_count: int, impressions_count: int):
    if impressions_count == 0:
        return 0.0
    return (clicks_count / impressions_count) * 100


def cvr_calculation(conversions: int, total_visitors: int):
    if total_visitors == 0:
        return 0.0
    return (conversions / total_visitors) * 100



# features from raw data for the isolation forest
def compute_features(df):
    features = df.copy()  # copying raw data for the isolation forest
    
    # calculate CTR and CVR
    features['ctr'] = np.where(features['impression_count'] > 0, features['click_count'] / features['impression_count'], 0.0)
    #                          condition,                        if condition is true,                                   if condition is false
    
    features['cvr'] = np.where(features['click_count'] > 0, features['conversion_count'] / features['click_count'], 0.0)
    #                          condition,                   if condition is true,                                   if condition is false

    # sorting by timestamp (from oldest to newest)
    features = features.sort_values('bucket_timestamp')
    
    # rolling statistics (window of 5 hours -> looking at the last 5 rows)
    features['ctr_rolling_mean'] = features['ctr'].rolling(window=5, min_periods=1).mean()
    features['ctr_rolling_std'] = features['ctr'].rolling(window=5, min_periods=1).std().fillna(0)
    
    # deviation from rolling mean
    features['ctr_deviation'] = np.abs(features['ctr'] - features['ctr_rolling_mean'])
    
    # Impression volume patterns
    features['impression_rolling_mean'] = features['impression_count'].rolling(window=5, min_periods=1).mean()
    features['impression_ratio'] = np.where(features['impression_rolling_mean'] > 0, features['impression_count'] / features['impression_rolling_mean'], 1.0)
    
    return features

# isolation forest anomaly detection 
class AnomalyDetection:

    
    def __init__(self, contamination=0.05, threshold=0.7):
        """
        contamination=0.05 => we expect 5% of data to be non-organic (fake engagement)
        threshold=0.7 => trust scores below 0.7 are flagged as non-organic
        """
        self.contamination = contamination
        self.threshold = threshold
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=200,
            random_state=42
        )
        self.is_fitted = False
        
        # features for the model
        self.feature_cols = [
            'ctr',
            'cvr',
            'ctr_rolling_mean',
            'ctr_rolling_std',
            'ctr_deviation',
            'impression_count',
            'impression_ratio'
        ]
    
    def fit(self, df):
        """training the isolation forest on historical data.
        it learns what normal engagement looks like by studing the features"""
        features = compute_features(df)
        
        # selecting only the feature columns and removing any missing values
        X = features[self.feature_cols].dropna()
        
        # training the model
        self.model.fit(X)
        self.is_fitted = True  # mark model as trained

    
    def predict(self, df):
        """detecting anomalies in new data."""
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        features = compute_features(df)
        # selecting feature columns and filling missing values with 0
        X = features[self.feature_cols].fillna(0)
        
        # get raw anomaly scores from the model
        raw_scores = self.model.decision_function(X)
        
        # converting raw scores to trust score (0-1 scale)
        trust_scores = self.normalise_scores(raw_scores)
        
        # add results to the dataframe
        features['trust_score'] = trust_scores
        features['is_organic'] = (trust_scores >= self.threshold).astype(int)  # 1=organic, 0=non-organic
        
        return features
    
    def normalise_scores(self, scores):
        """
        converting raw anomaly scores to trust score [0-1].
        I'm using the formula from ml pod doc:
        T = 1 - (s - s_min) / (s_max - s_min)
        
        Higher trust score = more organic
        Lower trust score = more suspicious
        """
        s_min, s_max = scores.min(), scores.max()
        
        # edge case where all scores are the same
        # 1e-9 = 0.000000001 
        if s_max - s_min < 1e-9:
            return np.full_like(scores, 0.5)
        
        # normalising the score using trust score formula
        # isolation forests return higher (less negative) scores for normal data
        # so I flip it: trust score = 1 - normalised score
        normalised = (scores - s_min) / (s_max - s_min)
        trust_score = 1 - normalised
        
        # round to 2 decimal points and make sure it's between 0 and 1
        return np.clip(np.round(trust_score, 2), 0.0, 1.0)
    
    def get_model_logs(self, predictions, model_name="isolation_forest_v1"):
        """
        converting the predictions to format for database log.
        returns: timestamp, publisher_id, model_name, score
        """
        logs = []
        for _, row in predictions.iterrows():
            logs.append((
                row['bucket_timestamp'],
                int(row['publisher_id']),
                model_name,
                float(row['trust_score'])  # this is the score that goes to the DB
            ))
        return logs


# freezing the model
def save_model(anomaly_detector, filepath = 'app/ml/models/_isolation_forest.joblib'):
    """
    freezing (saving) a trained model to a .joblib file
        
    anomaly_detector = trained anomaly detection model
    filepath = where I'm saving the trained model
    """
# compression = making a file smaller
# compress = 3   => best option. it's fast but balanced 

    if not anomaly_detector.is_fitted:
        raise RuntimeError("Can't save the model. Train the model first with fit().")
        
    # saving the trained model to filepath
    joblib.dump(anomaly_detector, filepath, compress = 3)


def load_model(filepath= 'app/ml/models/_isolation_forest.joblib'):
    """
    unfreezing (loading) a previously saved model

    filepath = where the model was saved

    It loades anomaly detection object that is ready to use
    """

    anomaly_detector = joblib.load(filepath)
    return anomaly_detector
    
def train_isolation_forest(df: pd.DataFrame, contamination: float = 0.05, threshold: float = 0.7) -> pd.DataFrame:
    """
    Train model and return predictions with trust_score and is_organic columns.
    
    """
    # creating an instance of the AnomalyDetection (contamination, threshold) class
    model = AnomalyDetection(contamination = contamination, threshold = threshold)

    # calling model.fit(df) function - training the model on historical data
    model.fit(df)

    # returning predcitions (model.predict(df))
    predictions = model.predict(df)
    return predictions


def run_full_pipeline(
    start_date,
    end_date,
    publisher_id = None,
    model_name: str = "isolation_forest_v1",
    contamination: float = 0.05,
    threshold: float = 0.7
) -> dict:
    """
    Full pipeline: fetch data -> train model -> log to database.
    Returns {"status": "success"/"error", "records_processed": int, "records_logged": int}

    """

    # wrap in try/except
    try:
        # fetch raw data from database
        raw_data = fetch_raw_data(start_date, end_date, publisher_id)
        
        if raw_data.empty:
            return {
                "status": "error",
                "error_message": "No data found for the specified date range"
            }
        
        
        # train the model and get predictions
        predictions = train_isolation_forest(
            raw_data, 
            contamination=contamination, 
            threshold=threshold
        )
        
        
        # log results back to database
        log_results_to_db(predictions, model_name=model_name)
                
        # return success dictionary with details
        return {
            "status": "success",
            "records_processed": len(raw_data),
            "records_logged": len(predictions)
        }
    
    # catch any errors and return error dictionary
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }
