-- migrate:up
CREATE TABLE IF NOT EXISTS publishers(
  publisher_id     integer PRIMARY KEY,
  publisher_name   text    NOT NULL
);

-- migrate:down
DROP TABLE IF EXISTS publishers;
