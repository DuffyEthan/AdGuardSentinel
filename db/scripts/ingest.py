# https://www.geeksforgeeks.org/python/sqlalchemy-orm-adding-objects/
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

Base=declarative_base()

class RawMetrics(Base):
    __tablename__    ="raw_metrics"
    bucket_timestamp =sa.Column(sa.DateTime(timezone=True), primary_key=True, nullable=False)
    publisher_id     =sa.Column(sa.Integer(), primary_key=True, nullable=False)
    impression_count =sa.Column(sa.Integer(),nullable=False)
    click_count      =sa.Column(sa.Integer(),nullable=False)
    conversion_count =sa.Column(sa.Integer(),nullable=False)
class MLLogs(Base):
    __tablename__    ="model_logs"
    timestamp    =sa.Column(sa.DateTime(timezone=True), primary_key=True, nullable=False)
    publisher_id =sa.Column(sa.Integer(), primary_key=True, nullable=False)
    model_name   =sa.Column(sa.Text(), nullable=False)
    score        =sa.Column(sa.Numeric(),nullable=False)

def ingestTimeSeries(session,df)->None:
    listOfTS=df.to_numpy()
    for x in listOfTS:
        print(x)
        session.add(
            RawMetrics(
                bucket_timestamp =x[0],
                publisher_id     =x[1],
                impression_count =x[2],
                click_count      =x[3],
                conversion_count =x[4])
        )
    session.commit()

def ingestMLLog(session,df)->None:
    listOfTS=df.to_numpy()
    for x in listOfTS:
        session.add(
            MLLogs(
                timestamp    =x[0],
                publisher_id =x[1],
                model_name   =x[2],
                score        =x[3])
        )
    session.commit()
