import pytest

from packages.agent_runtime.gateway import MockProvider, ModelGateway
from packages.agent_runtime.planner import StructuredPlanner
from packages.agent_runtime.routing import ModelRoute, ModelRouter
from packages.tools.registry import ToolRegistry

@pytest.mark.asyncio
async def test_structured_planner_uses_safe_mock_route():
    gateway=ModelGateway(ModelRouter([ModelRoute(
        provider="mock", model="reasoning-default",
        max_context_tokens=1_000_000,
        capabilities=frozenset({"reasoning","structured_output"}),
    )]))
    gateway.register("mock",MockProvider())
    steps=await StructuredPlanner(gateway,ToolRegistry()).plan(
        "hello",model="reasoning-default")
    assert steps[0].tool=="__final__"

def test_structured_planner_rejects_unregistered_tool():
    planner=StructuredPlanner(ModelGateway(),ToolRegistry())
    with pytest.raises(ValueError,match="unregistered"):
        planner.validate({"steps":[{"id":"1","tool":"not_registered","arguments":{}}]})
