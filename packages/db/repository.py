from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuditEvent, RunRecord

async def create_run(session: AsyncSession, **values) -> RunRecord:
    # Idempotency is tenant-scoped at the API boundary; unique DB key prevents duplicates.
    key = values.get("idempotency_key")
    if key:
        existing = await session.scalar(select(RunRecord).where(RunRecord.tenant_id == values.get("tenant_id"), RunRecord.idempotency_key == key))
        if existing:
            return existing
    record = RunRecord(**values)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record

async def get_run(session: AsyncSession, run_id: UUID) -> RunRecord | None:
    return await session.scalar(select(RunRecord).where(RunRecord.id == run_id))

async def update_run(session: AsyncSession, run_id: UUID, **values) -> None:
    await session.execute(update(RunRecord).where(RunRecord.id == run_id).values(**values))
    await session.commit()

async def audit(session: AsyncSession, **values) -> AuditEvent:
    event = AuditEvent(**values)
    session.add(event)
    await session.commit()
    return event
