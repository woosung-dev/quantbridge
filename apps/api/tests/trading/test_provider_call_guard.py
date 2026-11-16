"""거래소 호출 공통 예외 사다리의 특성화 테스트.

`BybitDemoProvider`·`BybitFuturesProvider`·`OkxDemoProvider` 의 14개 메서드는 같은
사다리를 갖는다. 메서드마다 아래를 고정한다.

- 본문이 던진 `ProviderError` 는 **같은 객체**로 통과한다(재포장 금지).
- ccxt `BaseError` 는 `ProviderError("<Type>: <msg>")` 로 바뀌고 `__cause__` 가 원본이다.
- 그 밖의 예외는 메시지를 숨기고 체인을 끊는다(`from None`) — SECURITY.
- 작업 취소(`asyncio.CancelledError`)는 포장하지 않고 그대로 통과시킨다.
- `close()` 실패는 결과를 바꾸지 않고 메서드별 이벤트명으로 warning 을 남긴다.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import ccxt.async_support as ccxt_async
import pytest

from src.trading.exceptions import ProviderError
from src.trading.models import OrderSide, OrderType
from src.trading.providers import (
    BybitDemoProvider,
    BybitFuturesProvider,
    Credentials,
    OkxDemoProvider,
    OrderSubmit,
)

_CREDS = Credentials(api_key="guard-key", api_secret="guard-secret", passphrase="guard-pass")
_SPOT_ORDER = OrderSubmit(
    symbol="BTC/USDT",
    side=OrderSide.buy,
    type=OrderType.market,
    quantity=Decimal("0.01"),
    price=None,
)
_FUTURES_ORDER = OrderSubmit(
    symbol="BTC/USDT",
    side=OrderSide.buy,
    type=OrderType.market,
    quantity=Decimal("0.01"),
    price=None,
    leverage=5,
    margin_mode="cross",
)

Call = Callable[[], Awaitable[Any]]

# (id, ccxt 클래스 이름, 실패를 심을 exchange 메서드, 호출, close 실패 이벤트명)
_SITES: list[tuple[str, str, str, Call, str]] = [
    (
        "demo.create_order",
        "bybit",
        "create_order",
        lambda: BybitDemoProvider().create_order(_CREDS, _SPOT_ORDER),
        "bybit_close_failed",
    ),
    (
        "demo.cancel_order",
        "bybit",
        "cancel_order",
        lambda: BybitDemoProvider().cancel_order(_CREDS, "oid", "BTC/USDT"),
        "bybit_close_failed",
    ),
    (
        "futures.create_order",
        "bybit",
        "create_order",
        lambda: BybitFuturesProvider().create_order(_CREDS, _FUTURES_ORDER),
        "bybit_futures_close_failed",
    ),
    (
        "futures.set_trading_stop",
        "bybit",
        "load_markets",
        lambda: BybitFuturesProvider().set_trading_stop(
            _CREDS, symbol="BTC/USDT", side=OrderSide.sell, qty=Decimal("1"), distance=Decimal("5")
        ),
        "bybit_futures_close_failed",
    ),
    (
        "futures.fetch_position",
        "bybit",
        "fetch_positions",
        lambda: BybitFuturesProvider().fetch_position(_CREDS, "BTC/USDT"),
        "bybit_futures_close_failed",
    ),
    (
        "futures.fetch_api_identity",
        "bybit",
        "privateGetV5UserQueryApi",
        lambda: BybitFuturesProvider().fetch_api_identity(_CREDS),
        "bybit_futures_close_failed",
    ),
    (
        "futures.fetch_open_positions",
        "bybit",
        "fetch_positions",
        lambda: BybitFuturesProvider().fetch_open_positions(_CREDS, "BTC/USDT"),
        "bybit_futures_close_failed",
    ),
    (
        "futures.fetch_all_open_positions",
        "bybit",
        "fetch_positions",
        lambda: BybitFuturesProvider().fetch_all_open_positions(_CREDS),
        "bybit_futures_close_failed",
    ),
    (
        "futures.fetch_open_conditional_orders",
        "bybit",
        "fetch_open_orders",
        lambda: BybitFuturesProvider().fetch_open_conditional_orders(_CREDS, "BTC/USDT"),
        "bybit_futures_close_failed",
    ),
    (
        "futures.cancel_order",
        "bybit",
        "cancel_order",
        lambda: BybitFuturesProvider().cancel_order(_CREDS, "oid", "BTC/USDT"),
        "bybit_futures_close_failed",
    ),
    (
        "futures.fetch_balance",
        "bybit",
        "fetch_balance",
        lambda: BybitFuturesProvider().fetch_balance(_CREDS),
        "bybit_futures_close_failed",
    ),
    (
        "futures.fetch_usdt_balance_snapshot",
        "bybit",
        "fetch_balance",
        lambda: BybitFuturesProvider().fetch_usdt_balance_snapshot(_CREDS),
        "bybit_futures_close_failed",
    ),
    (
        "okx.create_order",
        "okx",
        "create_order",
        lambda: OkxDemoProvider().create_order(_CREDS, _SPOT_ORDER),
        "okx_close_failed",
    ),
    (
        "okx.cancel_order",
        "okx",
        "cancel_order",
        lambda: OkxDemoProvider().cancel_order(_CREDS, "oid", "BTC/USDT"),
        "okx_close_failed",
    ),
]

_SITE_PARAMS = [
    pytest.param(cls_name, method, call, event, id=site_id)
    for site_id, cls_name, method, call, event in _SITES
]


def _install_exchange(
    monkeypatch: pytest.MonkeyPatch, cls_name: str, method: str, side_effect: BaseException
) -> MagicMock:
    exchange = MagicMock()
    exchange.load_markets = AsyncMock(return_value={})
    exchange.amount_to_precision = MagicMock(side_effect=lambda symbol, amount: str(amount))
    exchange.price_to_precision = MagicMock(side_effect=lambda symbol, price: str(price))
    exchange.set_margin_mode = AsyncMock(return_value=None)
    exchange.set_leverage = AsyncMock(return_value=None)
    exchange.close = AsyncMock()
    setattr(exchange, method, AsyncMock(side_effect=side_effect))
    monkeypatch.setattr(ccxt_async, cls_name, MagicMock(return_value=exchange))
    # OKX 는 제품 정책이 CCXT 생성 전에 막는다. 사다리 자체를 재기 위해서만 연다.
    monkeypatch.setattr(OkxDemoProvider, "_raise_product_policy_error", staticmethod(lambda: None))
    return exchange


@pytest.mark.parametrize(("cls_name", "method", "call", "event"), _SITE_PARAMS)
async def test_provider_error_passes_through_as_same_object(
    monkeypatch: pytest.MonkeyPatch, cls_name: str, method: str, call: Call, event: str
) -> None:
    original = ProviderError("already wrapped")
    exchange = _install_exchange(monkeypatch, cls_name, method, original)

    with pytest.raises(ProviderError) as info:
        await call()

    assert info.value is original
    exchange.close.assert_awaited_once()


@pytest.mark.parametrize(("cls_name", "method", "call", "event"), _SITE_PARAMS)
async def test_ccxt_error_is_wrapped_with_cause(
    monkeypatch: pytest.MonkeyPatch, cls_name: str, method: str, call: Call, event: str
) -> None:
    original = ccxt_async.NetworkError("venue down")
    exchange = _install_exchange(monkeypatch, cls_name, method, original)

    with pytest.raises(ProviderError) as info:
        await call()

    assert str(info.value) == "NetworkError: venue down"
    assert info.value.__cause__ is original
    exchange.close.assert_awaited_once()


@pytest.mark.parametrize(("cls_name", "method", "call", "event"), _SITE_PARAMS)
async def test_non_ccxt_error_hides_message_and_breaks_chain(
    monkeypatch: pytest.MonkeyPatch, cls_name: str, method: str, call: Call, event: str
) -> None:
    original = RuntimeError("apiKey=guard-key leaked")
    exchange = _install_exchange(monkeypatch, cls_name, method, original)

    with pytest.raises(ProviderError) as info:
        await call()

    assert str(info.value) == "unexpected non-CCXT error: RuntimeError"
    assert info.value.__cause__ is None
    assert info.value.__suppress_context__ is True
    assert "guard-key" not in str(info.value)
    exchange.close.assert_awaited_once()


@pytest.mark.parametrize(("cls_name", "method", "call", "event"), _SITE_PARAMS)
async def test_non_ccxt_error_object_is_not_held_by_wrapper_traceback_frames(
    monkeypatch: pytest.MonkeyPatch, cls_name: str, method: str, call: Call, event: str
) -> None:
    """지역변수를 수집하는 리포터(Sentry 등)가 원래 예외 객체를 보지 못해야 한다."""
    original = RuntimeError("apiKey=guard-key leaked")
    _install_exchange(monkeypatch, cls_name, method, original)

    with pytest.raises(ProviderError) as info:
        await call()

    holders = []
    tb = info.value.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        if frame.f_code.co_filename != __file__ and any(
            value is original for value in frame.f_locals.values()
        ):
            holders.append(f"{frame.f_code.co_filename}:{frame.f_code.co_name}")
        tb = tb.tb_next
    assert holders == []


@pytest.mark.parametrize(("cls_name", "method", "call", "event"), _SITE_PARAMS)
async def test_cancellation_is_not_wrapped(
    monkeypatch: pytest.MonkeyPatch, cls_name: str, method: str, call: Call, event: str
) -> None:
    """작업 취소(`BaseException`)는 `ProviderError` 로 포장하지 않는다 — 포장하면 취소가 깨진다."""
    original = asyncio.CancelledError()
    exchange = _install_exchange(monkeypatch, cls_name, method, original)

    with pytest.raises(asyncio.CancelledError) as info:
        await call()

    assert info.value is original
    exchange.close.assert_awaited_once()


@pytest.mark.parametrize(("cls_name", "method", "call", "event"), _SITE_PARAMS)
async def test_close_failure_keeps_original_error_and_logs_event(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    cls_name: str,
    method: str,
    call: Call,
    event: str,
) -> None:
    original = ccxt_async.NetworkError("venue down")
    exchange = _install_exchange(monkeypatch, cls_name, method, original)
    exchange.close = AsyncMock(side_effect=OSError("socket"))

    with (
        caplog.at_level(logging.WARNING, logger="src.trading.providers"),
        pytest.raises(ProviderError) as info,
    ):
        await call()

    assert str(info.value) == "NetworkError: venue down"
    records = [r for r in caplog.records if r.getMessage() == event]
    assert len(records) == 1
    assert records[0].exc_info is not None
