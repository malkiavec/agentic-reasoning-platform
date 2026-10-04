from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from packages.observability.metrics import RunMetrics
from packages.security.kill_switch import KillSwitch
from packages.db.session import SessionLocal
from packages.db.repository import get_run, update_run
from apps.api.auth import RequestPrincipal, require_principal

router = APIRouter(prefix="/v1")
metrics = RunMetrics()
PROM_COUNTERS = {
    name: Counter(f"agent_{name}_total", f"Agent platform {name}")
    for name in ("completed_runs", "failed_runs", "tool_calls")
}
PROM_HISTOGRAMS = {
    name: Histogram(f"agent_{name}_seconds", f"Agent platform {name} latency")
    for name in ("run", "tool")
}

@router.get("/system/metrics")
async def system_metrics():
    return metrics.snapshot()

@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: UUID, principal: RequestPrincipal = Depends(require_principal)):
    async with SessionLocal() as session:
        record = await get_run(session, run_id)
        if record is None or record.tenant_id != principal.tenant_id:
            raise HTTPException(404, "run_not_found")
        if record.state in {"completed", "failed", "cancelled"}:
            return {"run_id": str(run_id), "state": record.state}
        await update_run(session, run_id, state="cancel_requested")
        return {"run_id": str(run_id), "state": "cancel_requested"}

@router.post("/admin/kill-switch")
async def set_kill_switch(enabled: bool = True, tenant_id: str | None = None,
                          principal: RequestPrincipal = Depends(require_principal)):
    if "admin" not in principal.roles:
        raise HTTPException(403, "admin_role_required")
    target = tenant_id or principal.tenant_id
    if tenant_id is not None and "admin" not in principal.roles:
        raise HTTPException(403, "cross_tenant_kill_switch_forbidden")
    switch = KillSwitch()
    if enabled:
        await switch.activate(target)
    else:
        await switch.deactivate(target)
    return {"enabled": enabled, "tenant_id": target}
