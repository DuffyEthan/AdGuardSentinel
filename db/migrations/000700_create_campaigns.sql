--migrate:up

CREATE TABLE IF NOT EXISTS campaigns(
  campaign_id UUID PRIMARY KEY,
  campaign_name TEXT NOT NULL,
  start_date TIMESTAMPTZ NOT NULL,
  end_date TIMESTAMPTZ
);

ALTER TABLE raw_metrics
    ADD COLUMN campaign_id UUID;

ALTER TABLE raw_metrics
    ALTER COLUMN campaign_id SET NOT NULL,
    ADD CONSTRAINT raw_metrics_campaign_id_fkey
      FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE raw_metrics
    DROP CONSTRAINT raw_metrics_pkey,
    ADD PRIMARY KEY (publisher_id, bucket_timestamp, campaign_id);

ALTER TABLE model_reports
    ADD COLUMN campaign_id UUID;

ALTER TABLE model_reports
    ALTER COLUMN campaign_id SET NOT NULL,
    ADD CONSTRAINT model_reports_campaign_id_fkey
      FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE model_reports
    DROP CONSTRAINT model_reports_pkey,
    ADD PRIMARY KEY (model_run_id, publisher_id, campaign_id, report_timestamp);


--migrate:down

ALTER TABLE raw_metrics
    DROP CONSTRAINT raw_metrics_pkey,
    ADD PRIMARY KEY (publisher_id, bucket_timestamp);

ALTER TABLE raw_metrics
    DROP COLUMN campaign_id;

ALTER TABLE model_reports
    DROP CONSTRAINT model_reports_pkey,
    ADD PRIMARY KEY (model_run_id, publisher_id, report_timestamp);

ALTER TABLE model_reports
    DROP COLUMN campaign_id;

DROP TABLE IF EXISTS campaigns;
