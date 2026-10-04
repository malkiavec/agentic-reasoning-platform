from dataclasses import dataclass
from typing import Any

@dataclass
class MemoryRecord:
    tenant_id: str
    content: str
    source: str
    confidence: float = 1.0
    metadata: dict[str, Any] | None = None

class MemoryStore:
    """Provider-neutral memory interface; PostgreSQL/pgvector implementation follows."""
    async def put(self, record: MemoryRecord) -> None:
        raise NotImplementedError

    async def search(self, tenant_id: str, query: str, limit: int = 10) -> list[MemoryRecord]:
        raise NotImplementedError
