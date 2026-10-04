from dataclasses import dataclass
from uuid import UUID

@dataclass
class CancellationRegistry:
    cancelled: set[UUID]

    def __init__(self):
        self.cancelled = set()

    def cancel(self, run_id: UUID) -> None:
        self.cancelled.add(run_id)

    def is_cancelled(self, run_id: UUID) -> bool:
        return run_id in self.cancelled
