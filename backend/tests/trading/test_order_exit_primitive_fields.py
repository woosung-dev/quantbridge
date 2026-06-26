# Wave 1 — OrderSubmit/Order/schema exit-primitive 필드 round-trip 검증.
"""reduce_only/take_profit/stop_loss/trigger_price/trigger_by 신규 필드.

신규 필드는 전부 Optional/default None (reduce_only 만 bool default False).
기존 entry 주문은 필드 미지정 → 기존 동작 byte-identical 회귀.
"""
from __future__ import annotations

from decimal import Decimal


def test_order_submit_defaults_preserve_legacy_path():
    """필드 미지정 시 reduce_only=False, 나머지 None — 기존 entry 경로 회귀."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    assert submit.reduce_only is False
    assert submit.trigger_price is None
    assert submit.trigger_by is None
    assert submit.take_profit is None
    assert submit.stop_loss is None


def test_order_submit_accepts_exit_primitive_fields():
    """OrderSubmit 이 모든 exit-primitive 필드를 수용."""
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        reduce_only=True,
        trigger_price=Decimal("48000.5"),
        trigger_by="MarkPrice",
        take_profit=Decimal("52000"),
        stop_loss=Decimal("47000"),
    )
    assert submit.reduce_only is True
    assert submit.trigger_price == Decimal("48000.5")
    assert submit.trigger_by == "MarkPrice"
    assert submit.take_profit == Decimal("52000")
    assert submit.stop_loss == Decimal("47000")


def test_order_request_accepts_exit_primitive_fields():
    """OrderRequest 가 신규 optional 필드를 수용하고 default 는 안전값."""
    from uuid import uuid4

    from src.trading.models import OrderSide, OrderType
    from src.trading.schemas import OrderRequest

    req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        reduce_only=True,
        trigger_price=Decimal("48000"),
        trigger_by="MarkPrice",
        take_profit=Decimal("52000"),
        stop_loss=Decimal("47000"),
    )
    assert req.reduce_only is True
    assert req.trigger_price == Decimal("48000")
    assert req.trigger_by == "MarkPrice"
    assert req.take_profit == Decimal("52000")
    assert req.stop_loss == Decimal("47000")

    default_req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    assert default_req.reduce_only is False
    assert default_req.trigger_price is None


def test_order_model_has_exit_primitive_columns():
    """Order 모델이 신규 컬럼을 Decimal/bool/str 로 보유."""
    from uuid import uuid4

    from src.trading.models import Order, OrderSide, OrderState, OrderType

    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
        reduce_only=True,
        trigger_price=Decimal("48000"),
        trigger_by="MarkPrice",
        take_profit=Decimal("52000"),
        stop_loss=Decimal("47000"),
    )
    assert order.reduce_only is True
    assert order.trigger_price == Decimal("48000")
    assert order.trigger_by == "MarkPrice"
    assert order.take_profit == Decimal("52000")
    assert order.stop_loss == Decimal("47000")

    # default — 기존 entry 주문 회귀
    default_order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
    )
    assert default_order.reduce_only is False
    assert default_order.trigger_price is None
    assert default_order.trigger_by is None
    assert default_order.take_profit is None
    assert default_order.stop_loss is None
