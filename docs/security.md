# Security model

The platform treats model output as untrusted intent.

1. Input passes through guardrails.
2. The model may propose a tool call, but cannot authorize it.
3. Tool arguments are schema-validated.
4. The policy engine evaluates tenant, actor, tool, and risk.
5. High-risk actions pause for human approval.
6. Adapters execute with isolated credentials and controlled egress.
7. Outputs are validated/redacted before persistence or delivery.
8. Audit events provide an immutable operational trail.

Secrets must remain in the execution environment and are never injected into model context unless explicitly required by a narrowly scoped adapter contract.
