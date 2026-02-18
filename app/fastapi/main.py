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

