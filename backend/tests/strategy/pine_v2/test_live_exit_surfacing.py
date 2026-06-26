# 라이브 exit-level surfacing — StrategyState.exit_levels_for + run_live fold 검증 (Phase 3).
"""Phase 3 A1/A2 — 라이브 전략의 exit 레벨(TP/SL/trail)을 주문 경로로 surfacing.

A1: StrategyState.exit_levels_for(trade_id) 가 pending_exits 레그에서 TP/SL/trail 추출.
A2: run_live 가 entry signal 에 exit 레벨을 fold (백테스트 sim 의 exit 계약을 라이브로 노출).

핵심 불변식 — exit 미사용 전략은 전부 None (회귀 0). float(pine 관례) → Decimal 경계 변환.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd

from src.strategy.pine_v2.event_loop import run_live
from src.strategy.pine_v2.strategy_state import StrategyState, Trade

# ── A1: StrategyState.exit_levels_for ─────────────────────────────────────


def _open_long(state: StrategyState, tid: str = "L", entry: float = 100.0) -> None:
    state.open_trades[tid] = Trade(
        id=tid, direction="long", qty=1.0, entry_bar=0, entry_price=entry
    )


def test_exit_levels_for_extracts_tp_sl() -> None:
    state = StrategyState()
    _open_long(state)
    state.place_exit(from_entry="L", exit_id="X", bar=1, stop=95.0, limit=105.0)
    levels = state.exit_levels_for("L")
    assert levels.take_profit == 105.0
    assert levels.stop_loss == 95.0
    assert levels.trailing_stop is None


def test_exit_levels_for_trailing() -> None:
    state = StrategyState()
    _open_long(state)
    state.place_exit(from_entry="L", exit_id="X", bar=1, trail_offset=3.0)
    levels = state.exit_levels_for("L")
    assert levels.trailing_stop == 3.0
    assert levels.take_profit is None
    assert levels.stop_loss is None


def test_exit_levels_for_no_pending_exits_all_none() -> None:
    state = StrategyState()
    _open_long(state)
    levels = state.exit_levels_for("L")
    assert levels == (None, None, None)


def test_exit_levels_for_unknown_trade_all_none() -> None:
    state = StrategyState()
    levels = state.exit_levels_for("NOPE")
    assert levels == (None, None, None)


# ── A2: run_live exit fold ────────────────────────────────────────────────


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=i) for i in range(len(closes))],
            "open": opens,
            "high": [c * 1.02 for c in closes],
            "low": [c * 0.98 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


_ENTRY_TP_SL = """//@version=5
strategy("entry with tp/sl")
if close > open
    strategy.entry("L", strategy.long, qty=1.0)
strategy.exit("X", "L", stop=95.0, limit=105.0)
"""

_ENTRY_TRAIL = """//@version=5
strategy("entry with trail")
if close > open
    strategy.entry("L", strategy.long, qty=1.0)
strategy.exit("X", "L", trail_offset=3.0)
"""

_ENTRY_NO_EXIT = """//@version=5
strategy("entry only")
if close > open
    strategy.entry("L", strategy.long, qty=1.0)
"""


def test_run_live_entry_carries_tp_sl() -> None:
    # 마지막 bar green → entry; 같은 bar strategy.exit 가 TP/SL leg placement.
    result = run_live(_ENTRY_TP_SL, _ohlcv([100.0, 100.0, 102.0]))
    entries = [s for s in result.signals if s.action == "entry"]
    assert len(entries) == 1
    e = entries[0]
    assert e.take_profit == Decimal("105.0")
    assert e.stop_loss == Decimal("95.0")
    assert e.trailing_stop is None


def test_run_live_entry_carries_trailing() -> None:
    result = run_live(_ENTRY_TRAIL, _ohlcv([100.0, 100.0, 102.0]))
    entries = [s for s in result.signals if s.action == "entry"]
    assert len(entries) == 1
    assert entries[0].trailing_stop == Decimal("3.0")
    assert entries[0].take_profit is None
    assert entries[0].stop_loss is None


def test_run_live_entry_without_exit_has_none_levels() -> None:
    # 회귀 0 — exit 미사용 전략은 exit 필드 전부 None.
    result = run_live(_ENTRY_NO_EXIT, _ohlcv([100.0, 100.0, 102.0]))
    entries = [s for s in result.signals if s.action == "entry"]
    assert len(entries) == 1
    e = entries[0]
    assert e.take_profit is None
    assert e.stop_loss is None
    assert e.trailing_stop is None
