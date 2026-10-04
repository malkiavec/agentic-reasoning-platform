import asyncio
import pytest
from packages.orchestration.executor import PlanExecutor, StepResult

class Step:
    def __init__(self, id, group=None):
        self.id, self.parallel_group = id, group

@pytest.mark.asyncio
async def test_parallel_group_executes():
    async def handle(step):
        return StepResult(step.id, True)
    results = await PlanExecutor(handle).execute([Step("a", "g"), Step("b", "g")])
    assert {r.step_id for r in results} == {"a", "b"}


@pytest.mark.asyncio
async def test_checkpoint_skips_completed_steps():
    calls = []
    async def handle(step):
        calls.append(step.id)
        return StepResult(step.id, True, output=f"ran:{step.id}")
    results = await PlanExecutor(handle).execute(
        [Step("a"), Step("b")],
        checkpoint={"completed_steps": ["a"], "results": {"a": "restored"}},
    )
    assert [r.output for r in results] == ["restored", "ran:b"]
    assert calls == ["b"]

@pytest.mark.asyncio
async def test_run_deadline_is_enforced():
    async def handle(step):
        await asyncio.sleep(0.05)
        return StepResult(step.id, True)
    with pytest.raises(TimeoutError, match="run_deadline_exceeded"):
        await PlanExecutor(handle).execute([Step("a")], deadline_seconds=0.001)
