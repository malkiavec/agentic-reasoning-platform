import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class StepResult:
    step_id: str
    ok: bool
    output: Any = None
    error: str | None = None

class PlanExecutor:
    """Bounded concurrent execution with deterministic result ordering."""

    def __init__(
        self,
        step_handler: Callable[[Any], Awaitable[StepResult]],
        max_concurrency: int = 8,
    ):
        self.step_handler = step_handler
        self.max_concurrency = max(1, max_concurrency)

    async def execute(self, steps: list[Any]) -> list[StepResult]:
        groups: dict[str, list[Any]] = {}
        for step in steps:
            groups.setdefault(
                step.parallel_group or f"serial:{step.id}", []
            ).append(step)

        results: list[StepResult] = []
        for group in groups.values():
            sem = asyncio.Semaphore(self.max_concurrency)

            async def run_one(step: Any) -> StepResult:
                async with sem:
                    return await self.step_handler(step)

            results.extend(await asyncio.gather(*(run_one(step) for step in group)))
        return results
