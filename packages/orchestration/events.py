from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

@dataclass(frozen=True)
class RunEvent:
    run_id: UUID
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class EventBus:
    def __init__(self) -> None:
        self._events: dict[UUID, list[RunEvent]] = {}

    async def publish(self, event: RunEvent) -> None:
        self._events.setdefault(event.run_id, []).append(event)

    async def history(self, run_id: UUID) -> list[RunEvent]:
        return list(self._events.get(run_id, []))
