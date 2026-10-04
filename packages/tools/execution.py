from dataclasses import dataclass
from typing import Any
from jsonschema import Draft202012Validator
from packages.security.policy import Action, PolicyEngine
from packages.tools.registry import ToolRegistry

@dataclass(frozen=True)
class ApprovalRequired:
    approval_id: str

@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    output: Any=None
    error: str|None=None
    approval_id: str|None=None

class ToolExecutor:
    """Only authorized, schema-valid tools can execute. Approval is a first-class result."""
    def __init__(self, registry: ToolRegistry, policy: PolicyEngine|None=None, approval_service=None):
        self.registry=registry
        self.policy=policy or PolicyEngine()
        self.approval_service=approval_service

    async def execute(self, tool_name: str, arguments: dict, *, actor: str, tenant_id: str,
                      run_id: str|None=None) -> ExecutionResult:
        spec=self.registry.get(tool_name)
        if spec is None:
            return ExecutionResult(False,error="tool_not_registered")
        errors=list(Draft202012Validator(spec.input_schema).iter_errors(arguments))
        if errors:
            return ExecutionResult(False,error="invalid_tool_arguments")
        decision=self.policy.evaluate(Action(tool=tool_name,arguments=arguments,actor=actor,tenant_id=tenant_id))
        if not decision.allowed:
            return ExecutionResult(False,error=decision.reason)
        if decision.requires_approval or spec.requires_approval:
            if self.approval_service is None or run_id is None:
                return ExecutionResult(False,error="approval_service_unavailable")
            approval=await self.approval_service.request(run_id=run_id,tenant_id=tenant_id,
                actor=actor,tool=tool_name,arguments=arguments,risk=decision.risk.name.lower())
            return ExecutionResult(False,error="approval_pending",approval_id=str(approval.id))
        handler=self.registry.handler(tool_name)
        if handler is None:
            return ExecutionResult(False,error="tool_handler_unavailable")
        value=handler(**arguments)
        if hasattr(value,"__await__"):
            value=await value
        return ExecutionResult(True,output=value)
