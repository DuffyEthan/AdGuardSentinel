from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.ml_types import InternalState, DataPacket  

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]

def normal_behavior(settings: InternalState) -> DataPacket:
    """Normal behaviour"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(8000)
    clicks = np.random.poisson(420)
    conversions = np.random.poisson(35)
    return (timestamp, impressions, clicks, conversions)

def click_injection_behavior(settings: InternalState) -> DataPacket:
    """Click injection (high CVR)"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(8000)
    clicks = np.random.poisson(420)
    conversion_multiplier = np.random.randint(6, 11)
    conversions = np.random.poisson(35) * conversion_multiplier
    conversions = min(conversions, clicks)
    return (timestamp, impressions, clicks, conversions)

dog_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.93, "normal"),
            (0.07, "click_injection")
        ]
    },
    "click_injection": {
        "function": click_injection_behavior,
        "edges": [
            (0.88, "click_injection"),
            (0.12, "normal")
        ]
    }
}

pub_dog = MarkovDataGenerator.from_dict(dog_graph, "normal")

# Stationary fraud fraction: π(click_injection) = p/(p+q) = 0.07/(0.07+0.12) ≈ 0.3684
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.0, 'impression_fraud': 0.0, 'click_injection': 0.3684}