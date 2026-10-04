from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

class RunState(StrEnum):
    CREATED="created"
    GUARDRAIL="guardrail"
    PLANNING="planning"
    EXECUTING="executing"
    WAITING_APPROVAL="waiting_approval"
    COMPLETED="completed"
    FAILED="failed"
    CANCELLED="cancelled"

@dataclass
class Checkpoint:
    state: RunState
    step_index: int = 0
    completed_steps: list[str] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)
    plan: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"state": self.state.value, "step_index": self.step_index,
                "completed_steps": self.completed_steps, "results": self.results, "plan": self.plan}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(state=RunState(data.get("state","created")),
                   step_index=int(data.get("step_index",0)),
                   completed_steps=list(data.get("completed_steps",[])),
                   results=dict(data.get("results",{})),
                   plan=list(data.get("plan",[])))
