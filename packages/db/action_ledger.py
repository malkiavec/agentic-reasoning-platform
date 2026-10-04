from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.db.models import ToolActionRecord

async def begin_action(session: AsyncSession, *, tenant_id: str, run_id: UUID | None,
                       action_id: str, tool: str, idempotent: bool) -> ToolActionRecord:
    row = await session.scalar(
        select(ToolActionRecord)
        .where(ToolActionRecord.tenant_id == tenant_id, ToolActionRecord.action_id == action_id)
        .with_for_update()
    )
    if row is not None:
        return row
    row = ToolActionRecord(id=uuid4(), tenant_id=tenant_id, run_id=run_id,
                           action_id=action_id, tool=tool, status="in_progress",
                           idempotent=idempotent)
    session.add(row)
    await session.commit()
    return row

async def complete_action(session: AsyncSession, row: ToolActionRecord, output) -> None:
    row.status = "completed"
    row.output = output
    row.completed_at = datetime.now(timezone.utc)
    await session.commit()

async def fail_action(session: AsyncSession, row: ToolActionRecord, error: str, *, ambiguous: bool = False) -> None:
    row.status = "ambiguous" if ambiguous else "failed"
    row.error = error
    row.completed_at = datetime.now(timezone.utc)
    await session.commit()
