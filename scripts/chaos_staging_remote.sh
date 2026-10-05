#!/usr/bin/env sh
set -eu

: "${STAGING_SSH_HOST:?STAGING_SSH_HOST is required}"
: "${STAGING_SSH_USER:?STAGING_SSH_USER is required}"
: "${STAGING_SSH_KEY_PATH:?STAGING_SSH_KEY_PATH is required}"
: "${STAGING_DEPLOY_PATH:?STAGING_DEPLOY_PATH is required}"
: "${CONTROL_PLANE_URL:?CONTROL_PLANE_URL is required}"
: "${CONTROL_PLANE_TOKEN:?CONTROL_PLANE_TOKEN is required}"

ssh_opts="-i $STAGING_SSH_KEY_PATH -o BatchMode=yes -o StrictHostKeyChecking=no"
remote="ssh $ssh_opts $STAGING_SSH_USER@$STAGING_SSH_HOST"

run_smoke() {
  python scripts/acceptance_smoke.py
}

run_remote_restart() {
  service="$1"
  echo "restarting staging service: $service"
  $remote "cd '$STAGING_DEPLOY_PATH' && docker compose -f docker-compose.prod.yml restart '$service'"
  sleep 5
  run_smoke
}

run_remote_restart worker
run_remote_restart redis
run_remote_restart postgres

echo "remote staging restart chaos qualification passed"
