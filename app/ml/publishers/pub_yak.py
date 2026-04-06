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
    impressions = np.random.poisson(6500)
    clicks = np.random.poisson(340)
    conversions = np.random.poisson(28)
    return (timestamp, impressions, clicks, conversions)


def click_injection_behavior(settings: InternalState) -> DataPacket:
    """Mild click injection — 3-6x conversions"""
    timestamp = settings.get('timestamp', datetime.now())
    impressions = np.random.poisson(6500)
    clicks = np.random.poisson(340)
    multiplier = np.random.randint(3, 7)
    conversions = min(np.random.poisson(28) * multiplier, clicks)
    return (timestamp, impressions, clicks, conversions)


yak_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.96, "normal"),
            (0.04, "click_injection"),
        ]
    },
    "click_injection": {
        "function": click_injection_behavior,
        "edges": [
            (0.80, "click_injection"),
            (0.20, "normal"),
        ]
    },
}

pub_yak = MarkovDataGenerator.from_dict(yak_graph, "normal")

# Stationary fraud fraction: π(click_injection) = p/(p+q) = 0.04/(0.04+0.20) ≈ 0.1667
FRAUD_STATE_PROBABILITY = {'ctr_fraud': 0.0, 'impression_fraud': 0.0, 'click_injection': 0.1667}
