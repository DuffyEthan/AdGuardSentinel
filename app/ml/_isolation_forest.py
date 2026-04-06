# isolation forest implementation
# data from the db team:
# bucket_timestamp, publisher_id, impression_count, click_count, conversion_count

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import uuid
from app.db.session import get_session


def fetch_derived_metrics(session: Session, start_date, end_date, publisher_id=None) -> pd.DataFrame:
    from app.repositories.derived_metrics_repository import DerivedMetricsRepository
    repo = DerivedMetricsRepository(session)

    rows = repo.get_last_n_before(
        t=end_date,
        n=200,
        publisher_id=uuid.UUID(publisher_id) if publisher_id else None
    )

    filtered_rows = [r for r in rows if r.bucket_timestamp >= start_date]

    data = []
    for row in filtered_rows:
        data.append({
            'bucket_timestamp': row.bucket_timestamp,
            'publisher_id': str(row.publisher_id),
            'campaign_id': str(row.campaign_id) if row.campaign_id else None,
            'impressions_mean': row.impressions_mean,
            'clicks_mean': row.clicks_mean,
            'conversions_mean': row.conversions_mean,
            'impressions_std': row.impressions_std,
            'clicks_std': row.clicks_std,
            'conversions_std': row.conversions_std,
            'impressions_weighted_mean': row.impressions_weighted_mean,
            'clicks_weighted_mean': row.clicks_weighted_mean,
            'conversions_weighted_mean': row.conversions_weighted_mean,
            'sample_size': row.sample_size
        })

    df = pd.DataFrame(data)
    if not df.empty:
        df['bucket_timestamp'] = pd.to_datetime(df['bucket_timestamp'])
    return df


def fetch_and_merge(session: Session, start_date, end_date, publisher_id=None) -> pd.DataFrame:
    raw = fetch_raw_data(session, start_date, end_date, publisher_id)
    derived = fetch_derived_metrics(session, start_date, end_date, publisher_id)
    return raw.merge(derived, on=['bucket_timestamp', 'publisher_id'], how='inner')



def fetch_raw_data(session: Session, start_date, end_date, publisher_id=None):
    """
    USING DERIVED METRICS NOW
    fetching raw metrics from the database.
    
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
        session = SQLAlchemy session
        start_date = start timestamp
        end_date = end timestamp 
        publisher_id = optional (filter by specific publisher)
    

        It's returning DataFrame with columns: bucket_timestamp, publisher_id, 
                                impression_count, click_count, conversion_count
    """    
    # building SQL query
    if publisher_id is None:
        # get data for all publishers
        query = text("""
            SELECT bucket_timestamp, publisher_id, impression_count, 
                   click_count, conversion_count
            FROM raw_metrics
            WHERE bucket_timestamp >= :start_date AND bucket_timestamp < :end_date
            ORDER BY publisher_id, bucket_timestamp
        """)
        params = {'start_date': start_date, 'end_date': end_date}
    else:
        query = text("""
            SELECT bucket_timestamp, publisher_id, impression_count, 
                   click_count, conversion_count
            FROM raw_metrics
            WHERE bucket_timestamp >= :start_date AND bucket_timestamp < :end_date
              AND publisher_id = :publisher_id
            ORDER BY bucket_timestamp
        """)
        params = {'start_date': start_date, 'end_date': end_date, 'publisher_id': publisher_id}
    
    
    # use pandas to read SQL query into DataFrame
    df = pd.read_sql(query, session.bind, params=params)
    
    return df


def log_results_to_db(session: Session, predictions, model_name="isolation_forest_v1"):
    """
    logs model predictions back to the database
    inserts into model_logs table
    
    Arguments:
        session: SQLAlchemy session
        predictions = DataFrame with columns including bucket_timestamp, 
                     publisher_id, trust_score
        model_name = name of the model (default: "isolation_forest_v1")
    """
    # Insert query with ON CONFLICT
    insert_query = text("""
        INSERT INTO model_logs (log_timestamp, publisher_id, model_name, score, fraud_type)
        VALUES (:log_timestamp, :publisher_id, :model_name, :score, :fraud_type)
        ON CONFLICT (publisher_id, log_timestamp) 
        DO UPDATE SET 
            score = EXCLUDED.score,
            model_name = EXCLUDED.model_name,
            fraud_type = EXCLUDED.fraud_type
    """)
    for _, row in predictions.iterrows():
        # get fraud type (if column exists, otherwise default to 'unknown')
        fraud_type = row.get('primary_fraud_type', 'unknown')
        
        session.execute(insert_query, {
            'log_timestamp': row['bucket_timestamp'],
            'publisher_id': int(row['publisher_id']),
            'model_name': model_name,
            'score': float(row['anomaly_score']),
            'fraud_type': fraud_type
        })
    
    # Commit changes
    session.commit()
    


def ctr_calculation(clicks_count: int, impressions_count: int):
    if impressions_count == 0:
        return 0.0
    return (clicks_count / impressions_count) * 100


def cvr_calculation(conversions: int, total_visitors: int):
    if total_visitors == 0:
        return 0.0
    return (conversions / total_visitors) * 100



# features from raw + pre-computed derived metrics
def compute_features(df):
    features = df.copy()
    features = features.sort_values('bucket_timestamp')

    # CTR/CVR from raw counts
    features['ctr'] = np.where(features['impression_count'] > 0, features['click_count'] / features['impression_count'], 0.0)
    features['cvr'] = np.where(features['click_count'] > 0, features['conversion_count'] / features['click_count'], 0.0)

    # expected CTR/CVR from pre-computed rolling means
    ctr_mean = np.where(features['impressions_mean'] > 0, features['clicks_mean'] / features['impressions_mean'], 0.0)
    cvr_mean = np.where(features['clicks_mean'] > 0, features['conversions_mean'] / features['clicks_mean'], 0.0)

    # CTR deviation from the pre-computed rolling mean
    features['ctr_rolling_mean'] = ctr_mean
    features['ctr_rolling_std'] = np.where(
        features['impressions_mean'] > 0,
        features['clicks_std'] / features['impressions_mean'],
        0.0
    )
    features['ctr_deviation'] = np.abs(features['ctr'] - ctr_mean)

    # IMPRESSION FRAUD — pre-computed mean is the rolling average
    features['impression_ratio'] = np.where(features['impressions_mean'] > 0, features['impression_count'] / features['impressions_mean'], 1.0)
    features['impression_velocity'] = features['impression_count'].diff().fillna(0)
    features['impression_spike_ratio'] = features['impression_ratio']  # same signal
    features['impression_volatility'] = features['impressions_std']    # pre-computed
    features['abnormal_volume'] = np.where(features['impression_count'] > features['impressions_mean'] * 10, 1, 0)

    # CLICK INJECTION — use pre-computed CVR mean as baseline
    features['cvr_spike_ratio'] = np.where(cvr_mean > 0, features['cvr'] / cvr_mean, 1.0)
    features['suspicious_cvr'] = np.where(features['cvr'] > cvr_mean * 3, 1, 0)

    # conversion clustering: share of the rolling daily expectation
    daily_expected = features['conversions_mean'] * 24
    features['conversion_clustering'] = np.where(daily_expected > 0, features['conversion_count'] / daily_expected, 0.0)

    features = features.fillna(0)
    features = features.replace([np.inf, -np.inf], 0)

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
            'impressions_mean',
            'impressions_std',
            'impressions_weighted_mean',
            'impression_ratio',
            'impression_velocity',
            'impression_spike_ratio',
            'impression_volatility',
            'abnormal_volume',
            'click_count',
            'clicks_mean',
            'clicks_std',
            'clicks_weighted_mean',
            'conversion_count',
            'conversions_mean',
            'conversions_std',
            'conversions_weighted_mean',
            'sample_size',
            'cvr_spike_ratio',
            'suspicious_cvr',
            'conversion_clustering',
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
        features['anomaly_score'] = trust_scores
        features['is_organic'] = (trust_scores >= self.threshold).astype(int)  # 1=organic, 0=non-organic
        
        return features
    
    def normalise_scores(self, scores):
        """
        converting raw anomaly scores to anomaly score [0-1].
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
                float(row['anomaly_score'])  # this is the score that goes to the DB
            ))
        return logs

class CTRFraudDetection(AnomalyDetection):
    # An Isolation Forest just for the CTR fraud detection
    
    def __init__(self, contamination=0.05, threshold=0.7):
        super().__init__(contamination, threshold)
        
        # CTR related features
        self.feature_cols = [
            'ctr',
            'ctr_rolling_mean',
            'ctr_rolling_std',
            'ctr_deviation',
            'click_count',
            'clicks_mean',
            'clicks_std',
            'clicks_weighted_mean',
            'impression_count',
            'impressions_mean',
            'impressions_std',
            'impressions_weighted_mean',
            'sample_size',
        ]

class ImpressionFraudDetection(AnomalyDetection):
    # An Isolation Forest just for the impression fraud detection

    def __init__(self, contamination=0.05, threshold=0.7):
        super().__init__(contamination, threshold)
        
        # impression-related features
        self.feature_cols = [
            'impression_count',
            'impressions_mean',
            'impressions_std',
            'impressions_weighted_mean',
            'impression_ratio',
            'impression_velocity',
            'impression_spike_ratio',
            'impression_volatility',
            'abnormal_volume',
            'sample_size',
        ]


class ClickInjectionDetection(AnomalyDetection):
    # An isolation forest for the click injection fraud detection

    # NO TIMING FEATURES, uses only CVR patterns

    def __init__(self, contamination=0.05, threshold=0.7):
        super().__init__(contamination, threshold)
        
        # click injection-related features (CVR-based, no timing)
        self.feature_cols = [
            'cvr',
            'cvr_spike_ratio',
            'suspicious_cvr',
            'conversion_clustering',
            'conversion_count',
            'conversions_mean',
            'conversions_std',
            'conversions_weighted_mean',
            'click_count',
            'clicks_mean',
            'clicks_std',
            'sample_size',
        ]


# freezing the model
def save_model(anomaly_detector: AnomalyDetection, filepath = 'app/ml/models/_isolation_forest.joblib'):
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


def load_model(filepath= 'app/ml/models/_isolation_forest.joblib') -> AnomalyDetection:
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
    # creating an instance of the anomaly_detection (contamination, threshold) class
    model = AnomalyDetection(contamination = contamination, threshold = threshold)

    # calling model.fit(df) function - training the model on historical data
    model.fit(df)

    # returning predcitions (model.predict(df))
    predictions = model.predict(df)
    return predictions

def train_multiple_detection_model(
       df: pd.DataFrame,
    contamination: float = 0.05,
    threshold: float = 0.7
) -> tuple[pd.DataFrame, tuple]: 

    # train seperate isolation forests, one for each fraud type
    # Returns:
    #   - preditions: individual fraud score and overall score
    #   - models
    
    ctr_detector = CTRFraudDetection(contamination, threshold)
    impression_detector = ImpressionFraudDetection(contamination, threshold)
    click_detector = ClickInjectionDetection(contamination, threshold)
    
    # training each model
    ctr_detector.fit(df)
    impression_detector.fit(df)
    click_detector.fit(df)
    
    # ----

    # continuous score 
    features = compute_features(df)
    
    # feature matrices for each model
    X_ctr = features[ctr_detector.feature_cols].fillna(0)
    X_impression = features[impression_detector.feature_cols].fillna(0)
    X_injection = features[click_detector.feature_cols].fillna(0)
    
    # decision scores from each model (continuous!!)
    ctr_decision = ctr_detector.model.decision_function(X_ctr)
    impression_decision = impression_detector.model.decision_function(X_impression)
    injection_decision = click_detector.model.decision_function(X_injection)
    
    # normalise to between 0 and 1 range (0=fraud, 1=organic)
    scaler = MinMaxScaler()
    ctr_normalised = scaler.fit_transform(ctr_decision.reshape(-1, 1)).flatten()
    impression_normalised = scaler.fit_transform(impression_decision.reshape(-1, 1)).flatten()
    injection_normalised = scaler.fit_transform(injection_decision.reshape(-1, 1)).flatten()
    
    result = df.copy()
    result['ctr_anomaly_score'] = ctr_normalised
    result['impression_anomaly_score'] = impression_normalised
    result['click_injection_anomaly_score'] = injection_normalised
    
    # anomaly score = minimum of the three (worst score)
    result['anomaly_score'] = result[[
        'ctr_anomaly_score',
        'impression_anomaly_score',
        'click_injection_anomaly_score'
    ]].min(axis=1)
    
    # organic flag
    result['is_organic'] = (result['anomaly_score'] >= threshold).astype(int)


    # fraud type flags (which fraud was detected)
    result['has_ctr_fraud'] = (result['ctr_anomaly_score'] < threshold).astype(int)
    result['has_impression_fraud'] = (result['impression_anomaly_score'] < threshold).astype(int)
    result['has_click_injection'] = (result['click_injection_anomaly_score'] < threshold).astype(int)

    # determine primary fraud type (lowest score = most anomalous)
    fraud_scores = result[['ctr_anomaly_score', 'impression_anomaly_score', 'click_injection_anomaly_score']]
    result['primary_fraud_type'] = fraud_scores.idxmin(axis=1).map({
        'ctr_anomaly_score': 'ctr',
        'impression_anomaly_score': 'impression',
        'click_injection_anomaly_score': 'click_injection'
    })
    
    # If organic, set fraud type to 'none'
    result.loc[result['is_organic'] == 1, 'primary_fraud_type'] = 'none'
    # ----
    
    return result, (ctr_detector, impression_detector, click_detector)

def run_full_pipeline(
    session: Session,
    start_date,
    end_date,
    publisher_id = None,
    model_name: str = "isolation_forest_v2",
    contamination: float = 0.05,
    threshold: float = 0.7
) -> dict:
    """
    Full pipeline: fetch data -> train model -> log to database.
    Returns {"status": "success"/"error", "records_processed": int, "records_logged": int}

    """

    # wrap in try/except
    try:
        # fetch and merge raw + pre-computed derived metrics
        data = fetch_and_merge(session, start_date, end_date, publisher_id)

        if data.empty:
            return {
                "status": "error",
                "error_message": "No data found for the specified date range"
            }
        
        
        
        # train the model and get predictions
        predictions = train_isolation_forest(
            data,
            contamination=contamination,
            threshold=threshold
        )

        # log results back to database
        log_results_to_db(session, predictions, model_name=model_name)

        # return success dictionary with details
        return {
            "status": "success",
            "records_processed": len(data),
            "records_logged": len(predictions)
        }
    
    # catch any errors and return error dictionary
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }






def convert_raw_to_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived metrics from raw counts (used for training with synthetic data)."""
    derived = df.copy().sort_values('bucket_timestamp')

    window = 24
    for raw_col, prefix in [
        ('impression_count', 'impressions'),
        ('click_count', 'clicks'),
        ('conversion_count', 'conversions'),
    ]:
        derived[f'{prefix}_mean'] = derived[raw_col].rolling(window=window, min_periods=1).mean()
        derived[f'{prefix}_std'] = derived[raw_col].rolling(window=window, min_periods=1).std().fillna(0)
        derived[f'{prefix}_weighted_mean'] = derived[f'{prefix}_mean']  # equal weights for synthetic data

    derived['sample_size'] = derived['impression_count'].rolling(window=window, min_periods=1).count()
    derived['campaign_id'] = 'test_campaign'

    return derived


# TRAINING AND FREEZING THE MODELS

if __name__ == "__main__":

    from datetime import datetime, timedelta
    from app.ml.publishers import publisher_catalog
    import pandas as pd
    
    
    data = []
    start_time = datetime(2026, 1, 1, 0, 0, 0)
    
    for pub_name, publisher in publisher_catalog.items():
        
        for hour in range(200):
            timestamp = start_time + timedelta(hours=hour)
            settings = {'timestamp': timestamp}
            ts, impressions, clicks, conversions = publisher["generator"].publisher_data_next(settings)
            
            data.append({
                'bucket_timestamp': ts,
                'publisher_id': pub_name,
                'impression_count': impressions,
                'click_count': clicks,
                'conversion_count': conversions
            })
    
    df = pd.DataFrame(data)
    
    df_derived = convert_raw_to_derived(df)

    predictions, (ctr_model, impression_model, click_model) = train_multiple_detection_model(
        df_derived,
        contamination=0.1,
        threshold=0.7
    )

    save_model(ctr_model, 'app/ml/models/ctr_fraud_detector_v2.joblib')
    save_model(impression_model, 'app/ml/models/impression_fraud_detector_v2.joblib')
    save_model(click_model, 'app/ml/models/click_injection_detector_v2.joblib')
    
    total_fraud = len(predictions[predictions['is_organic'] == 0])
    total_organic = len(predictions[predictions['is_organic'] == 1])
    
    for fraud_type in ['ctr', 'impression', 'click_injection', 'none']:
        count = len(predictions[predictions['primary_fraud_type'] == fraud_type])
   