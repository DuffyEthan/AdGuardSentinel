"""
Time-Series Data Generator

Generates synthetic advertising metrics one time interval at a time
and writes them to the raw_metrics hypertable continuously.

Adds: campaign_id feature.

Parameter justification:

CTR and conversion assumptions derived from industry benchmarks:

- WordStream (Google Ads Benchmarks):
  https://www.wordstream.com/blog/ws/google-ads-benchmarks

- HubSpot Conversion Benchmarks:
  https://blog.hubspot.com/marketing/average-conversion-rate

Typical ranges:
- CTR: 3-6% (search), 0.5-1% (display)
- Conversion rate: 2-10%

This generator assumes ~5% CTR and ~8% conversion rate,
which fall within published benchmark ranges.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db.models import Campaign, Publishers, RawMetrics

load_dotenv()


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration for synthetic metric generation."""

    interval_minutes: int = 5
    anomaly_duration_intervals: int = 12  # ~1 hour at 5-minute intervals

    # Baseline mean event rates per interval (Poisson lambdas)
    impressions_lambda: int = 8000
    clicks_lambda: int = 420
    conversions_lambda: int = 35

    # Anomaly spike multiplier range (applied to impressions)
    spike_multiplier_min: int = 2
    spike_multiplier_max: int = 4

    # Feature window for weighted stats / rolling calculations
    feature_window: int = 250

    # Runtime controls
    run_forever: bool = True
    max_intervals: int = 1000  # only used if run_forever is False


DEFAULT_PUBLISHER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_CAMPAIGN_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def get_uuid_from_env(env_name: str, default: uuid.UUID) -> uuid.UUID:
    """Return UUID from env, falling back to default if missing or invalid."""
    value = os.getenv(env_name)

    if not value or not value.strip():
        return default

    try:
        return uuid.UUID(value.strip())
    except (ValueError, AttributeError):
        print(
            f"[time_series_data_generator] Invalid {env_name}={value!r}; "
            f"falling back to default {default}"
        )
        return default


def get_bool_from_env(env_name: str, default: bool) -> bool:
    """Parse boolean env var safely."""
    value = os.getenv(env_name)
    if not value or not value.strip():
        return default

    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}


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
    publisher_id: uuid.UUID = DEFAULT_PUBLISHER_ID,
) -> uuid.UUID:
    """Ensure a publisher exists to satisfy foreign key constraints."""
    existing = session.get(Publishers, publisher_id)
    if existing is None:
        session.add(
            Publishers(
                publisher_id=publisher_id,
                publisher_name="Test Publisher",
            )
        )
        session.flush()
    return publisher_id


def ensure_campaign_exists(
    session: Session,
    campaign_id: uuid.UUID = DEFAULT_CAMPAIGN_ID,
    publisher_id: uuid.UUID = DEFAULT_PUBLISHER_ID,
) -> uuid.UUID:
    """Ensure a campaign exists to satisfy foreign key constraints."""
    existing = session.get(Campaign, campaign_id)
    if existing is None:
        session.add(
            Campaign(
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


def build_anomaly_schedule(
    config: GeneratorConfig,
    random_generator: np.random.Generator,
    total_intervals: int,
) -> tuple[int, int, int]:
    """
    Build one anomaly window for the run.

    Returns:
        (anomaly_start_index, anomaly_end_index_exclusive, spike_multiplier)
    """
    anomaly_window_size = min(config.anomaly_duration_intervals, total_intervals)
    anomaly_start_index = int(
        random_generator.integers(0, total_intervals - anomaly_window_size + 1)
    )
    anomaly_end_index = anomaly_start_index + anomaly_window_size
    spike_multiplier = int(
        random_generator.integers(
            config.spike_multiplier_min,
            config.spike_multiplier_max + 1,
        )
    )
    return anomaly_start_index, anomaly_end_index, spike_multiplier


def generate_time_series_point(
    config: GeneratorConfig,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    bucket_timestamp: datetime,
    random_generator: np.random.Generator,
    apply_anomaly: bool = False,
    spike_multiplier: int = 1,
) -> pd.DataFrame:
    """Generate one synthetic row for a single interval."""
    impressions = int(random_generator.poisson(lam=config.impressions_lambda))
    clicks = int(random_generator.poisson(lam=config.clicks_lambda))
    conversions = int(random_generator.poisson(lam=config.conversions_lambda))

    if apply_anomaly:
        impressions *= spike_multiplier

    return pd.DataFrame(
        [
            {
                "bucket_timestamp": bucket_timestamp,
                "publisher_id": publisher_id,
                "campaign_id": campaign_id,
                "impression_count": impressions,
                "click_count": clicks,
                "conversion_count": conversions,
            }
        ]
    )


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


def fetch_raw_metrics_from_db(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    limit: int = 1000,
) -> pd.DataFrame:
    """Fetch recent rows for a publisher + campaign."""
    rows = (
        session.query(RawMetrics)
        .filter(
            RawMetrics.publisher_id == publisher_id,
            RawMetrics.campaign_id == campaign_id,
        )
        .order_by(RawMetrics.bucket_timestamp)
        .limit(limit)
        .all()
    )

    if not rows:
        return pd.DataFrame(
            columns=[
                "bucket_timestamp",
                "publisher_id",
                "campaign_id",
                "impression_count",
                "click_count",
                "conversion_count",
            ]
        )

    df = pd.DataFrame(
        [
            {
                "bucket_timestamp": r.bucket_timestamp,
                "publisher_id": r.publisher_id,
                "campaign_id": r.campaign_id,
                "impression_count": r.impression_count,
                "click_count": r.click_count,
                "conversion_count": r.conversion_count,
            }
            for r in rows
        ]
    )
    df["bucket_timestamp"] = pd.to_datetime(df["bucket_timestamp"], utc=True)
    return df


def plot_metrics(
    df: pd.DataFrame,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> None:
    """Plot impression/click/conversion counts."""
    if df.empty:
        print(
            f"No data found for publisher_id={publisher_id}, campaign_id={campaign_id}."
        )
        return

    plt.figure()
    plt.plot(df["bucket_timestamp"], df["impression_count"], label="impressions")
    plt.plot(df["bucket_timestamp"], df["click_count"], label="clicks")
    plt.plot(df["bucket_timestamp"], df["conversion_count"], label="conversions")

    plt.title(
        f"Raw Metrics Over Time (publisher_id={publisher_id}, campaign_id={campaign_id})"
    )
    plt.xlabel("bucket_timestamp")
    plt.ylabel("count")

    ax = plt.gca()
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    plt.xticks(rotation=0)

    plt.legend()
    plt.tight_layout()
    plt.show()


def _weighted_stats(
    values: np.ndarray,
    weights: np.ndarray,
) -> tuple[float, float, float]:
    """Return weighted mean, variance, std."""
    wsum = float(np.sum(weights))
    if wsum <= 0:
        return float("nan"), float("nan"), float("nan")

    mean = float(np.sum(weights * values) / wsum)
    var = float(np.sum(weights * (values - mean) ** 2) / wsum)
    std = float(np.sqrt(var))
    return mean, var, std


def add_isoforest_features(
    df: pd.DataFrame,
    window: int = 250,
    eps: float = 1e-9,
) -> pd.DataFrame:
    """
    Adds:
      - Weighted mean/variance/std of impressions over last `window` rows
      - Poisson rolling rate
      - Log-likelihood ratio
      - Impression->conversion rate
      - Click wastage rate
      - Impression bursts
    """
    if df.empty:
        return df.copy()

    out = df.sort_values("bucket_timestamp").reset_index(drop=True).copy()

    imp = out["impression_count"].astype(float).to_numpy()

    rolling_lambda = (
        out["impression_count"]
        .rolling(window=window, min_periods=max(5, window // 10))
        .mean()
        .astype(float)
    )
    out["poisson_rolling_rate"] = rolling_lambda

    out["imp_to_conv_rate"] = out["conversion_count"] / (out["impression_count"] + eps)

    out["click_wastage_rate"] = (out["click_count"] - out["conversion_count"]) / (
        out["click_count"] + eps
    )

    rolling_max_imp = (
        out["impression_count"]
        .rolling(window=window, min_periods=max(5, window // 10))
        .max()
    )
    rolling_mean_imp = (
        out["impression_count"]
        .rolling(window=window, min_periods=max(5, window // 10))
        .mean()
    )
    out["impression_bursts"] = rolling_max_imp / (rolling_mean_imp + eps)

    baseline_lambda = out["impression_count"].expanding(min_periods=10).mean()

    x = out["impression_count"].astype(float)
    lam_t = rolling_lambda.fillna(baseline_lambda).clip(lower=eps)
    lam_b = baseline_lambda.clip(lower=eps)
    out["log_likelihood_ratio"] = (x * np.log(lam_t) - lam_t) - (
        x * np.log(lam_b) - lam_b
    )

    w_mean = np.full(len(out), np.nan, dtype=float)
    w_var = np.full(len(out), np.nan, dtype=float)
    w_std = np.full(len(out), np.nan, dtype=float)

    for i in range(len(out)):
        start = max(0, i - window + 1)
        segment = imp[start : i + 1]
        k = len(segment)
        if k < max(5, window // 10):
            continue
        weights = np.arange(1, k + 1, dtype=float)
        mean, var, std = _weighted_stats(segment, weights)
        w_mean[i] = mean
        w_var[i] = var
        w_std[i] = std

    out["mean_weighted"] = w_mean
    out["variance_weighted"] = w_var
    out["std_weighted"] = w_std

    return out


def main() -> None:
    config = GeneratorConfig()

    seed_env = os.getenv("RANDOM_SEED")
    seed = int(seed_env) if seed_env and seed_env.strip() else int(time.time_ns())
    print(f"[time_series_data_generator] seed={seed}")
    rng = np.random.default_rng(seed)

    publisher_id = get_uuid_from_env("PUBLISHER_ID", DEFAULT_PUBLISHER_ID)
    campaign_id = get_uuid_from_env("CAMPAIGN_ID", DEFAULT_CAMPAIGN_ID)

    run_forever = get_bool_from_env("RUN_FOREVER", config.run_forever)
    max_intervals = get_int_from_env("MAX_INTERVALS", config.max_intervals)

    assert SessionLocal is not None, (
        "DATABASE_URL is not configured; cannot create a session."
    )

    session = SessionLocal()
    try:
        ensure_publisher_exists(session, publisher_id)
        ensure_campaign_exists(session, campaign_id, publisher_id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    start_timestamp = get_aligned_start_timestamp(config.interval_minutes)
    print(
        f"Starting time-series generation at {start_timestamp.isoformat()} "
        f"with interval={config.interval_minutes} minutes"
    )

    interval_index = 0

    if run_forever:
        anomaly_start_index = None
        anomaly_end_index = None
        spike_multiplier = None
    else:
        (
            anomaly_start_index,
            anomaly_end_index,
            spike_multiplier,
        ) = build_anomaly_schedule(config, rng, max_intervals)
        print(
            f"Scheduled anomaly from interval {anomaly_start_index} "
            f"to {anomaly_end_index - 1} with multiplier={spike_multiplier}"
        )

    current_timestamp = start_timestamp

    try:
        while True:
            if not run_forever and interval_index >= max_intervals:
                print(f"Completed {max_intervals} intervals.")
                break

            if run_forever and interval_index % 100 == 0:
                anomaly_start_index = interval_index + int(rng.integers(5, 30))
                anomaly_end_index = anomaly_start_index + config.anomaly_duration_intervals
                spike_multiplier = int(
                    rng.integers(
                        config.spike_multiplier_min,
                        config.spike_multiplier_max + 1,
                    )
                )

            apply_anomaly = (
                anomaly_start_index is not None
                and anomaly_end_index is not None
                and anomaly_start_index <= interval_index < anomaly_end_index
            )

            point_df = generate_time_series_point(
                config=config,
                publisher_id=publisher_id,
                campaign_id=campaign_id,
                bucket_timestamp=current_timestamp,
                random_generator=rng,
                apply_anomaly=apply_anomaly,
                spike_multiplier=spike_multiplier if spike_multiplier is not None else 1,
            )

            session = SessionLocal()
            try:
                affected_rows = upsert_raw_metrics(session, point_df)
                session.commit()

                row = point_df.iloc[0]
                print(
                    f"[{interval_index}] Upserted {affected_rows} row | "
                    f"ts={row['bucket_timestamp'].isoformat()} | "
                    f"impressions={row['impression_count']} | "
                    f"clicks={row['click_count']} | "
                    f"conversions={row['conversion_count']} | "
                    f"anomaly={apply_anomaly}"
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
                sleep_until(current_timestamp)

    except KeyboardInterrupt:
        print("Time-series generation stopped by user.")


if __name__ == "__main__":
    main()

    publisher_id = get_uuid_from_env("PUBLISHER_ID", DEFAULT_PUBLISHER_ID)
    campaign_id = get_uuid_from_env("CAMPAIGN_ID", DEFAULT_CAMPAIGN_ID)

    assert SessionLocal is not None, (
        "DATABASE_URL is not configured; cannot create a session."
    )

    session = SessionLocal()
    try:
        df_db = fetch_raw_metrics_from_db(
            session,
            publisher_id=publisher_id,
            campaign_id=campaign_id,
            limit=1000,
        )
    finally:
        session.close()

    plot_metrics(df_db, publisher_id=publisher_id, campaign_id=campaign_id)

    if not df_db.empty:
        features_df = add_isoforest_features(df_db, window=250)
        print(
            features_df.tail(3)[
                [
                    "bucket_timestamp",
                    "impression_count",
                    "poisson_rolling_rate",
                    "mean_weighted",
                    "std_weighted",
                    "log_likelihood_ratio",
                    "imp_to_conv_rate",
                    "click_wastage_rate",
                    "impression_bursts",
                ]
            ]
        )