# isolation forest implementation
# data from the db team:
# bucket_timestamp, publisher_id, impression_count, click_count, conversion_count

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

def ctr_calculation(clicks_count : int, impressions_count : int):
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
# loging the prediction back to database
    pass

def compute_feautes():
    pass

class anomaly_Detecion:
# isolation forest based anomaly detection
    def __init__(self, contamination=0, threshold=0):
        self.contamination = contamination
        self.threshold = threshold
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=0,
            random_state=0
        )
        self.is_fitted = False

        # ^ I put all zeroes just for now
    
    def fit(self, df):
    # training the isolation forest on historical data
        pass

    def predict(self, df):
    # detecting anomalies in new data
        pass

    def normalise_scores(self, scores):
    # converting raw anomaly scores from the isolation forest to 0, 1 scale
        pass

    def get_model_logs(self, predictions):
    # converting the predictions to format for database log
        pass