from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.types import InternalState, DataPacket

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(8500)
    clicks = np.random.poisson(440)
    conversions = np.random.poisson(38)
    return (timestamp, impressions, clicks, conversions)


def ctr_fraud_behavior(settings: InternalState) -> DataPacket:
    """CTR inflation — 4-8x clicks"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(8500)
    multiplier = np.random.randint(4, 9)
    clicks = np.random.poisson(440) * multiplier
    conversions = np.random.poisson(38)
    return (timestamp, impressions, clicks, conversions)


def click_injection_behavior(settings: InternalState) -> DataPacket:
    """Click injection — 5-9x conversions"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(8500)
    clicks = np.random.poisson(440)
    multiplier = np.random.randint(5, 10)
    conversions = min(np.random.poisson(38) * multiplier, clicks)
    return (timestamp, impressions, clicks, conversions)


jay_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.90, "normal"),
            (0.06, "ctr_fraud"),
            (0.04, "click_injection"),
        ]
    },
    "ctr_fraud": {
        "function": ctr_fraud_behavior,
        "edges": [
            (0.80, "ctr_fraud"),
            (0.20, "normal"),
        ]
    },
    "click_injection": {
        "function": click_injection_behavior,
        "edges": [
            (0.85, "click_injection"),
            (0.15, "normal"),
        ]
    },
}

pub_jay = MarkovDataGenerator.from_dict(jay_graph, "normal")

# Trimodal stationary distribution (solved via πP = π, Σπ = 1):
#   π_ctr   = 0.30 · π_n  →  0.1915
#   π_click = (4/15) · π_n  →  0.1702
#   π_n  = 1 / (1 + 0.30 + 4/15) ≈ 0.6383
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.1915, 'impression_fraud': 0.0, 'click_injection': 0.1702}
