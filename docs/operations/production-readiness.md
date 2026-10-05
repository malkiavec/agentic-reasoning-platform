# Production readiness and release gates

## Build
- Python dependency resolution is deterministic.
- Ruff, pytest, pip-audit, frontend build, npm audit, and PostgreSQL restore pass.
- No open PR remains unresolved before release promotion.

## Security
- OIDC issuer, audience, and JWKS are mandatory outside development.
- Tenant membership is enforced.
- Every executable tool must be registered.
- Every integration is tenant-configured before execution.
- Credentials are resolved by tenant and optional secret reference and never enter model context.
- High-risk actions require persistent approval.
- Kill switch fails closed when Redis is unavailable in production.
- SSRF and egress boundaries reject private and metadata targets.

## Durability
- Tool actions use a durable PostgreSQL ledger.
- Idempotent actions replay from completed ledger records.
- Ambiguous non-idempotent actions enter `recovery_required` instead of being duplicated.
- Celery retries transient runtime failures with bounded exponential backoff.
- PostgreSQL, Redis, and worker restart qualification is executed in staging.

## Operations
- Runs, events, audit, approvals, policies, budgets, integrations, retry/cancel, and kill switch are tenant-bound.
- Prometheus and OpenTelemetry hooks are enabled.
- API readiness checks PostgreSQL and Redis.
- Backup/restore is tested from an actual dump.

## External certification
For every enabled provider or integration: credentials are injected only through secret references; read-only smoke operations succeed; timeout/error behavior is captured; tenant isolation is proven; approval-gated writes reject forged approval IDs; and audit records contain actor, tenant, tool, and decision.

## Load and chaos
The release candidate must pass the bounded load test and staging restart chaos harness. Full production-scale load and failure injection run against staging infrastructure, never customer systems.

## Release procedure
1. Build and tag immutable API/worker images from the release commit.
2. Apply migrations before enabling traffic.
3. Verify `/ready`.
4. Run backup and restore verification.
5. Run authenticated smoke and load tests.
6. Enable integrations one tenant at a time.
7. Monitor errors, latency, queue depth, approval backlog, and budget consumption.
8. Roll back application images first; roll back migrations only with a tested forward migration strategy.
