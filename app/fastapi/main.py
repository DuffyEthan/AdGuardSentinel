from fastapi import FastAPI, Depends
from datetime import datetime, timezone, timedelta
from app.db.session import get_session

from app.db import SessionLocal
from app.db.models import ModelLogs
from app.db.models import RawMetrics
from app.repositories.model_logs_repository import ModelLogsRepository
from app.repositories.raw_metrics_repository import RawMetricsRepository

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
    return {"0":"get-between"}

@app.get("/raw-metrics")
def model_logs_get_between():
    return {"0":"get-last-n-before"}

@app.get("/model-logs/get-between")
def model_logs_get_between(
    t1: datetime,
    t2: datetime,
    publisher_id: int,
    session: Session = Depends(get_session)
):
    given=ModelLogsRepository(session).get_between(t1, t2, publisher_id)
    res=[]
    for x in given:
        res.append(vars(x[0])|(vars(x[1])))
    return res

@app.get("/raw-metrics/get-last-n-before")
def raw_metrics_get_last_n_before(
    t: datetime,
    n: int,
    publisher_id: int,
    session: Session = Depends(get_session)
):
    return RawMetricsRepository(session).get_last_n_before(t, n, publisher_id)


@app.post("/pipeline/train-model")  #runs full anomaly detection pipeline
def train_model_endpoint(
        publisher_id: str,
        hours: int = 24,
        model_name: str = "isolation_forest_v1"
):
    """
    Trigger full pipeline: fetch -> train -> log.
    Returns {"status": "success"/"error", "records_processed": int, "records_logged": int}
    """
    now=datetime.now()
    return run_full_pipeline(
        start_date = now - timedelta(hours=hours),
        end_date = now,
        publisher_id = publisher_id,
        model_name = model_name
    )


@app.get("/pipeline/results")
def get_pipeline_results(publisher_id: str, t1: datetime, t2: datetime, session: Session = Depends(get_session)):
    """
    Get raw metrics + model predictions in time range.
    Returns {"raw_metrics": [...], "model_predictions": [...], "summary": {...}}
    """
    raw_metrics_repo = RawMetricsRepository(session)
    model_logs_repo = ModelLogsRepository(session)
    
    # Get raw metrics and filter between t1-t2
    all_raw_metrics = raw_metrics_repo.get_last_n_before(t2, 1000, publisher_id)
    raw_metrics = [m for m in all_raw_metrics if t1 <= m.bucket_timestamp <= t2]
    
    # Get model predictions in time range
    model_predictions_data = model_logs_repo.get_between(t1, t2, publisher_id)
    model_predictions = []
    for pred_tuple in model_predictions_data:
        model_predictions.append(vars(pred_tuple[0]) | vars(pred_tuple[1]))
    
    # Convert raw metrics to dict format
    raw_metrics_list = [vars(m) for m in raw_metrics]
    
    return {
        "raw_metrics": raw_metrics_list,
        "model_predictions": model_predictions,
        "summary": {
            "total_raw_records": len(raw_metrics_list),
            "total_predictions": len(model_predictions),
            "time_range": {"start": t1, "end": t2}
        }
    }
