"""
Batch Data Generator

Generates synthetic time-series advertising metrics and writes them
to the raw_metrics hypertable in batch form.

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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import psycopg

import matplotlib.pyplot as plt

@dataclass(frozen=True)
class GeneratorConfig:
    #Configuration for synthetic metric generation.
    interval_minutes: int = 5
    batch_size: int = 1000
    anomaly_duration_intervals: int = 12  # ~1 hour at 5-minute intervals

    # Baseline traffic parameters
    impressions_mean: float = 8000
    impressions_std: float = 1200
    clicks_mean: float = 420
    clicks_std: float = 70
    conversions_mean: float = 35
    conversions_std: float = 10

    # Anomaly spike multiplier range
    spike_multiplier_min: int = 2
    spike_multiplier_max: int = 4



def connect_db() -> psycopg.Connection:
    #Create a database connection using environment variables.#
    host = os.getenv("DB_HOST", "db")
    port = int(os.getenv("DB_PORT", "5432"))
    dbname = os.getenv("DB_NAME", "StreamlitDB")
    user = os.getenv("DB_USER", "postgres")

    print(f"[connect_db] host={host} port={port} dbname={dbname} user={user}")

    return psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=os.getenv("DB_PASSWORD", "123456789"),
    )


def ensure_publisher_exists(conn: psycopg.Connection, publisher_id: int = 1) -> int:
    #Ensure a publisher exists to satisfy foreign key constraints.
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
    #Align the start timestamp to the nearest interval boundary.
    current_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    aligned_minute = (current_time.minute // interval_minutes) * interval_minutes
    return current_time.replace(minute=aligned_minute)


def generate_time_series_batch(
    config: GeneratorConfig,
    publisher_id: int,
    start_timestamp: datetime,
    random_generator: np.random.Generator,
) -> pd.DataFrame:
    #Generate a synthetic batch of time-series metrics with one injected anomaly window.
    interval_delta = timedelta(minutes=config.interval_minutes)

    timestamps = [
        start_timestamp + i * interval_delta
        for i in range(config.batch_size)
    ]

    impressions = random_generator.normal(
        config.impressions_mean,
        config.impressions_std,
        config.batch_size,
    )
    clicks = random_generator.normal(
        config.clicks_mean,
        config.clicks_std,
        config.batch_size,
    )
    conversions = random_generator.normal(
        config.conversions_mean,
        config.conversions_std,
        config.batch_size,
    )

    impressions = np.clip(np.rint(impressions), 0, None).astype(int)
    clicks = np.clip(np.rint(clicks), 0, None).astype(int)
    conversions = np.clip(np.rint(conversions), 0, None).astype(int)

    anomaly_window_size = min(config.anomaly_duration_intervals, config.batch_size)
    anomaly_start_index = random_generator.integers(
        0, config.batch_size - anomaly_window_size + 1
    )
    anomaly_end_index = anomaly_start_index + anomaly_window_size

    spike_multiplier = random_generator.integers(
        config.spike_multiplier_min, config.spike_multiplier_max + 1
    )
    impressions[anomaly_start_index:anomaly_end_index] *= spike_multiplier

    return pd.DataFrame(
        {
            "bucket_timestamp": timestamps,
            "publisher_id": publisher_id,
            "impression_count": impressions,
            "click_count": clicks,
            "conversion_count": conversions,
        }
    )


def upsert_raw_metrics(conn: psycopg.Connection, data_frame: pd.DataFrame) -> int:
    #Insert or update a batch into raw_metrics (rerunnable via ON CONFLICT).
    rows = list(
        data_frame[
            ["bucket_timestamp", "publisher_id", "impression_count", "click_count", "conversion_count"]
        ].itertuples(index=False, name=None)
    )

    query = """
    INSERT INTO raw_metrics (
        bucket_timestamp, publisher_id, impression_count, click_count, conversion_count
    )
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (publisher_id, bucket_timestamp)
    DO UPDATE SET
        impression_count = EXCLUDED.impression_count,
        click_count = EXCLUDED.click_count,
        conversion_count = EXCLUDED.conversion_count;
    """

    with conn.cursor() as cur:
        cur.executemany(query, rows)

    conn.commit()
    return len(rows)


def main() -> None:
    #Entry point: generate a batch and write to the database.
    config = GeneratorConfig()
    random_generator = np.random.default_rng(123)
    publisher_id = int(os.getenv("PUBLISHER_ID", "1"))

    connection = connect_db()

    try:
        ensure_publisher_exists(connection, publisher_id)

        start_timestamp = get_aligned_start_timestamp(config.interval_minutes)
        batch_dataframe = generate_time_series_batch(
            config,
            publisher_id,
            start_timestamp,
            random_generator,
        )

        affected_rows = upsert_raw_metrics(connection, batch_dataframe)

        print(f"Upserted {affected_rows} rows into raw_metrics for publisher_id={publisher_id}")
        print(f"Start bucket_timestamp: {start_timestamp.isoformat()} | interval={config.interval_minutes}min")
    finally:
        connection.close()


if __name__ == "__main__":
    main()

conn = psycopg.connect(
    host="localhost",
    port=5433,
    dbname="StreamlitDB",
    user="postgres",
    password="123456789"
)

df = pd.read_sql(
    """
    SELECT bucket_timestamp, impression_count
    FROM raw_metrics
    WHERE publisher_id = 1
    ORDER BY bucket_timestamp
    """,
    conn
)

print(df.head())     
print(df.tail())

df.plot(x="bucket_timestamp", y="impression_count")
plt.show()
