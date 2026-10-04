from packages.agent_runtime.context import ContextManager, ContextWindow

def test_context_budget():
    manager = ContextManager(ContextWindow(max_tokens=100, reserved_output_tokens=20))
    assert len(manager.fit(["a", "b"], [80, 10])) == 1
