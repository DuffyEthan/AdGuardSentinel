--migrate:up

CREATE TABLE IF NOT EXISTS campaigns(
  campaign_id UUID PRIMARY KEY,
  publisher_id UUID NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,
  start_date TIMESTAMPTZ NOT NULL,
  end_date TIMESTAMPTZ
);

ALTER TABLE raw_metrics
    ADD COLUMN campaign_id UUID REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE raw_metrics
    DROP CONSTRAINT raw_metrics_pkey,
    ADD PRIMARY KEY (publisher_id, bucket_timestamp, campaign_id);


--migrate:down

ALTER TABLE raw_metrics
    DROP CONSTRAINT raw_metrics_pkey,
    ADD PRIMARY KEY (publisher_id, bucket_timestamp);

ALTER TABLE raw_metrics
    DROP COLUMN campaign_id;

DROP TABLE IF EXISTS campaigns;
