from packages.security.policy import Action, PolicyEngine, Risk

def test_shell_requires_approval():
    d = PolicyEngine().evaluate(Action("shell", {}, "agent", "tenant"))
    assert d.allowed is True
    assert d.risk == Risk.HIGH
    assert d.requires_approval is True

def test_invalid_tenant_is_denied():
    d = PolicyEngine().evaluate(Action("search", {}, "agent", ""))
    assert d.allowed is False
