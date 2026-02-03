CREATE TABLE IF NOT EXISTS impression (
  impression_ts TIMESTAMPTZ NOT NULL,
  impression_date DATE NOT NULL,
  impression_time TIME NOT NULL,
  impression_clicks INT NOT NULL
);

SELECT create_hypertable('impression', 'impression_ts', if_not_exists => TRUE);
