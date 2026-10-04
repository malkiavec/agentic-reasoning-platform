from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from packages.observability.metrics import RunMetrics
from packages.db.session import SessionLocal
from packages.db.repository import get_run, update_run
from apps.api.auth import RequestPrincipal, require_principal

router=APIRouter(prefix="/v1")
metrics = RunMetrics()
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
PROM_GAUGES = {
    name: Gauge(f"agent_{name}", f"Agent platform {name}")
    for name in ("completed_runs", "failed_runs", "input_tokens", "output_tokens", "tool_calls")
}

@router.get("/system/metrics")
async def system_metrics():
    return metrics.snapshot()

@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    snapshot = metrics.snapshot()
    values = {
        "completed_runs": snapshot["completed_runs"],
        "failed_runs": snapshot["failed_runs"],
        "input_tokens": snapshot["input_tokens"],
        "output_tokens": snapshot["output_tokens"],
        "tool_calls": snapshot["tool_calls"],
    }
    for name, value in values.items():
        PROM_GAUGES[name].set(value)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: UUID, principal: RequestPrincipal=Depends(require_principal)):
    async with SessionLocal() as session:
        record=await get_run(session,run_id)
        if record is None or record.tenant_id != principal.tenant_id:
            raise HTTPException(404,"run_not_found")
        if record.state in {"completed","failed","cancelled"}:
            return {"run_id":str(run_id),"state":record.state}
        await update_run(session,run_id,state="cancel_requested")
        return {"run_id":str(run_id),"state":"cancel_requested"}
