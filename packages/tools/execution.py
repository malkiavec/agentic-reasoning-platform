import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from redis.asyncio import Redis

from packages.security.kill_switch import KillSwitch
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

    def __init__(self, registry: ToolRegistry, policy: PolicyEngine | None = None, approval_service=None,
                 redis_url: str | None = None, kill_switch: KillSwitch | None = None):
        self.registry = registry
        self.policy = policy or PolicyEngine()
        self.approval_service = approval_service
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.kill_switch = kill_switch or KillSwitch(self.redis_url)

    async def execute(self, tool_name: str, arguments: dict[str, Any], *, actor: str,
                      tenant_id: str, run_id: str | None = None, request_id: str | None = None,
                      approved_approval_id: str | None = None,
                      actor_permissions: frozenset[str] = frozenset(),
                      actor_auth: frozenset[str] = frozenset(),
                      idempotency_key: str | None = None) -> ExecutionResult:
        spec = self.registry.get(tool_name)
        if spec is None:
            return ExecutionResult(False, error="tool_not_registered")
        if await self.kill_switch.is_active(tenant_id):
            return ExecutionResult(False, error="kill_switch_active")
        if spec.security.allowed_tenants is not None and tenant_id not in spec.security.allowed_tenants:
            return ExecutionResult(False, error="tool_tenant_not_allowed")
        if spec.permissions and not spec.permissions.issubset(actor_permissions):
            return ExecutionResult(False, error="tool_permission_denied")
        if spec.auth_requirements and not spec.auth_requirements.issubset(actor_auth):
            return ExecutionResult(False, error="tool_auth_requirement_missing")
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

        redis = Redis.from_url(self.redis_url, decode_responses=True)
        lock_key = f"agent:tool:lock:{tenant_id}:{action_id}"
        idem_key = idempotency_key or f"{run_id or request_id or actor}:{action_id}"
        result_key = f"agent:tool:result:{tenant_id}:{idem_key}"
        acquired = False
        try:
            window = int(time.time() // 60)
            rate_key = f"agent:tool:rate:{tenant_id}:{tool_name}:{window}"
            count = await redis.incr(rate_key)
            if count == 1:
                await redis.expire(rate_key, 120)
            if count > spec.rate_limit_per_minute:
                return ExecutionResult(False, error="tool_rate_limit_exceeded", action_id=action_id)

            if spec.security.idempotent:
                cached = await redis.get(result_key)
                if cached:
                    try:
                        return ExecutionResult(True, output=json.loads(cached), action_id=action_id)
                    except json.JSONDecodeError:
                        await redis.delete(result_key)

            acquired = bool(await redis.set(lock_key, actor, nx=True, ex=max(1, int(spec.security.timeout_seconds) + 5)))
            if not acquired:
                return ExecutionResult(False, error="tool_execution_locked", action_id=action_id)

            context = ToolContext(tenant_id=tenant_id, actor=actor, run_id=run_id or "", request_id=request_id or run_id or "")
            try:
                value = await asyncio.wait_for(adapter.invoke(arguments, context), timeout=spec.security.timeout_seconds)
            except TimeoutError:
                return ExecutionResult(False, error="tool_timeout", action_id=action_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                return ExecutionResult(False, error=f"tool_error:{type(exc).__name__}", action_id=action_id)

            if spec.output_schema is not None and list(Draft202012Validator(spec.output_schema).iter_errors(value)):
                return ExecutionResult(False, error="invalid_tool_output", action_id=action_id)
            if spec.security.idempotent:
                try:
                    await redis.set(result_key, json.dumps(value, ensure_ascii=False), ex=86400)
                except (TypeError, ValueError):
                    pass
            return ExecutionResult(True, output=value, approval_id=approved_approval_id, action_id=action_id)
        finally:
            if acquired:
                await redis.delete(lock_key)
            await redis.aclose()
