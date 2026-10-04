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
    record = ApprovalRecord(**values)
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
    record = await get_approval(session, approval_id)
    if record is None or record.status != "pending":
        return None
    if not actor:
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

    decision = ApprovalDecisionRecord(
        approval_id=approval_id,
        tenant_id=record.tenant_id,
        approver_subject=actor,
        decision="approved" if approved else "rejected",
        comment=comment[:4000],
    )
    session.add(decision)
    if not approved:
        record.status = "rejected"
    else:
        record.approvals_received += 1
        if record.approvals_received >= record.required_approvers:
            record.status = "approved"
    await session.commit()
    await session.refresh(record)
    return record
