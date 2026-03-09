from app.ml.markov import MarkovDataGenerator

# taken from app.ml.markov

# dummy functions that just print the current state
def foo(_):
    print("foo")
    return (0,0,0,0)

def bar(_):
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

pub_owl = MarkovDataGenerator.from_dict(bimodal, "normal")
