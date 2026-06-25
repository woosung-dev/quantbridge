# ExitOrder 체결 분기(TP/SL gap-through)·trailing ratchet·OCO 형제취소 검증.
"""T0-pine-oco C2/C4 — ExitOrder fill branch + trailing + OCO sibling-cancel.

C2: ExitOrder 단일 leg 체결 (limit gap-through / stop gap-through / 방향대칭 / placed_bar gate / trailing ratchet).
C4: pending_exits OCO 형제취소 + 동시-bar TP+SL → SL 우선(pessimistic).
"""
from __future__ import annotations

from src.strategy.pine_v2.exit_orders import ExitOrderKind
from src.strategy.pine_v2.strategy_state import ExitOrder, StrategyState

# ---- C2: ExitOrder 단일 leg 체결 분기 ----------------------------------


def _tp(direction: str, limit: float, placed: int = 0) -> ExitOrder:
    return ExitOrder(
        from_entry="L",
        exit_id="X",
        position_direction=direction,  # type: ignore[arg-type]
        kind=ExitOrderKind.TAKE_PROFIT,
        placed_bar=placed,
        limit_price=limit,
    )


def _sl(direction: str, stop: float, placed: int = 0) -> ExitOrder:
    return ExitOrder(
        from_entry="L",
        exit_id="X",
        position_direction=direction,  # type: ignore[arg-type]
        kind=ExitOrderKind.STOP_LOSS,
        placed_bar=placed,
        stop_price=stop,
    )


def test_exit_not_filled_on_placement_bar() -> None:
    # placed_bar >= bar → 같은 bar 즉시 체결 금지 (entry 관례 일치).
    o = _tp("long", 110.0, placed=5)
    assert o.try_fill_exit(bar=5, open_=100, high=120, low=99) is None


def test_long_tp_fills_at_limit_when_price_reaches() -> None:
    o = _tp("long", 110.0, placed=0)
    # high 가 limit 도달 → limit 가에 체결.
    assert o.try_fill_exit(bar=1, open_=105, high=112, low=104) == 110.0


def test_long_tp_gap_through_fills_at_open() -> None:
    o = _tp("long", 110.0, placed=0)
    # bar open 이 이미 limit 위로 갭 → open 에 체결 (매도자에 유리).
    assert o.try_fill_exit(bar=1, open_=115, high=118, low=114) == 115.0


def test_long_sl_fills_at_stop_when_low_reaches() -> None:
    o = _sl("long", 90.0, placed=0)
    assert o.try_fill_exit(bar=1, open_=95, high=96, low=88) == 90.0


def test_long_sl_gap_through_fills_at_open() -> None:
    o = _sl("long", 90.0, placed=0)
    # open 이 이미 stop 아래로 갭 → open 에 체결 (매도자에 불리, 현실적).
    assert o.try_fill_exit(bar=1, open_=85, high=86, low=84) == 85.0


def test_short_tp_fills_at_limit_when_low_reaches() -> None:
    o = _tp("short", 90.0, placed=0)
    assert o.try_fill_exit(bar=1, open_=95, high=96, low=88) == 90.0


def test_short_sl_fills_at_stop_when_high_reaches() -> None:
    o = _sl("short", 110.0, placed=0)
    assert o.try_fill_exit(bar=1, open_=105, high=112, low=104) == 110.0


def test_no_fill_when_price_does_not_reach() -> None:
    assert _tp("long", 110.0).try_fill_exit(bar=1, open_=100, high=105, low=99) is None
    assert _sl("long", 90.0).try_fill_exit(bar=1, open_=100, high=105, low=95) is None


# ---- C2: trailing ratchet (불리방향 고정) ------------------------------


def test_long_trailing_ratchets_up_only() -> None:
    o = ExitOrder(
        from_entry="L",
        exit_id="X",
        position_direction="long",
        kind=ExitOrderKind.TRAILING_STOP,
        placed_bar=0,
        trail_offset=5.0,
    )
    # bar1 high=120 → anchor=120, stop=115. low 안 닿음.
    o.update_trailing(high=120, low=116)
    assert o.try_fill_exit(bar=1, open_=118, high=120, low=116) is None
    # bar2 high=118(더 낮음) → anchor 유지 120 (ratchet), stop 여전히 115.
    o.update_trailing(high=118, low=114)
    # low=114 < stop 115 → 체결 at min(open, 115)=115.
    assert o.try_fill_exit(bar=2, open_=117, high=118, low=114) == 115.0


def test_short_trailing_ratchets_down_only() -> None:
    o = ExitOrder(
        from_entry="S",
        exit_id="X",
        position_direction="short",
        kind=ExitOrderKind.TRAILING_STOP,
        placed_bar=0,
        trail_offset=5.0,
    )
    o.update_trailing(high=84, low=80)  # anchor=80, stop=85
    assert o.try_fill_exit(bar=1, open_=82, high=84, low=80) is None
    o.update_trailing(high=86, low=82)  # anchor 유지 80 (ratchet), stop 85
    assert o.try_fill_exit(bar=2, open_=83, high=86, low=82) == 85.0


# ---- C2: pending_exits slot + place_exit 저장 --------------------------


def test_place_exit_stores_bracket_legs() -> None:
    st = StrategyState()
    st.entry("L", "long", qty=1.0, bar=0, fill_price=100.0)
    st.place_exit(from_entry="L", exit_id="X", stop=90.0, limit=110.0, bar=0)
    legs = st.pending_exits["L"]
    kinds = {leg.kind for leg in legs}
    assert kinds == {ExitOrderKind.STOP_LOSS, ExitOrderKind.TAKE_PROFIT}


def test_bracket_tp_fills_closes_position_and_tags_kind() -> None:
    st = StrategyState()
    st.entry("L", "long", qty=1.0, bar=0, fill_price=100.0)
    st.place_exit(from_entry="L", exit_id="X", stop=90.0, limit=110.0, bar=0)
    # bar1: high 가 TP 110 도달 (SL 90 미도달) → TP 체결 + 포지션 청산.
    filled = st.check_exit_fills(bar=1, open_=105, high=111, low=104)
    assert len(filled) == 1
    assert filled[0].exit_price == 110.0
    assert filled[0].exit_kind == ExitOrderKind.TAKE_PROFIT
    assert "L" not in st.open_trades  # 청산됨
    assert "L" not in st.pending_exits  # 포지션 닫히면 잔여 leg 정리


def test_no_exit_orders_regression() -> None:
    # strategy.exit 미사용 → pending_exits 비어있음 → check_exit_fills no-op.
    st = StrategyState()
    st.entry("L", "long", qty=1.0, bar=0, fill_price=100.0)
    assert st.pending_exits == {}
    assert st.check_exit_fills(bar=1, open_=100, high=200, low=50) == []
    assert "L" in st.open_trades  # 포지션 그대로
