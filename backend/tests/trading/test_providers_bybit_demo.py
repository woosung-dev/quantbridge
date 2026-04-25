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
        leverage=None,
        margin_mode=None,
    )


def test_order_submit_accepts_futures_fields():
    """Sprint 7a T1 — OrderSubmit이 futures 확장 필드를 수용.

    Spot 경로는 leverage/margin_mode 모두 None. Linear Perp 경로는 값 전달.
    """
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    assert submit.leverage == 5
    assert submit.margin_mode == "cross"


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
    assert call_kwargs["options"]["testnet"] is False
    mock_exchange.enable_demo_trading.assert_called_once_with(True)
    assert call_kwargs["enableRateLimit"] is True
    assert call_kwargs["timeout"] == 30000
    assert call_kwargs["options"]["defaultType"] == "spot"

    # 2. create_order 호출 인자 — client_order_id 미설정 시 기존 signature 유지
    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT", "market", "buy", 0.001, None
    )

    # 3. 주문 후 close() 호출 — credentials 메모리 잔존 최소화
    mock_exchange.close.assert_awaited_once()

    # 4. receipt 매핑
    assert receipt.exchange_order_id == "bybit-order-42"
    assert receipt.filled_price == Decimal("50123.45")


async def test_bybit_demo_create_order_passes_orderLinkId_when_client_order_id_set(
    credentials, ccxt_mock
):
    """Sprint 12 Phase C-pre: client_order_id 가 set 되면 params 6번째 positional arg 로 전달."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitDemoProvider, OrderSubmit

    mock_exchange, _ = ccxt_mock
    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=None,
        margin_mode=None,
        client_order_id="550e8400-e29b-41d4-a716-446655440000",
    )

    provider = BybitDemoProvider()
    await provider.create_order(credentials, submit)

    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT", "market", "buy", 0.001, None,
        {"orderLinkId": "550e8400-e29b-41d4-a716-446655440000"},
    )


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


async def test_bybit_demo_non_ccxt_exception_wrapped_safely(credentials, order_submit, ccxt_mock):
    """SECURITY C1: non-CCXT 예외도 ProviderError로 wrap + close() 호출 보장.

    raw exception이 traceback에 누출되면 ccxt.bybit의 apiKey/secret이 Sentry로 유출됨.
    """
    mock_exchange, _ = ccxt_mock
    mock_exchange.create_order = AsyncMock(side_effect=KeyError("simulated transport error"))
    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitDemoProvider

    provider = BybitDemoProvider()
    with pytest.raises(ProviderError, match="unexpected non-CCXT error: KeyError"):
        await provider.create_order(credentials, order_submit)

    # close() must still be called (finally guarantee)
    mock_exchange.close.assert_awaited_once()


@pytest.mark.parametrize(
    "ccxt_status,expected",
    [
        ("closed", "filled"),
        ("filled", "filled"),
        ("canceled", "rejected"),
        ("rejected", "rejected"),
        ("open", "submitted"),
        ("partially_filled", "submitted"),
        (None, "submitted"),
        ("weird-status", "submitted"),
    ],
)
def test_map_ccxt_status(ccxt_status, expected):
    """CCXT 상태 어휘 변경 시 silent mis-classification 회귀 방지."""
    from src.trading.providers import _map_ccxt_status

    assert _map_ccxt_status(ccxt_status) == expected
