import uuid
from datetime import datetime, timezone

from app.ml.publishers.pub_cat import pub_cat
from app.ml.publishers.pub_dog import pub_dog
from app.ml.publishers.pub_fox import pub_fox
from app.ml.publishers.pub_owl import pub_owl
from app.ml.publishers.pub_spy import pub_spy

# Campaign catalog keyed by campaign UUID.
# Alpha contains the three baseline/fraud-light publishers;
# Bravo contains the two heavier-fraud publishers.

CAMPAIGN_ALPHA = uuid.UUID("00000000-0000-0000-0000-000000000001")
CAMPAIGN_BRAVO = uuid.UUID("00000000-0000-0000-0000-000000000002")

campaign_catalog: dict[uuid.UUID, dict] = {
    CAMPAIGN_ALPHA: {
        "name": "Alpha",
        "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
    },
    CAMPAIGN_BRAVO: {
        "name": "Bravo",
        "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
    },
}

# Publisher catalog keyed by publisher UUID.
# SPY / CAT / DOG belong to Campaign Alpha.
# OWL / FOX belong to Campaign Bravo.

publisher_catalog: dict[uuid.UUID, dict] = {
    uuid.UUID("00000000-0000-0000-0000-000000000010"): {
        "name": "SPY",
        "generator": pub_spy,
        "campaign_id": CAMPAIGN_ALPHA,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000020"): {
        "name": "CAT",
        "generator": pub_cat,
        "campaign_id": CAMPAIGN_ALPHA,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000030"): {
        "name": "DOG",
        "generator": pub_dog,
        "campaign_id": CAMPAIGN_ALPHA,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000040"): {
        "name": "OWL",
        "generator": pub_owl,
        "campaign_id": CAMPAIGN_BRAVO,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000050"): {
        "name": "FOX",
        "generator": pub_fox,
        "campaign_id": CAMPAIGN_BRAVO,
    },
}
