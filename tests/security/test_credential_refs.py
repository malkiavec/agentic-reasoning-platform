import os

import pytest

from packages.security.credentials import CredentialResolver


def test_credential_ref_resolves_only_named_secret(monkeypatch):
    monkeypatch.setenv("TENANT_A_SLACK", "secret-a")
    monkeypatch.setenv("TENANT_B_SLACK", "secret-b")
    resolver = CredentialResolver()
    assert resolver.get("tenant-a", "slack", "TENANT_A_SLACK") == "secret-a"
    assert resolver.get("tenant-a", "slack", "TENANT_B_SLACK") == "secret-b"


def test_credential_ref_rejects_shell_expression(monkeypatch):
    resolver = CredentialResolver()
    monkeypatch.setenv("TENANT_A_SLACK", "secret-a")
    with pytest.raises(RuntimeError, match="invalid_credential_ref"):
        resolver.get("tenant-a", "slack", "TENANT_A_SLACK;env")
