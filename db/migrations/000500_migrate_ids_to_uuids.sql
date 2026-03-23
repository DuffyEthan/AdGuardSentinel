--migrate:up
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE publishers
  ADD COLUMN publisher_uuid UUID;

UPDATE publishers
  SET publisher_uuid = gen_random_uuid()
  WHERE publisher_uuid IS NULL;

ALTER TABLE publishers
  ALTER COLUMN publisher_uuid SET NOT NULL;

CREATE TEMP TABLE publisher_id_map AS
  SELECT publisher_id AS old_id, publisher_uuid AS new_id
  FROM publishers;

ALTER TABLE raw_metrics
  ADD COLUMN publisher_uuid UUID;

UPDATE raw_metrics rm
  SET publisher_uuid = map.new_id
  FROM publisher_id_map map
  WHERE rm.publisher_id = map.old_id;

ALTER TABLE raw_metrics
  ALTER COLUMN publisher_uuid SET NOT NULL;

ALTER TABLE model_logs
  ADD COLUMN publisher_uuid UUID;

UPDATE model_logs ml
  SET publisher_uuid = map.new_id
  FROM publisher_id_map map
  WHERE ml.publisher_id = map.old_id;

ALTER TABLE model_logs
  ALTER COLUMN publisher_uuid SET NOT NULL;

ALTER TABLE raw_metrics
  DROP CONSTRAINT IF EXISTS raw_metrics_pkey;

ALTER TABLE raw_metrics
  DROP CONSTRAINT IF EXISTS raw_metrics_publisher_id_fkey;

ALTER TABLE model_logs
  DROP CONSTRAINT IF EXISTS model_logs_pkey;

ALTER TABLE model_logs
  DROP CONSTRAINT IF EXISTS model_logs_publisher_id_fkey;

ALTER TABLE publishers
  DROP CONSTRAINT IF EXISTS publishers_pkey;

ALTER TABLE raw_metrics
  DROP COLUMN publisher_id;

ALTER TABLE model_logs
  DROP COLUMN publisher_id;

ALTER TABLE publishers
  DROP COLUMN publisher_id;

ALTER TABLE raw_metrics
  RENAME COLUMN publisher_uuid TO publisher_id;

ALTER TABLE model_logs
  RENAME COLUMN publisher_uuid TO publisher_id;

ALTER TABLE publishers
  RENAME COLUMN publisher_uuid TO publisher_id;

ALTER TABLE publishers
  ADD PRIMARY KEY (publisher_id);

ALTER TABLE raw_metrics
  ADD PRIMARY KEY (publisher_id, bucket_timestamp);

ALTER TABLE model_logs
  ADD PRIMARY KEY (publisher_id, log_timestamp);

ALTER TABLE raw_metrics
  ADD CONSTRAINT raw_metrics_publisher_id_fkey
  FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id) ON DELETE CASCADE;

ALTER TABLE model_logs
  ADD CONSTRAINT model_logs_publisher_id_fkey
  FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id) ON DELETE CASCADE;

DROP TABLE IF EXISTS publisher_id_map;

--migrate:down
ALTER TABLE publishers
  ADD COLUMN publisher_int_id integer;

UPDATE publishers p
  SET publisher_int_id = sub.rn
  FROM (
    SELECT publisher_id, row_number() OVER (ORDER BY publisher_id) AS rn
    FROM publishers
  ) sub
  WHERE p.publisher_id = sub.publisher_id;

ALTER TABLE publishers
  ALTER COLUMN publisher_int_id SET NOT NULL;

CREATE TEMP TABLE publisher_uuid_map AS
  SELECT publisher_id AS old_id, publisher_int_id AS new_id
  FROM publishers;

ALTER TABLE raw_metrics
  ADD COLUMN publisher_int_id integer;

UPDATE raw_metrics rm
  SET publisher_int_id = map.new_id
  FROM publisher_uuid_map map
  WHERE rm.publisher_id = map.old_id;

ALTER TABLE raw_metrics
  ALTER COLUMN publisher_int_id SET NOT NULL;

ALTER TABLE model_logs
  ADD COLUMN publisher_int_id integer;

UPDATE model_logs ml
  SET publisher_int_id = map.new_id
  FROM publisher_uuid_map map
  WHERE ml.publisher_id = map.old_id;

ALTER TABLE model_logs
  ALTER COLUMN publisher_int_id SET NOT NULL;

ALTER TABLE raw_metrics
  DROP CONSTRAINT IF EXISTS raw_metrics_pkey;

ALTER TABLE raw_metrics
  DROP CONSTRAINT IF EXISTS raw_metrics_publisher_id_fkey;

ALTER TABLE model_logs
  DROP CONSTRAINT IF EXISTS model_logs_pkey;

ALTER TABLE model_logs
  DROP CONSTRAINT IF EXISTS model_logs_publisher_id_fkey;

ALTER TABLE publishers
  DROP CONSTRAINT IF EXISTS publishers_pkey;

ALTER TABLE raw_metrics
  DROP COLUMN publisher_id;

ALTER TABLE model_logs
  DROP COLUMN publisher_id;

ALTER TABLE publishers
  DROP COLUMN publisher_id;

ALTER TABLE raw_metrics
  RENAME COLUMN publisher_int_id TO publisher_id;

ALTER TABLE model_logs
  RENAME COLUMN publisher_int_id TO publisher_id;

ALTER TABLE publishers
  RENAME COLUMN publisher_int_id TO publisher_id;

ALTER TABLE publishers
  ADD PRIMARY KEY (publisher_id);

ALTER TABLE raw_metrics
  ADD PRIMARY KEY (publisher_id, bucket_timestamp);

ALTER TABLE model_logs
  ADD PRIMARY KEY (publisher_id, log_timestamp);

ALTER TABLE raw_metrics
  ADD CONSTRAINT raw_metrics_publisher_id_fkey
  FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id) ON DELETE CASCADE;

ALTER TABLE model_logs
  ADD CONSTRAINT model_logs_publisher_id_fkey
  FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id) ON DELETE CASCADE;

DROP TABLE IF EXISTS publisher_uuid_map;
