-- migrate:up
CREATE TABLE IF NOT EXISTS model_logs(
  timestamp      timestamptz  NOT NULL,
  publisher_id   integer      NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,
  model_name     text         NOT NULL,
  score          numeric(3,2) NOT NULL CHECK (score >= 0 AND score <= 1),

  PRIMARY KEY (publisher_id, timestamp)
);

SELECT create_hypertable('model_logs', 'timestamp', if_not_exists => TRUE);

-- migrate:down
DROP TABLE IF EXISTS model_logs;
