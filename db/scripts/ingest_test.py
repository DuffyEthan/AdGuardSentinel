#!/bin/python3

import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import psycopg
import sys

import ingest
import numpy as np
import pandas as pd

import time

errorCode=[
    "Unknown args"
]

Base=declarative_base()
class Publisher(Base):
    __tablename__  ="publishers"
    publisher_id   =sa.Column(sa.Integer(), primary_key=True, nullable=False)
    publisher_name =sa.Column(sa.Text(), nullable=False)


def createSession():
    engine = sa.create_engine(os.environ["DATABASE_URL"])
    return sessionmaker(autoflush=False, autocommit=False, bind=engine)()
def executeSQLFile(cursor,fileName):
    f=open(fileName)
    content=f.read()
    cursor.execute(content[:content.index("-- migrate:down")])
def main()->int:
    argv=sys.argv
    argc=len(argv)

    with psycopg.connect("dbname=%s user=%s"%(os.environ['POSTGRES_DB'],os.environ['POSTGRES_USER'])) as conn:
        with conn.cursor() as cur:
                executeSQLFile(cur,"../migrations/000100_extensions.sql")
                executeSQLFile(cur,"../migrations/000200_create_publishers.sql")
                executeSQLFile(cur,"../migrations/000300_create_raw_metrics.sql")
                executeSQLFile(cur,"../migrations/000400_create_model_logs.sql")
                conn.commit()

    if argc<=1:
        return 0

    session=createSession()
    session.close()

    if argv[1]=="mllog":
        mlExample=[
            [time.strftime("%Y-%m-%d %H:%M:%S"),21,"LLM",0.0],
            [time.strftime("%Y-%m-%d %H:%M:%S"),2,"Parser",0.5]
        ]
        mlData=pd.DataFrame(
            mlExample,
            columns=[
                "timestamp",
                "publisher_id",
                "model_name",
                "score"
            ]
        )

        print(mlData)
        ingest.ingestMLLog(session,mlData)
    elif argv[1]=="publisher":
        session.add(
            Publisher(
                publisher_id   =21,
                publisher_name ="rnicrosift"
            )
        )
        session.add(
            Publisher(
                publisher_id   =2,
                publisher_name ="Intelligent LTD"
            )
        )
        session.commit()

        # session.execute("""
        # INSERT INTO publishers (publisher_id, publisher_name)
        # VALUES (%d, '%s');
        # """%(2,"Intelligent LTD"))
        # if argv[1]=="seed":
        #     if argc!=2:
        #         return 2

    #     with open("../init/02_seed.sql") as seed:
    #         session.execute(seed.read())
    #         seed.close()
    elif argv[1]=="ts":
        tsExample=[
            [time.strftime("%Y-%m-%d %H:%M:%S"),21,420,69,67],
            [time.strftime("%Y-%m-%d %H:%M:%S"),2,16,8,4]
        ]

        tsData=pd.DataFrame(
            tsExample,
            columns=[
                "bucket_timestamp",
                "publisher_id",
                "impression_count",
                "click_count",
                "conversion_count"
            ]
        )

        print(tsData)
        ingest.ingestTimeSeries(session,tsData)
    else:
        return 1
    session.close()
    return 0

if __name__=="__main__":
    exitCode=main()
    print("Program exited with code %d"%exitCode)
    if exitCode:
        print(errorCode[exitCode-1])
