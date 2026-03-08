"""Temporary seed script — run once inside the fastapi container, then delete."""
import uuid
from datetime import datetime, timezone

import numpy as np

from app.db import SessionLocal
from app.db.models import Campaign, Publishers
from app.ml.batch_data_generator import (
    GeneratorConfig,
    generate_time_series_batch,
    get_aligned_start_timestamp,
    upsert_raw_metrics,
)

PUBLISHERS = [
    ("SPY", uuid.UUID("00000000-0000-0000-0000-000000000010"), uuid.UUID("00000000-0000-0000-0000-000000000011")),
    ("CAT", uuid.UUID("00000000-0000-0000-0000-000000000020"), uuid.UUID("00000000-0000-0000-0000-000000000021")),
    ("DOG", uuid.UUID("00000000-0000-0000-0000-000000000030"), uuid.UUID("00000000-0000-0000-0000-000000000031")),
    ("OWL", uuid.UUID("00000000-0000-0000-0000-000000000040"), uuid.UUID("00000000-0000-0000-0000-000000000041")),
    ("FOX", uuid.UUID("00000000-0000-0000-0000-000000000050"), uuid.UUID("00000000-0000-0000-0000-000000000051")),
]

config = GeneratorConfig()  # batch_size=1000 by default
rng = np.random.default_rng(42)

assert SessionLocal is not None, "DATABASE_URL not configured"
session = SessionLocal()
try:
    for name, pub_id, camp_id in PUBLISHERS:
        if session.get(Publishers, pub_id) is None:
            session.add(Publishers(publisher_id=pub_id, publisher_name=name))
            session.flush()

        if session.get(Campaign, camp_id) is None:
            session.add(Campaign(
                campaign_id=camp_id,
                publisher_id=pub_id,
                start_date=datetime.now(timezone.utc),
            ))
            session.flush()

        start_ts = get_aligned_start_timestamp(config.interval_minutes)
        df = generate_time_series_batch(config, pub_id, camp_id, start_ts, rng)
        count = upsert_raw_metrics(session, df)
        print(f"{name}: upserted {count} rows (pub={pub_id})")

    session.commit()
    print("Done.")
except Exception:
    session.rollback()
    raise
finally:
    session.close()
