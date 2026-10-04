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
    """Tenant-scoped memory repository with lexical and pgvector search."""

    async def put(
        self,
        session: AsyncSession,
        *,
        tenant_id: str,
        kind: str,
        content: str,
        source: str,
        confidence: float = 1.0,
        metadata: dict | None = None,
        embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
        provenance_hash: str | None = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            tenant_id=tenant_id,
            kind=kind,
            content=content,
            source=source,
            confidence=max(0.0, min(1.0, confidence)),
            metadata=metadata or {},
            embedding=list(embedding) if embedding is not None else None,
            embedding_model=embedding_model,
            provenance_hash=provenance_hash,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def lexical_search(
        self, session: AsyncSession, tenant_id: str, query: str, limit: int = 10
    ) -> list[MemoryRecord]:
        result = await session.execute(
            select(MemoryRecord)
            .where(
                MemoryRecord.tenant_id == tenant_id,
                MemoryRecord.content.ilike(f"%{query}%"),
            )
            .limit(max(1, min(limit, 100))),
        )
        return list(result.scalars())

    async def vector_search(
        self,
        session: AsyncSession,
        tenant_id: str,
        embedding: Sequence[float],
        limit: int = 10,
    ) -> list[VectorHit]:
        vector = list(embedding)
        rows = await session.execute(
            select(
                MemoryRecord.id,
                MemoryRecord.content,
                MemoryRecord.source,
                (1 - MemoryRecord.embedding.cosine_distance(vector)).label("score"),
            )
            .where(
                MemoryRecord.tenant_id == tenant_id,
                MemoryRecord.embedding.is_not(None),
            )
            .order_by(MemoryRecord.embedding.cosine_distance(vector))
            .limit(max(1, min(limit, 100))),
        )
        return [
            VectorHit(str(row.id), row.content, float(row.score), row.source)
            for row in rows
        ]
