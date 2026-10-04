import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from packages.security.policy import Action, PolicyEngine
from packages.tools.contracts import ToolContext
from packages.tools.registry import ToolRegistry

def action_fingerprint(tool: str, arguments: dict[str, Any]) -> str:
    payload = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()

@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    output: Any = None
    error: str | None = None
    approval_id: str | None = None
    action_id: str | None = None

class ToolExecutor:
    """Final policy enforcement point for every Tool Registry action."""

    def __init__(self, registry: ToolRegistry, policy: PolicyEngine | None = None, approval_service=None):
        self.registry = registry
        self.policy = policy or PolicyEngine()
        self.approval_service = approval_service

    async def execute(self, tool_name: str, arguments: dict[str, Any], *, actor: str,
                      tenant_id: str, run_id: str | None = None, request_id: str | None = None,
                      approved_approval_id: str | None = None) -> ExecutionResult:
        spec = self.registry.get(tool_name)
        if spec is None:
            return ExecutionResult(False, error="tool_not_registered")
        if spec.security.allowed_tenants is not None and tenant_id not in spec.security.allowed_tenants:
            return ExecutionResult(False, error="tool_tenant_not_allowed")
        if list(Draft202012Validator(spec.input_schema).iter_errors(arguments)):
            return ExecutionResult(False, error="invalid_tool_arguments")
        if spec.allowed_agents is not None and actor not in spec.allowed_agents:
            return ExecutionResult(False, error="tool_actor_not_allowed")

        decision = self.policy.evaluate(Action(tool=tool_name, arguments=arguments, actor=actor, tenant_id=tenant_id))
        if not decision.allowed:
            return ExecutionResult(False, error=decision.reason)

        action_id = action_fingerprint(tool_name, arguments)
        needs_approval = decision.requires_approval or spec.requires_approval
        if needs_approval and approved_approval_id is None:
            if self.approval_service is None or run_id is None:
                return ExecutionResult(False, error="approval_required", action_id=action_id)
            approval = await self.approval_service.request(
                run_id=run_id, tenant_id=tenant_id, actor=actor, tool=tool_name,
                arguments=arguments, risk=decision.risk.name.lower(),
            )
            return ExecutionResult(False, error="approval_pending", approval_id=str(approval.id), action_id=action_id)

        if needs_approval and (
            self.approval_service is None or
            not await self.approval_service.verify(
                approval_id=approved_approval_id, run_id=run_id, tenant_id=tenant_id,
                tool=tool_name, arguments=arguments,
            )
        ):
            return ExecutionResult(False, error="approval_invalid", action_id=action_id)

        adapter = self.registry.adapter(tool_name)
        if adapter is None:
            return ExecutionResult(False, error="tool_adapter_unavailable", action_id=action_id)

        context = ToolContext(tenant_id=tenant_id, actor=actor, run_id=run_id or "", request_id=request_id or run_id or "")
        try:
            value = await asyncio.wait_for(adapter.invoke(arguments, context), timeout=spec.security.timeout_seconds)
        except TimeoutError:
            return ExecutionResult(False, error="tool_timeout", action_id=action_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            return ExecutionResult(False, error=f"tool_error:{type(exc).__name__}", action_id=action_id)
        return ExecutionResult(True, output=value, approval_id=approved_approval_id, action_id=action_id)
