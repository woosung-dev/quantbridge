# 이 테스트는 수식 중복 정의의 유일한 정당화 근거로 Pine v2와 주문 도메인의 청산가 일치를 CI에서 강제한다.

from __future__ import annotations

from decimal import Decimal

import pytest

from src.strategy.pine_v2.leverage_model import liquidation_price
from src.trading.liquidation import calculate_liquidation_price
from src.trading.models import OrderSide


@pytest.mark.parametrize("leverage", [1, 2, 3, 5, 10, 25, 50, 100, 125])
@pytest.mark.parametrize("entry_price", [0.5, 1.0, 100.0, 63500.25])
@pytest.mark.parametrize("mmr", [0.005, 0.01, 0.05])
@pytest.mark.parametrize(
    ("direction", "side"),
    [("long", OrderSide.buy), ("short", OrderSide.sell)],
)
def test_pine_v2_formula_matches_trading_liquidation(
    leverage: int,
    entry_price: float,
    mmr: float,
    direction: str,
    side: OrderSide,
) -> None:
    pine = liquidation_price(
        entry_price=entry_price,
        direction=direction,  # type: ignore[arg-type]
        leverage=float(leverage),
        mmr=mmr,
    )
    live = calculate_liquidation_price(
        entry_price=Decimal(str(entry_price)),
        side=side,
        leverage=leverage,
        maintenance_margin_rate=Decimal(str(mmr)),
    )

    assert pine is not None
    assert pine == pytest.approx(float(live), rel=1e-12)
