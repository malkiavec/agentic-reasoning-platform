# Platform roadmap

## Implemented foundation
- Durable run records and checkpoints
- Celery/Redis asynchronous execution
- Policy enforcement and HITL primitives
- Tool schema validation
- Tenant isolation primitives
- WebSocket transport
- Security guardrails and output validation
- Model, planner, retrieval, memory, multimodal, and evaluation contracts

## Next production layers
1. Redis-backed event streaming and durable event history
2. Real provider adapters and model routing/fallback
3. PostgreSQL vector/lexical memory implementation with provenance and deduplication
4. Browser/computer-use sandbox with controlled egress
5. Approval persistence, multi-approver workflows, and emergency kill switch
6. OpenTelemetry metrics/traces and Prometheus/Grafana dashboards
7. API authentication, JWT/OIDC, tenant RBAC, quotas, and request signing
8. Production Nginx/TLS, backups, restore verification, and deployment manifests
9. Web control plane for runs, approvals, tools, memory, and evaluations
10. Benchmark runners for long-context and long-horizon agentic tasks
