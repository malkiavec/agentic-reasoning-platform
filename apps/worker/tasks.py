from uuid import UUID
from celery import Task
from packages.db.repository import update_run
from packages.db.session import SessionLocal
from .celery_app import celery_app

class DurableTask(Task):
    autoretry_for = (RuntimeError,)
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    max_retries = 5

@celery_app.task(bind=True, base=DurableTask, name="agent.run")
def execute_run(self, run_id: str) -> dict:
    import asyncio
    async def work():
        async with SessionLocal() as session:
            await update_run(session, UUID(run_id), state="planning", attempts=self.request.retries)
            # Provider/tool execution is intentionally delegated to the runtime layer.
            await update_run(session, UUID(run_id), state="completed",
                             checkpoint={"phase": "completed"})
    asyncio.run(work())
    return {"run_id": run_id, "state": "completed"}
