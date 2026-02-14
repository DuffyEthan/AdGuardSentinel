@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "PROJECT_ROOT=%%~fI"

echo Seeding database...
docker compose -f "%PROJECT_ROOT%\docker-compose.yml" exec db psql -U postgres -d StreamlitDB -f /seed/02_seed.sql
if errorlevel 1 (
    echo ERROR: Failed to seed the database.
    exit /b 1
)
echo Seed data loaded.

endlocal
