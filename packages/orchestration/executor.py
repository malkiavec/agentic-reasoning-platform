import asyncio
from typing import Awaitable, Callable

class PlanExecutor:
    """Bounded concurrent execution with deterministic result ordering."""
    def __init__(self, step_handler: Callable, max_concurrency: int = 8):
        self.step_handler = step_handler
        self.max_concurrency = max(1, max_concurrency)

    async def execute(self, steps):
        groups: dict[str, list] = {}
        for step in steps:
            groups.setdefault(step.parallel_group or f"serial:{step.id}", []).append(step)
        results = []
        for group in groups.values():
            sem = asyncio.Semaphore(self.max_concurrency)
            async def run(step):
                async with sem:
                    return await self.step_handler(step)
            results.extend(await asyncio.gather(*(run(s) for s in group)))
        return results
