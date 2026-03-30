import uuid

from app.ml.publishers.pub_cat import pub_cat
from app.ml.publishers.pub_dog import pub_dog
from app.ml.publishers.pub_fox import pub_fox
from app.ml.publishers.pub_owl import pub_owl
from app.ml.publishers.pub_spy import pub_spy

# Publisher catalog keyed by publisher UUID.
# Each entry contains the Markov generator, associated campaign UUID,
# and a human-readable name.
#
# UUIDs match those seeded by _seed_publishers.py so that foreign-key
# constraints are satisfied when the orchestrator writes rows.

publisher_catalog: dict[uuid.UUID, dict] = {
    uuid.UUID("00000000-0000-0000-0000-000000000010"): {
        "name": "SPY",
        "generator": pub_spy,
        "campaign_id": uuid.UUID("00000000-0000-0000-0000-000000000011"),
    },
    uuid.UUID("00000000-0000-0000-0000-000000000020"): {
        "name": "CAT",
        "generator": pub_cat,
        "campaign_id": uuid.UUID("00000000-0000-0000-0000-000000000021"),
    },
    uuid.UUID("00000000-0000-0000-0000-000000000030"): {
        "name": "DOG",
        "generator": pub_dog,
        "campaign_id": uuid.UUID("00000000-0000-0000-0000-000000000031"),
    },
    uuid.UUID("00000000-0000-0000-0000-000000000040"): {
        "name": "OWL",
        "generator": pub_owl,
        "campaign_id": uuid.UUID("00000000-0000-0000-0000-000000000041"),
    },
    uuid.UUID("00000000-0000-0000-0000-000000000050"): {
        "name": "FOX",
        "generator": pub_fox,
        "campaign_id": uuid.UUID("00000000-0000-0000-0000-000000000051"),
    },
}
