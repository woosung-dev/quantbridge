# Redis pubsub 이벤트를 사용자별 WebSocket 연결로 전달하는 관리자.
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket
from redis.asyncio import Redis

from src.common.redis_client import get_redis_lock_pool
from src.realtime.schemas import (
    TICKER_CHANNEL_PREFIX,
    USER_CHANNEL_PREFIX,
    WS_CLOSE_CONNECTION_LIMIT,
    RealtimeEnvelope,
)

_LOGGER = logging.getLogger(__name__)
_CHANNEL_PATTERNS = (
    f"{USER_CHANNEL_PREFIX}*",
    f"{TICKER_CHANNEL_PREFIX}*",
)
_MAX_CONNECTIONS_PER_USER = 3


class ConnectionManager:
    """사용자별 최대 세 연결을 보관하고, 초과 시 가장 오래된 연결을 4408로 닫는다.

    새 연결을 거부하는 것보다 기존 탭 하나만 정리하면 최신 클라이언트가 즉시 연결되므로
    브라우저 재연결과 멀티 탭 사용에서 회복이 단순하다.
    """

    def __init__(
        self,
        redis_pool_factory: Callable[[], Redis] | None = None,
    ) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._connection_order: dict[str, list[WebSocket]] = {}
        self._redis_pool_factory = redis_pool_factory or get_redis_lock_pool

    async def register(self, user_id: str, websocket: WebSocket) -> None:
        """연결을 등록하고 상한을 넘으면 가장 오래된 연결을 종료한다."""
        connections = self._connections.setdefault(user_id, set())
        order = self._connection_order.setdefault(user_id, [])
        if len(connections) >= _MAX_CONNECTIONS_PER_USER:
            oldest = order.pop(0)
            connections.discard(oldest)
            with contextlib.suppress(Exception):
                await oldest.close(code=WS_CLOSE_CONNECTION_LIMIT)
        connections.add(websocket)
        order.append(websocket)

    def unregister(self, user_id: str, websocket: WebSocket) -> None:
        """연결을 제거하고 비어 있는 사용자 버킷을 정리한다."""
        connections = self._connections.get(user_id)
        if connections is None:
            return
        connections.discard(websocket)
        order = self._connection_order[user_id]
        with contextlib.suppress(ValueError):
            order.remove(websocket)
        if not connections:
            self._connections.pop(user_id, None)
            self._connection_order.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict[str, object]) -> None:
        """현재 연결된 해당 사용자 소켓에 JSON 메시지를 fan-out한다."""
        for websocket in tuple(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(message)
            except Exception:  # 연결 종료와 send 경쟁은 정상적인 정리 경로다.
                self.unregister(user_id, websocket)

    async def send_to_all(self, message: dict[str, object]) -> None:
        """인증 완료된 모든 사용자 소켓에 JSON 메시지를 fan-out한다."""
        for user_id, connections in tuple(self._connections.items()):
            for websocket in tuple(connections):
                try:
                    await websocket.send_json(message)
                except Exception:  # 연결 종료와 send 경쟁은 정상적인 정리 경로다.
                    self.unregister(user_id, websocket)

    async def listen(self) -> None:
        """단일 psubscribe listener를 실행하고 Redis 장애 시 backoff 재연결한다."""
        retry_seconds = 1.0
        while True:
            pubsub: Any | None = None
            try:
                pubsub = self._redis_pool_factory().pubsub()
                await pubsub.psubscribe(*_CHANNEL_PATTERNS)
                retry_seconds = 1.0
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                    if message is not None:
                        await self._dispatch_pubsub_message(message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # Redis 불능은 앱 기동을 막지 않는 degraded 경로다.
                _LOGGER.warning("realtime_pubsub_listener_failed error=%s", exc)
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(retry_seconds * 2, 30.0)
            finally:
                if pubsub is not None:
                    with contextlib.suppress(Exception):
                        await pubsub.aclose()

    async def close(self) -> None:
        """남은 WebSocket 연결을 서버 종료 코드로 닫는다."""
        connections = [
            websocket
            for user_connections in self._connections.values()
            for websocket in user_connections
        ]
        self._connections.clear()
        self._connection_order.clear()
        for websocket in connections:
            with contextlib.suppress(Exception):
                await websocket.close(code=1001)

    async def _dispatch_pubsub_message(self, message: dict[str, object]) -> None:
        channel = message.get("channel")
        data = message.get("data")
        if not isinstance(channel, (str, bytes)) or not isinstance(data, (str, bytes, bytearray)):
            return
        channel_name = channel.decode() if isinstance(channel, bytes) else channel
        is_user_channel = channel_name.startswith(USER_CHANNEL_PREFIX)
        is_ticker_channel = channel_name.startswith(TICKER_CHANNEL_PREFIX)
        if not is_user_channel and not is_ticker_channel:
            return
        try:
            envelope = RealtimeEnvelope.model_validate(json.loads(data))
        except (TypeError, ValueError):
            _LOGGER.warning("realtime_pubsub_invalid_message channel=%s", channel_name)
            return
        payload = envelope.model_dump(mode="json")
        if is_user_channel:
            user_id = channel_name.removeprefix(USER_CHANNEL_PREFIX)
            if user_id:
                await self.send_to_user(user_id, payload)
        elif is_ticker_channel:
            await self.send_to_all(payload)
