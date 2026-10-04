from enum import StrEnum
from dataclasses import dataclass, field
from typing import Any

class RunState(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Run:
    id: str
    state: RunState = RunState.CREATED
    checkpoint: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0

    def checkpoint_state(self, **values: Any) -> None:
        self.checkpoint.update(values)
