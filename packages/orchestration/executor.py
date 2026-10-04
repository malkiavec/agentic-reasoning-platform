import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

@dataclass(frozen=True)
class StepResult:
    step_id: str
    ok: bool
    output: Any = None
    error: str | None = None

class PlanExecutor:
    """Runs independent plan steps concurrently while preserving explicit boundaries."""
    def __init__(self, step_handler: Callable[[Any], Awaitable[StepResult]]):
        self.step_handler = step_handler

    async def execute(self, steps: list[Any]) -> list[StepResult]:
        groups: dict[str, list[Any]] = {}
        for step in steps:
            groups.setdefault(step.parallel_group or f"serial:{step.id}", []).append(step)
        results: list[StepResult] = []
        for group in groups.values():
            if len(group) == 1:
                results.append(await self.step_handler(group[0]))
            else:
                results.extend(await asyncio.gather(*(self.step_handler(s) for s in group)))
        return results
