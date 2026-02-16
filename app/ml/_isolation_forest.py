# isolation forest implementation
# data from the db team:
# bucket_timestamp, publisher_id, impression_count, click_count, conversion_count

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest



def ctr_calculation(clicks_count: int, impressions_count: int):
    if impressions_count == 0:
        return 0.0
    return (clicks_count / impressions_count) * 100


def cvr_calculation(conversions: int, total_visitors: int):
    if total_visitors == 0:
        return 0.0
    return (conversions / total_visitors) * 100


def fetch_raw_data(start_date, end_date):
    # fetching raw metrics from the database
    pass


def log_results_to_db(predictions):
    # logging the prediction back to database
    pass

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
       # print(f"Model fitted on {len(X)} samples")  # printing a message saying how many rows were used
    
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


