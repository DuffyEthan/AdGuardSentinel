"""
Batch Data Generator

Generates synthetic time-series advertising metrics and writes them
to the raw_metrics hypertable in batch form.

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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import psycopg

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration for synthetic metric generation."""
    interval_minutes: int = 5
    batch_size: int = 1000
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


def connect_db() -> psycopg.Connection:
    """Create a database connection using environment variables."""
    host = os.getenv("DB_HOST", "db")
    port = int(os.getenv("DB_PORT", "5432"))
    dbname = os.getenv("DB_NAME", "StreamlitDB")
    user = os.getenv("DB_USER", "postgres")

    return psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=os.getenv("DB_PASSWORD", "123456789"),
    )


def ensure_publisher_exists(conn: psycopg.Connection, publisher_id: int = 1) -> int:
    """Ensure a publisher exists to satisfy foreign key constraints (if any)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO publishers (publisher_id, publisher_name)
            VALUES (%s, %s)
            ON CONFLICT (publisher_id) DO NOTHING
            """,
            (publisher_id, "Test Publisher"),
        )
    conn.commit()
    return publisher_id


def get_aligned_start_timestamp(interval_minutes: int) -> datetime:
    """Align the start timestamp to the nearest interval boundary."""
    current_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    aligned_minute = (current_time.minute // interval_minutes) * interval_minutes
    return current_time.replace(minute=aligned_minute)


def generate_time_series_batch(
    config: GeneratorConfig,
    publisher_id: int,
    campaign_id: int,
    start_timestamp: datetime,
    random_generator: np.random.Generator,
) -> pd.DataFrame:
    """Generate a synthetic batch of time-series metrics with one injected anomaly window."""
    interval_delta = timedelta(minutes=config.interval_minutes)

    timestamps = [start_timestamp + i * interval_delta for i in range(config.batch_size)]

    impressions = random_generator.poisson(lam=config.impressions_lambda, size=config.batch_size)
    clicks = random_generator.poisson(lam=config.clicks_lambda, size=config.batch_size)
    conversions = random_generator.poisson(lam=config.conversions_lambda, size=config.batch_size)

    # Inject anomaly: spike impressions over a contiguous window
    anomaly_window_size = min(config.anomaly_duration_intervals, config.batch_size)
    anomaly_start_index = random_generator.integers(0, config.batch_size - anomaly_window_size + 1)
    anomaly_end_index = anomaly_start_index + anomaly_window_size

    spike_multiplier = random_generator.integers(config.spike_multiplier_min, config.spike_multiplier_max + 1)
    impressions[anomaly_start_index:anomaly_end_index] *= spike_multiplier

    return pd.DataFrame(
        {
            "bucket_timestamp": timestamps,
            "publisher_id": publisher_id,
            "campaign_id": campaign_id,
            "impression_count": impressions.astype(int),
            "click_count": clicks.astype(int),
            "conversion_count": conversions.astype(int),
        }
    )


def upsert_raw_metrics(conn: psycopg.Connection, data_frame: pd.DataFrame) -> int:
    """Insert or update a batch into raw_metrics (rerunnable via ON CONFLICT)."""
    rows = list(
        data_frame[
            [
                "bucket_timestamp",
                "publisher_id",
                "campaign_id",
                "impression_count",
                "click_count",
                "conversion_count",
            ]
        ].itertuples(index=False, name=None)
    )

    # IMPORTANT:
    # This assumes your unique constraint is: (publisher_id, campaign_id, bucket_timestamp)
    query = """
    INSERT INTO raw_metrics (
        bucket_timestamp, publisher_id, campaign_id, impression_count, click_count, conversion_count
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (publisher_id, campaign_id, bucket_timestamp)
    DO UPDATE SET
        impression_count = EXCLUDED.impression_count,
        click_count = EXCLUDED.click_count,
        conversion_count = EXCLUDED.conversion_count;
    """

    with conn.cursor() as cur:
        cur.executemany(query, rows)

    conn.commit()
    return len(rows)


def fetch_raw_metrics_from_db(
    publisher_id: int,
    campaign_id: int,
    limit: int = 1000,
) -> pd.DataFrame:
    """Fetch recent rows for a publisher + campaign."""
    conn = connect_db()
    try:
        df = pd.read_sql(
            """
            SELECT bucket_timestamp, publisher_id, campaign_id,
                   impression_count, click_count, conversion_count
            FROM raw_metrics
            WHERE publisher_id = %s AND campaign_id = %s
            ORDER BY bucket_timestamp
            LIMIT %s
            """,
            conn,
            params=(publisher_id, campaign_id, limit),
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df["bucket_timestamp"] = pd.to_datetime(df["bucket_timestamp"], utc=True)
    return df


def plot_metrics(
    df: pd.DataFrame,
    publisher_id: int,
    campaign_id: int,
) -> None:
    """Plot impression/click/conversion counts."""
    if df.empty:
        print(f"No data found for publisher_id={publisher_id}, campaign_id={campaign_id}.")
        return

    plt.figure()
    plt.plot(df["bucket_timestamp"], df["impression_count"], label="impressions")
    plt.plot(df["bucket_timestamp"], df["click_count"], label="clicks")
    plt.plot(df["bucket_timestamp"], df["conversion_count"], label="conversions")

    plt.title(f"Raw Metrics Over Time (publisher_id={publisher_id}, campaign_id={campaign_id})")
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


# ---------------------------
# Isolation Forest features
# ---------------------------

def _weighted_stats(values: np.ndarray, weights: np.ndarray) -> tuple[float, float, float]:
    """Return weighted mean, variance, std. Assumes 1D arrays, weights >= 0."""
    wsum = float(np.sum(weights))
    if wsum <= 0:
        return (float("nan"), float("nan"), float("nan"))

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
      - Weighted mean/variance/std of impressions over last `window` rows (newer rows weighted more)
      - Poisson rolling rate (rolling mean impressions)
      - Log-likelihood ratio (Poisson approx: compare point x to rolling lambda)
      - Impression->conversion rate
      - Click wastage rate = (clicks - conversions) / clicks
      - Impression bursts = max(impressions in window) / mean(impressions in window)
    """
    if df.empty:
        return df.copy()

    out = df.sort_values("bucket_timestamp").reset_index(drop=True).copy()

    # Safe float versions
    imp = out["impression_count"].astype(float).to_numpy()
    clk = out["click_count"].astype(float).to_numpy()
    conv = out["conversion_count"].astype(float).to_numpy()

    # Rolling Poisson rate (lambda) as rolling mean
    rolling_lambda = (
        out["impression_count"]
        .rolling(window=window, min_periods=max(5, window // 10))
        .mean()
        .astype(float)
    )
    out["poisson_rolling_rate"] = rolling_lambda

    # Impression->conversion rate
    out["imp_to_conv_rate"] = out["conversion_count"] / (out["impression_count"] + eps)

    # Click wastage rate: (clicks - conversions)/clicks
    out["click_wastage_rate"] = (out["click_count"] - out["conversion_count"]) / (out["click_count"] + eps)

    # Impression bursts: rolling max / rolling mean
    rolling_max_imp = out["impression_count"].rolling(window=window, min_periods=max(5, window // 10)).max()
    rolling_mean_imp = out["impression_count"].rolling(window=window, min_periods=max(5, window // 10)).mean()
    out["impression_bursts"] = rolling_max_imp / (rolling_mean_imp + eps)

    # Log-likelihood ratio (Poisson-ish):
    # LLR ~ log P(x | lambda_t) - log P(x | lambda_baseline)
    # Here baseline = expanding mean (or could be long rolling mean)
    baseline_lambda = out["impression_count"].expanding(min_periods=10).mean()

    # Poisson log PMF (up to constant -log(x!)) approximation:
    # log P(x|λ) = x log λ - λ - log(x!)
    # When comparing two λs for same x, the -log(x!) cancels.
    x = out["impression_count"].astype(float)
    lam_t = rolling_lambda.fillna(baseline_lambda).clip(lower=eps)
    lam_b = baseline_lambda.clip(lower=eps)
    out["log_likelihood_ratio"] = (x * np.log(lam_t) - lam_t) - (x * np.log(lam_b) - lam_b)

    # Weighted mean/var/std over rolling window with newer rows weighted more:
    # weights = 1..k within window (older=1, newest=k)
    w_mean = np.full(len(out), np.nan, dtype=float)
    w_var = np.full(len(out), np.nan, dtype=float)
    w_std = np.full(len(out), np.nan, dtype=float)

    for i in range(len(out)):
        start = max(0, i - window + 1)
        segment = imp[start : i + 1]
        k = len(segment)
        if k < max(5, window // 10):
            continue
        weights = np.arange(1, k + 1, dtype=float)  # newer gets bigger weight
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
    print(f"[batch_data_generator] seed={seed}")
    rng = np.random.default_rng(seed)

    publisher_id = int(os.getenv("PUBLISHER_ID", "1"))
    campaign_id = int(os.getenv("CAMPAIGN_ID", "1"))

    connection = connect_db()
    try:
        ensure_publisher_exists(connection, publisher_id)

        start_timestamp = datetime.now(timezone.utc)

        batch_df = generate_time_series_batch(
            config=config,
            publisher_id=publisher_id,
            campaign_id=campaign_id,
            start_timestamp=start_timestamp,
            random_generator=rng,
        )

        affected_rows = upsert_raw_metrics(connection, batch_df)

        print(f"Upserted {affected_rows} rows into raw_metrics for publisher_id={publisher_id}, campaign_id={campaign_id}")
        print(f"Start bucket_timestamp: {start_timestamp.isoformat()} | interval={config.interval_minutes}min")
    finally:
        connection.close()


if __name__ == "__main__":
    main()

    pub = int(os.getenv("PUBLISHER_ID", "1"))
    camp = int(os.getenv("CAMPAIGN_ID", "1"))

    df_db = fetch_raw_metrics_from_db(publisher_id=pub, campaign_id=camp, limit=1000)
    plot_metrics(df_db, publisher_id=pub, campaign_id=camp)

    # Optional: generate features for Isolation Forest input
    if not df_db.empty:
        features_df = add_isoforest_features(df_db, window=250)
        print(features_df.tail(3)[
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
        ])