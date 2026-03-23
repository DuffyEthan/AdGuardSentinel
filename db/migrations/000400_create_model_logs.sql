-- migrate:up
CREATE TABLE IF NOT EXISTS model_logs(
  log_timestamp  TIMESTAMPTZ NOT NULL,
  publisher_id   INTEGER NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,
  model_name     TEXT NOT NULL,
  fraud_type     TEXT NOT NULL,
  score          NUMERIC(3,2) NOT NULL CHECK (score >= 0 AND score <= 1),

  PRIMARY KEY (publisher_id, log_timestamp)
);

SELECT create_hypertable('model_logs', 'log_timestamp');

-- migrate:down
DROP TABLE IF EXISTS model_logs;
