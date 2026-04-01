from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.types import InternalState, DataPacket  

# taken from app.ml.markov

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    """Normal publisher behavior"""
    timestamp = settings.get('timestamp', datetime.now())
    
    # different values from cat publisher which also has a normal behaviour
    impressions = np.random.poisson(8000)
    clicks = np.random.poisson(420)
    conversions = np.random.poisson(35)
    
    return (timestamp, impressions, clicks, conversions)

spy_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [(1.0, "normal")] 
    }
}

pub_spy = MarkovDataGenerator.from_dict(spy_graph, "normal")

# Stationary fraud fractions — all zero (single normal state)
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.0, 'impression_fraud': 0.0, 'click_injection': 0.0}