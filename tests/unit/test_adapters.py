import pytest

from packages.tools.builtins import ApprovalProbeAdapter, EchoAdapter
from packages.tools.contracts import ToolContext

@pytest.mark.asyncio
async def test_echo_adapter_is_tenant_bound():
    result = await EchoAdapter().invoke(
        {"text": "hello"},
        ToolContext(tenant_id="t1", actor="a1", run_id="r1", request_id="q1"),
    )
    assert result["tenant_id"] == "t1"

def test_approval_probe_requires_approval():
    assert ApprovalProbeAdapter.security.requires_approval is True
