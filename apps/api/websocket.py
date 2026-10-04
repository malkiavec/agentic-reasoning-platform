import asyncio
import os
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from apps.api.auth import principal_from_token
from packages.db.event_history import replay_events
from packages.db.repository import get_run
from packages.db.session import SessionLocal

router = APIRouter()

def _token(websocket: WebSocket) -> str | None:
    authorization = websocket.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        return authorization[7:].strip()
    # Browser WebSockets cannot set arbitrary Authorization headers; use an HttpOnly
    # same-site access-token cookie in production deployments.
    return websocket.cookies.get("access_token")

@router.websocket("/v1/runs/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: UUID):
    await websocket.accept()
    try:
        if os.getenv("AUTH_MODE", "oidc").lower() == "oidc":
            token = _token(websocket)
            if not token:
                await websocket.close(code=4401)
                return
            principal = await principal_from_token(token)
            tenant_id = principal.tenant_id
        else:
            tenant_id = websocket.headers.get("x-tenant-id")
            if not tenant_id:
                await websocket.close(code=4401)
                return

        last_sequence = -1
        terminal = False
        while not terminal:
            async with SessionLocal() as session:
                run = await get_run(session, run_id)
                if run is None or run.tenant_id != tenant_id:
                    await websocket.close(code=4404)
                    return
                events = await replay_events(
                    session, tenant_id=tenant_id, run_id=run_id,
                    after_sequence=last_sequence if last_sequence >= 0 else None,
                    limit=5000,
                )
                state = run.state

            for event in events:
                last_sequence = max(last_sequence, event.sequence)
                await websocket.send_json({
                    "type": event.event_type,
                    "run_id": str(run_id),
                    "event_id": str(event.id),
                    "sequence": event.sequence,
                    "actor": event.actor,
                    **event.payload,
                })

            if state in {"completed", "failed", "cancelled"}:
                terminal = True
            else:
                await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
