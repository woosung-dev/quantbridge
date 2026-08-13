"""Sprint 12 Phase C — WebSocket test fixtures.

FakeWebSocket: scripted recv() + send() capture. websockets 라이브러리 mock
대용. ``BybitPrivateStream(connect_func=...)`` 로 주입.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest


class FakeWebSocket:
    """Scripted recv() + send() capture.

    사용:
        ws = FakeWebSocket()
        ws.queue_recv({"op": "auth", "success": True})
        ws.queue_recv({"topic": "order", "data": [{"orderLinkId": "...", "orderStatus": "Filled"}]})

        # connect_func 가 awaitable 반환:
        async def fake_connect(endpoint):
            return ws

        async with BybitPrivateStream(..., connect_func=fake_connect) as stream:
            ...
    """

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self._recv_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._closed = False

    def queue_recv(self, msg: dict[str, Any]) -> None:
        """recv() 가 반환할 메시지 큐잉."""
        self._recv_queue.put_nowait(json.dumps(msg))

    def queue_close(self) -> None:
        """recv() 가 ConnectionClosed 던지도록."""
        self._recv_queue.put_nowait(_CLOSE_SENTINEL)

    async def send(self, raw: str) -> None:
        if self._closed:
            from websockets.exceptions import ConnectionClosed

            raise ConnectionClosed(rcvd=None, sent=None)
        self.sent.append(json.loads(raw))

    async def recv(self) -> str:
        item = await self._recv_queue.get()
        if item is _CLOSE_SENTINEL:
            self._closed = True
            from websockets.exceptions import ConnectionClosed

            raise ConnectionClosed(rcvd=None, sent=None)
        return item  # type: ignore[no-any-return]

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    async def __anext__(self) -> str:
        try:
            return await self.recv()
        except Exception as exc:
            from websockets.exceptions import ConnectionClosed

            if isinstance(exc, ConnectionClosed):
                raise StopAsyncIteration from exc
            raise

    async def close(self, code: int = 1000) -> None:
        self._closed = True


_CLOSE_SENTINEL = object()


@pytest.fixture
def fake_ws() -> FakeWebSocket:
    return FakeWebSocket()


@pytest.fixture
def fake_connect(fake_ws: FakeWebSocket):  # type: ignore[no-untyped-def]
    """websockets.connect 대체 — 주입된 fake_ws 반환."""

    async def _connect(endpoint: str) -> FakeWebSocket:
        return fake_ws

    return _connect
