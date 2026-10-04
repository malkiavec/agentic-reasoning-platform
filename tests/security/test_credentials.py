from packages.security.credentials import CredentialResolver

def test_credentials_are_tenant_scoped(monkeypatch):
    monkeypatch.setenv("TOOL_CREDENTIALS_JSON", '{"tenant-a":{"github":"token-a"},"tenant-b":{"github":"token-b"}}')
    resolver = CredentialResolver()
    assert resolver.get("tenant-a", "github") == "token-a"
    assert resolver.get("tenant-b", "github") == "token-b"
    assert resolver.get("tenant-c", "github") is None

def test_credentials_do_not_fall_back_across_tenants(monkeypatch):
    monkeypatch.setenv("TOOL_CREDENTIALS_JSON", '{"tenant-a":{"github":"token-a"}}')
    monkeypatch.delenv("GITHUB_TOKEN_TENANT_B", raising=False)
    resolver = CredentialResolver()
    assert resolver.get("tenant-b", "github") is None
