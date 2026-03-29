-- migrate:up
CREATE VIEW publisher_trust_score AS
SELECT
    publisher_id,
    -- model_name,
    -- TRUST SCORE:
    -- The formula is: SUM(Score * Weight) / SUM(Weight)
    SUM(
        ((1 - score) * 100) *
        POWER(1 - (EXTRACT(EPOCH FROM (NOW() - log_timestamp)) / 86400), 2)
    )
    /
    -- We use NULLIF to prevent division by zero in the case
    -- that all logs are exactly 24 hours old (i.e. weight = 0)
    NULLIF(
        SUM(POWER(1 - (EXTRACT(EPOCH FROM (NOW() - log_timestamp)) / 86400), 2)),
        0
    ) AS trust_score,

    MAX(log_timestamp) AS last_calculated

FROM Model_Logs
WHERE log_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY publisher_id;--, model_name;

-- migrate:down
DROP VIEW IF EXISTS publisher_trust_score;