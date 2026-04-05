-- migrate:up
CREATE VIEW publisher_trust_score AS

-- Step 1: Get a unique list of publishers
WITH Publishers AS (
    SELECT DISTINCT publisher_id FROM model_logs
),
-- Step 2: Get the newest timestamp for each publisher
LatestLogs AS (
    SELECT p.publisher_id, l.latest_ts
    FROM Publishers p
    CROSS JOIN LATERAL (
        SELECT log_timestamp AS latest_ts
        FROM model_logs m
        WHERE m.publisher_id = p.publisher_id
        ORDER BY log_timestamp DESC
        LIMIT 1
    ) l
)
-- Step 3: Fetch the last 24 hours of logs relative to that newest timestamp
SELECT
    ll.publisher_id,
    ll.latest_ts as latest_ts,

    SUM(
        ((1 - logs.score) * 100) *
        POWER(1 - (EXTRACT(EPOCH FROM (ll.latest_ts - logs.log_timestamp)) / 86400), 2)
    )
    /
    NULLIF(
        SUM(POWER(1 - (EXTRACT(EPOCH FROM (ll.latest_ts - logs.log_timestamp)) / 86400), 2)),
        0
    ) AS trust_score

FROM LatestLogs ll
JOIN LATERAL (
    SELECT score, log_timestamp
    FROM model_logs m
    WHERE m.publisher_id = ll.publisher_id
      AND m.log_timestamp >= ll.latest_ts - INTERVAL '24 hours'
      AND m.log_timestamp <= ll.latest_ts
) logs ON true
GROUP BY ll.publisher_id, ll.latest_ts;

-- migrate:down
DROP VIEW IF EXISTS publisher_trust_score;