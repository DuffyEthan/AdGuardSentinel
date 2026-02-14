-- migrate:up
CREATE TABLE IF NOT EXISTS raw_metrics(
  bucket_timestamp  timestamptz NOT NULL,
  publisher_id      integer     NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,

  impression_count  integer     NOT NULL DEFAULT 0,
  click_count       integer     NOT NULL DEFAULT 0,
  conversion_count  integer     NOT NULL DEFAULT 0,

  PRIMARY KEY (publisher_id, bucket_timestamp)
);

SELECT create_hypertable('raw_metrics', 'bucket_timestamp');

-- migrate:down
DROP TABLE IF EXISTS raw_metrics;
