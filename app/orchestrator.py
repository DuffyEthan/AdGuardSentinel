"""
Backend orchestration loop.

Run as a standalone process:
    python -m app.orchestrator

Each tick simulates one 5-minute data bucket:

  1. DATA GEN    – call publisher_data_next() for every publisher in the
                   catalog and upsert the resulting row into raw_metrics.
  2. DERIVED     – recompute derived_metrics for every publisher/campaign
                   (IQR-filtered mean/std/weighted-mean over the last 250 rows).
  3. ML INFERENCE– every N ticks, run 3 pre-trained fraud-detection models
                   (CTR fraud, impression fraud, click injection) on a rolling
                   window of raw_metrics, combine scores, and write to
                   model_logs.  Then update anomaly_periods incrementally.
  4. EXTRAS      – an extensible list of additional step callables that
                   receive (session, publisher_id, campaign_id, sim_time).

The API layer (FastAPI / uvicorn) runs as a **separate** process and
reads the same database; there is no direct communication between
the orchestrator and the API server.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from sqlalchemy import text

from app.db import SessionLocal, engine
from app.db.models import Base, Campaigns, Publishers
from app.fastapi.services.anomaly_periods_service import process_new_log
from app.fastapi.services.derived_metrics_service import compute_and_store
from app.ml._isolation_forest import *
from app.ml.time_series_data_generator import upsert_raw_metrics
from app.ml.publishers import campaign_catalog, publisher_catalog
from app.repositories.derived_metrics_repository import DerivedMetricsRepository
from app.repositories.model_logs_repository import ModelLogsRepository
from app.repositories.raw_metrics_repository import RawMetricsRepository

logger = logging.getLogger("orchestrator")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TICK_INTERVAL_SECONDS: float = 2.0
"""Wall-clock seconds between ticks."""

SIMULATED_INTERVAL_MINUTES: int = 5
"""Each tick advances the simulated clock by this many minutes."""

ML_INFERENCE_EVERY_N_TICKS: int = 50
"""Run ML inference once every N ticks."""

ML_WINDOW_SIZE: int = 250
"""Number of most-recent raw_metrics rows fed to the models."""

ML_MIN_ROWS: int = 100
"""Minimum rows required before inference is attempted."""

WARMUP_TICKS: int = 100
"""Number of ticks to run instantly at startup (no sleep) to pre-seed data."""

MODEL_PATHS: dict[str, str] = {
    "ctr_fraud": "app/ml/models/ctr_fraud_detector_v2.joblib",
    "impression_fraud": "app/ml/models/impression_fraud_detector_v2.joblib",
    "click_injection": "app/ml/models/click_injection_detector_v2.joblib",
}
"""Paths to the 3 pre-trained fraud-detection model files."""

FEATURE_SETS: dict[str, list[str]] = {
    "ctr_fraud": [
        "ctr",
        "ctr_rolling_mean",
        "ctr_rolling_std",
        "ctr_deviation",
    ],
    "impression_fraud": [
        "impression_count",
        "impression_ratio",
        "impression_velocity",
        "impression_spike_ratio",
        "impression_volatility",
        "abnormal_volume",
    ],
    "click_injection": [
        "cvr",
        "cvr_spike_ratio",
        "suspicious_cvr",
        "conversion_clustering",
    ],
}
"""Feature columns required by each model."""

MODEL_NAME: str = "multi_model_v2"
"""Model name written into model_logs.model_name."""

# Type alias for extensible extra-step callables.
StepCallable = Callable[[Session, uuid.UUID, uuid.UUID, datetime], None]

# Extra pipeline steps can be appended here. Each callable receives
# (session, publisher_id, campaign_id, current_sim_time).
extra_steps: list[StepCallable] = []


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def step_generate_data(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    generator: Any,
    current_sim_time: datetime,
) -> int:
    """Generate one data row for a single publisher and upsert to raw_metrics.

    Returns the number of rows written (always 1 on success).
    """
    settings: dict[str, Any] = {}
    _timestamp, impressions, clicks, conversions = generator.publisher_data_next(
        settings,
    )

    # Build a single-row DataFrame compatible with upsert_raw_metrics().
    row_df = pd.DataFrame(
        [
            {
                "bucket_timestamp": current_sim_time,
                "publisher_id": publisher_id,
                "campaign_id": campaign_id,
                "impression_count": int(impressions),
                "click_count": int(clicks),
                "conversion_count": int(conversions),
            }
        ]
    )
    return upsert_raw_metrics(session, row_df)


def step_derived_metrics(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_sim_time: datetime,
) -> bool:
    """Recompute derived metrics for one publisher/campaign.

    Returns True if a DerivedMetrics row was produced, False if there was
    insufficient data.
    """
    result = compute_and_store(session, publisher_id, campaign_id, current_sim_time)
    return result is not None


def _determine_fraud_type(
    per_model_scores: dict[str, np.ndarray],
    anomaly_scores: np.ndarray,
    threshold: float = 0.5,
) -> list[str]:
    """Determine the primary fraud type for each row.

    For rows where anomaly_score < threshold, the fraud type is ``"none"``.
    For anomalous rows, the fraud type is the model with the highest score.
    """
    n_rows = len(anomaly_scores)
    fraud_types: list[str] = []

    for i in range(n_rows):
        if anomaly_scores[i] < threshold:
            fraud_types.append("none")
            continue

        # Find the model with the highest (most suspicious) score.
        worst_type = "none"
        worst_score = 0.0
        for fraud_type, scores in per_model_scores.items():
            if scores[i] > worst_score:
                worst_score = scores[i]
                worst_type = fraud_type
        fraud_types.append(worst_type)

    return fraud_types


def step_ml_inference(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_sim_time: datetime,
    models: dict[str, AnomalyDetection],
) -> int:
    """Run 3 fraud-detection models and write combined scores to model_logs.

    Steps:
      1. Fetch rolling window of raw_metrics rows.
      2. Compute features (CTR, CVR, rolling stats, etc.).
      3. Run each model's decision_function on its feature subset.
      4. Normalize scores to [0, 1] and combine (element-wise max).
      5. Write one row per timestamp to model_logs.
      6. Call process_new_log() for the latest row to update anomaly_periods.

    Returns the number of model_logs rows written, or 0 if skipped.
    """
    raw_repo = RawMetricsRepository(session)
    derived_repo = DerivedMetricsRepository(session)
    # Use current_sim_time + 1 minute so the row we just wrote
    # (at current_sim_time) is included in the window.
    upper_bound = current_sim_time + timedelta(minutes=1)
    rows = raw_repo.get_last_n_before(
        t=upper_bound,
        n=ML_WINDOW_SIZE,
        publisher_id=publisher_id,
        campaign_id=campaign_id,
    )

    if len(rows) < ML_MIN_ROWS:
        logger.info(
            "  [ML] %s: only %d rows (need %d), skipping",
            publisher_id,
            len(rows),
            ML_MIN_ROWS,
        )
        return 0

    # Convert ORM rows to a DataFrame.
    raw_df = pd.DataFrame(
        [
            {
                "bucket_timestamp": r.bucket_timestamp,
                "publisher_id": r.publisher_id,
                "impression_count": r.impression_count,
                "click_count": r.click_count,
                "conversion_count": r.conversion_count,
            }
            for r in rows
        ]
    )
    raw_df["bucket_timestamp"] = pd.to_datetime(raw_df["bucket_timestamp"], utc=True)

    derived_rows = derived_repo.get_last_n_before(
        t=upper_bound,
        n=ML_WINDOW_SIZE,
        publisher_id=publisher_id,
        campaign_id=campaign_id,
    )
    derived_df = pd.DataFrame(
        [
            {
                "bucket_timestamp": r.bucket_timestamp,
                "publisher_id": r.publisher_id,
                "impressions_mean": r.impressions_mean,
                "clicks_mean": r.clicks_mean,
                "conversions_mean": r.conversions_mean,
                "impressions_std": r.impressions_std,
                "clicks_std": r.clicks_std,
                "conversions_std": r.conversions_std,
                "impressions_weighted_mean": r.impressions_weighted_mean,
                "clicks_weighted_mean": r.clicks_weighted_mean,
                "conversions_weighted_mean": r.conversions_weighted_mean,
                "sample_size": r.sample_size,
            }
            for r in derived_rows
        ]
    )
    derived_df["bucket_timestamp"] = pd.to_datetime(derived_df["bucket_timestamp"], utc=True)

    df = raw_df.merge(derived_df, on=["bucket_timestamp", "publisher_id"], how="inner")

    # Run each model and collect normalized anomaly scores (model.predict handles
    # feature engineering internally and returns scores already in [0, 1]).
    per_model_scores: dict[str, np.ndarray] = {}
    for fraud_type, model in models.items():
        pred_df = model.predict(df)
        per_model_scores[fraud_type] = pred_df["anomaly_score"].values

    # Combined anomaly score = element-wise maximum across all 3 models (worst = highest).
    all_scores = np.stack(list(per_model_scores.values()), axis=0)
    anomaly_scores: np.ndarray = np.max(all_scores, axis=0)

    # Determine primary fraud type per row.
    fraud_types = _determine_fraud_type(per_model_scores, anomaly_scores)

    # Only log the latest row — ML runs every tick so each row is scored
    # exactly once when it becomes the most recent entry in the window.
    latest_idx = len(anomaly_scores) - 1
    timestamps = df["bucket_timestamp"].tolist()
    log_tuples: list[tuple] = [
        (
            timestamps[latest_idx],
            publisher_id,
            MODEL_NAME,
            fraud_types[latest_idx],
            round(float(anomaly_scores[latest_idx]), 2),
        )
    ]

    logs_repo = ModelLogsRepository(session)
    logs_repo.bulk_insert(log_tuples)

    # Update anomaly_periods for the most recent timestamp.
    process_new_log(
        session=session,
        publisher_id=publisher_id,
        campaign_id=campaign_id,
        timestamp=timestamps[latest_idx],
        score=float(anomaly_scores[latest_idx]),
    )

    return len(log_tuples)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def _try_load_models() -> dict[str, AnomalyDetection] | None:
    """Attempt to load all 3 pre-trained fraud-detection models.

    Returns a dict mapping fraud_type -> sklearn model, or None if any
    model is missing or fails to load.
    """
    loaded: dict[str, Any] = {}
    for fraud_type, path in MODEL_PATHS.items():
        try:
            loaded[fraud_type] = joblib.load(path)
            logger.info("Loaded %s model from %s", fraud_type, path)
        except FileNotFoundError:
            logger.warning(
                "Model not found: %s – ML inference will be skipped "
                "until all 3 models are available.",
                path,
            )
            return None
        except Exception:
            logger.exception("Failed to load model from %s", path)
            return None

    logger.info("All %d ML models loaded successfully", len(loaded))
    return loaded


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------

def initialise_database() -> None:
    """Wipe all data and re-seed publishers and campaigns.

    Called once at orchestrator startup to guarantee a clean slate.
    Tables are truncated (not dropped) so the schema is preserved.
    Run ``docker-compose down -v`` once to clear a stale volume.
    """
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    # Ensure all tables exist (no-op if already present).
    Base.metadata.create_all(bind=engine)

    # Truncate all data in dependency-safe order.
    with engine.connect() as conn:
        conn.execute(text(
            "TRUNCATE TABLE "
            "model_logs, anomaly_periods, derived_metrics, model_reports, "
            "raw_metrics, model_runs, campaigns, publishers "
            "RESTART IDENTITY CASCADE"
        ))
        conn.commit()

    # Seed campaigns and publishers.
    with SessionLocal() as session:
        for camp_id, info in campaign_catalog.items():
            session.merge(Campaigns(
                campaign_id=camp_id,
                campaign_name=info["name"],
                start_date=info["start_date"],
            ))
        for pub_id, info in publisher_catalog.items():
            session.merge(Publishers(
                publisher_id=pub_id,
                publisher_name=info["name"],
            ))
        session.commit()

    logger.info(
        "Database initialised: %d campaign(s), %d publisher(s) seeded.",
        len(campaign_catalog),
        len(publisher_catalog),
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run(
    *,
    tick_interval: float = TICK_INTERVAL_SECONDS,
    ml_every_n: int = ML_INFERENCE_EVERY_N_TICKS,
    max_ticks: int | None = None,
) -> None:
    """Run the orchestration loop.

    Parameters
    ----------
    tick_interval:
        Wall-clock seconds between ticks.
    ml_every_n:
        Run ML inference once every *ml_every_n* ticks.
    max_ticks:
        If set, stop after this many ticks (useful for testing).
    """
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured; cannot create a session.")

    logger.info("Orchestrator starting")
    initialise_database()
    logger.info(
        "  tick_interval=%.1fs  sim_interval=%dmin  ml_every_n=%d",
        tick_interval,
        SIMULATED_INTERVAL_MINUTES,
        ml_every_n,
    )
    logger.info("  publishers: %d", len(publisher_catalog))

    # Attempt to load the 3 pre-trained models once at startup.
    models = _try_load_models()

    current_sim_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    tick_count = 0

    # ── Warmup: generate WARMUP_TICKS rows per publisher with no sleep ──────
    logger.info("Warmup: generating %d ticks with no sleep...", WARMUP_TICKS)
    for _ in range(WARMUP_TICKS):
        tick_count += 1
        session: Session = SessionLocal()
        try:
            for pub_id, info in publisher_catalog.items():
                camp_id: uuid.UUID = info["campaign_id"]
                generator = info["generator"]
                try:
                    step_generate_data(session, pub_id, camp_id, generator, current_sim_time)
                    step_derived_metrics(session, pub_id, camp_id, current_sim_time)
                except Exception:
                    logger.exception("  [warmup] Error for %s at tick %d", info["name"], tick_count)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Warmup tick %d failed, rolled back", tick_count)
        finally:
            session.close()
        current_sim_time += timedelta(minutes=SIMULATED_INTERVAL_MINUTES)
    logger.info("Warmup complete (%d ticks). Entering normal loop.", WARMUP_TICKS)
    # ────────────────────────────────────────────────────────────────────────

    while True:
        tick_count += 1
        if max_ticks is not None and tick_count > max_ticks:
            logger.info("Reached max_ticks=%d, stopping.", max_ticks)
            break

        logger.info(
            "=== Tick %d | sim_time=%s ===",
            tick_count,
            current_sim_time.isoformat(),
        )

        session: Session = SessionLocal()
        try:
            for pub_id, info in publisher_catalog.items():
                camp_id: uuid.UUID = info["campaign_id"]
                generator = info["generator"]
                name: str = info["name"]

                try:
                    # --- Step 1: Generate data --------------------------------
                    written = step_generate_data(
                        session,
                        pub_id,
                        camp_id,
                        generator,
                        current_sim_time,
                    )
                    logger.info("  [DataGen]  %s: %d row(s) written", name, written)

                    # --- Step 2: Derived metrics ------------------------------
                    produced = step_derived_metrics(
                        session,
                        pub_id,
                        camp_id,
                        current_sim_time,
                    )
                    if produced:
                        logger.info("  [Derived]  %s: recomputed", name)
                    else:
                        logger.debug(
                            "  [Derived]  %s: not enough data yet",
                            name,
                        )

                    # --- Step 3: ML inference (every N ticks) -----------------
                    if models is not None and tick_count >= ML_MIN_ROWS:
                        scored = step_ml_inference(
                            session,
                            pub_id,
                            camp_id,
                            current_sim_time,
                            models,
                        )
                        logger.info(
                            "  [ML]       %s: %d prediction(s) logged",
                            name,
                            scored,
                        )
                    elif models is None and tick_count % ml_every_n == 0:
                        logger.debug(
                            "  [ML]       %s: models not loaded, skipping",
                            name,
                        )

                    # --- Step 4: Extensible extra steps -----------------------
                    for step_fn in extra_steps:
                        step_fn(session, pub_id, camp_id, current_sim_time)

                except Exception:
                    logger.exception("  [%s] Error during tick %d", name, tick_count)
                    # Skip this publisher but continue with the rest.
                    continue

            session.commit()
            logger.info("--- Tick %d committed ---", tick_count)

        except Exception:
            session.rollback()
            logger.exception("Tick %d failed, rolled back", tick_count)
        finally:
            session.close()

        # Advance simulated clock.
        current_sim_time += timedelta(minutes=SIMULATED_INTERVAL_MINUTES)

        # Wait for next tick.
        time.sleep(tick_interval)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-14s  %(levelname)-7s  %(message)s",
    )
    run()
