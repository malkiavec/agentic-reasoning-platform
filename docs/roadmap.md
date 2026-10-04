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

## Remaining production gates
1. Complete provider-specific multimodal/streaming conformance tests against each vendor's current API.
2. Finish browser/computer-use sandboxing and business-app adapters (Slack, Gmail, Drive, Notion, Linear, Jira, databases, webhooks, MCP).
3. Add full load, chaos, penetration, SSRF, prompt-injection, and disaster-recovery restore tests in a production-like environment.
4. Complete authenticated control-plane wiring and operational dashboards.
5. Execute the registered benchmark suites and establish regression thresholds before production promotion.
