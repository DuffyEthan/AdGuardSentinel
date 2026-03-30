import uuid
from datetime import datetime, timezone

from app.ml.publishers.pub_cat import pub_cat, FRAUD_STATE_PROBABILITY as FSP_CAT
from app.ml.publishers.pub_dog import pub_dog, FRAUD_STATE_PROBABILITY as FSP_DOG
from app.ml.publishers.pub_fox import pub_fox, FRAUD_STATE_PROBABILITY as FSP_FOX
from app.ml.publishers.pub_owl import pub_owl, FRAUD_STATE_PROBABILITY as FSP_OWL
from app.ml.publishers.pub_spy import pub_spy, FRAUD_STATE_PROBABILITY as FSP_SPY
from app.ml.publishers.pub_ram import pub_ram, FRAUD_STATE_PROBABILITY as FSP_RAM
from app.ml.publishers.pub_eel import pub_eel, FRAUD_STATE_PROBABILITY as FSP_EEL
from app.ml.publishers.pub_jay import pub_jay, FRAUD_STATE_PROBABILITY as FSP_JAY
from app.ml.publishers.pub_gnu import pub_gnu, FRAUD_STATE_PROBABILITY as FSP_GNU
from app.ml.publishers.pub_yak import pub_yak, FRAUD_STATE_PROBABILITY as FSP_YAK

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
# Alpha: SPY, CAT, DOG, RAM, YAK
# Bravo: OWL, FOX, EEL, JAY, GNU

publisher_catalog: dict[uuid.UUID, dict] = {
    uuid.UUID("00000000-0000-0000-0000-000000000010"): {
        "name": "SPY",
        "generator": pub_spy,
        "campaign_id": CAMPAIGN_ALPHA,
        "fraud_probabilities": FSP_SPY,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000020"): {
        "name": "CAT",
        "generator": pub_cat,
        "campaign_id": CAMPAIGN_ALPHA,
        "fraud_probabilities": FSP_CAT,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000030"): {
        "name": "DOG",
        "generator": pub_dog,
        "campaign_id": CAMPAIGN_ALPHA,
        "fraud_probabilities": FSP_DOG,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000060"): {
        "name": "RAM",
        "generator": pub_ram,
        "campaign_id": CAMPAIGN_ALPHA,
        "fraud_probabilities": FSP_RAM,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000090"): {
        "name": "YAK",
        "generator": pub_yak,
        "campaign_id": CAMPAIGN_ALPHA,
        "fraud_probabilities": FSP_YAK,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000040"): {
        "name": "OWL",
        "generator": pub_owl,
        "campaign_id": CAMPAIGN_BRAVO,
        "fraud_probabilities": FSP_OWL,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000050"): {
        "name": "FOX",
        "generator": pub_fox,
        "campaign_id": CAMPAIGN_BRAVO,
        "fraud_probabilities": FSP_FOX,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000070"): {
        "name": "EEL",
        "generator": pub_eel,
        "campaign_id": CAMPAIGN_BRAVO,
        "fraud_probabilities": FSP_EEL,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000080"): {
        "name": "JAY",
        "generator": pub_jay,
        "campaign_id": CAMPAIGN_BRAVO,
        "fraud_probabilities": FSP_JAY,
    },
    uuid.UUID("00000000-0000-0000-0000-000000000100"): {
        "name": "GNU",
        "generator": pub_gnu,
        "campaign_id": CAMPAIGN_BRAVO,
        "fraud_probabilities": FSP_GNU,
    },
}
