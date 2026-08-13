# Wave 1 — ExitOrderKind → 라이브 주문 프리미티브 매핑 정합 검증.
"""백테스트 sim(exit_orders) 의 fill_type 과 라이브 주문 프리미티브가 1:1 정합.

TP=reduce-only limit(maker), SL/Trail=reduce-only trigger market(taker).
매핑은 순수함수 — ExitOrderKind 를 import 재사용(중복 정의 0).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.strategy.pine_v2.exit_orders import ExitOrderKind, fill_type_for


def test_take_profit_maps_to_reduce_only_limit_maker():
    from src.strategy.pine_v2.exit_order_mapping import map_exit_kind

    p = map_exit_kind(ExitOrderKind.TAKE_PROFIT, exit_price=Decimal("52000"))
    from src.trading.models import OrderType

    assert p.order_type == OrderType.limit
    assert p.reduce_only is True
    assert p.limit_price == Decimal("52000")
    assert p.trigger_price is None
    assert p.fill_type == "maker"


def test_stop_loss_maps_to_reduce_only_trigger_market_taker():
    from src.strategy.pine_v2.exit_order_mapping import map_exit_kind
    from src.trading.models import OrderType

    p = map_exit_kind(ExitOrderKind.STOP_LOSS, exit_price=Decimal("47000"))
    assert p.order_type == OrderType.market
    assert p.reduce_only is True
    assert p.trigger_price == Decimal("47000")
    assert p.limit_price is None
    assert p.fill_type == "taker"


def test_trailing_stop_maps_to_reduce_only_trigger_market_taker():
    from src.strategy.pine_v2.exit_order_mapping import map_exit_kind
    from src.trading.models import OrderType

    p = map_exit_kind(ExitOrderKind.TRAILING_STOP, exit_price=Decimal("47500"))
    assert p.order_type == OrderType.market
    assert p.reduce_only is True
    assert p.trigger_price == Decimal("47500")
    assert p.limit_price is None
    assert p.fill_type == "taker"


@pytest.mark.parametrize("kind", list(ExitOrderKind))
def test_primitive_fill_type_matches_backtest_fill_type_for(kind):
    """라이브 프리미티브의 fill_type 이 백테스트 cost SSOT(fill_type_for)와 1:1 정합."""
    from src.strategy.pine_v2.exit_order_mapping import map_exit_kind

    p = map_exit_kind(kind, exit_price=Decimal("50000"))
    assert p.fill_type == fill_type_for(kind)


@pytest.mark.parametrize("kind", list(ExitOrderKind))
def test_all_exit_primitives_are_reduce_only(kind):
    """모든 exit 주문은 reduce-only (포지션 청산 전용, over-fill 방지)."""
    from src.strategy.pine_v2.exit_order_mapping import map_exit_kind

    p = map_exit_kind(kind, exit_price=Decimal("50000"))
    assert p.reduce_only is True
