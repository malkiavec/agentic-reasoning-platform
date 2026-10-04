from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import AuditEvent

async def append_event(session: AsyncSession, *, tenant_id: str, run_id: UUID,
                       event_type: str, actor: str, payload: dict) -> AuditEvent:
    event = AuditEvent(
        tenant_id=tenant_id, run_id=run_id, event_type=event_type,
        actor=actor, payload=payload,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event

async def replay_events(session: AsyncSession, *, tenant_id: str, run_id: UUID,
                        after_id: UUID | None = None, limit: int = 500) -> list[AuditEvent]:
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tenant_id,
        AuditEvent.run_id == run_id,
    )
    if after_id is not None:
        stmt = stmt.where(AuditEvent.id > after_id)
    stmt = stmt.order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars())
