import pytest
from packages.security.credentials import CredentialResolver
from packages.security.policy import Action, PolicyEngine
from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity
from packages.tools.registry import ToolRegistry, ToolSpec
from packages.tools.execution import ToolExecutor
from packages.security.ssrf import SSRFViolation, validate_url

class NoopAdapter(ToolAdapter):
    name="safe.action"
    security=ToolSecurity(risk="high",requires_approval=True,idempotent=False)
    async def invoke(self,arguments,context): return {"tenant":context.tenant_id}

def registry():
    r=ToolRegistry()
    r.register(ToolSpec("safe.action","safe",{"type":"object","additionalProperties":False},
                        security=NoopAdapter.security,allowed_agents=frozenset({"agent"})),NoopAdapter())
    return r

def test_cross_tenant_access_is_denied():
    r=ToolRegistry()
    security=ToolSecurity(allowed_tenants=frozenset({"tenant-a"}))
    class TenantAdapter(ToolAdapter):
        name="tenant.tool"; security=security
        async def invoke(self,arguments,context): return {"ok":True}
    r.register(ToolSpec("tenant.tool","tenant scoped",{"type":"object"},security=security),TenantAdapter())
    assert r.get("tenant.tool").security.allowed_tenants==frozenset({"tenant-a"})

def test_credential_isolation_and_no_global_fallback(monkeypatch):
    monkeypatch.setenv("TOOL_CREDENTIALS_JSON",'{"a":{"slack":"A"},"b":{"slack":"B"}}')
    monkeypatch.setenv("SLACK_TOKEN_A","A-env"); monkeypatch.setenv("SLACK_TOKEN_B","B-env")
    c=CredentialResolver()
    assert c.get("a","slack")=="A" and c.get("b","slack")=="B" and c.get("c","slack") is None

def test_unregistered_tools_are_denied():
    d=PolicyEngine().evaluate(Action("not.registered",{}, "agent","tenant-a"),registered_tools=frozenset({"safe.action"}))
    assert not d.allowed and d.reason=="tool_not_registered"

@pytest.mark.asyncio
async def test_approval_bypass_is_denied():
    class DenyApproval:
        async def verify(self,**kwargs): return False
        async def request(self,**kwargs): raise AssertionError("must not request when approval id supplied")
    result=await ToolExecutor(registry(),approval_service=DenyApproval(),redis_url="redis://invalid:6399/0").execute(
        "safe.action",{},actor="agent",tenant_id="tenant-a",run_id="00000000-0000-0000-0000-000000000001",approved_approval_id="forged")
    assert not result.ok and result.error=="approval_invalid"

def test_restricted_operations_are_denied():
    engine=PolicyEngine()
    for tool in ("admin.delete","secrets.read","credential.export","identity.impersonate"):
        d=engine.evaluate(Action(tool,{},"agent","tenant-a"),registered_tools=frozenset({tool}))
        assert not d.allowed and d.reason=="restricted_tool"

def test_ssrf_private_and_metadata_addresses_are_denied():
    for url in ("http://127.0.0.1/","http://169.254.169.254/latest/meta-data/","http://10.0.0.1/"):
        with pytest.raises(SSRFViolation): validate_url(url)

class CompromisedAdapter(ToolAdapter):
    name="compromised"; security=ToolSecurity()
    async def invoke(self,arguments,context):
        assert "credential" not in arguments
        assert context.tenant_id=="tenant-a"
        return {"ok":True}

@pytest.mark.asyncio
async def test_compromised_adapter_receives_no_credentials():
    assert await CompromisedAdapter().invoke({},ToolContext("tenant-a","agent","run","request"))=={"ok":True}
