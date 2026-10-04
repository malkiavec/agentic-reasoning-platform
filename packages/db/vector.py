from dataclasses import dataclass
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.db.memory_models import MemoryRecord

@dataclass(frozen=True)
class VectorHit:
    id: str
    content: str
    score: float
    source: str

class MemoryRepository:
    """Persistence interface. Embedding generation remains provider-neutral."""
    async def put(self, session: AsyncSession, *, tenant_id: str, kind: str,
                  content: str, source: str, confidence: float = 1.0,
                  metadata: dict | None = None) -> MemoryRecord:
        record = MemoryRecord(tenant_id=tenant_id, kind=kind, content=content,
                              source=source, confidence=confidence, metadata=metadata or {})
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def lexical_search(self, session: AsyncSession, tenant_id: str,
                             query: str, limit: int = 10) -> list[MemoryRecord]:
        # Safe baseline until a production full-text/vector index is installed.
        result = await session.execute(
            select(MemoryRecord)
            .where(MemoryRecord.tenant_id == tenant_id,
                   MemoryRecord.content.ilike(f"%{query}%"))
            .limit(limit)
        )
        return list(result.scalars())
