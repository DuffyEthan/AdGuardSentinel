from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.ml_types import InternalState, DataPacket 

# taken from app.ml.markov

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    """Normal publisher"""
    timestamp = settings.get('timestamp', datetime.now())
    
    # different values from spy publisher which has also normal behaviour
    impressions = max(1, int((np.random.poisson(7500)) * np.random.lognormal(0, 0.25)))
    clicks = np.random.poisson(400)
    conversions = np.random.poisson(32)
    
    return (timestamp, impressions, clicks, conversions)

cat_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [(1.0, "normal")]  
    }
}

pub_cat = MarkovDataGenerator.from_dict(cat_graph, "normal")

# Stationary fraud fractions — all zero (single normal state)
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.0, 'impression_fraud': 0.0, 'click_injection': 0.0}