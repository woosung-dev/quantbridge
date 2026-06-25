# strategy.exit 인터프리터 본격 구현(NOP 교체) — TP/SL/trail 바인딩 end-to-end 검증.
"""T0-pine-oco C3 — strategy.exit (TP/SL/trail binding) replaces NOP (BL-104).

parse_and_run_v2 로 전체 event-loop 경유. exit order 가 다음 bar 에 target 가에서
체결되어 포지션이 청산되는지 검증.
"""
from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.compat import parse_and_run_v2
from src.strategy.pine_v2.exit_orders import ExitOrderKind


def _ohlcv_from(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """(open, high, low, close) 행 리스트 → OHLCV (volume=1000, 1h UTC)."""
    return pd.DataFrame(
        {
            "open": [r[0] for r in rows],
            "high": [r[1] for r in rows],
            "low": [r[2] for r in rows],
            "close": [r[3] for r in rows],
            "volume": [1000.0] * len(rows),
        },
        index=pd.date_range("2026-01-01", periods=len(rows), freq="1h", tz="UTC"),
    )


def _run(source: str, rows: list[tuple[float, float, float, float]]):
    result = parse_and_run_v2(source, _ohlcv_from(rows), strict=True)
    assert result.historical is not None
    state = result.historical.strategy_state
    assert state is not None
    return state


def test_strategy_exit_tp_limit_closes_position_at_target() -> None:
    source = """//@version=5
strategy("exit tp")
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", "L", stop=95.0, limit=105.0)
"""
    # bar0/1 평탄, bar2 high=106 → TP 105 체결.
    rows = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),  # bar1 entry
        (102.0, 106.0, 101.0, 104.0),  # bar2 → TP 105 fill
        (104.0, 105.0, 103.0, 104.0),
    ]
    state = _run(source, rows)
    assert len(state.closed_trades) == 1
    t = state.closed_trades[0]
    assert t.exit_price == 105.0
    assert t.exit_kind == ExitOrderKind.TAKE_PROFIT
    assert "L" not in state.open_trades


def test_strategy_exit_sl_stop_closes_position_at_target() -> None:
    source = """//@version=5
strategy("exit sl")
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", "L", stop=95.0, limit=120.0)
"""
    rows = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),  # bar1 entry
        (98.0, 99.0, 94.0, 96.0),  # bar2 low=94 → SL 95 fill
        (96.0, 97.0, 95.0, 96.0),
    ]
    state = _run(source, rows)
    assert len(state.closed_trades) == 1
    t = state.closed_trades[0]
    assert t.exit_price == 95.0
    assert t.exit_kind == ExitOrderKind.STOP_LOSS


def test_strategy_exit_empty_from_entry_applies_to_all_open() -> None:
    # from_entry 생략 → 모든 open 포지션에 적용.
    source = """//@version=5
strategy("exit all")
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", limit=105.0)
"""
    rows = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (102.0, 106.0, 101.0, 104.0),
    ]
    state = _run(source, rows)
    assert len(state.closed_trades) == 1
    assert state.closed_trades[0].exit_kind == ExitOrderKind.TAKE_PROFIT


def test_strategy_exit_when_false_places_nothing() -> None:
    source = """//@version=5
strategy("exit when false")
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", "L", stop=95.0, limit=105.0, when=false)
"""
    rows = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (102.0, 106.0, 101.0, 104.0),
    ]
    state = _run(source, rows)
    # exit 미배치 → 청산 안 됨, 포지션 유지.
    assert state.pending_exits == {}
    assert "L" in state.open_trades
