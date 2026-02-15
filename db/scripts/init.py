#!/bin/python3

import ingest
import os
import psycopg
import sys

import ingest
import numpy as np
import pandas as pd

import time

errorCode=[
    "unknown args"
]

def createCursor():
    connection=psycopg.connect("dbname=%s user=%s"%(os.environ["POSTGRES_DB"],os.environ["POSTGRES_USER"]))
    return (connection,connection.cursor())

def executeSQLFile(cursor,fileName):
    f=open(fileName)
    content=f.read()
    cursor.execute(content[:content.index("-- migrate:down")])

def main()->int:
    argv=sys.argv
    argc=len(argv)
    
    (connection,cursor)=createCursor()
    executeSQLFile(cursor,"../migrations/000100_extensions.sql")
    executeSQLFile(cursor,"../migrations/000200_create_publishers.sql")
    executeSQLFile(cursor,"../migrations/000300_create_raw_metrics.sql")
    executeSQLFile(cursor,"../migrations/000400_create_model_logs.sql")x
            
    if argc<=1:
        connection.commit()
        return 0
    
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
        ingest.ingestMLLog(cursor,mlData)
    elif argv[1]=="publisher":
        cursor.execute("""
        INSERT INTO publishers (publisher_id, publisher_name)
        VALUES (%d, '%s');
        """%(21,"rnicrosift"))
        
        cursor.execute("""
        INSERT INTO publishers (publisher_id, publisher_name)
        VALUES (%d, '%s');
        """%(2,"Intelligent LTD"))
        # if argv[1]=="seed":
        #     if argc!=2:
        #         return 2
    
    #     with open("../init/02_seed.sql") as seed:
    #         cursor.execute(seed.read())
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
        ingest.ingestTimeSeries(cursor,tsData)
    else:
        return 1
    connection.commit()
    return 0

if __name__=="__main__":



    exitCode=main()
    print("Program exited with code %d"%exitCode)
    if exitCode:
        print(errorCode[exitCode-1])

