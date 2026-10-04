#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
db_url="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgresql\+asyncpg://#postgresql://#')"

psql "$db_url" --set ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
  version VARCHAR(255) PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
SQL

for migration in migrations/*.sql; do
  [ -f "$migration" ] || continue
  version="$(basename "$migration")"
  applied="$(psql "$db_url" -Atqc "SELECT 1 FROM schema_migrations WHERE version = '$version' LIMIT 1")"
  if [ "$applied" = "1" ]; then
    echo "skipping $version"
    continue
  fi
  echo "applying $version"
  psql "$db_url" --set ON_ERROR_STOP=1 --file "$migration"
  psql "$db_url" --set ON_ERROR_STOP=1 --command "INSERT INTO schema_migrations(version) VALUES ('$version')"
done
echo "migrations complete"
