from fastapi import FastAPI
from pydantic import BaseModel, Field
from uuid import uuid4

app = FastAPI(title="Agentic Reasoning Platform API", version="0.1.0")

class RunRequest(BaseModel):
    prompt: str = Field(min_length=1)
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
async def create_run(request: RunRequest):
    run_id = str(uuid4())
    return RunResponse(run_id=run_id, status="accepted", message="Run queued")

@app.get("/v1/runs/{run_id}")
async def get_run(run_id: str):
    return {"run_id": run_id, "status": "not_started"}
