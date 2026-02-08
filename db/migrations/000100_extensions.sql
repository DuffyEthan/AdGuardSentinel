-- migrate:up
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- migrate:down
DROP EXTENSION IF EXISTS timescaledb;
