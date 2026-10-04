from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from packages.observability.metrics import RunMetrics
from packages.db.session import SessionLocal
from packages.db.repository import get_run, update_run
from apps.api.auth import RequestPrincipal, require_principal

router=APIRouter(prefix="/v1")
metrics=RunMetrics()

@router.get("/system/metrics")
async def system_metrics():
    return metrics.snapshot()

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
