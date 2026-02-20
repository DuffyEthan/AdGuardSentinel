import uuid

from fastapi import FastAPI, Depends
from datetime import datetime, timezone
from app.db.session import get_session

from app.db import SessionLocal
from app.db.models import ModelLogs
from app.db.models import RawMetrics
from app.repositories.model_logs_repository import ModelLogsRepository
from app.repositories.raw_metrics_repository import RawMetricsRepository

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
        t1: datetime, # inclusive lower bound timestamp
        t2: datetime, # inclusive upper bound timestamp
        publisher_id: uuid.UUID, # filter by publisher_id
        campaign_id: uuid.UUID, # filter by campaign_id (used in join)
        session: Session = Depends(get_session)
):
    given=ModelLogsRepository(session).get_between(t1, t2, publisher_id, campaign_id)
    # res=[]
    # for x in given:
    #     res.append(vars(x[0])|(vars(x[1])))
    return given

@app.get("/raw-metrics/get-last-n-before")
def raw_metrics_get_last_n_before(
        t: datetime, # exclusive upper-bound timestamp
        n: int, # maximum number of rows to return
        publisher_id: uuid.UUID | None = None,  # optionally filter by publisher_id
        campaign_id: uuid.UUID | None = None, # optionally filter by campaign_id
        session: Session = Depends(get_session)
):
    return RawMetricsRepository(session).get_last_n_before(t, n, publisher_id, campaign_id)


@app.post("/pipeline/train-model")  #runs full anomaly detection pipeline
def train_model_endpoint(publisher_id: str, hours: int = 24, model_name: str = "isolation_forest_v1"):
    """
    Trigger full pipeline: fetch -> train -> log.
    Returns {"status": "success"/"error", "records_processed": int, "records_logged": int}

    TODO:
    1. Import run_full_pipeline from app.ml._isolation_forest
    2. Calculate start_date = now - timedelta(hours=hours), end_date = now
    3. Call and return run_full_pipeline(start_date, end_date, publisher_id, model_name)
    """
    # TODO: IMPLEMENT THIS ENDPOINT
    raise NotImplementedError("Implement POST /pipeline/train-model")


@app.get("/pipeline/results")
def get_pipeline_results(publisher_id: str, t1: datetime, t2: datetime, session: Session = Depends(get_session)):
    """
    Get raw metrics + model predictions in time range.
    Returns {"raw_metrics": [...], "model_predictions": [...], "summary": {...}}

    TODO:
    1. Call RawMetricsRepository(session).get_last_n_before(t2, 1000, publisher_id) and filter between t1-t2
    2. Call ModelLogsRepository(session).get_between(t1, t2, publisher_id)
    3. Return {"raw_metrics": raw, "model_predictions": predictions, "summary": {...}} -> combine and send both back to frontend to display on chart
    """
    # TODO: IMPLEMENT THIS ENDPOINT
    raise NotImplementedError("Implement GET /pipeline/results")
