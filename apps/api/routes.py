from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import select, text
from packages.observability.metrics import RunMetrics
from packages.security.kill_switch import KillSwitch
from packages.db.session import SessionLocal
from packages.db.repository import get_run, update_run, audit
from packages.db.models import RunRecord
from packages.db.event_history import replay_events
from packages.tools.catalog import build_default_registry
from apps.api.auth import RequestPrincipal, require_principal

router=APIRouter(prefix="/v1")
metrics=RunMetrics()
PROM_COUNTERS={n:Counter(f"agent_{n}_total",f"Agent platform {n}") for n in ("completed_runs","failed_runs","tool_calls")}
PROM_HISTOGRAMS={n:Histogram(f"agent_{n}_seconds",f"Agent platform {n} latency") for n in ("run","tool")}

@router.get("/system/metrics")
async def system_metrics(): return metrics.snapshot()

@router.get("/metrics",include_in_schema=False)
async def prometheus_metrics(): return Response(content=generate_latest(),media_type=CONTENT_TYPE_LATEST)

@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id:UUID,principal:RequestPrincipal=Depends(require_principal)):
    async with SessionLocal() as s:
        r=await get_run(s,run_id)
        if r is None or r.tenant_id!=principal.tenant_id: raise HTTPException(404,"run_not_found")
        if r.state in {"completed","failed","cancelled"}: return {"run_id":str(run_id),"state":r.state}
        await update_run(s,run_id,state="cancel_requested")
        await audit(s,tenant_id=principal.tenant_id,run_id=run_id,event_type="run.cancel_requested",actor=principal.subject,payload={})
        return {"run_id":str(run_id),"state":"cancel_requested"}

@router.post("/admin/kill-switch")
async def set_kill_switch(enabled:bool=True,tenant_id:str|None=None,global_scope:bool=False,principal:RequestPrincipal=Depends(require_principal)):
    if "admin" not in principal.roles: raise HTTPException(403,"admin_role_required")
    if global_scope and tenant_id is not None: raise HTTPException(400,"global_and_tenant_scope_conflict")
    if tenant_id is not None and tenant_id!=principal.tenant_id: raise HTTPException(403,"cross_tenant_kill_switch_forbidden")
    target=None if global_scope else (tenant_id or principal.tenant_id); switch=KillSwitch()
    await (switch.activate(target) if enabled else switch.deactivate(target))
    return {"enabled":enabled,"scope":"global" if global_scope else "tenant","tenant_id":target}

@router.get("/runs")
async def list_runs(limit:int=50,principal:RequestPrincipal=Depends(require_principal)):
    limit=max(1,min(limit,200))
    async with SessionLocal() as s:
        rows=await s.scalars(select(RunRecord).where(RunRecord.tenant_id==principal.tenant_id).order_by(RunRecord.created_at.desc()).limit(limit))
        return [{"run_id":str(r.id),"state":r.state,"model":r.model,"reasoning_effort":r.reasoning_effort,"created_at":r.created_at.isoformat(),"updated_at":r.updated_at.isoformat()} for r in rows]

@router.get("/runs/{run_id}/events")
async def run_events(run_id:UUID,after_sequence:int|None=None,limit:int=500,principal:RequestPrincipal=Depends(require_principal)):
    async with SessionLocal() as s:
        r=await get_run(s,run_id)
        if r is None or r.tenant_id!=principal.tenant_id: raise HTTPException(404,"run_not_found")
        events=await replay_events(s,tenant_id=principal.tenant_id,run_id=run_id,after_sequence=after_sequence,limit=max(1,min(limit,1000)))
        return [{"event_id":str(e.id),"sequence":e.sequence,"type":e.event_type,"actor":e.actor,"payload":e.payload,"created_at":e.created_at.isoformat()} for e in events]

@router.get("/runs/{run_id}/audit")
async def run_audit(run_id:UUID,limit:int=500,principal:RequestPrincipal=Depends(require_principal)):
    async with SessionLocal() as s:
        r=await get_run(s,run_id)
        if r is None or r.tenant_id!=principal.tenant_id: raise HTTPException(404,"run_not_found")
        rows=(await s.execute(text("""SELECT sequence,event_type,actor,payload,created_at FROM audit_events WHERE tenant_id=:tenant AND run_id=:run ORDER BY sequence DESC LIMIT :limit"""),{"tenant":principal.tenant_id,"run":run_id,"limit":max(1,min(limit,1000))})).mappings().all()
        return [dict(x) for x in rows]

@router.post("/runs/{run_id}/retry")
async def retry_run(run_id:UUID,principal:RequestPrincipal=Depends(require_principal)):
    async with SessionLocal() as s:
        r=await get_run(s,run_id)
        if r is None or r.tenant_id!=principal.tenant_id: raise HTTPException(404,"run_not_found")
        if r.state not in {"failed","cancelled"}: raise HTTPException(409,"run_not_retryable")
        cp=dict(r.checkpoint or {}); cp["state"]="executing"; cp.pop("error",None)
        step=cp.get("step_index"); plan=cp.get("plan",[])
        if isinstance(step,int) and 0<=step<len(plan): cp.get("results",{}).pop(plan[step].get("id"),None)
        await update_run(s,run_id,state="executing",checkpoint=cp)
        await audit(s,tenant_id=principal.tenant_id,run_id=run_id,event_type="run.retry_requested",actor=principal.subject,payload={})
    from apps.worker.tasks import execute_run
    execute_run.delay(str(run_id))
    return {"run_id":str(run_id),"state":"retry_queued"}

@router.get("/tools")
async def list_tools(principal:RequestPrincipal=Depends(require_principal)):
    registry=build_default_registry()
    return [{"name":s.name,"description":s.description,"risk":s.risk,"requires_approval":s.requires_approval,"permissions":sorted(s.permissions),"auth_requirements":sorted(s.auth_requirements),"rate_limit_per_minute":s.rate_limit_per_minute} for s in registry.list()]

@router.get("/admin/policy")
async def get_policy(principal:RequestPrincipal=Depends(require_principal)):
    if "admin" not in principal.roles: raise HTTPException(403,"admin_role_required")
    async with SessionLocal() as s:
        row=(await s.execute(text("SELECT policy,updated_by,updated_at FROM tenant_policies WHERE tenant_id=:tenant"),{"tenant":principal.tenant_id})).mappings().first()
        return dict(row) if row else {"policy":{},"updated_by":None,"updated_at":None}

@router.put("/admin/policy")
async def set_policy(policy:dict,principal:RequestPrincipal=Depends(require_principal)):
    if "admin" not in principal.roles: raise HTTPException(403,"admin_role_required")
    async with SessionLocal() as s:
        await s.execute(text("""INSERT INTO tenant_policies(tenant_id,policy,updated_by,updated_at) VALUES(:tenant,CAST(:policy AS jsonb),:actor,now())
        ON CONFLICT(tenant_id) DO UPDATE SET policy=EXCLUDED.policy,updated_by=EXCLUDED.updated_by,updated_at=now()"""),
        {"tenant":principal.tenant_id,"policy":__import__("json").dumps(policy),"actor":principal.subject})
        await s.commit()
        await audit(s,tenant_id=principal.tenant_id,run_id=None,event_type="policy.updated",actor=principal.subject,payload={"keys":list(policy)[:50]})
    return {"updated":True,"tenant_id":principal.tenant_id}

@router.get("/admin/budget")
async def get_budget(principal:RequestPrincipal=Depends(require_principal)):
    if "admin" not in principal.roles: raise HTTPException(403,"admin_role_required")
    async with SessionLocal() as s:
        row=(await s.execute(text("SELECT monthly_run_limit,monthly_tool_call_limit,monthly_token_limit,monthly_cost_limit_micros,used_runs,used_tool_calls,used_tokens,used_cost_micros,period_start,updated_at FROM tenant_budgets WHERE tenant_id=:tenant"),{"tenant":principal.tenant_id})).mappings().first()
        return dict(row) if row else None

@router.put("/admin/budget")
async def set_budget(monthly_run_limit:int=10000,monthly_tool_call_limit:int=100000,monthly_token_limit:int=100000000,monthly_cost_limit_micros:int=1000000000,principal:RequestPrincipal=Depends(require_principal)):
    if "admin" not in principal.roles: raise HTTPException(403,"admin_role_required")
    if min(monthly_run_limit,monthly_tool_call_limit,monthly_token_limit,monthly_cost_limit_micros)<1: raise HTTPException(400,"budget_values_must_be_positive")
    async with SessionLocal() as s:
        await s.execute(text("""INSERT INTO tenant_budgets(tenant_id,monthly_run_limit,monthly_tool_call_limit,monthly_token_limit,monthly_cost_limit_micros)
        VALUES(:tenant,:runs,:calls,:tokens,:cost) ON CONFLICT(tenant_id) DO UPDATE SET monthly_run_limit=EXCLUDED.monthly_run_limit,monthly_tool_call_limit=EXCLUDED.monthly_tool_call_limit,monthly_token_limit=EXCLUDED.monthly_token_limit,monthly_cost_limit_micros=EXCLUDED.monthly_cost_limit_micros,updated_at=now()"""),
        {"tenant":principal.tenant_id,"runs":monthly_run_limit,"calls":monthly_tool_call_limit,"tokens":monthly_token_limit,"cost":monthly_cost_limit_micros})
        await s.commit()
        await audit(s,tenant_id=principal.tenant_id,run_id=None,event_type="budget.updated",actor=principal.subject,payload={"runs":monthly_run_limit,"calls":monthly_tool_call_limit})
    return {"updated":True}

@router.get("/admin/integrations")
async def list_integrations(principal:RequestPrincipal=Depends(require_principal)):
    if "admin" not in principal.roles: raise HTTPException(403,"admin_role_required")
    async with SessionLocal() as s:
        rows=(await s.execute(text("SELECT tool_name,enabled,config,credential_ref,updated_by,updated_at FROM tenant_integrations WHERE tenant_id=:tenant ORDER BY tool_name"),{"tenant":principal.tenant_id})).mappings().all()
        return [dict(x) for x in rows]

@router.put("/admin/integrations/{tool_name}")
async def configure_integration(tool_name:str,enabled:bool=True,config:dict|None=None,credential_ref:str|None=None,principal:RequestPrincipal=Depends(require_principal)):
    if "admin" not in principal.roles: raise HTTPException(403,"admin_role_required")
    if build_default_registry().get(tool_name) is None: raise HTTPException(404,"tool_not_registered")
    if credential_ref and len(credential_ref)>512: raise HTTPException(400,"credential_ref_too_long")
    async with SessionLocal() as s:
        await s.execute(text("""INSERT INTO tenant_integrations(tenant_id,tool_name,enabled,config,credential_ref,updated_by,updated_at)
        VALUES(:tenant,:tool,:enabled,CAST(:config AS jsonb),:ref,:actor,now()) ON CONFLICT(tenant_id,tool_name) DO UPDATE SET enabled=EXCLUDED.enabled,config=EXCLUDED.config,credential_ref=EXCLUDED.credential_ref,updated_by=EXCLUDED.updated_by,updated_at=now()"""),
        {"tenant":principal.tenant_id,"tool":tool_name,"enabled":enabled,"config":__import__("json").dumps(config or {}),"ref":credential_ref,"actor":principal.subject})
        await s.commit()
        await audit(s,tenant_id=principal.tenant_id,run_id=None,event_type="integration.configured",actor=principal.subject,payload={"tool":tool_name,"enabled":enabled,"credential_ref":bool(credential_ref)})
    return {"tool_name":tool_name,"enabled":enabled,"configured":True}
