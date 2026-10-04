import os
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException
from redis.asyncio import Redis
from sqlalchemy import text
from pydantic import BaseModel, Field
from packages.db.repository import create_run, get_run
from packages.db.session import SessionLocal
from apps.worker.tasks import execute_run
from apps.api.websocket import router as websocket_router
from apps.api.approvals import router as approval_router
from apps.api.routes import router as api_router
from apps.api.auth import RequestPrincipal, require_principal

app = FastAPI(title="Agentic Reasoning Platform API", version="0.4.0")
app.include_router(websocket_router)
app.include_router(approval_router)
app.include_router(api_router)

class RunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=200_000)
    tenant_id: str | None = Field(default=None, min_length=1, max_length=128)
    model: str | None = None
    reasoning_effort: str = "medium"
    max_steps: int = Field(default=20, ge=1, le=200)
    idempotency_key: str | None = Field(default=None, max_length=256)

class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        redis = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        try:
            await redis.ping()
        finally:
            await redis.aclose()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="dependencies_unready") from exc
    return {"status": "ready"}

@app.post("/v1/runs", response_model=RunResponse)
async def create_agent_run(request: RunRequest, principal: RequestPrincipal = Depends(require_principal)):
    tenant_id = principal.tenant_id
    if request.tenant_id is not None and request.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_mismatch")
    async with SessionLocal() as session:
        record = await create_run(session, tenant_id=tenant_id, prompt=request.prompt,
                                  model=request.model or "reasoning-default",
                                  reasoning_effort=request.reasoning_effort,
                                  idempotency_key=request.idempotency_key,
                                  checkpoint={"max_steps": request.max_steps})
    execute_run.delay(str(record.id))
    return RunResponse(run_id=str(record.id), status="accepted", message="Run queued")

@app.get("/v1/runs/{run_id}")
async def get_agent_run(run_id: UUID, principal: RequestPrincipal = Depends(require_principal)):
    async with SessionLocal() as session:
        record = await get_run(session, run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="run_not_found")
        if record.tenant_id != principal.tenant_id:
            raise HTTPException(status_code=404, detail="run_not_found")
        return {"run_id": str(record.id), "state": record.state,
                "checkpoint": record.checkpoint, "attempts": record.attempts}
