# AdGuard Anomaly Detection

## Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [Python 3.10+](https://www.python.org/downloads/)
- [dbmate](https://github.com/amacneil/dbmate) — database migration tool

### Installing dbmate

**macOS (Homebrew)[Recommended]:**
```bash
brew install dbmate
```

**Linux[Recommended]:**
```bash
sudo curl -fsSL -o /usr/local/bin/dbmate https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64
sudo chmod +x /usr/local/bin/dbmate
```

**Windows (Scoop):**
```bash
scoop install dbmate
```

**Windows (Winget)[Recommended]:**
```bash
winget install dbmate
```

**Windows/macOS/Linux (NPM):**
```bash
npm install -g dbmate
```

## Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd sweng26_group20-adguardanomalydetection
```

### 2. Set up environment files

```bash
# Docker database credentials
cp .secrets/.env.example .secrets/.env

# dbmate config (for running migrations locally)
cp db/.env.example db/.env

# Streamlit secrets (for running the frontend locally)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit these files if you need to change the default credentials. The defaults work out of the box for local development.

> **Note:** When running the frontend locally (not via Docker), change `DB_HOST` in `.streamlit/secrets.toml` from `db` to `localhost`.

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

or (depending on how your python is setup)

```bash
pip3 install -r requirements.txt
```

### 4. Start the database

```bash
docker compose up db -d
```

Wait a few seconds for TimescaleDB to initialize.


### 5. Run database migrations

```bash
cd db
dbmate up
```

This creates the database schema (tables, extensions, hypertables). You should see:

```
Applying: 000100_extensions.sql
Applying: 000200_create_impression.sql
```

### 6. Seed the database with data (optional)

**macOS/Linux:**
```bash
./db/scripts/seed.sh
```

**Windows:**
```cmd
db\scripts\seed.bat
```

This loads sample impression data into the database.

### 7. Run the app

**run the Streamlit frontend directly:**
```bash
streamlit run frontend/frontend.py
```

The dashboard is available at http://localhost:8501.

## Database Migrations

Migrations are managed with [dbmate](https://github.com/amacneil/dbmate) using plain SQL files in `db/migrations/`.

All dbmate commands should be run from the `db/` directory:

```bash
cd db
```

| Task | Command |
|------|---------|
| Apply pending migrations | `dbmate up` |
| Roll back last migration | `dbmate down` |
| Check migration status | `dbmate status` |
| Create a new migration | `dbmate new <name>` |
| Drop and recreate the DB | `dbmate drop && dbmate up` |

### Creating a new migration

```bash
cd db
dbmate new add_users_table
```

This creates a file in `db/migrations/` with a timestamp prefix. **Rename it to use the project's sequential numbering scheme** — migrations use a `000x00_` format that increments by 100:

```
000100_extensions.sql
000200_create_impression.sql
000300_add_users_table.sql
000400_add_analytics.sql
...
000900_something.sql
001000_another_thing.sql
001100_yet_another.sql
```

Leaving a gap of 100 between each migration number (e.g., `000200`, `000300`) allows you to insert multiple related migrations in sequence. For example, if you create a `users` table at `000300_add_users_table.sql` and later need to add columns or indexes to that table, you can add files like `000310_add_username_to_users.sql`, `000320_add_user_profile.sql`, etc., grouped together and still in the correct order.

**Note:** Once a migration file has been merged into the `develop` branch, **do not modify it**. Always create a new migration file to make changes, instead of editing existing migrations.

Edit the SQL:

```sql
-- migrate:up
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE IF EXISTS users;
```

Apply it with `dbmate up`, then regenerate the SQLAlchemy models.

## SQLAlchemy ORM

SQLAlchemy models are auto-generated from the live database schema using [sqlacodegen](https://github.com/agronholm/sqlacodegen).

After applying new migrations, regenerate the models:

**macOS/Linux:**
```bash
cd db
./scripts/generate_models.sh
```

**Windows:**
```cmd
cd db
scripts\generate_models.bat
```

This writes `app/db/models.py`. Commit the regenerated file alongside your migration.

### Using the ORM in code

```python
from app.db.session import get_session
from app.db.models import t_impression

with get_session() as session:
    results = session.execute(t_impression.select()).fetchall()
```

> **Note:** `DATABASE_URL` must be set in the environment for the SQLAlchemy engine to initialize.

## Project Structure

```
├── app/
│   ├── db/
│   │   ├── __init__.py          # SQLAlchemy engine + session factory
│   │   ├── models.py            # Auto-generated models (sqlacodegen)
│   │   └── session.py           # get_session() context manager
│   ├── ml/
│   │   └── markov.py            # Markov chain data generator
│   └── main.py                  # App entry point
├── db/
│   ├── init/
│   │   └── 02_seed.sql          # Seed data
│   ├── migrations/
│   │   ├── 000100_extensions.sql
│   │   └── 000200_create_impression.sql
│   ├── scripts/
│   │   ├── generate_models.sh   # Regenerate SQLAlchemy models (macOS/Linux)
│   │   ├── generate_models.bat  # Regenerate SQLAlchemy models (Windows)
│   │   ├── seed.sh              # Load seed data (macOS/Linux)
│   │   └── seed.bat             # Load seed data (Windows)
│   ├── .env.example             # dbmate environment config
│   └── schema.sql               # Full schema dump (auto-generated)
├── frontend/
│   └── frontend.py              # Streamlit dashboard
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .gitlab-ci.yml
```

## CI Pipeline

The GitLab CI pipeline automatically:

1. Starts a fresh TimescaleDB container
2. Installs dbmate and runs all migrations — **pipeline fails if any migration fails**
3. Installs Python dependencies
4. Runs pytest — **pipeline fails if any test fails**

No manual database setup is needed in CI.

# Running Fast API server

1. Navigate to the project directory
2. Create environment configuration - copied from .secrets\.env.example 
3. Copy the env file to the db folder (.\.secrets\.env .\db\.env)
4. Start the database and FastAPI services: "docker-compose down", "docker compose build --no-cache", "docker-compose up fastapi"
5. Verify its working, open http://localhost:8000, should see "{"Hello":"World"}"
6. To stop the services: "docker-compose down"

Current available Endpoints:
1. GET / - Health check
2. GET /model-logs/get-between?t1=<datetime>&t2=<datetime>&publisher_id=<id> - Get model logs
3. GET /raw-metrics/get-last-n-before?t=<datetime>&n=<count>&publisher_id=<id> - Get metrics


## Contributors

- Alexander Nevin
- Alex Leung
- Zofia Marta Sekulska
- Thomas Shanahan
