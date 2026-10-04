from packages.security.policy import Action, PolicyEngine

def test_shell_requires_approval():
    decision = PolicyEngine().evaluate(Action("shell", {}, "agent", "tenant"), registered_tools=frozenset({"shell"}))
    assert decision.allowed is True
    assert decision.requires_approval is True

def test_missing_tenant_is_denied():
    decision = PolicyEngine().evaluate(Action("echo", {}, "agent", ""), registered_tools=frozenset({"echo"}))
    assert decision.allowed is False
    assert decision.risk.name == "CRITICAL"

def test_restricted_tool_is_denied():
    decision = PolicyEngine().evaluate(Action("secrets.read", {}, "agent", "tenant"), registered_tools=frozenset({"secrets.read"}))
    assert decision.allowed is False


def test_unknown_tool_is_denied_by_default():
    decision = PolicyEngine().evaluate(Action("unknown.tool", {}, "agent", "tenant"))
    assert decision.allowed is False
    assert decision.reason == "tool_not_registered"
