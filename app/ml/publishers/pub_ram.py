from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.ml_types import InternalState, DataPacket

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    """Smaller publisher, normal behaviour"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(6000)
    clicks = np.random.poisson(300)
    conversions = np.random.poisson(25)
    return (timestamp, impressions, clicks, conversions)


def impression_fraud_behavior(settings: InternalState) -> DataPacket:
    """Impression stuffing — 10-30x impressions, clicks/conversions unchanged"""
    timestamp = settings.get('timestamp', datetime.now())
    spike = np.random.randint(10, 31)
    impressions = np.random.poisson(6000) * spike
    clicks = np.random.poisson(300)
    conversions = np.random.poisson(25)
    return (timestamp, impressions, clicks, conversions)


ram_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.95, "normal"),
            (0.05, "impression_fraud"),
        ]
    },
    "impression_fraud": {
        "function": impression_fraud_behavior,
        "edges": [
            (0.82, "impression_fraud"),
            (0.18, "normal"),
        ]
    },
}

pub_ram = MarkovDataGenerator.from_dict(ram_graph, "normal")

# Stationary fraud fraction: π(impression_fraud) = p/(p+q) = 0.05/(0.05+0.18) ≈ 0.2174
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.0, 'impression_fraud': 0.2174, 'click_injection': 0.0}
