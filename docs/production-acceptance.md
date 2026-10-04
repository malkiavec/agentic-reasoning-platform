# 1.0 Production Acceptance

The platform is considered 1.0-ready only when all gates below are green.

## Functional path
- Authenticated tenant submits a run.
- Planner produces a validated plan.
- Every tool call passes through Tool Registry and PolicyEngine.
- Risky actions create persistent HITL approvals.
- Completed steps are checkpointed.
- Run events are durably persisted and replayable.
- API/worker restart resumes from the last checkpoint.
- Idempotent actions deduplicate through the durable action ledger.
- Ambiguous non-idempotent actions enter recovery_required and are never blindly replayed.

## Security
- Unknown tools are denied.
- Tenant boundaries are enforced on runs, approvals, events, credentials and tools.
- Credentials are tenant-scoped and never exposed to model context.
- Kill switches are enforced before tool execution.
- Approval decisions are actor-bound and action-hash-bound.
- SSRF and outbound domains are allowlisted.
- Tool arguments and outputs are schema-validated and redacted where required.
- Prompt-injection/guardrail tests pass.

## Reliability
- Worker retries are bounded with backoff.
- Step and run deadlines are enforced.
- Cancellation is persisted and observed by workers.
- Durable action ledger prevents duplicate non-idempotent replay.
- PostgreSQL backup/restore verification passes.
- CI runs PostgreSQL, pgvector and Redis integration services.

## Control plane
- Authenticated run listing.
- Live/replayable execution events.
- Cancel/retry operations.
- Approval operations.
- Tool inventory.
- Kill-switch administration.
- System metrics and health endpoints.
- Dashboard consumes live API data rather than mock telemetry.

## Verification
CI must pass:
1. Ruff
2. pip-audit
3. Unit tests
4. Integration tests
5. Frontend production build
6. npm audit
7. PostgreSQL backup/restore verification

Load, concurrency, chaos and external-provider acceptance tests must additionally pass in the deployment environment before sensitive production workloads.