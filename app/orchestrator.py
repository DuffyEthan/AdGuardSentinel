"""
Backend orchestration loop.

Run as a standalone process:
    python -m app.orchestrator

Each tick simulates one 5-minute data bucket:

  1. DATA GEN    – call publisher_data_next() for every publisher in the
                   catalog and upsert the resulting row into raw_metrics.
  2. DERIVED     – recompute derived_metrics for every publisher/campaign
                   (IQR-filtered mean/std/weighted-mean over the last 250 rows).
  3. ML INFERENCE– every N ticks, load the pre-trained Isolation Forest
                   model, run predict() on a rolling window of raw_metrics,
                   and write trust-scores into model_logs.
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

import pandas as pd
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.fastapi.services.derived_metrics_service import compute_and_store
from app.ml.batch_data_generator import upsert_raw_metrics
from app.ml.publishers import publisher_catalog
from app.repositories.model_logs_repository import ModelLogsRepository
from app.repositories.raw_metrics_repository import RawMetricsRepository

logger = logging.getLogger("orchestrator")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TICK_INTERVAL_SECONDS: float = 5.0
"""Wall-clock seconds between ticks."""

SIMULATED_INTERVAL_MINUTES: int = 5
"""Each tick advances the simulated clock by this many minutes."""

ML_INFERENCE_EVERY_N_TICKS: int = 50
"""Run ML inference once every N ticks."""

ML_WINDOW_SIZE: int = 250
"""Number of most-recent raw_metrics rows fed to the model."""

ML_MIN_ROWS: int = 25
"""Minimum rows required before inference is attempted."""

MODEL_PATH: str = "app/ml/models/_isolation_forest.joblib"
"""Path to the pre-trained Isolation Forest .joblib file."""

MODEL_NAME: str = "isolation_forest_v1"
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


def step_ml_inference(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_sim_time: datetime,
    model: Any,
) -> int:
    """Run inference on a rolling window and write trust-scores to model_logs.

    Returns the number of prediction rows written, or 0 if skipped.
    """
    raw_repo = RawMetricsRepository(session)
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

    # Convert ORM rows to a DataFrame matching what the model expects.
    df = pd.DataFrame(
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
    df["bucket_timestamp"] = pd.to_datetime(df["bucket_timestamp"], utc=True)

    predictions = model.predict(df)

    # Format as (timestamp, publisher_id, model_name, score) tuples for bulk_insert.
    log_tuples: list[tuple] = [
        (
            row["bucket_timestamp"],
            publisher_id,
            MODEL_NAME,
            float(row["trust_score"]),
        )
        for _, row in predictions.iterrows()
    ]

    logs_repo = ModelLogsRepository(session)
    logs_repo.bulk_insert(log_tuples)
    return len(log_tuples)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def _try_load_model(path: str) -> Any | None:
    """Attempt to load a pre-trained model. Returns None on failure."""
    try:
        from app.ml._isolation_forest import load_model

        model = load_model(path)
        logger.info("Loaded ML model from %s", path)
        return model
    except FileNotFoundError:
        logger.warning(
            "No ML model found at %s – inference step will be skipped until "
            "the ML team delivers a trained model.",
            path,
        )
        return None
    except Exception:
        logger.exception("Failed to load ML model from %s", path)
        return None


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
    assert SessionLocal is not None, (
        "DATABASE_URL is not configured; cannot create a session."
    )

    logger.info("Orchestrator starting")
    logger.info(
        "  tick_interval=%.1fs  sim_interval=%dmin  ml_every_n=%d",
        tick_interval,
        SIMULATED_INTERVAL_MINUTES,
        ml_every_n,
    )
    logger.info("  publishers: %d", len(publisher_catalog))

    # Attempt to load the pre-trained model once at startup.
    model = _try_load_model(MODEL_PATH)

    current_sim_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    tick_count = 0

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
                    if model is not None and tick_count % ml_every_n == 0:
                        scored = step_ml_inference(
                            session,
                            pub_id,
                            camp_id,
                            current_sim_time,
                            model,
                        )
                        logger.info(
                            "  [ML]       %s: %d prediction(s) logged",
                            name,
                            scored,
                        )
                    elif model is None and tick_count % ml_every_n == 0:
                        logger.debug(
                            "  [ML]       %s: no model loaded, skipping",
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
