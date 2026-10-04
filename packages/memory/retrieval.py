from dataclasses import dataclass
from typing import Any, Protocol

@dataclass(frozen=True)
class RetrievalHit:
    content: str
    score: float
    source: str
    metadata: dict[str, Any]

class Retriever(Protocol):
    async def search(self, tenant_id: str, query: str, limit: int = 10) -> list[RetrievalHit]: ...

class Reranker(Protocol):
    async def rerank(self, tenant_id: str, query: str, hits: list[RetrievalHit], limit: int) -> list[RetrievalHit]: ...

class HybridRetriever:
    """Tenant-scoped lexical/vector fusion with deterministic deduplication and optional reranking."""
    def __init__(self, lexical: Retriever | None = None, vector: Retriever | None = None,
                 reranker: Reranker | None = None, lexical_weight: float = 1.0,
                 vector_weight: float = 1.0, rrf_k: int = 60):
        self.lexical = lexical
        self.vector = vector
        self.reranker = reranker
        self.lexical_weight = max(0.0, lexical_weight)
        self.vector_weight = max(0.0, vector_weight)
        self.rrf_k = max(1, rrf_k)

    async def search(self, tenant_id: str, query: str, limit: int = 10) -> list[RetrievalHit]:
        lexical_hits = await self.lexical.search(tenant_id, query, limit * 3) if self.lexical else []
        vector_hits = await self.vector.search(tenant_id, query, limit * 3) if self.vector else []
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for weight, hits in ((self.lexical_weight, lexical_hits), (self.vector_weight, vector_hits)):
            for rank, hit in enumerate(hits, start=1):
                key = (hit.source, hit.content)
                item = merged.setdefault(key, {"hit": hit, "score": 0.0})
                item["score"] += weight / (self.rrf_k + rank)
                if hit.score > item["hit"].score:
                    item["hit"] = hit
        fused = [RetrievalHit(x["hit"].content, x["score"], x["hit"].source, x["hit"].metadata)
                 for x in merged.values()]
        fused.sort(key=lambda x: (-x.score, x.source, x.content))
        if self.reranker:
            return await self.reranker.rerank(tenant_id, query, fused[:limit * 3], limit)
        return fused[:limit]
