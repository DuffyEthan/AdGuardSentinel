# modified of
#     https://www.psycopg.org/psycopg3/docs/basic/usage.html
# additional reasources:
#     https://www.tigerdata.com/learn/is-postgres-partitioning-really-that-hard-introducing-hypertables

DB_NAME="YourDBName"
USERNAME="YourUserName"

import psycopg

with psycopg.connect("dbname=%s user=%s"%(DB_NAME,USERNAME)) as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS interaction (
                time TIMESTAMP,
                impression INT,
                click INT,
                conversion INT
            )WITH(
                tsdb.hypertable,
                tsdb.orderby="time"
            )
        """)

        cur.execute(
            "INSERT INTO interaction (time, impression, click, conversion) VALUES (%s, %s, %s, %s)",
            ("2026-01-31 19:18:43",200,20,2)
        )
        conn.commit()
