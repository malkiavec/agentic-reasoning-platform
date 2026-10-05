import asyncio,json,os
from uuid import UUID
from celery import Task
from redis.asyncio import Redis
from packages.db.repository import get_run,update_run,audit
from packages.db.event_history import append_event
from packages.db.session import SessionLocal
from packages.agent_runtime.planner import Planner,StructuredPlanner
from packages.agent_runtime.provider_factory import build_gateway_from_env
from packages.guardrails.input import InputGuardrail
from packages.orchestration.state import Checkpoint,RunState
from packages.tools.execution import ToolExecutor
from packages.hitl.bridge import PersistentApprovalService
from packages.security.policy import PolicyEngine
from packages.security.redaction import redact_value
from .celery_app import celery_app
from packages.tools.catalog import build_default_registry
REDIS_URL=os.getenv("REDIS_URL","redis://redis:6379/0")
registry=build_default_registry()
try: gateway=build_gateway_from_env()
except RuntimeError:
 from packages.agent_runtime.gateway import MockProvider,ModelGateway
 from packages.agent_runtime.routing import ModelRoute,ModelRouter
 gateway=ModelGateway(ModelRouter([ModelRoute("mock","reasoning-default",1000000,frozenset({"reasoning","structured_output"}))])); gateway.register("mock",MockProvider())

async def emit(redis,run_id,event_type,**payload):
 tenant_id=payload.pop("_tenant_id",None); safe=redact_value(payload); event={"type":event_type,"run_id":run_id,**safe}
 if tenant_id:
  async with SessionLocal() as s: await append_event(s,tenant_id=tenant_id,run_id=UUID(run_id),event_type=event_type,actor="system",payload=safe)
 await redis.publish(f"run:{run_id}",json.dumps(event,separators=(",",":")))

async def mark_terminal_failure(run_id:str,reason:str):
 try:
  async with SessionLocal() as s:
   r=await get_run(s,UUID(run_id))
   if r and r.state not in {"completed","cancelled","recovery_required"}:
    cp=dict(r.checkpoint or {}); cp["state"]=RunState.FAILED.value; cp["error"]=reason
    await update_run(s,UUID(run_id),state="failed",checkpoint=cp)
    await audit(s,tenant_id=r.tenant_id,run_id=UUID(run_id),event_type="run.failed",actor="system",payload={"reason":reason})
 except Exception:
  pass

class DurableTask(Task):
 autoretry_for=(RuntimeError,)
 retry_backoff=True
 retry_backoff_max=300
 retry_jitter=True
 max_retries=5
 def on_failure(self,exc,task_id,args,kwargs,einfo):
  if self.request.retries>=self.max_retries:
   run_id=str(args[0]) if args else str(kwargs.get("run_id",""))
   if run_id: asyncio.run(mark_terminal_failure(run_id,f"{type(exc).__name__}:{exc}"))
  return super().on_failure(exc,task_id,args,kwargs,einfo)

@celery_app.task(bind=True,base=DurableTask,name="agent.run")
def execute_run(self,run_id:str)->dict: return asyncio.run(_execute_run(self,run_id))

async def _execute_run(task,run_id:str)->dict:
 redis=Redis.from_url(REDIS_URL,decode_responses=False)
 try:
  async with SessionLocal() as s:
   record=await get_run(s,UUID(run_id))
   if record is None:return {"run_id":run_id,"state":"missing"}
   await update_run(s,UUID(run_id),attempts=record.attempts+1)
   checkpoint=Checkpoint.from_dict(record.checkpoint or {})
   if checkpoint.state in {RunState.COMPLETED,RunState.CANCELLED}: return {"run_id":run_id,"state":checkpoint.state.value}
   if checkpoint.state!=RunState.WAITING_APPROVAL:
    verdict=InputGuardrail().check(record.prompt)
    if not verdict.allowed:
     checkpoint.state=RunState.FAILED; checkpoint.results["error"]="input_guardrail_blocked"
     await update_run(s,UUID(run_id),state="failed",checkpoint=checkpoint.as_dict()); await audit(s,tenant_id=record.tenant_id,run_id=UUID(run_id),event_type="guardrail.blocked",actor="system",payload={"findings":verdict.findings}); await emit(redis,run_id,"run.failed",reason="input_guardrail_blocked",_tenant_id=record.tenant_id); return {"run_id":run_id,"state":"failed"}
    await update_run(s,UUID(run_id),state="planning"); await emit(redis,run_id,"run.planning",_tenant_id=record.tenant_id)
    if not checkpoint.plan:
     max_steps=int((record.checkpoint or {}).get("max_steps",20))
     try: steps=await StructuredPlanner(gateway,registry).plan(record.prompt,model=record.model,reasoning_effort=record.reasoning_effort,max_steps=max_steps)
     except ValueError: steps=Planner().plan(record.prompt,max_steps)
     checkpoint.plan=[{"id":x.id,"tool":x.tool,"arguments":x.arguments,"parallel_group":x.parallel_group,"depends_on":getattr(x,"depends_on",None) or []} for x in steps]
     await update_run(s,UUID(run_id),checkpoint=checkpoint.as_dict())
  executor=ToolExecutor(registry,PolicyEngine(),PersistentApprovalService(SessionLocal))
  for index,raw in enumerate(checkpoint.plan):
   if raw["id"] in checkpoint.completed_steps: continue
   async with SessionLocal() as current:
    latest=await get_run(current,UUID(run_id))
    if latest is None:return {"run_id":run_id,"state":"missing"}
    if latest.state=="cancel_requested":
     checkpoint.state=RunState.CANCELLED; await update_run(current,UUID(run_id),state="cancelled",checkpoint=checkpoint.as_dict()); await emit(redis,run_id,"run.cancelled",_tenant_id=record.tenant_id); return {"run_id":run_id,"state":"cancelled"}
   checkpoint.state=RunState.EXECUTING; checkpoint.step_index=index; await update_run(s,UUID(run_id),state="executing",checkpoint=checkpoint.as_dict()); await emit(redis,run_id,"step.started",step_id=raw["id"],index=index,_tenant_id=record.tenant_id)
   if raw["tool"]=="__final__": result={"ok":True,"output":raw["arguments"]["prompt"]}
   else:
    prior=checkpoint.results.get(raw["id"],{}); approved_id=prior.get("approval_id") if prior.get("status")=="approval_pending" else None
    result=(await executor.execute(raw["tool"],raw["arguments"],actor="agent",tenant_id=record.tenant_id,run_id=run_id,approved_approval_id=approved_id)).__dict__
   if result.get("error")=="approval_pending":
    checkpoint.state=RunState.WAITING_APPROVAL; checkpoint.results[raw["id"]]={"status":"approval_pending","approval_id":result["approval_id"]}
    await update_run(s,UUID(run_id),state="waiting_approval",checkpoint=checkpoint.as_dict()); await emit(redis,run_id,"run.waiting_approval",step_id=raw["id"],approval_id=result["approval_id"],_tenant_id=record.tenant_id); await audit(s,tenant_id=record.tenant_id,run_id=UUID(run_id),event_type="approval.requested",actor="agent",payload=result); return {"run_id":run_id,"state":"waiting_approval","approval_id":result["approval_id"]}
   if not result.get("ok",False):
    checkpoint.results[raw["id"]]=result; recovery=result.get("error")=="action_recovery_required"; checkpoint.state=RunState.RECOVERY_REQUIRED if recovery else RunState.FAILED
    await update_run(s,UUID(run_id),state="recovery_required" if recovery else "failed",checkpoint=checkpoint.as_dict()); await emit(redis,run_id,"step.failed",step_id=raw["id"],error=result.get("error"),_tenant_id=record.tenant_id); return {"run_id":run_id,"state":"recovery_required" if recovery else "failed","error":result.get("error")}
   checkpoint.results[raw["id"]]=result; checkpoint.completed_steps.append(raw["id"]); checkpoint.step_index=index+1; await update_run(s,UUID(run_id),state="executing",checkpoint=checkpoint.as_dict()); await emit(redis,run_id,"step.completed",step_id=raw["id"],result=result,_tenant_id=record.tenant_id)
  checkpoint.state=RunState.COMPLETED; await update_run(s,UUID(run_id),state="completed",checkpoint=checkpoint.as_dict()); await audit(s,tenant_id=record.tenant_id,run_id=UUID(run_id),event_type="run.completed",actor="system",payload={"steps":len(checkpoint.completed_steps)}); await emit(redis,run_id,"run.completed",steps=len(checkpoint.completed_steps),_tenant_id=record.tenant_id); return {"run_id":run_id,"state":"completed"}
 except Exception:
  try: await emit(redis,run_id,"run.retry_scheduled",reason="execution_error")
  except Exception: pass
  raise
 finally: await redis.aclose()
