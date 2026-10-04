import json
import os
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from apps.api.auth import principal_from_token
from packages.db.event_history import replay_events
from packages.db.repository import get_run
from packages.db.session import SessionLocal

router = APIRouter()

@router.websocket("/v1/runs/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: UUID):
    await websocket.accept()
    redis = Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=False,
    )
    pubsub = redis.pubsub()
    try:
        if os.getenv("AUTH_MODE", "development").lower() == "oidc":
            authorization = websocket.headers.get("authorization", "")
            if not authorization.startswith("Bearer "):
                await websocket.close(code=4401)
                return
            principal = await principal_from_token(authorization[7:].strip())
            tenant_id = principal.tenant_id
        else:
            tenant_id = websocket.headers.get("x-tenant-id")
            if not tenant_id:
                await websocket.close(code=4401)
                return

        # Subscribe before replay so events cannot be lost between the two operations.
        await pubsub.subscribe(f"run:{run_id}")
        buffered: list[str] = []

        async with SessionLocal() as session:
            run = await get_run(session, run_id)
            if run is None or run.tenant_id != tenant_id:
                await websocket.close(code=4404)
                return
            history = await replay_events(
                session, tenant_id=tenant_id, run_id=run_id, limit=5000
            )

        await websocket.send_json(
            {"type": "run.connected", "run_id": str(run_id), "state": run.state}
        )
        for event in history:
            await websocket.send_json(
                {
                    "type": event.event_type,
                    "run_id": str(run_id),
                    "event_id": str(event.id),
                    "sequence": event.sequence,
                    "actor": event.actor,
                    **event.payload,
                }
            )

        # Consume messages published while the durable history was being replayed.
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=0.05
            )
            if message is None:
                break
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            buffered.append(data)

        for data in buffered:
            await websocket.send_text(data)

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            await websocket.send_text(data)
            try:
                event = json.loads(data)
                if event.get("type") in {"run.completed", "run.failed", "run.cancelled"}:
                    break
            except ValueError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"run:{run_id}")
        await pubsub.aclose()
        await redis.aclose()
