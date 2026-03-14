"""
Anomaly Period Detection Service
=================================
Processes model_logs rows and determines contiguous periods of anomalous
behaviour for a given publisher.  Each call to ``process_new_log`` is
intended to be invoked on every new model_log entry (e.g. during the
orchestration loop).  It maintains state through the ``anomaly_periods``
table so it can be called incrementally — one log at a time — without
needing to re-scan history.

Anomaly classification
----------------------
* **score > HIGH_THRESHOLD (0.7)**  → ``"critical"``
* **score > LOW_THRESHOLD  (0.3)**  → ``"warning"``
* **score ≤ LOW_THRESHOLD**         → *not anomalous* (closes any open period)

If the incoming log is anomalous and the previous open period has the
**same** anomaly type, the period is extended.  If the type changes
(e.g. warning → critical) the old period is closed and a new one is
opened so that periods group the *same* anomaly kind.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.db.models import AnomalyPeriods, ModelLogs, RawMetrics
from app.repositories.anomaly_periods_repository import AnomalyPeriodsRepository

# ── Thresholds ──────────────────────────────────────────────────────────
LOW_THRESHOLD = 0.3   # score > this → anomalous
HIGH_THRESHOLD = 0.7  # score > this → critical anomaly


def classify_score(score: float) -> Optional[str]:
    """Map a model-log anomaly score to an anomaly type label, or *None*."""
    if score > HIGH_THRESHOLD:
        return "critical"
    if score > LOW_THRESHOLD:
        return "warning"
    return None  # not anomalous


# ── Single-step incremental processor ──────────────────────────────────

def process_new_log(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    timestamp: datetime,
    score: float,
) -> Optional[AnomalyPeriods]:
    """Process one new model_log entry and update the anomaly_periods table.

    Call this once per new model-log row (inside the orchestration loop).
    It will:
    * Open a new period if we enter an anomalous state.
    * Extend an existing period if we stay in the same anomaly type.
    * Close the old period and open a new one if the type changes.
    * Close the current period if the score drops below threshold.

    Returns the open ``AnomalyPeriods`` row (or *None* if no period is
    open after this step).
    """
    repo = AnomalyPeriodsRepository(session)
    anomaly_type = classify_score(score)
    open_period = repo.get_open_period(publisher_id, campaign_id)

    if anomaly_type is None:
        # ── Score is normal → close any open period ─────────────────
        if open_period is not None:
            repo.close_period(open_period, end_timestamp=timestamp)
        return None

    # ── Score is anomalous ──────────────────────────────────────────
    if open_period is None:
        # No open period → start a new one
        return repo.open_period(
            publisher_id=publisher_id,
            campaign_id=campaign_id,
            start_timestamp=timestamp,
            anomaly_type=anomaly_type,
            score=score,
        )

    if open_period.anomaly_type == anomaly_type:
        # Same anomaly type → extend the existing period
        repo.update_period_stats(open_period, new_score=score, new_timestamp=timestamp)
        return open_period

    # Type changed (e.g. warning → critical) → close old, open new
    repo.close_period(open_period, end_timestamp=timestamp)
    return repo.open_period(
        publisher_id=publisher_id,
        campaign_id=campaign_id,
        start_timestamp=timestamp,
        anomaly_type=anomaly_type,
        score=score,
    )


# ── Batch / backfill processor ─────────────────────────────────────────

def backfill_anomaly_periods(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    since: Optional[datetime] = None,
) -> list[AnomalyPeriods]:
    """Re-compute anomaly periods from scratch for a publisher.

    Scans all ``model_logs`` rows for *publisher_id* (optionally from
    *since* onward), deletes existing anomaly periods, and re-creates
    them.  Useful for initial backfill or after changing thresholds.

    Returns the list of created ``AnomalyPeriods``.
    """
    repo = AnomalyPeriodsRepository(session)

    # Delete existing periods for this publisher
    existing = repo.get_all_periods(publisher_id, campaign_id)
    for p in existing:
        session.delete(p)
    session.flush()

    # Fetch model_logs ordered chronologically
    query = (
        session.query(ModelLogs)
        .join(
            RawMetrics,
            (ModelLogs.publisher_id == RawMetrics.publisher_id)
            & (ModelLogs.log_timestamp == RawMetrics.bucket_timestamp),
        )
        .filter(
            ModelLogs.publisher_id == publisher_id,
            RawMetrics.campaign_id == campaign_id,
        )
    )
    if since is not None:
        query = query.filter(ModelLogs.log_timestamp >= since)
    logs = query.order_by(asc(ModelLogs.log_timestamp)).all()

    # Process each log entry incrementally
    created_periods: list[AnomalyPeriods] = []
    for log in logs:
        result = process_new_log(
            session=session,
            publisher_id=publisher_id,
            campaign_id=campaign_id,
            timestamp=log.log_timestamp,
            score=float(log.score),
        )
        if result is not None and result not in created_periods:
            created_periods.append(result)

    return created_periods


# ── Query helpers for the frontend ──────────────────────────────────────

def get_anomaly_periods_for_chart(
    session: Session,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    t1: datetime,
    t2: datetime,
) -> list[dict]:
    """Return anomaly periods formatted for the frontend ``AnomalyEvent`` type.

    Each dict has keys: ``x1``, ``x2``, ``label``, ``fill``, ``stroke``.
    Open periods (``end_timestamp IS NULL``) use *t2* as their visual end.
    """
    repo = AnomalyPeriodsRepository(session)
    periods = repo.get_periods_between(publisher_id, campaign_id, t1, t2)

    FILL_MAP = {
        "critical": "rgba(255, 0, 0, 0.15)",
        "warning": "rgba(255, 165, 0, 0.12)",
        "anomaly": "rgba(255, 0, 0, 0.10)",
    }
    STROKE_MAP = {
        "critical": "#cc0000",
        "warning": "#cc8800",
        "anomaly": "#cc3333",
    }

    result: list[dict] = []
    for p in periods:
        end = p.end_timestamp if p.end_timestamp is not None else t2
        label = p.anomaly_type.capitalize()
        if p.max_score is not None:
            label += f" (peak {p.max_score:.0%})"

        result.append({
            "period_id": str(p.period_id),
            "publisher_id": str(p.publisher_id),
            "campaign_id": str(p.campaign_id),
            "x1": p.start_timestamp.isoformat(),
            "x2": end.isoformat(),
            "start_timestamp": p.start_timestamp.isoformat(),
            "end_timestamp": end.isoformat() if p.end_timestamp else None,
            "anomaly_type": p.anomaly_type,
            "avg_score": p.avg_score,
            "max_score": p.max_score,
            "log_count": p.log_count,
            "label": label,
            "fill": FILL_MAP.get(p.anomaly_type, FILL_MAP["anomaly"]),
            "stroke": STROKE_MAP.get(p.anomaly_type, STROKE_MAP["anomaly"]),
        })

    return result


