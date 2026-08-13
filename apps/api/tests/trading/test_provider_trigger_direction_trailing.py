# Wave 2 — provider triggerDirection + native trailingStop params shape 검증.
"""ccxt 4.5.49 bybit create_order_request 정합:
- triggerDirection: standalone 트리거 주문(linear) 필수 → params {"triggerDirection": "1"|"2"}.
- trailingStop: contract trailing → params {"trailingStop": str(amount)}.
- 둘 다 Bybit 전용. OKX 는 미주입(triggerDirection 개념 부재 + trailing 별 endpoint).
- oco_group_id 는 app-side 추적 전용 → ccxt params 미주입(Bybit linear 네이티브 OCO group param 부재).
- 값 None → 키 미포함 (기존 entry/exit 회귀 0).
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


# ── Bybit futures (linear) — triggerDirection ────────────────────────────


async def test_bybit_futures_standalone_sl_trigger_direction(credentials, bybit_mock):
    """SL trigger market(long 청산=sell) + trigger_direction=2 → params triggerDirection:"2"."""
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
        reduce_only=True,
        trigger_price=Decimal("47000"),
        trigger_direction=2,
    )
    await BybitFuturesProvider().create_order(credentials, submit)
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT",
        "market",
        "sell",
        "0.001",
        None,
        {
            "reduceOnly": True,
            "triggerPrice": "47000",
            "triggerDirection": "2",
        },
    )


async def test_bybit_futures_native_trailing_stop(credentials, bybit_mock):
    """trailing_stop=Decimal("150.5") → params trailingStop:"150.5" (Bybit native)."""
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
        reduce_only=True,
        trailing_stop=Decimal("150.5"),
    )
    await BybitFuturesProvider().create_order(credentials, submit)
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT",
        "market",
        "sell",
        "0.001",
        None,
        {
            "reduceOnly": True,
            "trailingStop": "150.5",
        },
    )


async def test_bybit_futures_entry_trailing_not_injected_without_reduce_only(
    credentials, bybit_mock
):
    """STEP B — entry(reduce_only=False) 에 trailing_stop 이 있어도 trailingStop 미주입.

    트레일링은 포지션 open 후 set_trading_stop 으로만 placement. entry create_order 에
    trailingStop 이 실리면 ccxt 가 trading-stop 엔드포인트로 라우팅해 entry 가 깨짐
    (+SL 동반 시 bybit.py:3987-3989 InvalidOrder). _merge_exit_params 는 reduce_only 일
    때만 trailingStop emit (defense-in-depth).
    """
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitFuturesProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
        reduce_only=False,  # entry
        trailing_stop=Decimal("150.5"),
    )
    await BybitFuturesProvider().create_order(credentials, submit)
    call = bybit_mock.create_order.call_args
    params = call.args[5] if len(call.args) == 6 else {}
    assert "trailingStop" not in params


async def test_bybit_futures_oco_group_id_not_injected(credentials, bybit_mock):
    """oco_group_id 는 app-side 추적 전용 → ccxt params 미포함."""
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
        reduce_only=True,
        trigger_price=Decimal("47000"),
        trigger_direction=2,
        oco_group_id="oco-trade-abc",
    )
    await BybitFuturesProvider().create_order(credentials, submit)
    params = bybit_mock.create_order.call_args.args[5]
    assert "oco_group_id" not in params
    assert "ocoGroupId" not in params
    assert params == {"reduceOnly": True, "triggerPrice": "47000", "triggerDirection": "2"}


# ── OKX — triggerDirection / trailingStop 미주입 (Bybit 전용) ──────────────


async def test_okx_does_not_inject_trigger_direction_or_trailing(okx_credentials, okx_mock):
    """OKX: trigger_direction/trailing_stop 설정해도 미주입 (triggerPrice/reduceOnly 만)."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OkxDemoProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        reduce_only=True,
        trigger_price=Decimal("48000"),
        trigger_direction=2,  # OKX 에 미주입
        trailing_stop=Decimal("100"),  # OKX 에 미주입
    )
    await OkxDemoProvider().create_order(okx_credentials, submit)
    okx_mock.create_order.assert_awaited_once_with(
        "BTC/USDT",
        "market",
        "sell",
        "0.001",
        None,
        {
            "reduceOnly": True,
            "triggerPrice": "48000",
        },
    )


async def test_bybit_futures_entry_no_wave2_fields_byte_identical(credentials, bybit_mock):
    """Wave2 필드 미설정 entry → 5-arg 호출 (회귀 0)."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitFuturesProvider, OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    await BybitFuturesProvider().create_order(credentials, submit)
    bybit_mock.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT", "market", "buy", "0.001", None
    )
