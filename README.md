# AdGuard Anomaly Detection

## Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js & npm](https://nodejs.org/) — required for the React frontend
- [dbmate](https://github.com/amacneil/dbmate) — database migration tool

### Installing dbmate

**macOS (Homebrew):**
```bash
brew install dbmate
```

**Linux:**
```bash
sudo curl -fsSL -o /usr/local/bin/dbmate https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64
sudo chmod +x /usr/local/bin/dbmate
```

**Windows (Winget):**
```bash
winget install dbmate
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
```

Edit these files if you need to change the default credentials. The defaults work out of the box for local development.

> **Note:** The `dbmate` command reads its configuration from `db/.env`. If you encounter authentication issues, ensure that the `DATABASE_URL` in `db/.env` has the correct password and is not relying on an environment variable that may not be set in your shell. The default password is `changeme`.

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

or (depending on how your python is setup)

```bash
pip3 install -r requirements.txt
```

### 3a. Install React frontend dependencies

```bash
cd app/frontend
npm install
```

### 4. Start Backend Services

```bash
docker compose up --build -d
```

This command starts the database, FastAPI backend, and the data orchestrator. The orchestrator will automatically begin seeding the database with sample data, so no manual seeding is required.

Wait a few seconds for the services to initialize.


### 5. Run Database Migrations

```bash
cd db
dbmate up
```

This creates the database schema (tables, extensions, hypertables). You should see:

```
Applying: 000100_extensions.sql
Applying: 000200_create_publishers.sql
```

### 6. Run the app

**Run the React frontend:**
```bash
cd app/frontend
npm run dev
```

The dashboard is available at http://localhost:5173.

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
000200_create_publishers.sql
000300_create_raw_metrics.sql
...
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
from app.db.models import Publishers

with get_session() as session:
    results = session.query(Publishers).all()
```

> **Note:** `DATABASE_URL` must be set in the environment for the SQLAlchemy engine to initialize.

## Project Structure

```
├── .secrets/
│   ├── .env.example             # Docker/database credentials template
│   └── .env                     # Local credentials (not committed)
├── app/
│   ├── db/
│   │   ├── __init__.py          # SQLAlchemy engine + session factory
│   │   ├── models.py            # Auto-generated models (sqlacodegen)
│   │   └── session.py           # get_session() context manager
│   ├── fastapi/
│   │   └── main.py              # FastAPI app entry point
│   ├── frontend/                # React + Vite frontend
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── src/
│   │       ├── App.tsx
│   │       ├── main.tsx
│   │       ├── components/      # Reusable UI components
│   │       │   ├── AnomalyArea.tsx
│   │       │   ├── Navbar.tsx
│   │       │   ├── Sidebar.tsx
│   │       │   └── TimeSeriesChart.tsx
│   │       ├── context/
│   │       │   └── ThemeContext.tsx
│   │       └── pages/
│   │           ├── Dashboard.tsx
│   │           └── Home.tsx
│   ├── ml/
│   │   ├── _isolation_forest.py # Isolation Forest anomaly detection
│   │   ├── batch_data_generator.py
│   │   └── markov.py            # Markov chain data generator
│   ├── repositories/
│   │   ├── base.py
│   │   ├── model_logs_repository.py
│   │   └── raw_metrics_repository.py
├── db/
│   ├── init/
│   │   └── 02_seed.sql          # Seed data
│   ├── migrations/
│   │   ├── 000100_extensions.sql
│   │   ├── 000200_create_publishers.sql
│   │   ├── 000300_create_raw_metrics.sql
│   │   ├── 000400_create_model_logs.sql
│   │   ├── 000500_migrate_ids_to_uuids.sql
│   │   ├── 000600_model_reports.sql
│   │   └── 000700_create_campaigns.sql
│   ├── scripts/
│   │   ├── generate_models.sh   # Regenerate SQLAlchemy models (macOS/Linux)
│   │   ├── generate_models.bat  # Regenerate SQLAlchemy models (Windows)
│   │   ├── seed.sh              # Load seed data (macOS/Linux)
│   │   └── seed.bat             # Load seed data (Windows)
│   ├── .env.example             # dbmate environment config
│   └── schema.sql               # Full schema dump (auto-generated)
├── tests/
│   ├── conftest.py
│   ├── test_model_logs_repository.py
│   └── test_raw_metrics_repository.py
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
```

## CI Pipeline

The CI pipeline automatically:

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


## Contributors

- Alexander Nevin
- Alex Leung
- Zofia Marta Sekulska
- Thomas Shanahan
