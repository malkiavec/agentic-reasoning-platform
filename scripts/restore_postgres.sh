#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${CONFIRM_RESTORE:?CONFIRM_RESTORE=YES is required}"

if [ "$CONFIRM_RESTORE" != "YES" ]; then
  echo "Refusing restore: set CONFIRM_RESTORE=YES" >&2
  exit 1
fi

db_url="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+asyncpg://#postgresql://#')"
pg_restore "$db_url" --clean --if-exists --no-owner --no-acl --exit-on-error "$BACKUP_FILE"
echo "restore completed: $BACKUP_FILE"
