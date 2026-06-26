"""OrderService — notional check (CF5/MP-3 — Bybit/Binance initial-margin 모델).

ExchangeAccountService.fetch_balance_usdt 주입 시, leverage 포함 limit order는
`position_notional(qty x price) ≤ available x leverage x 0.95` 검증 (필요증거금 =
notional/leverage ≤ available x 0.95, 0.95 = open/close fee 버퍼). 초과 시 NotionalExceeded 422.

price=None (market order)과 exchange_service 미주입은 검증 건너뜀 (기존 경로 유지).
balance fetch 실패: demo 는 skip(fail-open), live 는 BalanceUnverified(fail-closed).
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


def _make_exchange_service_stub(
    usdt_available: Decimal | None,
    *,
    snapshot_account=None,
    mark_price: Decimal | None = None,
):
    """ExchangeAccountService 대체 stub — fetch_balance_usdt + Sprint 23 BL-102 _repo.get_by_id.

    snapshot_account: dispatch_snapshot(+CF5 live fail-closed mode 판정)용 account.
    기본 None → snapshot=None (legacy fallback, demo fail-open).
    mark_price: P1-13 (S5-B) market order notional 근사용. None → mark fetch 실패 시뮬레이션.
    """
    stub = MagicMock()
    stub.fetch_balance_usdt = AsyncMock(return_value=usdt_available)
    stub.fetch_mark_price = AsyncMock(return_value=mark_price)
    # Wave 1 C5 — min-notional 가드 기본 skip(None=fail-open). max-notional 거동 회귀 0.
    stub.fetch_min_notional = AsyncMock(return_value=None)
    stub._repo = MagicMock()
    stub._repo.get_by_id = AsyncMock(return_value=snapshot_account)
    return stub


async def test_notional_within_limit_passes(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """available=1000, leverage=5, qty=0.01, price=50000 → notional=2500.
    max = 1000 x 20 (bybit_futures_max_leverage) x 0.95 = 19000 → 통과."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

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
    """available=100, leverage=20, qty=0.1, price=50000 → position notional=5000 (qty×price).
    max = 100 x 20 x 0.95 = 1900 → 초과 → NotionalExceeded (필요증거금 250 > 95)."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

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
    assert err.notional == Decimal("5000.0")  # qty×price (no leverage) — initial-margin 모델
    assert err.available == Decimal("100")
    assert err.leverage == 20


async def test_notional_check_skipped_for_market_order_when_mark_unavailable(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """P1-13 (S5-B): price=None + demo + mark fetch 실패 (None 반환) → fail-open skip.

    이전 거동(price=None 즉시 skip)과 호환 — mark price 미가용 + demo 계좌면
    notional 검증 건너뜀 (서비스 중단 금지). live 계좌는 fail-closed (별도 테스트).
    """
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    exchange_stub = _make_exchange_service_stub(
        Decimal("1"), mark_price=None  # mark 미가용
    )
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
        price=None,  # market order
        leverage=5,
        margin_mode="cross",
    )

    resp, _ = await svc.execute(req, idempotency_key=None)

    # P1-13 (S5-B): mark price 시도 1회 + fetch_balance 는 mark None 으로 skip
    exchange_stub.fetch_mark_price.assert_awaited_once()
    exchange_stub.fetch_balance_usdt.assert_not_awaited()
    assert resp.leverage == 5


# ── P1-13 (S5-B) — market order notional 근사 가드 (live_signal 경로 보호) ──


async def test_notional_market_order_uses_mark_price_within_limit(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """P1-13 (S5-B): market order 가 mark price 로 근사 notional check 통과.

    mark=50000, buffer 1.02 → effective_price=51000, qty=0.01 → notional=510.
    available=1000, leverage=5 → max=1000*5*0.95=4750 → 통과.
    """
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    exchange_stub = _make_exchange_service_stub(
        Decimal("1000"), mark_price=Decimal("50000")
    )
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
        quantity=Decimal("0.01"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    resp, _ = await svc.execute(req, idempotency_key=None)
    assert resp.leverage == 5
    exchange_stub.fetch_mark_price.assert_awaited_once_with(
        exchange_account.id, "BTC/USDT:USDT"
    )
    exchange_stub.fetch_balance_usdt.assert_awaited_once()


async def test_notional_market_order_exceeding_with_mark_price_raises(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """P1-13 (S5-B): mark*buffer 기반 notional 이 max 초과 → NotionalExceeded.

    이전 거동은 market order 의 notional 가드를 항상 우회 (audit P1-13 핵심 결함).
    mark=50000, buffer 1.02 → 51000. qty=0.1 → notional=5100.
    available=100, leverage=20 → max=100*20*0.95=1900 → reject.
    """
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    exchange_stub = _make_exchange_service_stub(
        Decimal("100"), mark_price=Decimal("50000")
    )
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
        quantity=Decimal("0.1"),
        price=None,
        leverage=20,
        margin_mode="cross",
    )
    with pytest.raises(NotionalExceeded) as exc_info:
        await svc.execute(req, idempotency_key=None)
    # mark 50000 * 1.02 buffer = 51000 → notional = 0.1 * 51000 = 5100
    assert exc_info.value.notional == Decimal("5100.00")
    assert exc_info.value.leverage == 20


async def test_notional_market_order_live_mark_unavailable_fail_closed(
    db_session: AsyncSession, strategy, user: User, crypto: EncryptionService
):
    """P1-13 (S5-B): live 계좌 + market order + mark fetch 실패 → BalanceUnverified.

    audit DEC-7 spirit: live money path 는 검증 불가 시 fail-closed (silent 통과 금지).
    """
    from uuid import uuid4

    from src.trading.exceptions import BalanceUnverified
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    live_acct = ExchangeAccount(
        id=uuid4(),
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.live,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
    )
    exchange_stub = _make_exchange_service_stub(
        Decimal("1000"),
        snapshot_account=live_acct,
        mark_price=None,  # mark fetch 실패
    )
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=live_acct.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    with pytest.raises(BalanceUnverified):
        await svc.execute(req, idempotency_key=None)
    exchange_stub.fetch_mark_price.assert_awaited_once()
    exchange_stub.fetch_balance_usdt.assert_not_awaited()


async def test_notional_check_skipped_when_balance_unavailable(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """fetch_balance_usdt가 None 반환 (API 실패) → 검증 skip (trading 중단 금지)."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

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

    # balance None → demo 계좌(exchange_account fixture) → skip(fail-open) → 정상 주문 처리
    resp, _ = await svc.execute(req, idempotency_key=None)

    assert resp.leverage == 5
    exchange_stub.fetch_balance_usdt.assert_awaited_once()


async def test_notional_1x_position_over_balance_rejected(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """MP-3 — 1x 주문도 position notional 이 잔고 초과면 거부.

    이전 `max_leverage` ceiling 공식은 1x 에서 감당 불가 포지션을 잘못 통과시켰다.
    available=1000, leverage=1, qty=0.05, price=50000 → notional=2500 (필요증거금 2500)
    > 1000×1×0.95=950 → reject. (이전 공식: notional=2500×1, max=1000×20×0.95=19000 → 잘못 통과)
    """
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

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
        quantity=Decimal("0.05"),
        price=Decimal("50000"),
        leverage=1,
        margin_mode="cross",
    )
    with pytest.raises(NotionalExceeded) as exc_info:
        await svc.execute(req, idempotency_key=None)
    assert exc_info.value.notional == Decimal("2500.0")
    assert exc_info.value.leverage == 1


async def test_notional_balance_unavailable_live_fail_closed(
    db_session: AsyncSession, strategy, user: User, crypto: EncryptionService
):
    """CF5 — live 계좌 balance fetch 실패(None) → BalanceUnverified (fail-closed)."""
    from uuid import uuid4

    from src.trading.exceptions import BalanceUnverified
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    live_acct = ExchangeAccount(
        id=uuid4(),
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.live,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
    )
    exchange_stub = _make_exchange_service_stub(None, snapshot_account=live_acct)
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=live_acct.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.01"),
        price=Decimal("50000"),
        leverage=5,
        margin_mode="cross",
    )
    with pytest.raises(BalanceUnverified):
        await svc.execute(req, idempotency_key=None)
