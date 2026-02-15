from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import ModelLogs, Publishers, RawMetrics


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
    pub1 = Publishers(publisher_id=1, publisher_name="Acme Ads")
    pub2 = Publishers(publisher_id=2, publisher_name="BrightMedia")
    db_session.add_all([pub1, pub2])
    db_session.flush()

    
    raw_rows: list[RawMetrics] = [] # raw_metrics for publisher 1, hours 00-05
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
                publisher_id=1,
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
                publisher_id=2,
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
        ("2026-01-01 00:00:00", "markov_v1", Decimal("0.10")),
        ("2026-01-01 01:00:00", "markov_v1", Decimal("0.15")),
        ("2026-01-01 02:00:00", "markov_v1", Decimal("0.80")),
        ("2026-01-01 03:00:00", "markov_v1", Decimal("0.75")),
        ("2026-01-01 04:00:00", "markov_v1", Decimal("0.20")),
        ("2026-01-01 05:00:00", "markov_v1", Decimal("0.12")),
    ]
    for ts, model, score in p1_scores:
        ml_rows.append(
            ModelLogs(
                timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
                publisher_id=1,
                model_name=model,
                score=score,
            )
        )

    # model_logs – publisher 2, hours 02-04 only (intentionally sparse)
    p2_scores = [
        ("2026-01-01 02:00:00", "markov_v1", Decimal("0.50")),
        ("2026-01-01 03:00:00", "markov_v1", Decimal("0.55")),
        ("2026-01-01 04:00:00", "markov_v1", Decimal("0.45")),
    ]
    for ts, model, score in p2_scores:
        ml_rows.append(
            ModelLogs(
                timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
                publisher_id=2,
                model_name=model,
                score=score,
            )
        )
    db_session.add_all(ml_rows)
    db_session.flush()

    return {
        "publishers": [pub1, pub2],
        "raw_metrics": raw_rows,
        "model_logs": ml_rows,
    }
