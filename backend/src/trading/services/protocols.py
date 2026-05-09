# trading service — OrderDispatcher + StrategySessionsPort Protocol 정의 단독

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class OrderDispatcher(Protocol):
    async def dispatch_order_execution(self, order_id: UUID) -> None: ...


class StrategySessionsPort(Protocol):
    """Sprint 7d. OrderService → strategy.trading_sessions 조회 어댑터.

    strategy 도메인 repository 와 trading 도메인 사이의 직접 의존을 피하기 위한 port.
    default DI 는 SQL one-liner 로 trading_sessions 컬럼만 select.
    """

    async def get_sessions(self, strategy_id: UUID) -> list[str]: ...
