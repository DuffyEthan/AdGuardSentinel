import uuid

from fastapi import FastAPI, Depends
from datetime import datetime, timezone, timedelta
from app.db.session import get_session

from app.db import SessionLocal
from app.db.models import ModelLogs
from app.db.models import RawMetrics
from app.repositories.model_logs_repository import ModelLogsRepository
from app.repositories.raw_metrics_repository import RawMetricsRepository
from app.repositories.sentinel_repository import SentinelRepository
from app.fastapi.services.sentinel_service import sentinel_service
from app.fastapi.services import anomaly_periods_service

from app.ml._isolation_forest import run_full_pipeline

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import os

from sqlalchemy.orm import sessionmaker

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/model-logs")
def model_logs_get_between():
    return {"0": "get-between"}


@app.get("/raw-metrics")
def model_logs_get_between():
    return {"0": "get-last-n-before"}


@app.get("/model-logs/get-between")
def model_logs_get_between(
    t1: datetime,
    t2: datetime,
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    given = ModelLogsRepository(session).get_between(t1, t2, publisher_id, campaign_id)
    res = []
    for x in given:
        res.append(vars(x[0]) | (vars(x[1])))
    return res


@app.get("/raw-metrics/get-last-n-before")
def raw_metrics_get_last_n_before(
    t: datetime,
    n: int,
    publisher_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
    session: Session = Depends(get_session),
):
    return RawMetricsRepository(session).get_last_n_before(
        t, n, publisher_id, campaign_id
    )


@app.post("/pipeline/train-model")
def train_model_endpoint(
    publisher_id: str, hours: int = 24, model_name: str = "isolation_forest_v1"
):
    now = datetime.now()
    return run_full_pipeline(
        start_date=now - timedelta(hours=hours),
        end_date=now,
        publisher_id=publisher_id,
        model_name=model_name,
    )


@app.get("/pipeline/results")
def get_pipeline_results(
    publisher_id: str,
    t1: datetime,
    t2: datetime,
    session: Session = Depends(get_session),
):
    raw_metrics_repo = RawMetricsRepository(session)
    model_logs_repo = ModelLogsRepository(session)

    all_raw_metrics = raw_metrics_repo.get_last_n_before(t2, 1000, publisher_id)
    raw_metrics = [m for m in all_raw_metrics if t1 <= m.bucket_timestamp <= t2]

    model_predictions_data = model_logs_repo.get_between(t1, t2, publisher_id)
    model_predictions = []
    for pred_tuple in model_predictions_data:
        model_predictions.append(vars(pred_tuple[0]) | vars(pred_tuple[1]))

    raw_metrics_list = [vars(m) for m in raw_metrics]

    return {
        "raw_metrics": raw_metrics_list,
        "model_predictions": model_predictions,
        "summary": {
            "total_raw_records": len(raw_metrics_list),
            "total_predictions": len(model_predictions),
            "time_range": {"start": t1, "end": t2},
        },
    }


# ── Sentinel Dashboard Endpoints ────────────────────────────────────────


@app.get("/sentinel/stats")
def sentinel_stats(
    since: datetime | None = None,
    session: Session = Depends(get_session),
):
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

    repo = SentinelRepository(session)
    return {
        "publisher_count": repo.get_publisher_count(),
        "suspicious_publisher_count": repo.get_suspicious_publisher_count(since),
        "avg_network_ctr": repo.get_avg_network_ctr(since),
        "fraud_event_count": repo.get_fraud_event_count(since),
        "network_trust_breakdown": repo.get_network_trust_breakdown(),
    }


@app.get("/sentinel/publishers")
def sentinel_publishers(
    as_of: datetime | None = None,
    session: Session = Depends(get_session),
):
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    repo = SentinelRepository(session)
    return repo.get_publisher_trust_summary(as_of)


@app.get("/sentinel/trust-distribution")
def sentinel_trust_distribution(
    as_of: datetime | None = None,
    session: Session = Depends(get_session),
):
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    repo = SentinelRepository(session)
    return repo.get_trust_score_distribution(as_of)


@app.get("/sentinel/fraud-events")
def sentinel_fraud_events(
    days: int = 7,
    session: Session = Depends(get_session),
):
    repo = SentinelRepository(session)
    return repo.get_daily_fraud_event_counts(days)


@app.get("/sentinel/assistant/explain/{publisher_id}")
def sentinel_explain(
    publisher_id: uuid.UUID,
    as_of: datetime | None = None,
    session: Session = Depends(get_session),
):
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    return sentinel_service.get_trust_score_explanation(session, publisher_id, as_of)


@app.get("/sentinel/assistant/evidence/{publisher_id}")
def sentinel_evidence(
    publisher_id: uuid.UUID,
    t1: datetime,
    t2: datetime,
    session: Session = Depends(get_session),
):
    repo = SentinelRepository(session)
    return repo.get_anomaly_evidence(publisher_id, t1, t2)


@app.get("/sentinel/assistant/compare/{publisher_id}")
def sentinel_compare(
    publisher_id: uuid.UUID,
    as_of: datetime | None = None,
    session: Session = Depends(get_session),
):
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    return sentinel_service.compare_publisher_to_network(session, publisher_id, as_of)


# ── Anomaly Periods Endpoints ───────────────────────────────────────────


@app.get("/anomaly-periods/{publisher_id}")
def get_anomaly_periods(
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    t1: datetime,
    t2: datetime,
    session: Session = Depends(get_session),
):
    """Return anomaly periods overlapping [t1, t2], formatted for the chart."""
    return anomaly_periods_service.get_anomaly_periods_for_chart(
        session, publisher_id, campaign_id, t1, t2
    )


@app.post("/anomaly-periods/backfill/{publisher_id}")
def backfill_anomaly_periods(
    publisher_id: uuid.UUID,
    campaign_id: uuid.UUID,
    since: datetime | None = None,
    session: Session = Depends(get_session),
):
    """Re-compute all anomaly periods from model_logs for a publisher."""
    periods = anomaly_periods_service.backfill_anomaly_periods(
        session, publisher_id, campaign_id, since
    )
    return {
        "publisher_id": str(publisher_id),
        "campaign_id": str(campaign_id),
        "periods_created": len(periods),
        "periods": [
            {
                "period_id": str(p.period_id),
                "anomaly_type": p.anomaly_type,
                "start": p.start_timestamp.isoformat(),
                "end": p.end_timestamp.isoformat() if p.end_timestamp else None,
                "avg_score": p.avg_score,
                "max_score": p.max_score,
                "log_count": p.log_count,
            }
            for p in periods
        ],
    }

