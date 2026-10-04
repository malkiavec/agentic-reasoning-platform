from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

@dataclass(frozen=True)
class Event:
    type: str
    run_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EventBus:
    """Process-local event bus; Redis transport is used by the API for live delivery."""
    def __init__(self):
        self._subscribers: list[Callable[[Event], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[Event], Awaitable[None]]) -> None:
        self._subscribers.append(callback)

    async def publish(self, event: Event) -> None:
        for callback in tuple(self._subscribers):
            await callback(event)
