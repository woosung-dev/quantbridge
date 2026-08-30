"""Bybit Demo 전용 provider dispatch 및 legacy egress 차단 회귀 테스트."""

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.tasks.trading import (
    _build_exchange_provider,
    _has_leverage,
    _provider_for_account_and_leverage,
)
from src.trading.encryption import EncryptionService
from src.trading.exceptions import BybitDemoOnlyError, ProviderError
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.providers import (
    BybitDemoProvider,
    BybitFuturesProvider,
    BybitLiveProvider,
    Credentials,
    FixtureExchangeProvider,
    OrderSubmit,
)

# ----------------------------------------------------------------------
# Phase A.5 — _provider_for_account_and_leverage unit tests
# ----------------------------------------------------------------------


class TestProviderDispatchHappyPath:
    """지원 (exchange, mode, has_leverage) 조합 → concrete provider."""

    def test_bybit_demo_spot(self) -> None:
        provider = _provider_for_account_and_leverage(
            ExchangeName.bybit, ExchangeMode.demo, has_leverage=False
        )
        assert isinstance(provider, BybitDemoProvider)

    def test_bybit_demo_futures(self) -> None:
        provider = _provider_for_account_and_leverage(
            ExchangeName.bybit, ExchangeMode.demo, has_leverage=True
        )
        assert isinstance(provider, BybitFuturesProvider)


class TestProviderDispatchPolicy:
    """Bybit Demo 이외 (exchange, mode, has_leverage)는 dispatch 전에 거부한다."""

    @pytest.mark.parametrize(
        "exchange,mode,has_leverage",
        [
            (ExchangeName.okx, ExchangeMode.demo, False),
            (ExchangeName.okx, ExchangeMode.demo, True),
            (ExchangeName.binance, ExchangeMode.demo, False),
            (ExchangeName.binance, ExchangeMode.demo, True),
            (ExchangeName.okx, ExchangeMode.live, False),
            (ExchangeName.bybit, ExchangeMode.live, False),
            (ExchangeName.bybit, ExchangeMode.live, True),
        ],
    )
    def test_legacy_account_is_blocked(
        self, exchange: ExchangeName, mode: ExchangeMode, has_leverage: bool
    ) -> None:
        with pytest.raises(BybitDemoOnlyError):
            _provider_for_account_and_leverage(exchange, mode, has_leverage)

    def test_product_policy_error_is_provider_error_subclass(self) -> None:
        assert issubclass(BybitDemoOnlyError, ProviderError)


class TestBybitLiveProviderBlock:
    """직접 legacy provider를 호출해도 CCXT 이전에 제품 정책으로 막힌다."""

    def test_bybit_live_dispatch_is_blocked(self) -> None:
        with pytest.raises(BybitDemoOnlyError):
            _provider_for_account_and_leverage(ExchangeName.bybit, ExchangeMode.live, False)

    @pytest.mark.asyncio
    async def test_bybit_live_create_order_raises_provider_error(self) -> None:
        """legacy provider의 create_order는 안전한 기본 credentials여도 차단한다."""
        provider = BybitLiveProvider()
        creds = Credentials(api_key="k", api_secret="s")
        submit = OrderSubmit(
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            price=None,
        )
        with pytest.raises(BybitDemoOnlyError):
            await provider.create_order(creds, submit)

    @pytest.mark.asyncio
    async def test_bybit_live_cancel_order_raises_provider_error(self) -> None:
        """legacy provider의 cancel_order도 차단한다."""
        provider = BybitLiveProvider()
        creds = Credentials(api_key="k", api_secret="s")
        with pytest.raises(BybitDemoOnlyError):
            await provider.cancel_order(creds, "fake-id", "BTC/USDT")

    @pytest.mark.asyncio
    async def test_bybit_live_fetch_order_raises_provider_error(self) -> None:
        """legacy provider의 fetch_order도 차단한다."""
        provider = BybitLiveProvider()
        creds = Credentials(api_key="k", api_secret="s")
        with pytest.raises(BybitDemoOnlyError):
            await provider.fetch_order(creds, "fake-id", "BTCUSDT")


class TestHasLeverageHelper:
    """P2 #1 — `_has_leverage` 가 None 과 0 둘 다 spot 으로 분류."""

    def test_none_is_spot(self) -> None:
        submit = OrderSubmit(
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            price=None,
            leverage=None,
        )
        assert _has_leverage(submit) is False

    def test_zero_is_spot(self) -> None:
        """legacy/zero row 방어 — leverage=0 이면 spot 으로 분류."""

        class _LegacyOrder:
            leverage = 0

        assert _has_leverage(_LegacyOrder()) is False

    def test_positive_is_futures(self) -> None:
        submit = OrderSubmit(
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            price=None,
            leverage=5,
            margin_mode="cross",
        )
        assert _has_leverage(submit) is True

    def test_missing_attribute_is_spot(self) -> None:
        """leverage 속성 없는 객체도 spot."""

        class _NoLeverage:
            pass

        assert _has_leverage(_NoLeverage()) is False

    def test_string_leverage_is_spot(self) -> None:
        """codex G.2 P2 #2 — legacy/manual mutation 으로 leverage="0" / "5" 면
        TypeError 회피하고 spot 분류 (조용히 fail-safe)."""

        class _LegacyStringLeverage:
            leverage = "5"

        assert _has_leverage(_LegacyStringLeverage()) is False

    def test_bool_leverage_is_spot(self) -> None:
        """bool 은 int subclass 이지만 의미상 leverage 아님 → spot 분류."""

        class _BoolLeverage:
            leverage = True

        assert _has_leverage(_BoolLeverage()) is False

    def test_decimal_leverage_positive_is_futures(self) -> None:
        """Decimal 타입은 정상 numeric → futures 정상 분기."""

        class _DecimalLeverage:
            leverage = Decimal("5")

        assert _has_leverage(_DecimalLeverage()) is True

    def test_decimal_zero_is_spot(self) -> None:
        """Decimal('0') 도 spot."""

        class _DecimalZero:
            leverage = Decimal("0")

        assert _has_leverage(_DecimalZero()) is False


class TestBuildExchangeProvider:
    """`_build_exchange_provider(account, submit)` public dispatcher."""

    def _account(self, exchange: ExchangeName, mode: ExchangeMode) -> ExchangeAccount:
        return ExchangeAccount(
            user_id=uuid4(),
            exchange=exchange,
            mode=mode,
            api_key_encrypted=b"x",
            api_secret_encrypted=b"x",
        )

    def _submit(self, leverage: int | None = None) -> OrderSubmit:
        return OrderSubmit(
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            price=None,
            leverage=leverage,
            margin_mode="cross" if leverage is not None else None,
        )

    def test_account_demo_spot_dispatches_bybit_demo(self) -> None:
        account = self._account(ExchangeName.bybit, ExchangeMode.demo)
        submit = self._submit(leverage=None)
        assert isinstance(_build_exchange_provider(account, submit), BybitDemoProvider)

    def test_account_demo_futures_dispatches_bybit_futures(self) -> None:
        account = self._account(ExchangeName.bybit, ExchangeMode.demo)
        submit = self._submit(leverage=5)
        assert isinstance(_build_exchange_provider(account, submit), BybitFuturesProvider)

    def test_legacy_live_account_is_blocked(self) -> None:
        account = self._account(ExchangeName.bybit, ExchangeMode.live)
        submit = self._submit(leverage=None)
        with pytest.raises(BybitDemoOnlyError):
            _build_exchange_provider(account, submit)


# ----------------------------------------------------------------------
# Phase B.3 — graceful rejected E2E verifier (P1 #2 + P1 #1)
# ----------------------------------------------------------------------


class _NoopEngine:
    async def dispose(self) -> None:
        return None


def _fake_engine_factory(db_session: AsyncSession):
    @asynccontextmanager
    async def _ctx():
        yield db_session

    class _SM:
        def __call__(self):
            return _ctx()

    def _factory():
        return _NoopEngine(), _SM()

    return _factory


@pytest.fixture
async def binance_pending_order(db_session: AsyncSession):
    """Binance legacy account의 pending Order — egress 없이 rejected 되어야 한다."""
    crypto = EncryptionService(settings.trading_encryption_keys)

    user = User(
        id=uuid4(),
        auth_subject=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="BL-091 unsupported",
        pine_source="//@version=5\nstrategy('x')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.binance,  # 미지원 (Sprint 22)
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
    )
    db_session.add(account)
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
    )
    db_session.add(order)
    await db_session.commit()
    return order


@pytest.fixture
async def bybit_live_pending_order(db_session: AsyncSession):
    """Bybit live legacy account의 pending Order — egress 없이 rejected 되어야 한다."""
    crypto = EncryptionService(settings.trading_encryption_keys)

    user = User(
        id=uuid4(),
        auth_subject=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="BL-091 bybit live",
        pine_source="//@version=5\nstrategy('x')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.live,  # BL-003 까지 stub
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
    )
    db_session.add(account)
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
    )
    db_session.add(order)
    await db_session.commit()
    return order


@pytest.mark.asyncio
async def test_legacy_exchange_routes_to_rejected_before_credential_decrypt(
    db_session: AsyncSession,
    binance_pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """legacy account은 submitted/decrypt/dispatch 전에 terminal rejected 된다."""
    import src.tasks.trading as task_mod

    order = binance_pending_order
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _fake_engine_factory(db_session))

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "rejected"
    assert result["error_message"] == "bybit_demo_only"

    await db_session.refresh(order)
    assert order.state == OrderState.rejected
    assert order.error_message is not None
    assert order.error_message == "bybit_demo_only"


@pytest.mark.asyncio
async def test_bybit_live_routes_to_rejected_before_credential_decrypt(
    db_session: AsyncSession,
    bybit_live_pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """legacy Bybit live order도 provider dispatch 전에 terminal rejected 된다."""
    import src.tasks.trading as task_mod

    order = bybit_live_pending_order
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _fake_engine_factory(db_session))

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "rejected"
    assert result["error_message"] == "bybit_demo_only"

    await db_session.refresh(order)
    assert order.state == OrderState.rejected
    assert order.error_message is not None
    assert order.error_message == "bybit_demo_only"


# ----------------------------------------------------------------------
# B.2 narrow guard — real account dispatch never returns Fixture
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "exchange,mode,has_leverage,expected_class",
    [
        (ExchangeName.bybit, ExchangeMode.demo, False, BybitDemoProvider),
        (ExchangeName.bybit, ExchangeMode.demo, True, BybitFuturesProvider),
    ],
)
def test_real_account_dispatch_never_returns_fixture(
    exchange: ExchangeName,
    mode: ExchangeMode,
    has_leverage: bool,
    expected_class: type,
) -> None:
    """허용된 실제 계정 dispatch가 정확한 concrete class 반환 +
    FixtureExchangeProvider 절대 안 나옴. 미래 누군가 fixture 임시 분기 추가 시
    즉시 fail.
    """
    provider = _provider_for_account_and_leverage(exchange, mode, has_leverage)
    assert isinstance(provider, expected_class)
    assert not isinstance(provider, FixtureExchangeProvider)
