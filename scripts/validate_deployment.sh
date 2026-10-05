#!/usr/bin/env sh
set -eu

: "${APP_ENV:=production}"
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${REDIS_URL:?REDIS_URL is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

case "$APP_ENV" in
  production|prod|staging)
    : "${AUTH_MODE:?AUTH_MODE is required}"
    [ "$AUTH_MODE" = "oidc" ] || {
      echo "AUTH_MODE must be oidc outside development" >&2
      exit 1
    }
    : "${OIDC_ISSUER:?OIDC_ISSUER is required}"
    : "${OIDC_AUDIENCE:?OIDC_AUDIENCE is required}"
    : "${OIDC_JWKS_URL:?OIDC_JWKS_URL is required}"
    ;;
esac

case "$REDIS_URL" in
  *localhost*|*127.0.0.1*) echo "Refusing production Redis on loopback" >&2; exit 1 ;;
esac

case "$DATABASE_URL" in
  *localhost*|*127.0.0.1*) echo "Refusing production database on loopback" >&2; exit 1 ;;
esac

echo "deployment configuration validation passed"
