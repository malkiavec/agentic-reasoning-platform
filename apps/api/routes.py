from uuid import UUID
from fastapi import APIRouter, HTTPException
from packages.db.repository import get_run
from packages.db.session import SessionLocal

router = APIRouter()

@router.get("/v1/runs/{run_id}")
async def get_run_status(run_id: UUID):
    async with SessionLocal() as session:
        run = await get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run_not_found")
        return {
            "run_id": str(run.id),
            "state": run.state,
            "model": run.model,
            "reasoning_effort": run.reasoning_effort,
            "checkpoint": run.checkpoint,
            "attempts": run.attempts,
        }
