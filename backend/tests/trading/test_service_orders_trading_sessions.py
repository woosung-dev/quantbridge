"""OrderService trading_sessions 가드 — Sprint 7d.

StrategySessionsPort로 주입된 세션 리스트가 현재 UTC hour를 허용하지 않으면
TradingSessionClosed로 빠르게 실패한다. 빈 리스트 또는 port가 None이면 24h 통과.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.trading.encryption import EncryptionService
from src.trading.exceptions import TradingSessionClosed
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderType,
)
from src.trading.schemas import OrderRequest


@pytest.fixture
def crypto():
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


@pytest.fixture
async def exchange_account(
    db_session: AsyncSession, user: User, crypto: EncryptionService
) -> ExchangeAccount:
    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


@pytest.fixture
def order_request(exchange_account: ExchangeAccount, strategy) -> OrderRequest:
    return OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )


class _PermissiveKillSwitch:
    async def ensure_not_gated(
        self, strategy_id: UUID, account_id: UUID
    ) -> None:        return None


class _Dispatcher:
    dispatched = 0

    async def dispatch_order_execution(
        self, order_id: UUID
    ) -> None:        _Dispatcher.dispatched += 1


class _FixedSessions:
    def __init__(self, sessions: list[str]) -> None:
        self._sessions = sessions

    async def get_sessions(self, strategy_id: UUID) -> list[str]:        return list(self._sessions)


async def test_trading_sessions_outside_rejects_order(
    db_session: AsyncSession,
    order_request: OrderRequest,
    monkeypatch,
):
    """세션 리스트가 채워져 있고 현재 hour가 밖이면 TradingSessionClosed."""
    from datetime import UTC, datetime

    from src.trading.repository import OrderRepository
    from src.trading.service import OrderService
    from src.trading.services import order_service as service_mod

    # 현재 시각을 14 UTC로 고정. asia=[0,7), 14 UTC는 asia 밖.
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2026, 4, 19, 14, 0, 0, tzinfo=tz or UTC)

    monkeypatch.setattr(service_mod, "datetime", _FrozenDatetime)

    repo = OrderRepository(db_session)
    _Dispatcher.dispatched = 0
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=_Dispatcher(),
        kill_switch=_PermissiveKillSwitch(),
        sessions_port=_FixedSessions(["asia"]),
    )

    with pytest.raises(TradingSessionClosed) as excinfo:
        await svc.execute(order_request, idempotency_key=None)
    assert excinfo.value.current_hour_utc == 14
    assert excinfo.value.sessions == ["asia"]
    assert _Dispatcher.dispatched == 0


async def test_trading_sessions_inside_allows_order(
    db_session: AsyncSession,
    order_request: OrderRequest,
    monkeypatch,
):
    """런던 세션 내부 시각이면 주문 통과."""
    from datetime import UTC, datetime

    from src.trading.repository import OrderRepository
    from src.trading.service import OrderService
    from src.trading.services import order_service as service_mod

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2026, 4, 19, 14, 0, 0, tzinfo=tz or UTC)

    monkeypatch.setattr(service_mod, "datetime", _FrozenDatetime)

    repo = OrderRepository(db_session)
    _Dispatcher.dispatched = 0
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=_Dispatcher(),
        kill_switch=_PermissiveKillSwitch(),
        sessions_port=_FixedSessions(["london"]),
    )
    response, replayed = await svc.execute(order_request, idempotency_key=None)
    assert replayed is False
    assert response.symbol == "BTC/USDT"
    assert _Dispatcher.dispatched == 1


async def test_empty_sessions_allows_order(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    """빈 리스트 = 24h. 시각 모킹 불필요."""
    from src.trading.repository import OrderRepository
    from src.trading.service import OrderService

    repo = OrderRepository(db_session)
    _Dispatcher.dispatched = 0
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=_Dispatcher(),
        kill_switch=_PermissiveKillSwitch(),
        sessions_port=_FixedSessions([]),
    )
    response, _ = await svc.execute(order_request, idempotency_key=None)
    assert response is not None
    assert _Dispatcher.dispatched == 1


async def test_no_sessions_port_skips_gate(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    """기존 callsite 호환 — sessions_port=None이면 체크 안 함."""
    from src.trading.repository import OrderRepository
    from src.trading.service import OrderService

    repo = OrderRepository(db_session)
    _Dispatcher.dispatched = 0
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=_Dispatcher(),
        kill_switch=_PermissiveKillSwitch(),
        # sessions_port 미주입
    )
    response, _ = await svc.execute(order_request, idempotency_key=None)
    assert response is not None
    assert _Dispatcher.dispatched == 1
