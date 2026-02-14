#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Seeding database..."
docker compose -f "$PROJECT_ROOT/docker-compose.yml" exec db psql -U postgres -d StreamlitDB -f /seed/02_seed.sql
echo "Seed data loaded."
