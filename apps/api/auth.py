from dataclasses import dataclass
from fastapi import Header, HTTPException

@dataclass(frozen=True)
class RequestPrincipal:
    subject: str
    tenant_id: str
    roles: frozenset[str]

async def require_principal(
    x_tenant_id: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
) -> RequestPrincipal:
    # Development transport contract. Production deployment must replace this with JWT/OIDC verification.
    if not x_tenant_id or not x_actor:
        raise HTTPException(status_code=401, detail="authentication_required")
    return RequestPrincipal(x_actor, x_tenant_id, frozenset())
