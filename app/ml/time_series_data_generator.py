"""
Time-Series Data Generator

Polls all publishers from app.ml.publishers each interval and writes
their output to the raw_metrics hypertable.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db.models import Campaigns, Publishers, RawMetrics
from app.ml.publishers import publisher_catalog

load_dotenv()


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration for the orchestration loop."""

    interval_minutes: int = 5
    run_forever: bool = False
    max_intervals: int = 5  # only used if run_forever is False


# Deterministic UUIDs derived from publisher names so DB rows are stable
# across restarts.
_PUB_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _pub_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(_PUB_NAMESPACE, f"pub:{name}")


def _campaign_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(_PUB_NAMESPACE, f"campaign:{name}")


def get_bool_from_env(env_name: str, default: bool) -> bool:
    """Parse boolean env var safely."""
    value = os.getenv(env_name)
    if not value or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_int_from_env(env_name: str, default: int) -> int:
    """Parse integer env var safely."""
    value = os.getenv(env_name)
    if not value or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        print(
            f"[time_series_data_generator] Invalid {env_name}={value!r}; "
            f"falling back to default {default}"
        )
        return default


def ensure_publisher_exists(
    session: Session,
    publisher_id: uuid.UUID,
    publisher_name: str = "Test Publisher",
) -> uuid.UUID:
    """Ensure a publisher exists to satisfy foreign key constraints."""
    existing = session.get(Publishers, publisher_id)
    if existing is None:
        session.add(
            Publishers(
                publisher_id=publisher_id,
                publisher_name=publisher_name,
            )
        )
        session.flush()
    return publisher_id


def ensure_campaign_exists(
    session: Session,
    campaign_id: uuid.UUID,
    publisher_id: uuid.UUID,
) -> uuid.UUID:
    """Ensure a campaign exists to satisfy foreign key constraints."""
    existing = session.get(Campaigns, campaign_id)
    if existing is None:
        session.add(
            Campaigns(
                campaign_id=campaign_id,
                publisher_id=publisher_id,
                start_date=datetime.now(timezone.utc),
            )
        )
        session.flush()
    return campaign_id


def get_aligned_start_timestamp(interval_minutes: int) -> datetime:
    """Align timestamp to the nearest interval boundary."""
    current_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    aligned_minute = (current_time.minute // interval_minutes) * interval_minutes
    return current_time.replace(minute=aligned_minute)


def get_next_bucket_timestamp(
    previous_timestamp: datetime,
    interval_minutes: int,
) -> datetime:
    """Return next bucket timestamp."""
    return previous_timestamp + timedelta(minutes=interval_minutes)


def sleep_until(target_timestamp: datetime) -> None:
    """Sleep until the target UTC timestamp."""
    while True:
        now = datetime.now(timezone.utc)
        remaining = (target_timestamp - now).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(remaining, 1.0))


def upsert_raw_metrics(session: Session, data_frame: pd.DataFrame) -> int:
    """Insert or update rows into raw_metrics."""
    rows = [
        {
            "bucket_timestamp": row.bucket_timestamp,
            "publisher_id": row.publisher_id,
            "campaign_id": row.campaign_id,
            "impression_count": int(row.impression_count),
            "click_count": int(row.click_count),
            "conversion_count": int(row.conversion_count),
        }
        for row in data_frame.itertuples(index=False)
    ]

    if not rows:
        return 0

    stmt = insert(RawMetrics).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="raw_metrics_pkey",
        set_={
            "impression_count": stmt.excluded.impression_count,
            "click_count": stmt.excluded.click_count,
            "conversion_count": stmt.excluded.conversion_count,
        },
    )
    session.execute(stmt)
    session.flush()
    return len(rows)


def main() -> None:
    config = GeneratorConfig()

    run_forever = get_bool_from_env("RUN_FOREVER", config.run_forever)
    max_intervals = get_int_from_env("MAX_INTERVALS", config.max_intervals)

    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured; cannot create a session.")

    # Build (generator, publisher_uuid, campaign_uuid) for every publisher.
    publishers = {
        name: (gen, _pub_uuid(name), _campaign_uuid(name))
        for name, gen in publisher_catalog.items()
    }

    # Bootstrap DB rows for all publishers/campaigns once before the loop.
    session = SessionLocal()
    try:
        for name, (_, pub_id, camp_id) in publishers.items():
            ensure_publisher_exists(session, pub_id, publisher_name=name)
            ensure_campaign_exists(session, camp_id, pub_id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    start_timestamp = get_aligned_start_timestamp(config.interval_minutes)
    print(
        f"Starting time-series generation at {start_timestamp.isoformat()} "
        f"with interval={config.interval_minutes} minutes | "
        f"publishers={list(publishers.keys())}"
    )

    interval_index = 0
    current_timestamp = start_timestamp

    try:
        while True:
            if not run_forever and interval_index >= max_intervals:
                print(f"Completed {max_intervals} intervals.")
                break

            session = SessionLocal()
            try:
                for name, (gen, pub_id, camp_id) in publishers.items():
                    _, impressions, clicks, conversions = gen.publisher_data_next({})
                    point_df = pd.DataFrame(
                        [
                            {
                                "bucket_timestamp": current_timestamp,
                                "publisher_id": pub_id,
                                "campaign_id": camp_id,
                                "impression_count": impressions,
                                "click_count": clicks,
                                "conversion_count": conversions,
                            }
                        ]
                    )
                    upsert_raw_metrics(session, point_df)
                session.commit()
                print(
                    f"[{interval_index}] ts={current_timestamp.isoformat()} | "
                    f"upserted {len(publishers)} rows"
                )
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

            interval_index += 1
            current_timestamp = get_next_bucket_timestamp(
                current_timestamp,
                config.interval_minutes,
            )

            if run_forever:
                time.sleep(5)
                # sleep_until(current_timestamp)

    except KeyboardInterrupt:
        print("Time-series generation stopped by user.")


if __name__ == "__main__":
    main()
