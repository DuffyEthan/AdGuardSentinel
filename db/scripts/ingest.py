def ingestTimeSeries(cursor,df)->None:
    listOfTS=df.to_numpy()
    for x in listOfTS:
        cursor.execute("""
    	INSERT INTO raw_metrics (bucket_timestamp,publisher_id,impression_count,click_count,conversion_count)
    	VALUES ('%s', %d, %d, %d, %d);
    	"""%(x[0],x[1],x[2],x[3],x[4]))

def ingestMLLog(cursor,df)->None:
    listOfTS=df.to_numpy()
    for x in listOfTS:
        cursor.execute("""
    	INSERT INTO model_logs (timestamp, publisher_id,model_name,score)
    	VALUES ('%s', %d, '%s', %f);
    	"""%(x[0],x[1],x[2],x[3]))
