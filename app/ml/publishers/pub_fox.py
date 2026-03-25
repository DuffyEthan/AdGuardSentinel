from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.types import InternalState, DataPacket  

# taken from app.ml.markov

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    """Normal state"""
    timestamp = settings.get('timestamp', datetime.now())
    
    impressions = np.random.poisson(8000)
    clicks = np.random.poisson(420)
    conversions = np.random.poisson(35)
    
    return (timestamp, impressions, clicks, conversions)


def impression_fraud_behavior(settings: InternalState) -> DataPacket:
    """Impression fraud (fake impressions)"""
    timestamp = settings.get('timestamp', datetime.now())
    
    # impressions 20-50x
    spike_multiplier = np.random.randint(20, 51)
    impressions = np.random.poisson(8000) * spike_multiplier
    
    # clicks and conversions stay normal (bots don't click)
    clicks = np.random.poisson(420)
    conversions = np.random.poisson(35)
    
    return (timestamp, impressions, clicks, conversions)


fox_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.92, "normal"),               
            (0.08, "impression_fraud")
        ]
    },
    "impression_fraud": {
        "function": impression_fraud_behavior,
        "edges": [
            (0.90, "impression_fraud"),     
            (0.10, "normal")
        ]
    }
}

pub_fox = MarkovDataGenerator.from_dict(fox_graph, "normal")