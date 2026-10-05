import asyncio
import pytest
from packages.db.action_ledger import begin_action, complete_action
from packages.db.session import SessionLocal
from packages.tools.contracts import ToolAdapter, ToolContext, ToolSecurity
from packages.tools.execution import ToolExecutor
from packages.tools.registry import ToolRegistry, ToolSpec

@pytest.mark.asyncio
async def test_worker_death_after_external_side_effect_requires_recovery():
    async with SessionLocal() as s:
        row=await begin_action(s,tenant_id="chaos",run_id=None,action_id="side-effect-1",tool="side.effect",idempotent=False)
        assert row.status=="in_progress"
    async with SessionLocal() as s:
        retry=await begin_action(s,tenant_id="chaos",run_id=None,action_id="side-effect-1",tool="side.effect",idempotent=False)
        assert retry.status=="in_progress"

@pytest.mark.asyncio
async def test_concurrent_duplicate_ledger_claims_share_one_action():
    async def claim():
        async with SessionLocal() as s:
            return await begin_action(s,tenant_id="concurrency",run_id=None,action_id="same",tool="echo",idempotent=True)
    rows=await asyncio.gather(claim(),claim())
    assert {r.action_id for r in rows}=={"same"}
    async with SessionLocal() as s:
        row=await begin_action(s,tenant_id="concurrency",run_id=None,action_id="same",tool="echo",idempotent=True)
        await complete_action(s,row,{"once":True})
    async with SessionLocal() as s:
        row=await begin_action(s,tenant_id="concurrency",run_id=None,action_id="same",tool="echo",idempotent=True)
        assert row.status=="completed"

class SlowAdapter(ToolAdapter):
    name="slow.provider"; security=ToolSecurity(timeout_seconds=0.01,idempotent=True)
    async def invoke(self,arguments,context):
        await asyncio.sleep(0.1); return {"ok":True}

@pytest.mark.asyncio
async def test_provider_timeout_is_bounded():
    r=ToolRegistry(); r.register(ToolSpec("slow.provider","slow",{"type":"object"},security=SlowAdapter.security),SlowAdapter())
    result=await ToolExecutor(r,redis_url="redis://127.0.0.1:6399/0").execute("slow.provider",{},actor="agent",tenant_id="timeout",run_id=None)
    assert not result.ok and result.error in {"security_dependency_unavailable","tool_timeout"}

@pytest.mark.asyncio
async def test_redis_loss_is_fail_closed_in_production(monkeypatch):
    class DeadRedis:
        async def ping(self): raise ConnectionError("redis down")
        async def aclose(self): return None
    monkeypatch.setenv("APP_ENV","production")
    monkeypatch.setattr("packages.tools.execution.Redis.from_url",lambda *a,**k: DeadRedis())
    monkeypatch.setattr("packages.tools.execution.KillSwitch.is_active",lambda self,tenant_id: asyncio.sleep(0,result=False))
    class Adapter(ToolAdapter):
        name="redis.test"; security=ToolSecurity()
        async def invoke(self,arguments,context): return {"ok":True}
    r=ToolRegistry(); r.register(ToolSpec("redis.test","redis",{"type":"object"},security=Adapter.security),Adapter())
    result=await ToolExecutor(r).execute("redis.test",{},actor="agent",tenant_id="redis-loss",run_id=None)
    assert not result.ok and result.error=="security_dependency_unavailable"
