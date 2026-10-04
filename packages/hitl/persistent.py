from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from packages.db.approval_models import ApprovalRecord

async def create_approval(session: AsyncSession, **values) -> ApprovalRecord:
    record = ApprovalRecord(**values)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record

async def decide_approval(session: AsyncSession, approval_id: UUID, approved: bool) -> ApprovalRecord | None:
    record = await session.scalar(select(ApprovalRecord).where(ApprovalRecord.id == approval_id))
    if record is None or record.status != "pending":
        return None
    if datetime.now(timezone.utc) >= record.expires_at:
        record.status = "expired"
    elif approved:
        record.approvals_received += 1
        if record.approvals_received >= record.required_approvers:
            record.status = "approved"
    else:
        record.status = "rejected"
    await session.commit()
    return record
