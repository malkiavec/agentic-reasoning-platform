from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    tool: str | None = None
    parallel_group: str | None = None

@dataclass(frozen=True)
class ExecutionPlan:
    steps: list[PlanStep]
    max_steps: int

class Planner:
    """Provider-agnostic planning contract; execution remains outside the model."""
    def build(self, output: dict[str, Any], max_steps: int) -> ExecutionPlan:
        raw = output.get("steps", [])
        steps = [
            PlanStep(
                id=str(item["id"]),
                description=str(item["description"]),
                tool=item.get("tool"),
                parallel_group=item.get("parallel_group"),
            )
            for item in raw[:max_steps]
        ]
        return ExecutionPlan(steps=steps, max_steps=max_steps)
