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
