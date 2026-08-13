# Wave 2 — Order/OrderRequest/OrderSubmit TP/SL placement 신규 필드 default None 회귀 가드.
"""신규 컬럼 default None = 기존 entry 주문 경로 회귀 0 (가드 테스트)."""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4


def test_order_wave2_fields_default_none() -> None:
    from src.trading.models import Order, OrderSide, OrderState, OrderType

    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
    )
    assert order.trigger_direction is None
    assert order.oco_group_id is None
    assert order.trailing_stop is None


def test_order_wave2_fields_settable() -> None:
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
        trigger_direction=2,
        oco_group_id="oco-abc",
        trailing_stop=Decimal("150.5"),
    )
    assert order.trigger_direction == 2
    assert order.oco_group_id == "oco-abc"
    assert order.trailing_stop == Decimal("150.5")


def test_order_request_wave2_fields_default_none() -> None:
    from src.trading.models import OrderSide, OrderType
    from src.trading.schemas import OrderRequest

    req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    assert req.trigger_direction is None
    assert req.oco_group_id is None
    assert req.trailing_stop is None
