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
    impressions = np.random.poisson(7500)
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