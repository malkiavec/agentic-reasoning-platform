from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from packages.db.session import SessionLocal
from packages.hitl.persistent import decide_approval
from apps.api.auth import RequestPrincipal, require_principal

router = APIRouter(prefix="/v1/approvals")

class ApprovalDecision(BaseModel):
    approved: bool

@router.post("/{approval_id}/decision")
async def approval_decision(approval_id: UUID, body: ApprovalDecision,
                            principal: RequestPrincipal = Depends(require_principal)):
    async with SessionLocal() as session:
        from packages.db.approval_models import ApprovalRecord
        record = await session.get(ApprovalRecord, approval_id)
        if record is None or record.tenant_id != principal.tenant_id:
            raise HTTPException(404, "approval_not_found_or_closed")
        if "approver" not in principal.roles and "admin" not in principal.roles:
            raise HTTPException(403, "approver_role_required")
        record = await decide_approval(session, approval_id, body.approved)
        if record is None:
            raise HTTPException(404, "approval_not_found_or_closed")
        return {"approval_id": str(record.id), "status": record.status,
                "approvals_received": record.approvals_received}
