--migrate:up

CREATE TABLE IF NOT EXISTS campaigns(
  campaign_id UUID PRIMARY KEY,
  publisher_id UUID NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,
  start_date TIMESTAMPTZ NOT NULL,
  end_date TIMESTAMPTZ
);

-- Ensure every publisher has at least one campaign so existing rows can be backfilled.
INSERT INTO campaigns (campaign_id, publisher_id, start_date)
SELECT gen_random_uuid(), p.publisher_id, NOW()
FROM publishers p
WHERE NOT EXISTS (
  SELECT 1
  FROM campaigns c
  WHERE c.publisher_id = p.publisher_id
);

ALTER TABLE raw_metrics
    ADD COLUMN campaign_id UUID;

UPDATE raw_metrics rm
SET campaign_id = (
  SELECT c.campaign_id
  FROM campaigns c
  WHERE c.publisher_id = rm.publisher_id
  ORDER BY c.start_date, c.campaign_id
  LIMIT 1
);

ALTER TABLE raw_metrics
    ALTER COLUMN campaign_id SET NOT NULL,
    ADD CONSTRAINT raw_metrics_campaign_id_fkey
      FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE;

ALTER TABLE raw_metrics
    DROP CONSTRAINT raw_metrics_pkey,
    ADD PRIMARY KEY (publisher_id, bucket_timestamp, campaign_id);

ALTER TABLE model_reports
    ADD COLUMN campaign_id UUID;

UPDATE model_reports mr
SET campaign_id = (
  SELECT c.campaign_id
  FROM campaigns c
  WHERE c.publisher_id = mr.publisher_id
  ORDER BY c.start_date, c.campaign_id
  LIMIT 1
);

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
