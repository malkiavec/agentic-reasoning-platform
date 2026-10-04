import pytest

from packages.security.policy import PolicyEngine
from packages.tools.http_rest import HttpRestAdapter
from packages.tools.catalog import build_default_registry

def test_http_adapter_requires_allowlist(monkeypatch):
    monkeypatch.setenv("HTTP_ALLOWED_DOMAINS", "example.com")
    adapter = HttpRestAdapter()
    assert adapter._allowed("https://example.com/path")
    assert not adapter._allowed("https://evil.example/path")

def test_http_write_policy_requires_approval():
    decision = PolicyEngine().evaluate(
        __import__("packages.security.policy", fromlist=["Action"]).Action(
            tool="http.rest",
            arguments={"method": "POST", "url": "https://example.com"},
            actor="agent",
            tenant_id="tenant",
        )
    )
    assert decision.requires_approval

def test_http_tool_is_registered():
    registry = build_default_registry()
    assert registry.get("http.rest") is not None
