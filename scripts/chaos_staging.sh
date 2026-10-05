#!/usr/bin/env sh
set -eu

: "${COMPOSE_FILE:=docker-compose.prod.yml}"
: "${CHAOS_COMPOSE_PROJECT:=agentic-staging}"
: "${CONTROL_PLANE_URL:?CONTROL_PLANE_URL is required}"
: "${CONTROL_PLANE_TOKEN:?CONTROL_PLANE_TOKEN is required}"

export COMPOSE_FILE CHAOS_COMPOSE_PROJECT

run_smoke() {
  python scripts/acceptance_smoke.py
}

echo "baseline smoke"
run_smoke

echo "worker restart recovery"
docker compose -p "$CHAOS_COMPOSE_PROJECT" restart worker
run_smoke

echo "redis restart recovery"
docker compose -p "$CHAOS_COMPOSE_PROJECT" restart redis
run_smoke

echo "postgres restart recovery"
docker compose -p "$CHAOS_COMPOSE_PROJECT" restart postgres
run_smoke

echo "chaos acceptance passed"
