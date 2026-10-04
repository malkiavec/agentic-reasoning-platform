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
    attempts: int = 1


class PlanExecutor:
    """Dependency-aware bounded executor with timeout, retry, cancellation, and budget controls."""

    def __init__(
        self,
        step_handler: Callable[[Any], Awaitable[StepResult]],
        max_concurrency: int = 8,
        step_timeout_seconds: float = 300.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        max_total_steps: int = 1000,
    ):
        self.step_handler = step_handler
        self.max_concurrency = max(1, max_concurrency)
        self.step_timeout_seconds = max(0.1, step_timeout_seconds)
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.max_total_steps = max(1, max_total_steps)

    async def _run_step(self, step: Any) -> StepResult:
        attempts = 0
        while attempts <= self.max_retries:
            attempts += 1
            try:
                result = await asyncio.wait_for(
                    self.step_handler(step), timeout=self.step_timeout_seconds
                )
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                result = StepResult(step.id, False, error="step_timeout", attempts=attempts)
            except Exception as exc:
                result = StepResult(
                    step.id, False, error=f"step_error:{type(exc).__name__}", attempts=attempts
                )
            if result.ok or attempts > self.max_retries:
                return (
                    result
                    if result.attempts == attempts
                    else StepResult(result.step_id, result.ok, result.output, result.error, attempts)
                )
            await asyncio.sleep(self.retry_backoff_seconds * (2 ** (attempts - 1)))
        return StepResult(step.id, False, error="step_retry_exhausted", attempts=attempts)

    async def execute(
        self,
        steps: list[Any],
        *,
        checkpoint: dict[str, Any] | None = None,
        deadline_seconds: float | None = None,
    ) -> list[StepResult]:
        if len(steps) > self.max_total_steps:
            raise ValueError("step_budget_exceeded")
        by_id = {step.id: step for step in steps}
        if len(by_id) != len(steps):
            raise ValueError("duplicate_step_id")
        deps = {step.id: set(getattr(step, "depends_on", None) or []) for step in steps}
        unknown = {d for values in deps.values() for d in values if d not in by_id}
        if unknown:
            raise ValueError("unknown_step_dependency")

        completed: dict[str, StepResult] = {}
        if checkpoint:
            for step_id in checkpoint.get("completed_steps", []):
                if step_id in by_id:
                    completed[step_id] = StepResult(
                        step_id,
                        True,
                        checkpoint.get("results", {}).get(step_id),
                        attempts=0,
                    )

        pending = set(by_id) - set(completed)
        deadline = (
            None
            if deadline_seconds is None
            else asyncio.get_running_loop().time() + max(0.0, deadline_seconds)
        )

        while pending:
            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("run_deadline_exceeded")
            ready = sorted(i for i in pending if deps[i].issubset(completed))
            if not ready:
                raise ValueError("cyclic_or_blocked_dependencies")
            batch = ready[: self.max_concurrency]
            coroutines = [self._run_step(by_id[i]) for i in batch]
            if deadline is None:
                results = await asyncio.gather(*coroutines)
            else:
                remaining = max(0.001, deadline - asyncio.get_running_loop().time())
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*coroutines), timeout=remaining
                    )
                except TimeoutError as exc:
                    raise TimeoutError("run_deadline_exceeded") from exc
            for result in results:
                completed[result.step_id] = result
                pending.remove(result.step_id)
            failed = {r.step_id for r in results if not r.ok}
            if failed:
                changed = True
                while changed:
                    changed = False
                    for i in list(pending):
                        if any(d in completed and not completed[d].ok for d in deps[i]):
                            completed[i] = StepResult(
                                i, False, error="dependency_failed", attempts=0
                            )
                            pending.remove(i)
                            changed = True

        return [completed[s.id] for s in steps]
