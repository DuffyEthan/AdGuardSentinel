# https://www.geeksforgeeks.org/python/sqlalchemy-orm-adding-objects/
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from app.db.models import RawMetrics, ModelLogs

Base=declarative_base()

def ingestTimeSeries(session,df) -> None:
    recs = df.to_dict('records')

    session.bulk_insert_mappings(RawMetrics, recs)
    session.commit()

def ingestMLLog(session,df) -> None:
    recs = df.to_dict('records')

    session.bulk_insert_mappings(ModelLogs, recs)
    session.commit()
