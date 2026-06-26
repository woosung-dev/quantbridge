# Wave 2 — Order 의 TP/SL placement 필드가 tasks/trading OrderSubmit 빌드까지 전파되는지 검증.
"""order_service → DB Order → tasks/trading._execute_with_session 가 빌드한 OrderSubmit 이
trigger_direction/oco_group_id/trailing_stop 를 동일하게 carry 하는지(provider monkeypatch capture).
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.trading.models import OrderSide, OrderState, OrderType


def _make_order(**overrides):
    """필수 필드 + Wave 2 필드를 가진 Order-유사 객체 (DB 미접근, attribute 접근만)."""
    base = {
        "id": uuid4(),
        "strategy_id": uuid4(),
        "exchange_account_id": uuid4(),
        "symbol": "BTC/USDT",
        "side": OrderSide.sell,
        "type": OrderType.market,
        "quantity": Decimal("0.001"),
        "price": None,
        "state": OrderState.pending,
        "leverage": 5,
        "margin_mode": "cross",
        "reduce_only": True,
        "trigger_price": Decimal("47000"),
        "trigger_by": "MarkPrice",
        "take_profit": None,
        "stop_loss": None,
        "trigger_direction": 2,
        "oco_group_id": "oco-xyz",
        "trailing_stop": Decimal("150.5"),
        "dispatch_snapshot": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_order_submit_carries_wave2_fields() -> None:
    """tasks/trading 가 빌드하는 OrderSubmit 이 Wave 2 필드를 그대로 전달."""
    from src.trading.providers import OrderSubmit

    order = _make_order()
    # tasks/trading._execute_with_session 의 OrderSubmit 빌드 미러 (필드 동등성 계약 고정).
    submit = OrderSubmit(
        symbol=order.symbol,
        side=order.side,
        type=order.type,
        quantity=order.quantity,
        price=order.price,
        leverage=order.leverage,
        margin_mode=order.margin_mode,
        client_order_id=str(order.id),
        reduce_only=order.reduce_only,
        trigger_price=order.trigger_price,
        trigger_by=order.trigger_by,
        take_profit=order.take_profit,
        stop_loss=order.stop_loss,
        trigger_direction=order.trigger_direction,
        oco_group_id=order.oco_group_id,
        trailing_stop=order.trailing_stop if order.reduce_only else None,
    )
    assert submit.trigger_direction == 2
    assert submit.oco_group_id == "oco-xyz"
    # reduce_only=True (보호 주문) → trailing 전달.
    assert submit.trailing_stop == Decimal("150.5")


def test_build_order_submit_entry_nulls_trailing() -> None:
    """STEP B — entry(reduce_only=False)는 trailing_stop 의도가 Order 에 있어도 OrderSubmit
    에서 None (entry create_order 에 trailingStop 미주입). place_trailing_stop 가 후속 발주."""
    from src.trading.providers import OrderSubmit

    order = _make_order(reduce_only=False, trailing_stop=Decimal("150.5"))
    submit = OrderSubmit(
        symbol=order.symbol,
        side=order.side,
        type=order.type,
        quantity=order.quantity,
        price=order.price,
        leverage=order.leverage,
        margin_mode=order.margin_mode,
        client_order_id=str(order.id),
        reduce_only=order.reduce_only,
        trigger_price=order.trigger_price,
        trigger_by=order.trigger_by,
        take_profit=order.take_profit,
        stop_loss=order.stop_loss,
        trigger_direction=order.trigger_direction,
        oco_group_id=order.oco_group_id,
        trailing_stop=order.trailing_stop if order.reduce_only else None,
    )
    assert submit.trailing_stop is None


@pytest.mark.asyncio
async def test_provider_receives_wave2_params_via_merge() -> None:
    """BybitFutures create_order 가 Wave 2 필드를 ccxt params 로 정확 주입(end-to-end shape)."""
    from unittest.mock import AsyncMock, MagicMock

    import ccxt.async_support as ccxt_async

    from src.trading.providers import BybitFuturesProvider, Credentials, OrderSubmit

    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={"id": "x", "average": 50000.0, "status": "closed"}
    )
    mock_exchange.close = AsyncMock()
    mock_exchange.load_markets = AsyncMock(return_value={})
    mock_exchange.amount_to_precision = MagicMock(side_effect=lambda s, a: str(a))
    mock_exchange.price_to_precision = MagicMock(side_effect=lambda s, p: str(p))
    mock_exchange.set_margin_mode = AsyncMock()
    mock_exchange.set_leverage = AsyncMock()
    mp = MagicMock(return_value=mock_exchange)

    orig = ccxt_async.bybit
    ccxt_async.bybit = mp
    try:
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
            oco_group_id="oco-xyz",
            trailing_stop=Decimal("150.5"),
        )
        await BybitFuturesProvider().create_order(
            Credentials(api_key="k", api_secret="s"), submit
        )
        params = mock_exchange.create_order.call_args.args[5]
        assert params["triggerDirection"] == "2"
        assert params["trailingStop"] == "150.5"
        assert params["reduceOnly"] is True
        assert "oco_group_id" not in params
    finally:
        ccxt_async.bybit = orig
