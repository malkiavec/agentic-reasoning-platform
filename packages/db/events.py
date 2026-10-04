from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.db.models import AuditEvent

async def record_event(session: AsyncSession, tenant_id: str, run_id: UUID | None,
                       event_type: str, actor: str, payload: dict) -> AuditEvent:
    event = AuditEvent(tenant_id=tenant_id, run_id=run_id, event_type=event_type,
                       actor=actor, payload=payload,
                       created_at=datetime.now(timezone.utc))
    session.add(event)
    await session.commit()
    return event

async def list_events(session: AsyncSession, tenant_id: str, run_id: UUID, limit: int = 500):
    result = await session.execute(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant_id, AuditEvent.run_id == run_id)
        .order_by(AuditEvent.created_at.desc()).limit(limit)
    )
    return list(result.scalars())
