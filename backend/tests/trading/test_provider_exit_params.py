# Wave 1 — 3 provider 의 create_order exit-primitive params 주입 shape 검증.
"""ccxt 4.5.49 unified param 계약에 맞춘 정확 shape 를 assert_awaited_once_with 로 고정.

검증 근거 (.venv/.../ccxt/async_support/{bybit,okx}.py create_order_request):
- reduceOnly(bool), triggerPrice(scalar str), takeProfit/stopLoss(object {"triggerPrice":..})
  는 Bybit·OKX 양쪽 동일 unified shape.
- triggerBy 는 Bybit 전용 (extend pass-through). OKX 는 미주입.
- 값 None/False → 키 미포함 (기존 entry 주문 byte-identical 회귀).
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
def okx_credentials():
    from src.trading.providers import Credentials

    return Credentials(api_key="okx-key", api_secret="okx-secret", passphrase="okx-pass")


def _make_ccxt_mock(monkeypatch, exchange_name: str):
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={"id": "order-42", "average": 50000.0, "status": "closed"}
    )
    mock_exchange.close = AsyncMock()
    mock_exchange.load_markets = AsyncMock(return_value={})
    mock_exchange.amount_to_precision = MagicMock(side_effect=lambda s, a: str(a))
    mock_exchange.price_to_precision = MagicMock(side_effect=lambda s, p: str(p))
    if exchange_name == "okx":
        mock_exchange.set_sandbox_mode = MagicMock()
    else:
        # Bybit futures: set_margin_mode / set_leverage 도 stub
        mock_exchange.set_margin_mode = AsyncMock()
        mock_exchange.set_leverage = AsyncMock()
    mock_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, exchange_name, mock_cls)
    return mock_exchange


@pytest.fixture
def bybit_mock(monkeypatch):
    return _make_ccxt_mock(monkeypatch, "bybit")


@pytest.fixture
def okx_mock(monkeypatch):
    return _make_ccxt_mock(monkeypatch, "okx")


# ── Bybit demo spot ──────────────────────────────────────────────────────


async def test_bybit_demo_reduce_only_only(credentials, bybit_mock):
    """reduce_only=True → params {"reduceOnly": True}. 다른 키 미포함."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitDemoProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        reduce_only=True,
    )
    await BybitDemoProvider().create_order(credentials, submit)
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT", "market", "sell", "0.001", None, {"reduceOnly": True}
    )


async def test_bybit_demo_full_bracket_trigger_with_client_order_id(credentials, bybit_mock):
    """reduce_only + trigger + triggerBy + bracket TP/SL + orderLinkId 정확 shape."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitDemoProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        client_order_id="cid-1",
        reduce_only=True,
        trigger_price=Decimal("48000.5"),
        trigger_by="MarkPrice",
        take_profit=Decimal("52000"),
        stop_loss=Decimal("47000"),
    )
    await BybitDemoProvider().create_order(credentials, submit)
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT",
        "market",
        "sell",
        "0.001",
        None,
        {
            "orderLinkId": "cid-1",
            "reduceOnly": True,
            "triggerPrice": "48000.5",
            "triggerBy": "MarkPrice",
            "takeProfit": {"triggerPrice": "52000", "price": "52000"},
            "stopLoss": {"triggerPrice": "47000"},
        },
    )


async def test_bybit_demo_entry_no_exit_fields_is_byte_identical(credentials, bybit_mock):
    """exit 필드 미설정 + client_order_id 미설정 → 기존 5-arg 호출 (회귀 0)."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitDemoProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    await BybitDemoProvider().create_order(credentials, submit)
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT", "market", "buy", "0.001", None
    )


# ── Bybit futures (linear) ───────────────────────────────────────────────


async def test_bybit_futures_trigger_market_reduce_only(credentials, bybit_mock):
    """SL/Trail trigger market: type=market + trigger_price + reduce_only + triggerBy."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitFuturesProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
        client_order_id="cid-2",
        reduce_only=True,
        trigger_price=Decimal("47000"),
        trigger_by="MarkPrice",
    )
    await BybitFuturesProvider().create_order(credentials, submit)
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT",
        "market",
        "sell",
        "0.001",
        None,
        {
            "orderLinkId": "cid-2",
            "reduceOnly": True,
            "triggerPrice": "47000",
            "triggerBy": "MarkPrice",
        },
    )


# ── OKX demo spot ────────────────────────────────────────────────────────


async def test_okx_demo_bracket_trigger_no_trigger_by(okx_credentials, okx_mock):
    """OKX: reduceOnly + triggerPrice + bracket TP/SL + clOrdId. triggerBy 미주입(Bybit 전용)."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OkxDemoProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        client_order_id="cid-3",
        reduce_only=True,
        trigger_price=Decimal("48000"),
        trigger_by="MarkPrice",  # OKX 에는 주입되지 않아야 함
        take_profit=Decimal("52000"),
        stop_loss=Decimal("47000"),
    )
    await OkxDemoProvider().create_order(okx_credentials, submit)
    okx_mock.create_order.assert_awaited_once_with(
        "BTC/USDT",
        "market",
        "sell",
        "0.001",
        None,
        {
            "clOrdId": "cid-3",
            "reduceOnly": True,
            "triggerPrice": "48000",
            "takeProfit": {"triggerPrice": "52000", "price": "52000"},
            "stopLoss": {"triggerPrice": "47000"},
        },
    )


async def test_okx_demo_entry_no_exit_fields_is_byte_identical(okx_credentials, okx_mock):
    """OKX entry (필드 미설정) → 기존 5-arg 호출 (회귀 0)."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OkxDemoProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    await OkxDemoProvider().create_order(okx_credentials, submit)
    okx_mock.create_order.assert_awaited_once_with(
        "BTC/USDT", "market", "buy", "0.001", None
    )
