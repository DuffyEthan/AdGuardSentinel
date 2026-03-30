from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.types import InternalState, DataPacket

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    """Larger publisher, normal behaviour"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(10000)
    clicks = np.random.poisson(550)
    conversions = np.random.poisson(45)
    return (timestamp, impressions, clicks, conversions)


def ctr_fraud_behavior(settings: InternalState) -> DataPacket:
    """CTR inflation — 3-6x clicks, impressions and conversions unchanged"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(10000)
    multiplier = np.random.randint(3, 7)
    clicks = np.random.poisson(550) * multiplier
    conversions = np.random.poisson(45)
    return (timestamp, impressions, clicks, conversions)


eel_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.94, "normal"),
            (0.06, "ctr_fraud"),
        ]
    },
    "ctr_fraud": {
        "function": ctr_fraud_behavior,
        "edges": [
            (0.75, "ctr_fraud"),
            (0.25, "normal"),
        ]
    },
}

pub_eel = MarkovDataGenerator.from_dict(eel_graph, "normal")

# Stationary fraud fraction: π(ctr_fraud) = p/(p+q) = 0.06/(0.06+0.25) ≈ 0.1935
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.1935, 'impression_fraud': 0.0, 'click_injection': 0.0}
