from typing import Any
from abc import ABC, abstractmethod
from datetime import datetime
from collections.abc import Callable
from numpy.random import choice

InternalState = dict[str, Any]

# timestamp, impressions, clicks, conversions
DataPacket = tuple[datetime, int, int, int]

# functional interface so I can do the markov thing
DataProducer = Callable[[InternalState], DataPacket]

MarkovStateDict = dict[str, dict[str, DataProducer|list[tuple[str, float]]]]

class DataGenerator(ABC):

    @abstractmethod
    def publisher_data_next(settings: InternalState) -> DataPacket:
        pass

# example: Markov Chain diagram that parses a dict as input
# and adapts produced data
class _MarkovState:
    name: str
    fun: DataProducer
    next_nodes: list[str]
    next_weights: list[float]

    def __init__(self, name: str, fun: DataProducer, edges: list[tuple[float, str]]):
        self.name = name
        self.fun = fun
        self.next_nodes, self.next_weights = zip(*edges)

    def next(self, settings: InternalState) -> tuple[DataPacket, str]:
        return (
            self.fun(settings),
            choice(self.next_nodes, p=self.next_weights)
        )

class MarkovDataGenerator(DataGenerator):
    states: dict[str, _MarkovState]
    current: _MarkovState

    def __init__(self, states: dict[str, _MarkovState], initial: str):
        self.states = states
        self.current = states[initial]

    @classmethod
    def from_dict(cls, state_dict: MarkovStateDict, initial: str):
        states = {
            k: _MarkovState(k, v["function"], v["edges"])
            for k, v in state_dict.items()
        }

        return cls(states, initial)

    def publisher_data_next(self, settings: InternalState) -> DataPacket:
        data, next = self.current.next(settings)
        self.current = self.states[next]
        return data

# dummy functions that just print the current state
def foo(x):
    print("foo")
    return (0,0,0,0)

def bar(x):
    print("bar")
    return (0,0,0,0)

# dict representation of our graph with functions for each node
bimodal = {
    "normal": {
        "function": foo,
        "edges": [("normal", 0.95), ("abnormal", 0.05)]
    },
    "abnormal": {
        "function": bar,
        "edges": [("abnormal", 0.95), ("normal", 0.05)]
    }
}

# sample run of the bimodal graph for a few cycles
if __name__ == "__main__":
    num_cycles = 30
    graph = MarkovDataGenerator.from_dict(bimodal, "normal")
    for i in range(num_cycles):
        print(i, end=" ")
        graph.publisher_data_next({})