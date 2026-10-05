#!/usr/bin/env sh
set -eu

: "${STAGING_SSH_HOST:?STAGING_SSH_HOST is required}"
: "${STAGING_SSH_USER:?STAGING_SSH_USER is required}"
: "${STAGING_SSH_KEY_PATH:?STAGING_SSH_KEY_PATH is required}"
: "${STAGING_DEPLOY_PATH:?STAGING_DEPLOY_PATH is required}"
: "${RELEASE_SHA:?RELEASE_SHA is required}"

ssh_opts="-i $STAGING_SSH_KEY_PATH -o BatchMode=yes -o StrictHostKeyChecking=no"
remote="ssh $ssh_opts $STAGING_SSH_USER@$STAGING_SSH_HOST"

$remote "cd '$STAGING_DEPLOY_PATH' && git fetch --prune origin && git checkout --detach '$RELEASE_SHA' && sh scripts/validate_deployment.sh && docker compose -f docker-compose.prod.yml config >/dev/null && docker compose -f docker-compose.prod.yml up -d --build --remove-orphans"

$remote "cd '$STAGING_DEPLOY_PATH' && docker compose -f docker-compose.prod.yml ps && docker compose -f docker-compose.prod.yml exec -T api python -c 'import os; print(os.environ.get("APP_ENV"), os.environ.get("ENVIRONMENT"))'"

echo "staging deployment completed for $RELEASE_SHA"
