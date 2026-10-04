from uuid import UUID
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from packages.db.repository import create_run, get_run
from packages.db.session import SessionLocal
from apps.worker.tasks import execute_run
from apps.api.websocket import router as websocket_router

app = FastAPI(title="Agentic Reasoning Platform API", version="0.2.0")
app.include_router(websocket_router)

class RunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    tenant_id: str = Field(default="default", min_length=1, max_length=128)
    model: str | None = None
    reasoning_effort: str = "medium"
    max_steps: int = Field(default=20, ge=1, le=200)

class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/runs", response_model=RunResponse)
async def create_agent_run(request: RunRequest):
    async with SessionLocal() as session:
        record = await create_run(session, tenant_id=request.tenant_id,
                                  prompt=request.prompt, model=request.model or "reasoning-default",
                                  reasoning_effort=request.reasoning_effort,
                                  checkpoint={"max_steps": request.max_steps})
    execute_run.delay(str(record.id))
    return RunResponse(run_id=str(record.id), status="accepted", message="Run queued")

@app.get("/v1/runs/{run_id}")
async def get_agent_run(run_id: UUID):
    async with SessionLocal() as session:
        record = await get_run(session, run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="run_not_found")
        return {"run_id": str(record.id), "state": record.state,
                "checkpoint": record.checkpoint, "attempts": record.attempts}
