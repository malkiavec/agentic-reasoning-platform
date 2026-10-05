#!/usr/bin/env sh
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${PSQL_DATABASE_URL:?PSQL_DATABASE_URL is required}"
: "${BACKUP_DIR:=./backups}"
sh scripts/backup_postgres.sh
latest="$(ls -1t "$BACKUP_DIR"/agentic-*.dump | head -n 1)"
restore_url="$(printf '%s' "$PSQL_DATABASE_URL" | sed 's#/agentic$#/agentic_restore#')"
psql "$PSQL_DATABASE_URL" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS agentic_restore WITH (FORCE);" -c "CREATE DATABASE agentic_restore;"
pg_restore --dbname="$restore_url" --no-owner --no-acl --exit-on-error "$latest"
psql "$restore_url" -v ON_ERROR_STOP=1 -c "SELECT 1 FROM schema_migrations ORDER BY version DESC LIMIT 1;"
echo "restore verification passed: $latest"
