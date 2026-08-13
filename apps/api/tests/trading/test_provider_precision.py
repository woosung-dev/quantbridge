# MP-4 회귀 — provider 가 거래소 제출 시 float() 정밀도 손실 없이 amount/price_to_precision 문자열을 사용하는지 검증
"""MP-4: CCXT 경계 Decimal→float 정밀도 손실 차단.

기존 provider 테스트(test_providers_*.py)는 fully-mocked exchange 라 amount_to_precision
의 실제 반올림을 검증 못 한다(mock-echo). 본 테스트는 **real ccxt 인스턴스 + 주입된
markets precision** 으로, provider 가 float() 대신 거래소 precision 문자열을 제출하는지
deterministic 하게 검증한다(네트워크 없음 — load_markets/create_order/set_* 만 stub).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import ccxt.async_support as ccxt_async
import pytest

from src.trading import providers
from src.trading.models import ExchangeMode, OrderSide, OrderType
from src.trading.providers import (
    BybitDemoProvider,
    BybitFuturesProvider,
    Credentials,
    OkxDemoProvider,
    OrderSubmit,
)

# instrument precision(amount step 0.001, price step 0.1) 보다 더 세밀한 입력.
# float() 경유 시 0.123456789 그대로 노출 → precision 경유 시 거래소 step 으로 반올림.
_QTY = Decimal("0.123456789")
_PRICE = Decimal("65432.16789")


def _inject_market(exchange: object, symbol: str) -> dict:
    """real ccxt 인스턴스에 markets 주입 + 네트워크 메서드만 stub.

    amount_to_precision / price_to_precision 는 real 로 유지(주입된 precision 사용).
    반환 dict 에 create_order 가 받은 인자를 capture.
    """
    market_id = symbol.replace("/", "").replace(":", "")
    market = {
        "symbol": symbol,
        "id": market_id,
        "precision": {"amount": 0.001, "price": 0.1},
        "limits": {"amount": {"min": 0.001}, "cost": {"min": 5.0}},
    }
    exchange.markets = {symbol: market}  # type: ignore[attr-defined]
    exchange.markets_by_id = {market_id: [market]}  # type: ignore[attr-defined]
    exchange.load_markets = AsyncMock(return_value=exchange.markets)  # type: ignore[attr-defined]
    captured: dict = {}

    async def _create_order(s, t, side, amount, price=None, params=None):
        captured.update(symbol=s, type=t, side=side, amount=amount, price=price, params=params)
        return {"id": "oid-1", "status": "closed", "average": "65000"}

    exchange.create_order = _create_order  # type: ignore[assignment]
    exchange.set_leverage = AsyncMock()  # type: ignore[attr-defined]
    exchange.set_margin_mode = AsyncMock()  # type: ignore[attr-defined]
    return captured


@pytest.mark.asyncio
async def test_bybit_demo_submits_precision_string_not_float(monkeypatch):
    ex = ccxt_async.bybit()
    captured = _inject_market(ex, "BTC/USDT")
    monkeypatch.setattr(providers.ccxt_async, "bybit", lambda *a, **k: ex)

    order = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=_QTY,
        price=_PRICE,
    )
    await BybitDemoProvider().create_order(
        Credentials(api_key="k", api_secret="s", environment=ExchangeMode.demo), order
    )

    expected_amount = ex.amount_to_precision("BTC/USDT", _QTY)
    expected_price = ex.price_to_precision("BTC/USDT", _PRICE)
    # 핵심: float 이 아니라 거래소 precision 문자열을 제출한다.
    assert isinstance(captured["amount"], str)
    assert captured["amount"] == expected_amount
    assert captured["price"] == expected_price
    assert captured["amount"] != float(_QTY)
    # load_markets 가 precision 계산 전에 호출됐다(markets 메타데이터 의존).
    ex.load_markets.assert_awaited()


@pytest.mark.asyncio
async def test_bybit_futures_submits_precision_string(monkeypatch):
    linear = "BTC/USDT:USDT"
    ex = ccxt_async.bybit()
    captured = _inject_market(ex, linear)
    monkeypatch.setattr(providers.ccxt_async, "bybit", lambda *a, **k: ex)

    order = OrderSubmit(
        symbol="BTC/USDT",  # provider 가 linear 로 normalize
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=_QTY,
        price=_PRICE,
        leverage=5,
        margin_mode="cross",
    )
    await BybitFuturesProvider().create_order(
        Credentials(api_key="k", api_secret="s", environment=ExchangeMode.demo), order
    )

    assert captured["symbol"] == linear
    assert isinstance(captured["amount"], str)
    assert captured["amount"] == ex.amount_to_precision(linear, _QTY)
    assert captured["price"] == ex.price_to_precision(linear, _PRICE)


@pytest.mark.asyncio
async def test_okx_demo_submits_precision_string(monkeypatch):
    ex = ccxt_async.okx()
    captured = _inject_market(ex, "BTC/USDT")
    monkeypatch.setattr(providers.ccxt_async, "okx", lambda *a, **k: ex)

    order = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.limit,
        quantity=_QTY,
        price=_PRICE,
    )
    await OkxDemoProvider().create_order(
        Credentials(api_key="k", api_secret="s", passphrase="p", environment=ExchangeMode.demo),
        order,
    )

    assert isinstance(captured["amount"], str)
    assert captured["amount"] == ex.amount_to_precision("BTC/USDT", _QTY)
    assert captured["price"] == ex.price_to_precision("BTC/USDT", _PRICE)


@pytest.mark.asyncio
async def test_market_order_price_stays_none(monkeypatch):
    """price=None(시장가) 은 precision 변환 없이 None 유지."""
    ex = ccxt_async.bybit()
    captured = _inject_market(ex, "BTC/USDT")
    monkeypatch.setattr(providers.ccxt_async, "bybit", lambda *a, **k: ex)

    order = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=_QTY,
        price=None,
    )
    await BybitDemoProvider().create_order(
        Credentials(api_key="k", api_secret="s", environment=ExchangeMode.demo), order
    )

    assert captured["price"] is None
    assert isinstance(captured["amount"], str)
