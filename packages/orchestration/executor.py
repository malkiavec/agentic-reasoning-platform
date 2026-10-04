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
    """Dependency-aware bounded executor with deterministic ready-batch scheduling."""

    def __init__(self, step_handler: Callable[[Any], Awaitable[StepResult]], max_concurrency: int = 8):
        self.step_handler = step_handler
        self.max_concurrency = max(1, max_concurrency)

    async def execute(self, steps: list[Any]) -> list[StepResult]:
        by_id = {step.id: step for step in steps}
        if len(by_id) != len(steps):
            raise ValueError("duplicate_step_id")
        deps = {step.id: set(getattr(step, "depends_on", None) or []) for step in steps}
        unknown = {d for values in deps.values() for d in values if d not in by_id}
        if unknown:
            raise ValueError("unknown_step_dependency")
        completed: dict[str, StepResult] = {}
        pending = set(by_id)
        while pending:
            ready = sorted(i for i in pending if deps[i].issubset(completed))
            if not ready:
                raise ValueError("cyclic_or_blocked_dependencies")
            batch = ready[:self.max_concurrency]
            results = await asyncio.gather(*(self.step_handler(by_id[i]) for i in batch))
            for result in results:
                completed[result.step_id] = result
                pending.remove(result.step_id)
            if any(not r.ok for r in results):
                changed = True
                while changed:
                    changed = False
                    for i in list(pending):
                        if any(d in completed and not completed[d].ok for d in deps[i]):
                            completed[i] = StepResult(i, False, error="dependency_failed")
                            pending.remove(i)
                            changed = True
        return [completed[s.id] for s in steps]
