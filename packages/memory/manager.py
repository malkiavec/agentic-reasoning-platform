from dataclasses import dataclass
from typing import Any, Protocol

@dataclass(frozen=True)
class MemoryItem:
    kind: str
    content: str
    source: str
    confidence: float = 1.0
    metadata: dict[str, Any] | None = None

class MemoryBackend(Protocol):
    async def put(self, tenant_id: str, item: MemoryItem) -> None: ...
    async def search(self, tenant_id: str, query: str, limit: int = 10) -> list[MemoryItem]: ...

class MemoryManager:
    """Tenant-scoped memory facade; retrieval backends may combine lexical/vector/reranked results."""
    def __init__(self, backend: MemoryBackend):
        self.backend = backend

    async def remember(self, tenant_id: str, item: MemoryItem) -> None:
        await self.backend.put(tenant_id, item)

    async def recall(self, tenant_id: str, query: str, limit: int = 10) -> list[MemoryItem]:
        return await self.backend.search(tenant_id, query, limit)
