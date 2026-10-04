import asyncio
import json
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/v1/runs/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: UUID):
    await websocket.accept()
    try:
        # Transport contract is stable; event production will be backed by Redis pub/sub.
        await websocket.send_text(json.dumps({"type": "run.connected", "run_id": str(run_id)}))
        while True:
            await asyncio.sleep(15)
            await websocket.send_text(json.dumps({"type": "run.keepalive", "run_id": str(run_id)}))
    except WebSocketDisconnect:
        return
