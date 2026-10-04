from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from packages.observability.metrics import RunMetrics
from packages.security.kill_switch import KillSwitch
from packages.db.session import SessionLocal
from packages.db.repository import get_run, update_run
from packages.db.models import RunRecord
from packages.db.event_history import replay_events
from packages.tools.catalog import build_default_registry
from sqlalchemy import select
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
async def set_kill_switch(enabled: bool = True, tenant_id: str | None = None, global_scope: bool = False,
                          principal: RequestPrincipal = Depends(require_principal)):
    if "admin" not in principal.roles:
        raise HTTPException(403, "admin_role_required")
    if global_scope and tenant_id is not None:
        raise HTTPException(400, "global_and_tenant_scope_conflict")
    if tenant_id is not None and tenant_id != principal.tenant_id:
        raise HTTPException(403, "cross_tenant_kill_switch_forbidden")
    target = None if global_scope else (tenant_id or principal.tenant_id)
    switch = KillSwitch()
    if enabled:
        await switch.activate(target)
    else:
        await switch.deactivate(target)
    return {"enabled": enabled, "scope": "global" if global_scope else "tenant", "tenant_id": target}


@router.get("/runs")
async def list_runs(limit: int = 50, principal: RequestPrincipal = Depends(require_principal)):
    limit = max(1, min(limit, 200))
    async with SessionLocal() as session:
        rows = await session.scalars(
            select(RunRecord)
            .where(RunRecord.tenant_id == principal.tenant_id)
            .order_by(RunRecord.created_at.desc())
            .limit(limit)
        )
        return [{
            "run_id": str(r.id), "state": r.state, "model": r.model,
            "reasoning_effort": r.reasoning_effort, "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        } for r in rows]

@router.get("/runs/{run_id}/events")
async def run_events(run_id: UUID, after_sequence: int | None = None, limit: int = 500,
                     principal: RequestPrincipal = Depends(require_principal)):
    async with SessionLocal() as session:
        run = await get_run(session, run_id)
        if run is None or run.tenant_id != principal.tenant_id:
            raise HTTPException(404, "run_not_found")
        events = await replay_events(
            session, tenant_id=principal.tenant_id, run_id=run_id,
            after_sequence=after_sequence, limit=limit
        )
        return [{
            "event_id": str(e.id), "sequence": e.sequence, "type": e.event_type,
            "actor": e.actor, "payload": e.payload, "created_at": e.created_at.isoformat()
        } for e in events]

@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: UUID, principal: RequestPrincipal = Depends(require_principal)):
    async with SessionLocal() as session:
        run = await get_run(session, run_id)
        if run is None or run.tenant_id != principal.tenant_id:
            raise HTTPException(404, "run_not_found")
        if run.state not in {"failed", "cancelled"}:
            raise HTTPException(409, "run_not_retryable")
        checkpoint = dict(run.checkpoint or {})
        checkpoint["state"] = "executing"
        checkpoint.pop("error", None)
        failed_step = checkpoint.get("step_index")
        plan = checkpoint.get("plan", [])
        if isinstance(failed_step, int) and 0 <= failed_step < len(plan):
            checkpoint.get("results", {}).pop(plan[failed_step].get("id"), None)
        await update_run(session, run_id, state="executing", checkpoint=checkpoint)
    from apps.worker.tasks import execute_run
    execute_run.delay(str(run_id))
    return {"run_id": str(run_id), "state": "retry_queued"}

@router.get("/tools")
async def list_tools(principal: RequestPrincipal = Depends(require_principal)):
    registry = build_default_registry()
    return [{
        "name": spec.name, "description": spec.description, "risk": spec.risk,
        "requires_approval": spec.requires_approval,
        "permissions": sorted(spec.permissions),
        "auth_requirements": sorted(spec.auth_requirements),
        "rate_limit_per_minute": spec.rate_limit_per_minute,
    } for spec in registry.list()]
