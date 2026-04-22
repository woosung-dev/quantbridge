"""BybitFuturesProvider — CCXT async_support을 monkeypatch로 mock.

실제 Bybit 호출 금지 (네트워크 isolation). BybitDemoProvider 테스트 패턴 계승.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials
    return Credentials(api_key="test-key", api_secret="test-secret")


@pytest.fixture
def order_submit_futures():
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit
    return OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )


@pytest.fixture
def ccxt_mock(monkeypatch):
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={
            "id": "bybit-futures-42",
            "average": 50123.45,
            "status": "closed",
            "symbol": "BTC/USDT:USDT",
        }
    )
    mock_exchange.cancel_order = AsyncMock(return_value={})
    mock_exchange.set_leverage = AsyncMock(return_value=None)
    mock_exchange.set_margin_mode = AsyncMock(return_value=None)
    mock_exchange.close = AsyncMock()

    mock_bybit_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async
    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit_cls)
    return mock_exchange, mock_bybit_cls


async def test_bybit_futures_create_order_sets_leverage_and_margin_mode(
    credentials, order_submit_futures, ccxt_mock
):
    mock_exchange, mock_bybit_cls = ccxt_mock

    # Parent manager — attach_mock으로 여러 AsyncMock 간 호출 순서를 보존.
    # mock_calls의 각 _Call 객체 첫 요소가 attach한 이름이 된다.
    parent = MagicMock()
    parent.attach_mock(mock_exchange.set_margin_mode, "set_margin_mode")
    parent.attach_mock(mock_exchange.set_leverage, "set_leverage")
    parent.attach_mock(mock_exchange.create_order, "create_order")

    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    receipt = await provider.create_order(credentials, order_submit_futures)

    # 1. CCXT config — defaultType=linear + demo
    call_kwargs = mock_bybit_cls.call_args.args[0]
    assert call_kwargs["apiKey"] == "test-key"
    assert call_kwargs["secret"] == "test-secret"
    assert call_kwargs["options"]["defaultType"] == "linear"
    assert call_kwargs["options"]["testnet"] is False
    mock_exchange.enable_demo_trading.assert_called_once_with(True)

    # 2. set_margin_mode BEFORE set_leverage BEFORE create_order
    mock_exchange.set_margin_mode.assert_awaited_once_with("cross", "BTC/USDT:USDT")
    mock_exchange.set_leverage.assert_awaited_once_with(5, "BTC/USDT:USDT")
    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT", "market", "buy", 0.001, None
    )

    # 2-a. 호출 순서 불변식 — Bybit v5 UTA 요구사항 (margin_mode → leverage → order).
    # assert_awaited_once_with는 per-mock 호출 횟수/인자만 검증하므로,
    # parent.mock_calls로 inter-mock 순서를 명시적으로 확인한다.
    assert [call[0] for call in parent.mock_calls] == [
        "set_margin_mode",
        "set_leverage",
        "create_order",
    ]

    # 3. finally close()
    mock_exchange.close.assert_awaited_once()

    # 4. receipt
    assert receipt.exchange_order_id == "bybit-futures-42"
    assert receipt.filled_price == Decimal("50123.45")
    assert receipt.status == "filled"


async def test_bybit_futures_rejects_missing_leverage(credentials, ccxt_mock):
    from src.trading.exceptions import ProviderError
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitFuturesProvider, OrderSubmit

    bad = OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=None,   # Missing
        margin_mode="cross",
    )
    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="requires leverage and margin_mode"):
        await provider.create_order(credentials, bad)


async def test_bybit_futures_rejects_missing_margin_mode(credentials, ccxt_mock):
    """Guard `leverage is None or margin_mode is None`의 두 번째 분기 커버.
    `and`로 바뀌면 이 테스트가 실패해야 한다 (Sprint 7a T2 리뷰 회귀 방지).
    """
    from src.trading.exceptions import ProviderError
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitFuturesProvider, OrderSubmit

    bad = OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode=None,   # Missing
    )
    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="requires leverage and margin_mode"):
        await provider.create_order(credentials, bad)


async def test_bybit_futures_close_called_on_exchange_error(
    credentials, order_submit_futures, ccxt_mock
):
    mock_exchange, _ = ccxt_mock
    import ccxt.async_support as ccxt_async

    mock_exchange.create_order = AsyncMock(
        side_effect=ccxt_async.InsufficientFunds("margin low")
    )
    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="InsufficientFunds"):
        await provider.create_order(credentials, order_submit_futures)
    mock_exchange.close.assert_awaited_once()


async def test_bybit_futures_non_ccxt_exception_wrapped(
    credentials, order_submit_futures, ccxt_mock
):
    """SECURITY: non-CCXT 예외는 traceback에 apiKey 노출 위험. from None으로 chain 제거."""
    mock_exchange, _ = ccxt_mock
    mock_exchange.create_order = AsyncMock(side_effect=KeyError("transport error"))
    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="unexpected non-CCXT error: KeyError"):
        await provider.create_order(credentials, order_submit_futures)
    mock_exchange.close.assert_awaited_once()


async def test_bybit_futures_cancel_order(credentials, ccxt_mock):
    mock_exchange, _ = ccxt_mock
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    await provider.cancel_order(credentials, "bybit-futures-42")
    mock_exchange.cancel_order.assert_awaited_once_with("bybit-futures-42")
    mock_exchange.close.assert_awaited_once()


# ── Sprint 8+ fetch_balance ───────────────────────────────────────────

async def test_bybit_futures_fetch_balance_returns_free_as_decimal(
    credentials, ccxt_mock
):
    """CCXT fetch_balance 응답의 free 값을 Decimal로 정규화."""
    mock_exchange, _ = ccxt_mock
    mock_exchange.fetch_balance = AsyncMock(
        return_value={
            "USDT": {"free": "1234.5", "used": "100.0", "total": "1334.5"},
            "BTC": {"free": 0.01, "used": 0, "total": 0.01},
            "info": {"raw": "bybit_response"},  # dict but no "free" — skipped
        }
    )
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    balances = await provider.fetch_balance(credentials)

    assert balances["USDT"] == Decimal("1234.5")
    assert balances["BTC"] == Decimal("0.01")
    assert "info" not in balances
    mock_exchange.close.assert_awaited_once()


async def test_bybit_futures_fetch_balance_wraps_ccxt_error(
    credentials, ccxt_mock
):
    """CCXT BaseError → ProviderError 래핑 + 클라이언트 close."""
    import ccxt.async_support as ccxt_async

    mock_exchange, _ = ccxt_mock
    mock_exchange.fetch_balance = AsyncMock(
        side_effect=ccxt_async.NetworkError("connection timeout")
    )
    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="NetworkError"):
        await provider.fetch_balance(credentials)
    mock_exchange.close.assert_awaited_once()


async def test_bybit_futures_fetch_balance_skips_malformed_entries(
    credentials, ccxt_mock
):
    """free 값이 None·비숫자·dict 아님인 항목은 건너뜀."""
    mock_exchange, _ = ccxt_mock
    mock_exchange.fetch_balance = AsyncMock(
        return_value={
            "USDT": {"free": "500"},
            "ETH": {"free": None},  # None → skip
            "XRP": {"free": "not-a-number"},  # ValueError → skip
            "LTC": "not-a-dict",  # dict 아님 → skip
        }
    )
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    balances = await provider.fetch_balance(credentials)

    assert balances == {"USDT": Decimal("500")}
