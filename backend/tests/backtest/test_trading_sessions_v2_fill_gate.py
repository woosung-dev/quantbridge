# Sprint 38 BL-188 v3 A2 — pending stop fill gate (E3 Live parity) carry-over 검증
"""disallowed session 의 pending stop 주문이 fill skip + carry-over 되는지 검증.

invariants:
- bar_ts 가 sessions_allowed 외부면 check_pending_fills 가 fill 0 → pending 유지
- 다음 allowed bar 에서 fill 재개
- 단일 reference: src.strategy.trading_sessions.is_allowed
"""
from __future__ import annotations

from datetime import UTC, datetime

from src.strategy.pine_v2.strategy_state import PendingOrder, StrategyState


def _utc_ts(hour: int) -> datetime:
    """tz-aware UTC datetime, 2026-04-01 hour:00:00."""
    return datetime(2026, 4, 1, hour, 0, 0, tzinfo=UTC)


def test_fill_gate_skips_disallowed_session_carry_over() -> None:
    """sessions=("asia",) (hour [0,7)) 에서 hour=10 (london only) 시 pending stop fill skip."""
    state = StrategyState()
    state.sessions_allowed = ("asia",)

    # bar 0 에 pending BUY STOP @ 100 등록 (placed_bar=0 이라 bar 0 에서는 즉시 fill 안 됨).
    state.pending_orders["L"] = PendingOrder(
        id="L", direction="long", qty=1.0, stop_price=100.0, placed_bar=0
    )

    # bar 1 (hour=10, london only) — disallowed asia. high=105 면 정상 시 fill 되지만,
    # session gate 가 fill 자체를 skip → pending 유지.
    filled = state.check_pending_fills(
        bar=1, open_=99.0, high=105.0, low=98.0, bar_ts=_utc_ts(10)
    )
    assert filled == [], "disallowed session 에서 fill 발생 — silent skip 실패"
    assert "L" in state.pending_orders, "fill skip 후 pending 유지 의무"
    assert len(state.open_trades) == 0


def test_fill_gate_resumes_at_allowed_session() -> None:
    """disallowed session 에서 carry-over 된 pending 이 다음 allowed bar 에서 fill."""
    state = StrategyState()
    state.sessions_allowed = ("asia",)
    state.pending_orders["L"] = PendingOrder(
        id="L", direction="long", qty=1.0, stop_price=100.0, placed_bar=0
    )

    # bar 1 (hour=10) — skip
    state.check_pending_fills(
        bar=1, open_=99.0, high=105.0, low=98.0, bar_ts=_utc_ts(10)
    )
    assert "L" in state.pending_orders

    # bar 2 (hour=3, asia allowed) — high=105 도달 → fill.
    filled = state.check_pending_fills(
        bar=2, open_=99.0, high=105.0, low=98.0, bar_ts=_utc_ts(3)
    )
    assert len(filled) == 1, "allowed session 에서 fill 미발생"
    assert filled[0].id == "L"
    assert "L" not in state.pending_orders
    assert "L" in state.open_trades


def test_fill_gate_empty_sessions_no_skip_regression() -> None:
    """sessions 비어있으면 bar_ts 무관 정상 fill (회귀 0)."""
    state = StrategyState()
    # sessions_allowed 기본값 () — 비어있음.
    state.pending_orders["L"] = PendingOrder(
        id="L", direction="long", qty=1.0, stop_price=100.0, placed_bar=0
    )

    # hour=10 (asia 외부) 라도 sessions 비어있어 fill 정상.
    filled = state.check_pending_fills(
        bar=1, open_=99.0, high=105.0, low=98.0, bar_ts=_utc_ts(10)
    )
    assert len(filled) == 1, "sessions 비어있는데 fill 미발생 — 회귀"


def test_fill_gate_no_bar_ts_no_skip() -> None:
    """sessions 명시되어 있어도 bar_ts=None 이면 fill 정상 (BarContext.timestamps None case)."""
    state = StrategyState()
    state.sessions_allowed = ("asia",)
    state.pending_orders["L"] = PendingOrder(
        id="L", direction="long", qty=1.0, stop_price=100.0, placed_bar=0
    )

    filled = state.check_pending_fills(
        bar=1, open_=99.0, high=105.0, low=98.0, bar_ts=None
    )
    assert len(filled) == 1, "bar_ts None 시 회귀 fill skip — 의도와 다름"
