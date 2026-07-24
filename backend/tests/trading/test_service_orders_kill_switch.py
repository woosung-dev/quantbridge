"""OrderService — KillSwitch in-tx gate (T15, autoplan E9)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.trading.encryption import EncryptionService
from src.trading.exceptions import KillSwitchActive
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


# ---------- helpers ----------


class _BlockingKillSwitch:
    """ensure_not_gated → 항상 KillSwitchActive raise."""

    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        raise KillSwitchActive("test: kill switch active")


class _Dispatcher:
    """Dispatch 카운팅 — kill switch가 차단하면 0이어야 한다."""

    dispatched = 0

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        _Dispatcher.dispatched += 1


class _ClosedSessions:
    async def get_sessions(self, strategy_id: UUID) -> list[str]:
        return ["asia"]


# ---------- tests ----------


async def test_kill_switch_blocks_order_creation(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    """E9: ensure_not_gated가 raise → 주문 미생성 + dispatch 미호출."""
    from sqlalchemy import func, select

    from src.trading.models import Order
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.order_service import OrderService

    repo = OrderRepository(db_session)
    _Dispatcher.dispatched = 0
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=_Dispatcher(),
        kill_switch=_BlockingKillSwitch(),
    )

    with pytest.raises(KillSwitchActive):
        await svc.execute(order_request, idempotency_key=None)

    count = (
        await db_session.execute(select(func.count()).select_from(Order))
    ).scalar_one()
    assert count == 0, f"Expected 0 orders, got {count}"
    assert _Dispatcher.dispatched == 0, "Dispatch should not fire when gate blocks"


async def test_reduce_only_flatten_bypasses_kill_switch_and_session_gates(
    db_session: AsyncSession,
    order_request: OrderRequest,
    monkeypatch,
):
    """청산은 활성 kill switch와 closed session에서도 반드시 발주한다."""
    from datetime import UTC, datetime

    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services import order_service as service_mod
    from src.trading.services.order_service import OrderService

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2026, 4, 19, 14, 0, 0, tzinfo=tz or UTC)

    monkeypatch.setattr(service_mod, "datetime", _FrozenDatetime)
    request = order_request.model_copy(update={"reduce_only": True})
    _Dispatcher.dispatched = 0
    service = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_Dispatcher(),
        kill_switch=_BlockingKillSwitch(),
        sessions_port=_ClosedSessions(),
    )

    response, replayed = await service.execute(
        request, idempotency_key=None, flatten=True
    )

    assert response.reduce_only is True
    assert replayed is False
    assert _Dispatcher.dispatched == 1


async def test_reduce_only_order_without_flatten_remains_kill_switch_blocked(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    """flatten 기본값 False는 기존 kill switch 동작을 바꾸지 않는다."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.order_service import OrderService

    request = order_request.model_copy(update={"reduce_only": True})
    service = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_Dispatcher(),
        kill_switch=_BlockingKillSwitch(),
    )

    with pytest.raises(KillSwitchActive):
        await service.execute(request, idempotency_key=None)


async def test_flatten_requires_reduce_only_order(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    """일반 진입 주문은 flatten으로 위험 가드를 우회할 수 없다."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.order_service import OrderService

    service = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_Dispatcher(),
        kill_switch=_BlockingKillSwitch(),
    )

    with pytest.raises(ValueError, match="flatten requires reduce_only"):
        await service.execute(order_request, idempotency_key=None, flatten=True)
