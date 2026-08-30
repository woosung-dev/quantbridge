"""Private WebSocket reconciliation transport adapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

ReconciliationCallback = Callable[[UUID], Awaitable[None]]


class Reconciler:
    """연결 직후 reconciliation 요청을 DB 유스케이스 callback으로 넘긴다."""

    def __init__(self, handler: ReconciliationCallback) -> None:
        self._handler = handler

    async def run(self, *, account_id: UUID) -> None:
        await self._handler(account_id)
