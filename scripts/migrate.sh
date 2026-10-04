#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
db_url="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+asyncpg://#postgresql://#')"

for migration in migrations/*.sql; do
  [ -f "$migration" ] || continue
  echo "applying $migration"
  psql "$db_url" --set ON_ERROR_STOP=1 --file "$migration"
done
echo "migrations complete"
