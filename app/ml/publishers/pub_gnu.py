from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.types import InternalState, DataPacket

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(7200)
    clicks = np.random.poisson(380)
    conversions = np.random.poisson(30)
    return (timestamp, impressions, clicks, conversions)


def impression_fraud_behavior(settings: InternalState) -> DataPacket:
    """Impression stuffing — 10-25x impressions"""
    timestamp = settings.get('timestamp', datetime.now())
    spike = np.random.randint(10, 26)
    impressions = np.random.poisson(7200) * spike
    clicks = np.random.poisson(380)
    conversions = np.random.poisson(30)
    return (timestamp, impressions, clicks, conversions)


def ctr_fraud_behavior(settings: InternalState) -> DataPacket:
    """CTR inflation — 4-8x clicks"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(7200)
    multiplier = np.random.randint(4, 9)
    clicks = np.random.poisson(380) * multiplier
    conversions = np.random.poisson(30)
    return (timestamp, impressions, clicks, conversions)


gnu_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.91, "normal"),
            (0.05, "impression_fraud"),
            (0.04, "ctr_fraud"),
        ]
    },
    "impression_fraud": {
        "function": impression_fraud_behavior,
        "edges": [
            (0.88, "impression_fraud"),
            (0.12, "normal"),
        ]
    },
    "ctr_fraud": {
        "function": ctr_fraud_behavior,
        "edges": [
            (0.82, "ctr_fraud"),
            (0.18, "normal"),
        ]
    },
}

pub_gnu = MarkovDataGenerator.from_dict(gnu_graph, "normal")

# Trimodal stationary distribution (solved via πP = π, Σπ = 1):
#   π_imp = (5/12) · π_n  →  15/59 ≈ 0.2542
#   π_ctr = (2/9)  · π_n  →  8/59  ≈ 0.1356
#   π_n   = 36/59 ≈ 0.6102
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.1356, 'impression_fraud': 0.2542, 'click_injection': 0.0}
