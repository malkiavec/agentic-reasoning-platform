import pytest
from packages.agent_runtime.multi_agent import Delegation, MultiAgentCoordinator

class FakeAgent:
    def __init__(self, name):
        self.name = name

    async def run(self, task, context):
        return {"task": task, "context": context}

@pytest.mark.asyncio
async def test_multi_agent_delegation_is_bounded_and_ordered():
    coordinator = MultiAgentCoordinator(
        {"research": FakeAgent("research"), "coder": FakeAgent("coder")},
        max_parallel=2,
    )
    results = await coordinator.execute([
        Delegation("research", "find evidence"),
        Delegation("coder", "write code"),
    ])
    assert [r.agent for r in results] == ["research", "coder"]
    assert all(r.ok for r in results)

@pytest.mark.asyncio
async def test_unknown_subagent_fails_closed():
    results = await MultiAgentCoordinator({}).execute([Delegation("missing", "task")])
    assert not results[0].ok
    assert results[0].error == "unknown_subagent"
