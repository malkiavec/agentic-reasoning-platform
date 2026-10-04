import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.db.approval_models import ApprovalDecisionRecord, ApprovalRecord

def canonical_action(tool: str, arguments: dict) -> str:
    return json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def action_hash(tool: str, arguments: dict) -> str:
    return hashlib.sha256(canonical_action(tool, arguments).encode()).hexdigest()

async def create_approval(session: AsyncSession, **values) -> ApprovalRecord:
    required = max(1, int(values.get("required_approvers", 1)))
    record = ApprovalRecord(**{**values, "required_approvers": required})
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record

async def get_approval(session: AsyncSession, approval_id: UUID) -> ApprovalRecord | None:
    return await session.scalar(select(ApprovalRecord).where(ApprovalRecord.id == approval_id))

async def decide_approval(
    session: AsyncSession,
    approval_id: UUID,
    approved: bool,
    *,
    actor: str | None = None,
    comment: str = "",
) -> ApprovalRecord | None:
    if not actor:
        return None
    # Lock the approval row so concurrent approvers cannot double-count a quorum.
    record = await session.scalar(
        select(ApprovalRecord).where(ApprovalRecord.id == approval_id).with_for_update()
    )
    if record is None or record.status != "pending":
        return None

    now = datetime.now(timezone.utc)
    if now >= record.expires_at:
        record.status = "expired"
        await session.commit()
        return record

    existing = await session.scalar(select(ApprovalDecisionRecord).where(
        ApprovalDecisionRecord.approval_id == approval_id,
        ApprovalDecisionRecord.approver_subject == actor,
    ))
    if existing is not None:
        return None

    session.add(ApprovalDecisionRecord(
        approval_id=approval_id,
        tenant_id=record.tenant_id,
        approver_subject=actor,
        decision="approved" if approved else "rejected",
        comment=comment[:4000],
    ))
    if not approved:
        record.status = "rejected"
    else:
        record.approvals_received += 1
        if record.approvals_received >= max(1, record.required_approvers):
            record.status = "approved"
    await session.commit()
    await session.refresh(record)
    return record
