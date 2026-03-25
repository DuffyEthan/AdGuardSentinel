-- migrate:up
CREATE TABLE IF NOT EXISTS derived_metrics (
    bucket_timestamp TIMESTAMPTZ NOT NULL,
    publisher_id UUID NOT NULL REFERENCES publishers(publisher_id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,

    -- Means (IQR outlier-excluded)
    impressions_mean DOUBLE PRECISION,
    clicks_mean DOUBLE PRECISION,
    conversions_mean DOUBLE PRECISION,

    -- Standard deviations (IQR outlier-excluded)
    impressions_std DOUBLE PRECISION,
    clicks_std DOUBLE PRECISION,
    conversions_std DOUBLE PRECISION,

    -- Weighted rolling means (linear weights, IQR outlier-excluded) = expected mean
    impressions_weighted_mean DOUBLE PRECISION,
    clicks_weighted_mean DOUBLE PRECISION,
    conversions_weighted_mean DOUBLE PRECISION,

    -- Number of raw_metrics rows used in the computation window
    sample_size INTEGER NOT NULL DEFAULT 250,

    PRIMARY KEY (publisher_id, bucket_timestamp, campaign_id)
);

SELECT create_hypertable('derived_metrics', 'bucket_timestamp');

-- migrate:down
DROP TABLE IF EXISTS derived_metrics;
