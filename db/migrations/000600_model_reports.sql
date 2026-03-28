--migrate:up

CREATE TABLE IF NOT EXISTS model_runs(
    model_run_id UUID PRIMARY KEY, 
    model_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_reports(
    model_run_id UUID REFERENCES model_runs(model_run_id) ON DELETE CASCADE,
    publisher_id UUID NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,
    report_timestamp TIMESTAMPTZ NOT NULL,
    report_data JSONB,
    PRIMARY KEY (model_run_id, publisher_id, report_timestamp)
);

--migrate:down
DROP TABLE IF EXISTS model_reports;

DROP TABLE IF EXISTS model_runs;