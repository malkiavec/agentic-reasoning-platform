import asyncio
import pytest
from packages.db.action_ledger import begin_action
from packages.db.session import SessionLocal

@pytest.mark.asyncio
async def test_concurrent_action_claim_load():
    async def claim(i):
        async with SessionLocal() as s:
            return await begin_action(s,tenant_id="load",run_id=None,action_id=f"action-{i%10}",tool="echo",idempotent=True)
    rows=await asyncio.gather(*(claim(i) for i in range(100)))
    assert len(rows)==100
    assert {r.action_id for r in rows}=={f"action-{i}" for i in range(10)}
