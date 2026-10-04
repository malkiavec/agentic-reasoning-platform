from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

@dataclass(frozen=True)
class ApprovalRequest:
    id: UUID
    run_id: UUID
    tenant_id: str
    action: str
    risk: str
    expires_at: datetime
    approved: bool | None = None

class ApprovalService:
    def __init__(self) -> None:
        self._pending: dict[UUID, ApprovalRequest] = {}

    def request(self, run_id: UUID, tenant_id: str, action: str, risk: str, ttl_seconds: int = 900) -> ApprovalRequest:
        item = ApprovalRequest(uuid4(), run_id, tenant_id, action, risk,
                               datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds))
        self._pending[item.id] = item
        return item

    def decide(self, approval_id: UUID, approved: bool) -> ApprovalRequest:
        item = self._pending[approval_id]
        if datetime.now(timezone.utc) >= item.expires_at:
            raise ValueError("approval_expired")
        updated = ApprovalRequest(item.id, item.run_id, item.tenant_id, item.action,
                                  item.risk, item.expires_at, approved)
        self._pending[approval_id] = updated
        return updated

    def get(self, approval_id: UUID) -> ApprovalRequest | None:
        return self._pending.get(approval_id)
