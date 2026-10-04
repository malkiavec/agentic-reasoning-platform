from packages.security.tenancy import Principal, TenantAuthorizer

def test_cross_tenant_access_denied():
    p = Principal("u1", "tenant-a")
    assert not TenantAuthorizer().authorize(p, "tenant-b")

def test_role_checked():
    p = Principal("u1", "tenant-a", frozenset({"operator"}))
    assert TenantAuthorizer().authorize(p, "tenant-a", "operator")
