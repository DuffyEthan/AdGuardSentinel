from app.ml.markov import MarkovDataGenerator
from datetime import datetime
from typing import Any
import numpy as np
from app.ml.ml_types import InternalState, DataPacket 

# taken from app.ml.markov

InternalState = dict[str, Any]
DataPacket = tuple[datetime, int, int, int]


def normal_behavior(settings: InternalState) -> DataPacket:
    """Normal behaviour"""

    # get timestamp
    timestamp = settings.get('timestamp', datetime.now())
    
    # generating impressions using Poisson distribution
    impressions = np.random.poisson(8000)

    # generating clicks using Poisson distribution
    clicks = np.random.poisson(420) 

    # generating conversions using Poisson distribution
    conversions = np.random.poisson(35)
    
    return (timestamp, impressions, clicks, conversions)


def ctr_fraud_behavior(settings: InternalState) -> DataPacket:
    """CTR fraud (5-10x clicks)"""

    # get timestamp
    timestamp = settings.get('timestamp', datetime.now())
    
    # generating impressions (they stay normal during CTR fraud)
    impressions = np.random.poisson(8000)
    
    # generate spike clicks 5-10x
    click_multiplier = np.random.randint(5, 11)
    # calculate fraud click count
    clicks = np.random.poisson(420) * click_multiplier
    
    # conversions increased slightly
    conversions = np.random.poisson(35) + np.random.poisson(10)
    
    return (timestamp, impressions, clicks, conversions)


owl_graph = {
    "normal": {
        "function": normal_behavior,
        "edges": [
            (0.95, "normal"),       
            (0.05, "ctr_fraud")
        ]
    },
    "ctr_fraud": {
        "function": ctr_fraud_behavior,
        "edges": [
            (0.85, "ctr_fraud"),    # 85% chance to stay in ctr fraud state
            (0.15, "normal")        # 15% chance to return to normal state
        ]
    }
}
# create the publisher using MarkovDataGenerator
pub_owl = MarkovDataGenerator.from_dict(owl_graph, "normal")