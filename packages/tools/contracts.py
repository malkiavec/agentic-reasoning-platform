from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ToolSecurity:
    risk: str = "low"
    requires_approval: bool = False
    timeout_seconds: float = 30.0
    idempotent: bool = True
    allowed_tenants: frozenset[str] | None = None

@dataclass(frozen=True)
class ToolContext:
    tenant_id: str
    actor: str
    run_id: str
    request_id: str
    credential_ref: str | None = None

class ToolAdapter:
    name: str
    security: ToolSecurity

    def is_idempotent(self, arguments: dict[str, Any]) -> bool:
        return self.security.idempotent

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        raise NotImplementedError
