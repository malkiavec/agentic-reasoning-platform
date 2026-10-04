import pytest
from packages.security.policy import PolicyEngine
from packages.tools.execution import ToolExecutor
from packages.tools.registry import ToolRegistry, ToolSpec

@pytest.mark.asyncio
async def test_tool_execution_validates_and_runs():
    registry = ToolRegistry()
    registry.register(ToolSpec("echo", "Echo", {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}),
                       lambda value: value)
    result = await ToolExecutor(registry, PolicyEngine()).execute("echo", {"value": "ok"}, actor="test", tenant_id="t1")
    assert result.ok and result.output == "ok"

@pytest.mark.asyncio
async def test_shell_is_blocked_for_approval():
    registry = ToolRegistry()
    registry.register(ToolSpec("shell", "Shell", {"type": "object"}), lambda: "bad")
    result = await ToolExecutor(registry, PolicyEngine()).execute("shell", {}, actor="test", tenant_id="t1")
    assert not result.ok and result.error == "approval_required"


@pytest.mark.asyncio
async def test_unregistered_tool_is_denied_before_execution():
    registry = ToolRegistry()
    registry.register(
        ToolSpec("echo", "Echo", {"type": "object"}),
        lambda: "ok",
    )
    result = await ToolExecutor(registry, PolicyEngine()).execute(
        "unknown.tool", {}, actor="test", tenant_id="t1"
    )
    assert not result.ok and result.error == "tool_not_registered"
