"""Private WebSocket order topic의 transport adapter.

DB lookup·transition·commit은 `WebSocketOrderEventService`가 담당한다. 이 adapter는
stream이 전달한 payload를 task 조립층의 callback으로 넘길 뿐이다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

OrderEventCallback = Callable[[UUID, dict[str, Any]], Awaitable[None]]


class StateHandler:
    """전송 계층과 DB 유스케이스를 분리하는 얇은 callback adapter."""

    def __init__(self, handler: OrderEventCallback) -> None:
        self._handler = handler

    async def handle_order_event(self, account_id: UUID, payload: dict[str, Any]) -> None:
        await self._handler(account_id, payload)
