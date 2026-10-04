# Architecture

## Execution path

Input -> guardrails -> planner -> policy enforcement point -> tool adapter -> checkpoint -> result.

The LLM is untrusted with respect to authorization. It may propose a tool call, but an external policy engine decides whether it is permitted and whether human approval is required.

## Planned production modules

1. Durable SQL-backed run/checkpoint store.
2. Celery retry/backoff, dead-letter handling, idempotency and cancellation.
3. Tenant-aware RBAC and audit log.
4. Model gateway adapters with streaming, structured output, parallel tool calls and configurable reasoning effort.
5. Multimodal document/video/image ingestion and smart document parsing.
6. Hybrid vector/lexical retrieval with reranking and provenance.
7. Browser/computer-use sandbox adapters.
8. HITL approval service with expiry, quorum and emergency kill switch.
9. OpenTelemetry traces and Prometheus metrics.
10. Evaluation runners for long-context, coding, search and automation benchmarks.
