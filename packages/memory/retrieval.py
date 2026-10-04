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

class HybridRetriever:
    """Contract for lexical + vector retrieval with optional reranking."""
    def __init__(self, lexical: Retriever | None = None, vector: Retriever | None = None):
        self.lexical, self.vector = lexical, vector

    async def search(self, tenant_id: str, query: str, limit: int = 10) -> list[RetrievalHit]:
        results = []
        if self.lexical:
            results.extend(await self.lexical.search(tenant_id, query, limit))
        if self.vector:
            results.extend(await self.vector.search(tenant_id, query, limit))
        return sorted(results, key=lambda x: x.score, reverse=True)[:limit]
