#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_DIR:=./backups}"
: "${BACKUP_RETENTION_DAYS:=14}"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
db_url="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+asyncpg://#postgresql://#')"
output="$BACKUP_DIR/agentic-$timestamp.dump"

pg_dump "$db_url" --format=custom --no-owner --no-acl --file="$output"
chmod 600 "$output"

find "$BACKUP_DIR" -type f -name 'agentic-*.dump' -mtime +"$BACKUP_RETENTION_DAYS" -delete
echo "backup created: $output"
