from fastapi import FastAPI, Depends
from datetime import datetime, timezone
from app.db.session import get_session
from app.db.models import RawMetrics
from app.repositories.model_logs_repository import ModelLogsRepository
from app.repositories.raw_metrics_repository import RawMetricsRepository

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import os

from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")
print("DATABASE_URL:",DATABASE_URL)

if DATABASE_URL:
    # Use psycopg v3 driver (not psycopg2) with SQLAlchemy
    SQLALCHEMY_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(SQLALCHEMY_URL, pool_pre_ping=True)
else:
    engine = None

from app.db.models import Base
Base.metadata.create_all(bind=engine)
    
SessionLocal = sessionmaker(bind=engine) if engine else None
print("SessionLocal type:", type(SessionLocal))

session=SessionLocal()
print("db_session type:", type(session))  

session: Session = next(get_session())
t=datetime(2026, 1, 1, 4, 0, tzinfo=timezone.utc)
n=5
publisher_id=1

print(session.query(RawMetrics).all())
# print(RawMetricsRepository(session).get_last_n_before(t, n, publisher_id))

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

# @app.get("/model-logs/get-between")
# def model_logs_get_between(
#     t1: datetime,
#     t2: datetime,
#     publisher_id: int,
#     session: Session = Depends(get_session)
# ):
#     return ModelLogsRepository(session).get_between(t1, t2, publisher_id)

@app.get("/raw-metrics/get-last-n-before")
def raw_metrics_get_last_n_before(
    t: datetime,
    n: int,
    publisher_id: int,
    session: Session = Depends(get_session)
):
    return RawMetricsRepository(session).get_last_n_before(t, n, publisher_id)


