from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from packages.db.session import SessionLocal
from packages.db.approval_models import ApprovalRecord
from packages.db.repository import audit, update_run
from packages.hitl.persistent import decide_approval, get_approval
from apps.api.auth import RequestPrincipal, require_principal
from apps.worker.tasks import execute_run

router = APIRouter(prefix="/v1/approvals")

class ApprovalDecision(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=4000)

@router.get("")
async def list_approvals(principal: RequestPrincipal = Depends(require_principal)):
    async with SessionLocal() as session:
        from sqlalchemy import select
        rows = await session.scalars(select(ApprovalRecord).where(
            ApprovalRecord.tenant_id == principal.tenant_id
        ).order_by(ApprovalRecord.created_at.desc()).limit(100))
        return [{"approval_id": str(x.id), "run_id": str(x.run_id), "action": x.action, "risk": x.risk,
                 "status": x.status, "expires_at": x.expires_at.isoformat(),
                 "approvals_received": x.approvals_received, "required_approvers": x.required_approvers} for x in rows]

@router.post("/{approval_id}/decision")
async def approval_decision(approval_id: UUID, body: ApprovalDecision,
                            principal: RequestPrincipal = Depends(require_principal)):
    async with SessionLocal() as session:
        record = await get_approval(session, approval_id)
        if record is None or record.tenant_id != principal.tenant_id:
            raise HTTPException(404, "approval_not_found_or_closed")
        if "approver" not in principal.roles and "admin" not in principal.roles:
            raise HTTPException(403, "approver_role_required")
        record = await decide_approval(
            session, approval_id, body.approved, actor=principal.subject, comment=body.comment
        )
        if record is None:
            raise HTTPException(409, "approval_not_pending_or_duplicate")
        await audit(session, tenant_id=record.tenant_id, run_id=record.run_id,
                    event_type="approval.decision", actor=principal.subject,
                    payload={"approval_id": str(record.id), "approved": body.approved,
                             "status": record.status, "comment": body.comment})
        if record.status == "approved":
            await update_run(session, record.run_id, state="executing")
            execute_run.delay(str(record.run_id))
        elif record.status in {"rejected", "expired"}:
            await update_run(session, record.run_id, state="failed",
                             checkpoint={"state": "failed", "error": f"approval_{record.status}",
                                         "approval_id": str(record.id)})
        return {"approval_id": str(record.id), "status": record.status,
                "approvals_received": record.approvals_received, "run_id": str(record.run_id)}
