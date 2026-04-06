#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load env vars from the secrets file
set -a
# shellcheck source=../.secrets/.env
source .secrets/.env
set +a

# ── 1. DB + FastAPI (depends_on handles DB startup order) ───────────────────
echo "[backend] Starting FastAPI + TimescaleDB..."
docker-compose up -d fastapi
FASTAPI_PID=""

# The generator runs on the host, not inside Docker, so it cannot resolve the
# 'db' Docker-internal hostname. Rewrite DATABASE_URL to use the mapped port.
DATABASE_URL="${DATABASE_URL//@db:5432/@localhost:5433}"
export DATABASE_URL

# Wait until the DB is actually accepting connections before launching the generator
echo "[backend] Waiting for database to accept connections..."
until docker exec app_timescale_db pg_isready -q 2>/dev/null; do
  sleep 1
done
echo "[backend] Database ready."

# ── 3. Data generator ────────────────────────────────────────────────────────
echo "[backend] Starting data generator (RUN_FOREVER=true, interval=5 min)..."
RUN_FOREVER=true python3 -m app.ml.time_series_data_generator &
DATAGEN_PID=$!

# ── Cleanup ──────────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "[backend] Shutting down data generator..."
  kill "$DATAGEN_PID" 2>/dev/null || true
  echo "[backend] Stopping FastAPI + database..."
  docker-compose stop fastapi db
  echo "[backend] Done."
}
trap cleanup INT TERM

echo "[backend] All services running. Ctrl+C to stop everything."
wait
