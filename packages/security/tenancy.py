from dataclasses import dataclass

@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str] = frozenset()

class TenantAuthorizer:
    def authorize(self, principal: Principal, tenant_id: str, required_role: str | None = None) -> bool:
        if principal.tenant_id != tenant_id:
            return False
        return required_role is None or required_role in principal.roles
