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

    async def get_owner(self, strategy_id: UUID) -> UUID | None:
        """strategy 소유자(user_id) 반환. 없으면 None — TRD-4 ownership gate 용."""
        ...

    async def is_owner_active(self, user_id: UUID) -> bool:
        """소유자 계정이 살아 있는가 (2026-08-15 surface-truth · S3).

        탈퇴(Clerk `user.deleted`)는 `users.is_active=false` 로 표시된다. 종전에는 그 값을
        **주문 경로에서 아무도 보지 않아** 탈퇴한 사용자의 세션이 계속 실주문을 냈다.
        `get_owner` 와 같은 port 에 두는 이유는 같은 것을 묻기 때문이다 — 「이 전략은
        누구 것이고, 그 사람이 아직 있는가」.

        존재하지 않는 user_id 는 **False** 다 (fail-closed).
        """
        ...
