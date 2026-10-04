import asyncio
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from packages.db.repository import get_run
from packages.db.session import SessionLocal

router = APIRouter()

@router.websocket("/v1/runs/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: UUID):
    await websocket.accept()
    redis = Redis.from_url("redis://redis:6379/0", decode_responses=False)
    try:
        async with SessionLocal() as session:
            run = await get_run(session, run_id)
        if run is None:
            await websocket.close(code=4404)
            return
        await websocket.send_json({"type":"run.connected","run_id":str(run_id),"state":run.state})
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"run:{run_id}")
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                data = message["data"]
                if isinstance(data, bytes):
                    data=data.decode("utf-8")
                await websocket.send_text(data)
                try:
                    event=__import__("json").loads(data)
                    if event.get("type") in {"run.completed","run.failed","run.cancelled"}:
                        break
                except ValueError:
                    pass
        finally:
            await pubsub.unsubscribe(f"run:{run_id}")
            await pubsub.aclose()
    except WebSocketDisconnect:
        pass
    finally:
        await redis.aclose()
