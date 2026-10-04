from typing import Any

from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity

class EchoAdapter(ToolAdapter):
    name = "echo"
    security = ToolSecurity(risk="low", idempotent=True)

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        return {"text": arguments["text"], "tenant_id": context.tenant_id}

class ApprovalProbeAdapter(ToolAdapter):
    name = "approval_probe"
    security = ToolSecurity(risk="high", requires_approval=True, idempotent=True)

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        return {"approved_action": arguments["action"], "run_id": context.run_id}
