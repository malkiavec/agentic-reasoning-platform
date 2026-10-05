# Staging qualification

Staging is a real deployment, not a mocked CI mode.

## Required controls

1. PostgreSQL and Redis are persistent services with health checks.
2. API and worker run from the same immutable image revision.
3. `AUTH_MODE=oidc`, issuer, audience, and JWKS are mandatory.
4. Tool credentials are injected through the secret manager or environment references. Never put tokens in `tenant_integrations.config` or source control.
5. External integrations are disabled until explicitly configured for a tenant.
6. Destructive integrations remain approval-gated.
7. `/health` is liveness; `/ready` is dependency readiness.
8. `/metrics` is internal-only and must not be exposed through the public reverse proxy.
9. Backups are produced before destructive database operations and restored on a disposable database during qualification.

## Qualification sequence

    sh scripts/validate_deployment.sh
    python scripts/acceptance_smoke.py
    python scripts/load_test.py
    sh scripts/chaos_staging.sh

Then run provider and integration certification gates with read-safe test identities.

The staging exit criterion is zero failed acceptance checks, a successful backup/restore, no cross-tenant findings, and every configured integration proving the Tool Registry -> policy -> approval -> adapter path.
