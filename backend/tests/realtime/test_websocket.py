# 실시간 WebSocket 인증과 Redis fan-in 계약을 검증한다.
from __future__ import annotations

import asyncio
from collections import deque
from contextlib import ExitStack
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient, WebSocketDenialResponse
from starlette.websockets import WebSocketDisconnect

from src.auth.exceptions import InvalidTokenError
from src.auth.schemas import CurrentUser
from src.main import create_app
from src.realtime.schemas import WS_CLOSE_ORIGIN_DENIED, user_channel

REALTIME_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakePubSub:
    """listener task에 전달할 최소 Redis pubsub 대역."""

    def __init__(self) -> None:
        self.messages: deque[dict[str, object]] = deque()
        self.patterns: list[str] = []
        self.closed = False

    async def psubscribe(self, *patterns: str) -> None:
        self.patterns.extend(patterns)

    async def get_message(self, **_: object) -> dict[str, object] | None:
        if self.messages:
            return self.messages.popleft()
        await asyncio.sleep(0.01)
        return None

    async def aclose(self) -> None:
        self.closed = True


class FakeRedis:
    """pubsub 전용 최소 Redis 대역."""

    def __init__(self) -> None:
        self.pubsub_instance = FakePubSub()

    def pubsub(self) -> FakePubSub:
        return self.pubsub_instance


@pytest.fixture
def realtime_app(monkeypatch: pytest.MonkeyPatch) -> tuple[FastAPI, FakeRedis]:
    """인증과 Redis를 프로세스 내 fake로 치환한 앱을 만든다."""
    from src.realtime import manager as manager_module
    from src.realtime import router as router_module

    fake_redis = FakeRedis()

    async def fake_healthcheck(app: FastAPI) -> bool:
        app.state.redis_lock_healthy = True
        return True

    async def fake_authenticate(_token: str, _service: Any) -> CurrentUser:
        return CurrentUser(
            id=REALTIME_USER_ID,
            clerk_user_id="user_realtime",
            email="realtime@example.com",
        )

    monkeypatch.setattr(manager_module, "get_redis_lock_pool", lambda: fake_redis)
    monkeypatch.setattr("src.common.redis_client.healthcheck_redis_lock", fake_healthcheck)
    monkeypatch.setattr(router_module, "authenticate_clerk_token", fake_authenticate)
    return create_app(), fake_redis


def _connect(client: TestClient):
    from src.core.config import settings

    return client.websocket_connect(
        "/api/v1/realtime/ws",
        headers={"origin": settings.frontend_url},
    )


@pytest.mark.asyncio
async def test_clerk_token_adapter_uses_authorization_header() -> None:
    """WS 토큰 helper는 Clerk Requestish에 Bearer Authorization을 전달해야 한다."""
    from src.realtime.auth import authenticate_clerk_token

    user = SimpleNamespace(
        id=uuid4(),
        clerk_user_id="user_realtime",
        email="realtime@example.com",
        username=None,
        is_active=True,
    )
    service = SimpleNamespace(get_or_create=AsyncMock(return_value=user))
    clerk = MagicMock()
    clerk.authenticate_request.return_value = SimpleNamespace(
        is_signed_in=True,
        payload={"sub": "user_realtime", "email": "realtime@example.com"},
    )

    current_user = await authenticate_clerk_token("jwt-token", service, clerk=clerk)

    request = clerk.authenticate_request.call_args.args[0]
    assert request.headers == {"Authorization": "Bearer jwt-token"}
    assert current_user.clerk_user_id == "user_realtime"


@pytest.mark.asyncio
async def test_http_auth_dependency_preserves_original_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP dependency는 cookie fallback을 가진 원본 Request를 공통 helper에 넘겨야 한다."""
    from src.auth.dependencies import get_current_user

    request = Request({"type": "http", "headers": [(b"cookie", b"__session=session-token")]})
    service = MagicMock()
    expected = CurrentUser(
        id=uuid4(),
        clerk_user_id="user_http",
        email="http@example.com",
    )
    captured: dict[str, object] = {}

    async def fake_authenticate(
        request_arg: Request,
        service_arg: object,
        clerk: object,
    ) -> CurrentUser:
        captured.update(request=request_arg, service=service_arg, clerk=clerk)
        return expected

    monkeypatch.setattr(
        "src.auth.dependencies.authenticate_clerk_request",
        fake_authenticate,
    )

    assert await get_current_user(request, service) == expected
    assert captured["request"] is request
    assert captured["service"] is service


@pytest.mark.asyncio
async def test_auth_disconnect_returns_without_close() -> None:
    """auth 전 disconnect는 close 재시도나 예외 전파 없이 종료해야 한다."""
    from src.core.config import settings
    from src.realtime.router import realtime_websocket

    websocket = MagicMock()
    websocket.headers = {"origin": settings.frontend_url}
    websocket.accept = AsyncMock()
    websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect())
    websocket.close = AsyncMock()

    await realtime_websocket(websocket, MagicMock())

    websocket.accept.assert_awaited_once()
    websocket.close.assert_not_awaited()


def test_auth_success_sends_ready(realtime_app: tuple[FastAPI, FakeRedis]) -> None:
    """유효 auth 메시지는 ready 응답 후 연결을 유지해야 한다."""
    app, _ = realtime_app
    with TestClient(app) as client, _connect(client) as websocket:
        websocket.send_json({"type": "auth", "token": "valid"})
        assert websocket.receive_json() == {"type": "ready"}


def test_ping_returns_pong(realtime_app: tuple[FastAPI, FakeRedis]) -> None:
    """인증된 연결의 텍스트 ping은 pong으로 응답해야 한다."""
    app, _ = realtime_app
    with TestClient(app) as client, _connect(client) as websocket:
        websocket.send_json({"type": "auth", "token": "valid"})
        assert websocket.receive_json() == {"type": "ready"}
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"


def test_invalid_token_closes_with_4401(
    realtime_app: tuple[FastAPI, FakeRedis], monkeypatch: pytest.MonkeyPatch
) -> None:
    """인증 실패는 accept 후 4401 close code를 전달해야 한다."""
    app, _ = realtime_app

    async def reject_token(_token: str, _service: Any) -> CurrentUser:
        raise InvalidTokenError(reason="token_invalid")

    monkeypatch.setattr("src.realtime.router.authenticate_clerk_token", reject_token)
    with TestClient(app) as client, _connect(client) as websocket:
        websocket.send_json({"type": "auth", "token": "invalid"})
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()
    assert exc_info.value.code == 4401


def test_invalid_auth_message_closes_with_4401(realtime_app: tuple[FastAPI, FakeRedis]) -> None:
    """auth 계약에 맞지 않는 첫 메시지는 4401로 거부해야 한다."""
    app, _ = realtime_app
    with TestClient(app) as client, _connect(client) as websocket:
        websocket.send_json({"type": "not-auth", "token": "valid"})
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()
    assert exc_info.value.code == 4401


def test_auth_timeout_closes_with_4401(
    realtime_app: tuple[FastAPI, FakeRedis], monkeypatch: pytest.MonkeyPatch
) -> None:
    """첫 auth 메시지 타임아웃도 accept 후 4401 close code를 전달해야 한다."""
    app, _ = realtime_app
    monkeypatch.setattr("src.realtime.router.AUTH_TIMEOUT_SECONDS", 0.01)
    with (
        TestClient(app) as client,
        _connect(client) as websocket,
        pytest.raises(WebSocketDisconnect) as exc_info,
    ):
        websocket.receive_json()
    assert exc_info.value.code == 4401


def test_invalid_origin_is_handshake_denial(realtime_app: tuple[FastAPI, FakeRedis]) -> None:
    """accept 전 Origin 거부는 WS close code 대신 HTTP 403 denial이어야 한다."""
    app, _ = realtime_app
    with (
        TestClient(app) as client,
        pytest.raises(WebSocketDenialResponse) as exc_info,
        client.websocket_connect(
            "/api/v1/realtime/ws",
            headers={"origin": "https://attacker.example"},
        ),
    ):
        pass
    assert exc_info.value.status_code == 403
    assert WS_CLOSE_ORIGIN_DENIED == 4403


def test_connection_limit_closes_oldest_connection(
    realtime_app: tuple[FastAPI, FakeRedis]
) -> None:
    """네 번째 동일 사용자 연결은 가장 오래된 연결을 4408로 정리해야 한다."""
    app, _ = realtime_app
    with TestClient(app) as client, ExitStack() as stack:
        sockets = [stack.enter_context(_connect(client)) for _ in range(4)]
        for websocket in sockets:
            websocket.send_json({"type": "auth", "token": "valid"})
            assert websocket.receive_json() == {"type": "ready"}
        with pytest.raises(WebSocketDisconnect) as exc_info:
            sockets[0].receive_json()
    assert exc_info.value.code == 4408


def test_pubsub_message_fans_in_to_user_socket(
    realtime_app: tuple[FastAPI, FakeRedis]
) -> None:
    """사용자 채널의 유효 envelope는 같은 사용자 소켓에 그대로 전달되어야 한다."""
    app, fake_redis = realtime_app
    with TestClient(app) as client, _connect(client) as websocket:
        websocket.send_json({"type": "auth", "token": "valid"})
        assert websocket.receive_json() == {"type": "ready"}
        fake_redis.pubsub_instance.messages.append(
            {
                "channel": user_channel(str(REALTIME_USER_ID)).encode(),
                "data": b'{"v":1,"type":"order_update","ts":1,"payload":{"order_id":"o1"}}',
            }
        )
        assert websocket.receive_json() == {
            "v": 1,
            "type": "order_update",
            "ts": 1,
            "payload": {"order_id": "o1"},
        }
