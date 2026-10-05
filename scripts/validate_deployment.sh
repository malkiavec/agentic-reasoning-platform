#!/usr/bin/env sh
set -eu

: "${APP_ENV:=production}"
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${REDIS_URL:?REDIS_URL is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

reject_placeholder() {
  value="$1"
  name="$2"
  case "$value" in
    ""|CHANGE_ME|changeme|change-me|REPLACE_ME|replace-me|example.com|https://idp.example.com/*)
      echo "$name contains a placeholder value" >&2
      exit 1
      ;;
  esac
}

reject_placeholder "$DATABASE_URL" DATABASE_URL
reject_placeholder "$REDIS_URL" REDIS_URL
reject_placeholder "$POSTGRES_PASSWORD" POSTGRES_PASSWORD

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
    reject_placeholder "$OIDC_ISSUER" OIDC_ISSUER
    reject_placeholder "$OIDC_AUDIENCE" OIDC_AUDIENCE
    reject_placeholder "$OIDC_JWKS_URL" OIDC_JWKS_URL
    ;;
esac

case "$REDIS_URL" in
  *localhost*|*127.0.0.1*) echo "Refusing production Redis on loopback" >&2; exit 1 ;;
esac

case "$DATABASE_URL" in
  *localhost*|*127.0.0.1*) echo "Refusing production database on loopback" >&2; exit 1 ;;
esac

case "$DATABASE_URL" in
  *password@*|*CHANGE_ME*|*change-me*) echo "Database URL contains an unsafe placeholder/password marker" >&2; exit 1 ;;
esac

echo "deployment configuration validation passed"
