from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from packages.db.session import SessionLocal
from packages.db.approval_models import ApprovalRecord
from packages.hitl.persistent import decide_approval

router = APIRouter(prefix="/v1/approvals")

class ApprovalDecision(BaseModel):
    approved: bool

@router.post("/{approval_id}/decision")
async def approval_decision(approval_id: UUID, body: ApprovalDecision):
    async with SessionLocal() as session:
        record = await decide_approval(session, approval_id, body.approved)
        if record is None:
            raise HTTPException(404, "approval_not_found_or_closed")
        return {"approval_id": str(record.id), "status": record.status,
                "approvals_received": record.approvals_received}
