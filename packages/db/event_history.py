from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models import AuditEvent

async def append_event(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: UUID,
    event_type: str,
    actor: str,
    payload: dict,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=tenant_id,
        run_id=run_id,
        event_type=event_type,
        actor=actor,
        payload=payload,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event

async def replay_events(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: UUID,
    after_sequence: int | None = None,
    limit: int = 500,
) -> list[AuditEvent]:
    stmt = select(AuditEvent).where(
        AuditEvent.tenant_id == tenant_id,
        AuditEvent.run_id == run_id,
    )
    if after_sequence is not None:
        stmt = stmt.where(AuditEvent.sequence > after_sequence)
    stmt = (
        stmt.order_by(AuditEvent.sequence.asc())
        .limit(max(1, min(limit, 5000)))
    )
    result = await session.execute(stmt)
    return list(result.scalars())
