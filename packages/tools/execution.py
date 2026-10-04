from dataclasses import dataclass
from typing import Any
from jsonschema import Draft202012Validator
from packages.security.policy import Action, PolicyEngine

@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    output: Any = None
    error: str | None = None

class ToolExecutor:
    """Policy-enforced execution boundary: validate -> authorize -> execute."""
    def __init__(self, registry, policy: PolicyEngine | None = None):
        self.registry = registry
        self.policy = policy or PolicyEngine()

    async def execute(self, tool_name: str, arguments: dict, *, actor: str, tenant_id: str) -> ExecutionResult:
        spec = self.registry.get(tool_name)
        if spec is None:
            return ExecutionResult(False, error="tool_not_registered")
        errors = list(Draft202012Validator(spec.input_schema).iter_errors(arguments))
        if errors:
            return ExecutionResult(False, error="invalid_tool_arguments")
        decision = self.policy.evaluate(Action(tool=tool_name, arguments=arguments, actor=actor, tenant_id=tenant_id))
        if not decision.allowed:
            return ExecutionResult(False, error=decision.reason)
        if decision.requires_approval or spec.requires_approval:
            return ExecutionResult(False, error="approval_required")
        handler = self.registry.handler(tool_name)
        if handler is None:
            return ExecutionResult(False, error="tool_handler_unavailable")
        value = handler(**arguments)
        if hasattr(value, "__await__"):
            value = await value
        return ExecutionResult(True, output=value)
