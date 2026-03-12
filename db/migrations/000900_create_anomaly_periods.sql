-- migrate:up
CREATE TABLE IF NOT EXISTS anomaly_periods (
    period_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publisher_id    UUID NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,
    anomaly_type    TEXT NOT NULL DEFAULT 'anomaly',

    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp   TIMESTAMPTZ,            -- NULL while the period is still open

    avg_score       DOUBLE PRECISION,       -- mean anomaly score during the period
    max_score       DOUBLE PRECISION,       -- peak anomaly score during the period
    log_count       INTEGER NOT NULL DEFAULT 0,  -- number of model_log entries in this period

    PRIMARY KEY (period_id, publisher_id, start_timestamp)
);

SELECT create_hypertable('anomaly_periods', 'start_timestamp');

-- migrate:down
DROP TABLE IF EXISTS anomaly_periods;

