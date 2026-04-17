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
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    receipt = await provider.create_order(credentials, order_submit_futures)

    # 1. CCXT config — defaultType=linear + testnet
    call_kwargs = mock_bybit_cls.call_args.args[0]
    assert call_kwargs["apiKey"] == "test-key"
    assert call_kwargs["secret"] == "test-secret"
    assert call_kwargs["options"]["defaultType"] == "linear"
    assert call_kwargs["options"]["testnet"] is True

    # 2. set_margin_mode BEFORE set_leverage BEFORE create_order
    mock_exchange.set_margin_mode.assert_awaited_once_with("cross", "BTC/USDT:USDT")
    mock_exchange.set_leverage.assert_awaited_once_with(5, "BTC/USDT:USDT")
    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT", "market", "buy", 0.001, None
    )

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
