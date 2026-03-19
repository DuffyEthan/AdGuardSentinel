-- migrate:up
CREATE TABLE IF NOT EXISTS publishers(
  publisher_id     INTEGER PRIMARY KEY,
  publisher_name   TEXT NOT NULL
);

-- migrate:down
DROP TABLE IF EXISTS publishers;
