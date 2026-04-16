"""BybitDemoProvider — CCXT async_support을 monkeypatch로 mock.

실제 Bybit 호출 금지 (네트워크 isolation). Sprint 5 T26 autouse fixture 연장.
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
def order_submit():
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit
    return OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )


@pytest.fixture
def ccxt_mock(monkeypatch):
    """ccxt.async_support.bybit를 AsyncMock으로 교체."""
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={
            "id": "bybit-order-42",
            "average": 50123.45,
            "status": "closed",
            "symbol": "BTC/USDT",
        }
    )
    mock_exchange.cancel_order = AsyncMock(return_value={})
    mock_exchange.close = AsyncMock()

    mock_bybit_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async
    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit_cls)
    return mock_exchange, mock_bybit_cls


async def test_bybit_demo_create_order_uses_credentials(credentials, order_submit, ccxt_mock):
    mock_exchange, mock_bybit_cls = ccxt_mock
    from src.trading.providers import BybitDemoProvider

    provider = BybitDemoProvider()
    receipt = await provider.create_order(credentials, order_submit)

    # 1. CCXT 인스턴스가 credentials로 생성됐는지
    mock_bybit_cls.assert_called_once()
    call_kwargs = mock_bybit_cls.call_args.args[0]  # bybit({config})
    assert call_kwargs["apiKey"] == "test-key"
    assert call_kwargs["secret"] == "test-secret"
    assert call_kwargs["options"]["testnet"] is True

    # 2. create_order 호출 인자
    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT", "market", "buy", 0.001, None
    )

    # 3. 주문 후 close() 호출 — credentials 메모리 잔존 최소화
    mock_exchange.close.assert_awaited_once()

    # 4. receipt 매핑
    assert receipt.exchange_order_id == "bybit-order-42"
    assert receipt.filled_price == Decimal("50123.45")
    assert receipt.status == "filled"


async def test_bybit_demo_close_called_even_on_exchange_error(credentials, order_submit, ccxt_mock):
    """CCXT 예외 발생해도 close() 호출 보장 (finally 블록)."""
    mock_exchange, _ = ccxt_mock
    import ccxt.async_support as ccxt_async

    mock_exchange.create_order = AsyncMock(side_effect=ccxt_async.InsufficientFunds("balance low"))
    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitDemoProvider

    provider = BybitDemoProvider()
    with pytest.raises(ProviderError, match="InsufficientFunds"):
        await provider.create_order(credentials, order_submit)

    mock_exchange.close.assert_awaited_once()


async def test_bybit_demo_cancel_order(credentials, ccxt_mock):
    mock_exchange, _ = ccxt_mock
    from src.trading.providers import BybitDemoProvider

    provider = BybitDemoProvider()
    await provider.cancel_order(credentials, "bybit-order-42")
    mock_exchange.cancel_order.assert_awaited_once_with("bybit-order-42")
    mock_exchange.close.assert_awaited_once()
