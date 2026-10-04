from dataclasses import dataclass
from typing import Any, Protocol

@dataclass(frozen=True)
class ToolContext:
    tenant_id: str
    actor: str
    run_id: str
    request_id: str

class ToolAdapter(Protocol):
    name: str
    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> Any: ...

class AdapterCatalog:
    """Collection boundary for external APIs; adapters own credential handling and egress policy."""
    def __init__(self):
        self._items: dict[str, ToolAdapter] = {}

    def register(self, adapter: ToolAdapter) -> None:
        if adapter.name in self._items:
            raise ValueError(f"adapter already registered: {adapter.name}")
        self._items[adapter.name] = adapter

    def get(self, name: str) -> ToolAdapter | None:
        return self._items.get(name)

    def names(self) -> list[str]:
        return sorted(self._items)
