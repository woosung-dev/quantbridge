# 인증된 실시간 이벤트 WebSocket 엔드포인트.
from __future__ import annotations

import asyncio
from typing import cast

from fastapi import APIRouter, Depends, Response, WebSocket
from starlette.websockets import WebSocketDisconnect

from src.auth.dependencies import get_user_service
from src.auth.exceptions import AuthError
from src.auth.service import UserService
from src.core.config import settings
from src.realtime.auth import authenticate_token
from src.realtime.manager import ConnectionManager
from src.realtime.schemas import (
    WS_CLOSE_AUTH_FAILED,
    AuthMessage,
)

router = APIRouter()
AUTH_TIMEOUT_SECONDS = 5.0


def _manager(websocket: WebSocket) -> ConnectionManager:
    """lifespan이 app.state에 저장한 연결 관리자를 반환한다."""
    return cast(ConnectionManager, websocket.app.state.realtime_manager)


@router.websocket("/realtime/ws")
async def realtime_websocket(
    websocket: WebSocket,
    service: UserService = Depends(get_user_service),
) -> None:
    """Origin 확인 후 첫 auth 메시지로 사용자를 인증하고 이벤트를 전달한다."""
    if websocket.headers.get("origin") != settings.frontend_url:
        # WS_CLOSE_ORIGIN_DENIED는 accept 후 protocol close code이며, 여기서는 accept 전이다.
        # accept 전 close(WS_CLOSE_ORIGIN_DENIED)는 TestClient에서 close frame으로 관측된다.
        # HTTP 403 handshake denial 계약을 보장하려면 denial response를 명시적으로 보낸다.
        await websocket.send_denial_response(Response(status_code=403))
        return

    await websocket.accept()
    try:
        raw_message = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=AUTH_TIMEOUT_SECONDS,
        )
        auth = AuthMessage.model_validate(raw_message)
        user = await authenticate_token(auth.token, service)
    except WebSocketDisconnect:
        return
    except (TimeoutError, ValueError, AuthError):
        await websocket.close(code=WS_CLOSE_AUTH_FAILED)
        return

    manager = _manager(websocket)
    user_id = str(user.id)
    await manager.register(user_id, websocket)
    try:
        await websocket.send_json({"type": "ready"})
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if message.get("text") == "ping":
                await websocket.send_text("pong")
    finally:
        manager.unregister(user_id, websocket)
