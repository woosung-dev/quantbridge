# Wave 1 C5 — min-notional 가드 (거래소 최소 주문 cost 미달 거부).
"""markets[symbol]['limits']['cost']['min'] (load_markets 메타) 로 notional 최소 검증.

미달 시 MinNotionalNotMet. min cost 미가용(None) → skip (fail-open, fetch_mark_price 패턴).
notional-MAX 가드(NotionalExceeded) 직후, 동일 effective_price/notional 재사용.
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
from src.trading.exceptions import MinNotionalNotMet
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


def _make_exchange_service_stub(
    usdt_available: Decimal | None,
    *,
    min_notional: Decimal | None = None,
):
    stub = MagicMock()
    stub.fetch_balance_usdt = AsyncMock(return_value=usdt_available)
    stub.fetch_mark_price = AsyncMock(return_value=None)
    stub.fetch_min_notional = AsyncMock(return_value=min_notional)
    stub._repo = MagicMock()
    stub._repo.get_by_id = AsyncMock(return_value=None)
    return stub


async def test_below_min_notional_rejected(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """qty=0.0001, price=50000 → notional=5. min_cost=10 → 미달 → MinNotionalNotMet."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    stub = _make_exchange_service_stub(Decimal("1000"), min_notional=Decimal("10"))
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.0001"),
        price=Decimal("50000"),
        leverage=5,
        margin_mode="cross",
    )
    with pytest.raises(MinNotionalNotMet) as exc_info:
        await svc.execute(req, idempotency_key=None)
    assert exc_info.value.notional == Decimal("5.0000")
    assert exc_info.value.min_notional == Decimal("10")
    stub.fetch_min_notional.assert_awaited_once_with(exchange_account.id, "BTC/USDT:USDT")


async def test_at_or_above_min_notional_passes(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """qty=0.01, price=50000 → notional=500 ≥ min_cost=10 → 통과."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    stub = _make_exchange_service_stub(Decimal("100000"), min_notional=Decimal("10"))
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=stub,
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


async def test_min_notional_unavailable_skips_fail_open(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """min_cost None (메타 미가용) → skip(fail-open). 작은 주문도 통과."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    stub = _make_exchange_service_stub(Decimal("1000"), min_notional=None)
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.0001"),
        price=Decimal("50000"),
        leverage=5,
        margin_mode="cross",
    )
    resp, _ = await svc.execute(req, idempotency_key=None)
    assert resp.leverage == 5


async def test_provider_fetch_min_notional_reads_limits_cost_min(monkeypatch):
    """BybitFuturesProvider.fetch_min_notional = load_markets → limits.cost.min."""
    mock_exchange = MagicMock()
    mock_exchange.load_markets = AsyncMock(
        return_value={"BTC/USDT:USDT": {"limits": {"cost": {"min": 5.0}}}}
    )
    mock_exchange.market = MagicMock(return_value={"limits": {"cost": {"min": 5.0}}})
    mock_exchange.close = AsyncMock()
    mock_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_cls)

    from src.trading.providers import BybitFuturesProvider, Credentials

    creds = Credentials(api_key="k", api_secret="s")
    result = await BybitFuturesProvider().fetch_min_notional(creds, "BTC/USDT:USDT")
    assert result == Decimal("5.0")
    mock_exchange.close.assert_awaited_once()
