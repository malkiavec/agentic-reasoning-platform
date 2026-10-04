import pytest
from packages.db.action_ledger import begin_action, complete_action
from packages.db.session import SessionLocal
from packages.db.models import ToolActionRecord

@pytest.mark.asyncio
async def test_durable_action_ledger_deduplicates_completed_action():
    async with SessionLocal() as session:
        first = await begin_action(
            session, tenant_id="tenant-a", run_id=None,
            action_id="action-test-1", tool="echo", idempotent=True,
        )
        await complete_action(session, first, {"ok": True})
    async with SessionLocal() as session:
        second = await begin_action(
            session, tenant_id="tenant-a", run_id=None,
            action_id="action-test-1", tool="echo", idempotent=True,
        )
        assert second.status == "completed"
        assert second.output == {"ok": True}

@pytest.mark.asyncio
async def test_durable_action_ledger_is_tenant_scoped():
    async with SessionLocal() as session:
        first = await begin_action(
            session, tenant_id="tenant-a", run_id=None,
            action_id="same-action", tool="echo", idempotent=True,
        )
        await complete_action(session, first, {"tenant": "a"})
    async with SessionLocal() as session:
        second = await begin_action(
            session, tenant_id="tenant-b", run_id=None,
            action_id="same-action", tool="echo", idempotent=True,
        )
        assert second.status == "in_progress"
        assert second.tenant_id == "tenant-b"
