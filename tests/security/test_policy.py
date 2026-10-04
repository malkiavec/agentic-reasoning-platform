import pytest
from packages.security.policy import Action, PolicyEngine, Risk

def test_policy_requires_context():
    d = PolicyEngine().evaluate(Action("echo", {}, "", "tenant"), registered_tools=frozenset({"echo"}))
    assert not d.allowed and d.risk == Risk.CRITICAL

def test_restricted_tools_are_denied():
    d = PolicyEngine().evaluate(Action("secrets.read", {}, "actor", "tenant"), registered_tools=frozenset({"secrets.read"}))
    assert not d.allowed

def test_external_writes_require_approval():
    d = PolicyEngine().evaluate(Action("http.rest", {"method": "POST"}, "actor", "tenant"), registered_tools=frozenset({"http.rest"}))
    assert d.allowed and d.requires_approval and d.risk == Risk.HIGH

def test_large_arguments_are_rejected():
    d = PolicyEngine().evaluate(Action("echo", {"payload": "x" * (256 * 1024)}, "actor", "tenant"), registered_tools=frozenset({"echo"}))
    assert not d.allowed
    assert d.reason == "arguments_too_large"


def test_registered_tool_boundary_denies_unknown_tool():
    d = PolicyEngine().evaluate(
        Action("unknown.tool", {}, "actor", "tenant"),
        registered_tools=frozenset({"echo"}),
    )
    assert not d.allowed
    assert d.reason == "tool_not_registered"
