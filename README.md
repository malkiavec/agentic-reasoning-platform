# Agentic Reasoning Platform

Security-first foundation for long-horizon, multimodal, multi-agent workloads.

## Core architecture

- FastAPI API + WebSocket streaming
- Celery + Redis asynchronous execution
- PostgreSQL + pgvector memory and retrieval
- External policy enforcement point before every tool/action
- Human-in-the-loop approvals with risk scoring and expiration
- Provider-agnostic reasoning/model gateway
- Multimodal ingestion interfaces for text, images, video, and PDF
- Multi-agent planning, delegation, and parallel execution
- Browser/computer-use adapters behind security controls
- Structured outputs and parallel tool calling
- OpenTelemetry-ready tracing, metrics, audit logs, token/cost/latency tracking
- Docker Compose deployment and backup/restore hooks
- Evaluation harness and benchmark integration points
- Web control plane for agents, runs, approvals, tools, memory, security, and observability

## Security model

The model proposes actions; the policy engine authorizes them; validated tool adapters execute only authorized actions. Secrets remain outside prompts and model context.

## Repository layout

- apps/: API, worker, web control plane, model/tool gateway
- packages/: runtime, orchestration, memory, retrieval, guardrails, tools, security, evaluations, observability
- infrastructure/: Docker, nginx, PostgreSQL, Redis, backups
- migrations/: database migrations
- tests/: unit, integration, security, evaluations
- docs/: architecture and operations
- .github/: CI workflows

## Status

Initial production-oriented scaffold. Provider adapters, browser/computer-use backends, benchmark runners, and integrations are modular and replaceable.
