"""OrderService — Sprint 8+ notional check (qty x price x leverage vs balance).

ExchangeAccountService.fetch_balance_usdt 주입 시, leverage 포함 limit order는
`notional ≤ available x max_leverage x 0.95` 검증. 초과 시 NotionalExceeded 422.

price=None (market order)과 exchange_service 미주입은 검증 건너뜀 (기존 경로 유지).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.trading.encryption import EncryptionService
from src.trading.exceptions import NotionalExceeded
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderType,
)


@pytest.fixture
def crypto() -> EncryptionService:
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


class _NoopKillSwitch:
    async def ensure_not_gated(self, strategy_id, account_id):
        return None


class _CapturingDispatcher:
    def __init__(self) -> None:
        self.last_id: UUID | None = None

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        self.last_id = order_id


def _make_exchange_service_stub(usdt_available: Decimal | None):
    """ExchangeAccountService 대체 stub — fetch_balance_usdt + Sprint 23 BL-102 _repo.get_by_id."""
    stub = MagicMock()
    stub.fetch_balance_usdt = AsyncMock(return_value=usdt_available)
    # Sprint 23 BL-102: OrderService._execute_inner 가 dispatch snapshot 위해 account fetch.
    # account 가 None 이면 snapshot=None 으로 graceful (legacy fallback path).
    # notional check 만 검증하는 test 들이므로 None 반환 OK.
    stub._repo = MagicMock()
    stub._repo.get_by_id = AsyncMock(return_value=None)
    return stub


async def test_notional_within_limit_passes(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """available=1000, leverage=5, qty=0.01, price=50000 → notional=2500.
    max = 1000 x 20 (bybit_futures_max_leverage) x 0.95 = 19000 → 통과."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    exchange_stub = _make_exchange_service_stub(Decimal("1000"))
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.01"),
        price=Decimal("50000"),
        leverage=5,
        margin_mode="cross",
    )

    resp, _ = await svc.execute(req, idempotency_key=None)

    assert resp.leverage == 5
    exchange_stub.fetch_balance_usdt.assert_awaited_once_with(exchange_account.id)


async def test_notional_exceeding_max_raises(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """available=100, leverage=20, qty=0.1, price=50000 → notional=100000.
    max = 100 x 20 x 0.95 = 1900 → 초과 → NotionalExceeded."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    exchange_stub = _make_exchange_service_stub(Decimal("100"))
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        leverage=20,
        margin_mode="cross",
    )

    with pytest.raises(NotionalExceeded) as exc_info:
        await svc.execute(req, idempotency_key=None)

    err = exc_info.value
    assert err.notional == Decimal("100000.0")
    assert err.available == Decimal("100")
    assert err.leverage == 20


async def test_notional_check_skipped_for_market_order(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """price=None (market) → notional 계산 불가 → 검증 skip (leverage cap만 1차 방어)."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    exchange_stub = _make_exchange_service_stub(Decimal("1"))  # 매우 작은 잔고
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,  # market order — notional 계산 불가
        leverage=5,
        margin_mode="cross",
    )

    resp, _ = await svc.execute(req, idempotency_key=None)

    # fetch_balance_usdt 호출되지 않음 (price=None으로 조기 skip)
    exchange_stub.fetch_balance_usdt.assert_not_awaited()
    assert resp.leverage == 5


async def test_notional_check_skipped_when_balance_unavailable(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """fetch_balance_usdt가 None 반환 (API 실패) → 검증 skip (trading 중단 금지)."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    exchange_stub = _make_exchange_service_stub(None)  # API 실패
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.01"),
        price=Decimal("50000"),
        leverage=5,
        margin_mode="cross",
    )

    # balance None → skip → 정상 주문 처리
    resp, _ = await svc.execute(req, idempotency_key=None)

    assert resp.leverage == 5
    exchange_stub.fetch_balance_usdt.assert_awaited_once()
