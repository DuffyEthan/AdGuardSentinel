import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Campaigns, DerivedMetrics, ModelLogs, Publishers, RawMetrics

# Fixed UUIDs for deterministic test data
PUB1_ID = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
PUB2_ID = uuid.UUID("b1ffcd00-ad1c-5f09-cc7e-7ccace491b22")
CAMP1_ID = uuid.UUID("c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33")
CAMP2_ID = uuid.UUID("d3bbef22-cf3e-7b2b-ee90-9eece06b3d44")


def _get_database_url() -> str:
    from pathlib import Path
    from dotenv import load_dotenv
    import os

    env_path = Path(__file__).resolve().parents[1] / "db" / ".env"
    load_dotenv(env_path)
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set – is db/.env present?")
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture()
def db_session():
    # session wrapped in a transaction that rolls back after each test
    engine = create_engine(_get_database_url(), pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture()
def seed_data(db_session: Session) -> dict:
    pub1 = Publishers(publisher_id=PUB1_ID, publisher_name="Acme Ads")
    pub2 = Publishers(publisher_id=PUB2_ID, publisher_name="BrightMedia")
    db_session.add_all([pub1, pub2])
    db_session.flush()

    camp1 = Campaigns(
        campaign_id=CAMP1_ID,
        publisher_id=PUB1_ID,
        start_date=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    camp2 = Campaigns(
        campaign_id=CAMP2_ID,
        publisher_id=PUB2_ID,
        start_date=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([camp1, camp2])
    db_session.flush()

    raw_rows: list[RawMetrics] = []  # raw_metrics for publisher 1, hours 00-05
    p1_data = [
        ("2026-01-01 00:00:00", 120, 8, 2),
        ("2026-01-01 01:00:00", 135, 9, 3),
        ("2026-01-01 02:00:00", 110, 10, 1),
        ("2026-01-01 03:00:00", 98, 8, 2),
        ("2026-01-01 04:00:00", 102, 9, 1),
        ("2026-01-01 05:00:00", 88, 7, 1),
    ]
    for ts, imp, clk, conv in p1_data:
        raw_rows.append(
            RawMetrics(
                bucket_timestamp=datetime.fromisoformat(ts).replace(
                    tzinfo=timezone.utc
                ),
                publisher_id=PUB1_ID,
                campaign_id=CAMP1_ID,
                impression_count=imp,
                click_count=clk,
                conversion_count=conv,
            )
        )

    # raw_metrics publisher 2, hours 00-05
    p2_data = [
        ("2026-01-01 00:00:00", 80, 5, 1),
        ("2026-01-01 01:00:00", 75, 4, 1),
        ("2026-01-01 02:00:00", 60, 3, 0),
        ("2026-01-01 03:00:00", 55, 3, 0),
        ("2026-01-01 04:00:00", 50, 2, 0),
        ("2026-01-01 05:00:00", 48, 2, 0),
    ]
    for ts, imp, clk, conv in p2_data:
        raw_rows.append(
            RawMetrics(
                bucket_timestamp=datetime.fromisoformat(ts).replace(
                    tzinfo=timezone.utc
                ),
                publisher_id=PUB2_ID,
                campaign_id=CAMP2_ID,
                impression_count=imp,
                click_count=clk,
                conversion_count=conv,
            )
        )
    db_session.add_all(raw_rows)
    db_session.flush()

    # model_logs publisher 1, hours 00-05
    ml_rows: list[ModelLogs] = []
    p1_scores = [
        ("2026-01-01 00:00:00", "markov_v1", Decimal("0.10"), "fraud_type_1"),
        ("2026-01-01 01:00:00", "markov_v1", Decimal("0.15"), "fraud_type_2"),
        ("2026-01-01 02:00:00", "markov_v1", Decimal("0.80"), "fraud_type_3"),
        ("2026-01-01 03:00:00", "markov_v1", Decimal("0.75"), "fraud_type_4"),
        ("2026-01-01 04:00:00", "markov_v1", Decimal("0.20"), "fraud_type_5"),
        ("2026-01-01 05:00:00", "markov_v1", Decimal("0.12"), "fraud_type_6"),
    ]
    for ts, model, score, fraud_type in p1_scores:
        ml_rows.append(
            ModelLogs(
                log_timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
                publisher_id=PUB1_ID,
                model_name=model,
                fraud_type=fraud_type,
                score=score,
            )
        )

    # model_logs – publisher 2, hours 02-04 only (intentionally sparse)
    p2_scores = [
        ("2026-01-01 02:00:00", "markov_v1", Decimal("0.50"), "unknown"),
        ("2026-01-01 03:00:00", "markov_v1", Decimal("0.55"), "unknown"),
        ("2026-01-01 04:00:00", "markov_v1", Decimal("0.45"), "unknown"),
    ]
    for ts, model, score, fraud_type in p2_scores:
        ml_rows.append(
            ModelLogs(
                log_timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
                publisher_id=PUB2_ID,
                model_name=model,
                score=score,
                fraud_type=fraud_type,
            )
        )
    db_session.add_all(ml_rows)
    db_session.flush()

    # derived_metrics for publisher 1, hours 03-05
    derived_rows: list[DerivedMetrics] = []
    p1_derived = [
        ("2026-01-01 03:00:00", 110.5, 8.5, 1.8, 12.0, 1.1, 0.7, 112.0, 8.8, 2.0, 4),
        ("2026-01-01 04:00:00", 111.0, 8.7, 1.9, 11.5, 1.0, 0.8, 113.5, 9.0, 2.1, 5),
        ("2026-01-01 05:00:00", 108.0, 8.4, 1.7, 13.0, 1.2, 0.9, 110.0, 8.6, 1.9, 6),
    ]
    for (
        ts,
        imp_m,
        clk_m,
        conv_m,
        imp_s,
        clk_s,
        conv_s,
        imp_wm,
        clk_wm,
        conv_wm,
        ss,
    ) in p1_derived:
        derived_rows.append(
            DerivedMetrics(
                bucket_timestamp=datetime.fromisoformat(ts).replace(
                    tzinfo=timezone.utc
                ),
                publisher_id=PUB1_ID,
                campaign_id=CAMP1_ID,
                impressions_mean=imp_m,
                clicks_mean=clk_m,
                conversions_mean=conv_m,
                impressions_std=imp_s,
                clicks_std=clk_s,
                conversions_std=conv_s,
                impressions_weighted_mean=imp_wm,
                clicks_weighted_mean=clk_wm,
                conversions_weighted_mean=conv_wm,
                sample_size=ss,
            )
        )
    db_session.add_all(derived_rows)
    db_session.flush()

    return {
        "publishers": [pub1, pub2],
        "campaigns": [camp1, camp2],
        "raw_metrics": raw_rows,
        "model_logs": ml_rows,
        "derived_metrics": derived_rows,
    }
