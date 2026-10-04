import asyncio
import os
from uuid import UUID
from celery import Task
from redis.asyncio import Redis
from packages.db.repository import get_run, update_run, audit
from packages.db.session import SessionLocal
from packages.agent_runtime.planner import Planner
from packages.guardrails.input import InputGuardrail
from packages.orchestration.state import Checkpoint, RunState
from .celery_app import celery_app

REDIS_URL=os.getenv("REDIS_URL","redis://redis:6379/0")

async def emit(redis: Redis, run_id: str, event_type: str, **payload):
    import json
    event={"type":event_type,"run_id":run_id,**payload}
    await redis.publish(f"run:{run_id}", json.dumps(event, separators=(",",":")))

class DurableTask(Task):
    autoretry_for=(RuntimeError,)
    retry_backoff=True
    retry_backoff_max=300
    retry_jitter=True
    max_retries=5

@celery_app.task(bind=True, base=DurableTask, name="agent.run")
def execute_run(self, run_id: str) -> dict:
    return asyncio.run(_execute_run(self, run_id))

async def _execute_run(task: DurableTask, run_id: str) -> dict:
    redis=Redis.from_url(REDIS_URL, decode_responses=False)
    try:
        async with SessionLocal() as session:
            record=await get_run(session, UUID(run_id))
            if record is None:
                return {"run_id":run_id,"state":"missing"}

            checkpoint=Checkpoint.from_dict(record.checkpoint or {})
            if checkpoint.state in {RunState.COMPLETED,RunState.CANCELLED}:
                return {"run_id":run_id,"state":checkpoint.state.value}

            await update_run(session, UUID(run_id), state=RunState.GUARDRAIL.value, attempts=task.request.retries)
            await emit(redis,run_id,"run.guardrail")
            verdict=InputGuardrail().check(record.prompt)
            if not verdict.allowed:
                checkpoint.state=RunState.FAILED
                checkpoint.results["error"]="input_guardrail_blocked"
                await update_run(session,UUID(run_id),state=RunState.FAILED.value,checkpoint=checkpoint.as_dict())
                await audit(session,tenant_id=record.tenant_id,run_id=UUID(run_id),event_type="guardrail.blocked",actor="system",payload={"findings":verdict.findings})
                await emit(redis,run_id,"run.failed",reason="input_guardrail_blocked")
                return {"run_id":run_id,"state":"failed"}

            await update_run(session,UUID(run_id),state=RunState.PLANNING.value)
            await emit(redis,run_id,"run.planning")
            if not checkpoint.plan:
                planner=Planner()
                checkpoint.plan=[{"id":s.id,"tool":s.tool,"arguments":s.arguments,
                                  "parallel_group":s.parallel_group} for s in planner.plan(record.prompt,int((record.checkpoint or {}).get("max_steps",20)))]
                checkpoint.state=RunState.PLANNING
                await update_run(session,UUID(run_id),checkpoint=checkpoint.as_dict())

            await update_run(session,UUID(run_id),state=RunState.EXECUTING.value)
            await emit(redis,run_id,"run.executing",steps=len(checkpoint.plan))

            # Resume semantics: completed step IDs are never re-executed.
            for index, raw in enumerate(checkpoint.plan):
                if raw["id"] in checkpoint.completed_steps:
                    continue
                if await _cancel_requested(run_id):
                    checkpoint.state=RunState.CANCELLED
                    await update_run(session,UUID(run_id),state=RunState.CANCELLED.value,checkpoint=checkpoint.as_dict())
                    await emit(redis,run_id,"run.cancelled")
                    return {"run_id":run_id,"state":"cancelled"}

                checkpoint.step_index=index
                await emit(redis,run_id,"step.started",step_id=raw["id"],index=index)
                if raw["tool"]=="__final__":
                    result={"output":raw["arguments"]["prompt"]}
                else:
                    # Tool execution is deliberately not bypassed here; it must enter the
                    # policy-enforced ToolExecutor before any external side effect.
                    result={"error":"tool_execution_not_configured","tool":raw["tool"]}
                checkpoint.results[raw["id"]]=result
                checkpoint.completed_steps.append(raw["id"])
                checkpoint.step_index=index+1
                await update_run(session,UUID(run_id),state=RunState.EXECUTING.value,checkpoint=checkpoint.as_dict())
                await emit(redis,run_id,"step.completed",step_id=raw["id"],result=result)

            checkpoint.state=RunState.COMPLETED
            await update_run(session,UUID(run_id),state=RunState.COMPLETED.value,checkpoint=checkpoint.as_dict())
            await audit(session,tenant_id=record.tenant_id,run_id=UUID(run_id),event_type="run.completed",actor="system",payload={"steps":len(checkpoint.completed_steps)})
            await emit(redis,run_id,"run.completed",steps=len(checkpoint.completed_steps))
            return {"run_id":run_id,"state":"completed"}
    except Exception as exc:
        async with SessionLocal() as session:
            await update_run(session,UUID(run_id),state=RunState.FAILED.value,
                             checkpoint={"state":"failed","error":"execution_error","detail":str(exc)[:1000]})
        await emit(redis,run_id,"run.failed",reason="execution_error")
        raise
    finally:
        await redis.aclose()

async def _cancel_requested(run_id: str) -> bool:
    # Cancellation endpoint can set a durable state; the worker checks it between steps.
    async with SessionLocal() as session:
        record=await get_run(session,UUID(run_id))
        return record is not None and record.state=="cancel_requested"
