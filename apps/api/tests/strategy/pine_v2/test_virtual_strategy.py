"""Tier-1 가상 strategy 래퍼 단위 테스트 (ADR-011 §2.1.4).

Sprint 8b: indicator + alertcondition → 자동 매매 실행 경로 변환.
"""

from __future__ import annotations

import pytest

from src.strategy.pine_v2.alert_hook import SignalKind
from src.strategy.pine_v2.virtual_strategy import (
    VirtualAction,
    signal_to_action,
)


@pytest.mark.parametrize(
    "signal,expected_kind,expected_id,expected_direction",
    [
        (SignalKind.LONG_ENTRY, "entry", "L", "long"),
        (SignalKind.SHORT_ENTRY, "entry", "S", "short"),
        (SignalKind.LONG_EXIT, "close", "L", None),
        (SignalKind.SHORT_EXIT, "close", "S", None),
    ],
)
def test_signal_to_action_produces_correct_action(
    signal: SignalKind,
    expected_kind: str,
    expected_id: str,
    expected_direction: str | None,
) -> None:
    action = signal_to_action(signal)
    assert action is not None
    assert isinstance(action, VirtualAction)
    assert action.kind == expected_kind
    assert action.trade_id == expected_id
    assert action.direction == expected_direction


@pytest.mark.parametrize("signal", [SignalKind.INFORMATION, SignalKind.UNKNOWN])
def test_signal_to_action_returns_none_for_non_trade_signals(
    signal: SignalKind,
) -> None:
    assert signal_to_action(signal) is None


# --- VirtualStrategyWrapper + run_virtual_strategy --------------------

import pandas as pd  # noqa: E402

from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy  # noqa: E402


def test_run_virtual_strategy_generates_long_entry_on_condition_true() -> None:
    """alertcondition(buy, 'Long', ...)에서 buy==True가 되는 bar에 strategy.entry('L', long)."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "buy = close > open\n"
        "alertcondition(buy, 'Long', 'UT Long')\n"
    )
    ohlcv = pd.DataFrame(
        {
            # bar 0: close==open → buy=False
            # bar 1: close>open → buy=True → strategy.entry('L', long)
            "open": [100.0, 100.0],
            "high": [101.0, 111.0],
            "low": [99.0, 99.0],
            "close": [100.0, 110.0],
            "volume": [100.0, 100.0],
        }
    )
    result = run_virtual_strategy(source, ohlcv)
    state = result.strategy_state
    assert "L" in state.open_trades
    assert state.open_trades["L"].direction == "long"
    assert state.open_trades["L"].entry_bar == 1


def test_run_virtual_strategy_long_then_short_reverses_position() -> None:
    """Long 진입 후 Short 신호가 오면 Long 자동 청산 + Short 진입 (UT Bot 패턴)."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "buy = close > open\n"
        "sell = close < open\n"
        "alertcondition(buy, 'UT Long', 'UT Long')\n"
        "alertcondition(sell, 'UT Short', 'UT Short')\n"
    )
    ohlcv = pd.DataFrame(
        {
            # bar 0: flat, bar 1: buy → L long, bar 2: sell → L close + S short
            "open": [100.0, 100.0, 110.0],
            "high": [101.0, 111.0, 111.0],
            "low": [99.0, 99.0, 98.0],
            "close": [100.0, 110.0, 100.0],
            "volume": [100.0, 100.0, 100.0],
        }
    )
    result = run_virtual_strategy(source, ohlcv)
    state = result.strategy_state
    # L은 closed, S는 open
    assert "S" in state.open_trades
    assert state.open_trades["S"].direction == "short"
    closed_l = [t for t in state.closed_trades if t.id == "L"]
    assert len(closed_l) == 1, f"L이 정확히 1회 청산되어야 함: {state.closed_trades}"


def test_run_virtual_strategy_edge_trigger_does_not_spam_entries() -> None:
    """조건이 연속 True여도 edge-trigger(False→True 전이)에서만 1회 entry."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "buy = close > open\n"
        "alertcondition(buy, 'UT Long', 'UT Long')\n"
    )
    ohlcv = pd.DataFrame(
        {
            # 3 bar 연속 buy=True → 첫 bar 1회만 entry 발생
            "open": [100.0, 100.0, 101.0, 102.0],
            "high": [101.0, 111.0, 112.0, 113.0],
            "low": [99.0, 99.0, 100.0, 101.0],
            "close": [100.0, 110.0, 111.0, 112.0],
            "volume": [100.0, 100.0, 100.0, 100.0],
        }
    )
    result = run_virtual_strategy(source, ohlcv)
    state = result.strategy_state
    # 단 한 번의 L 진입 (open 또는 closed 중 어느 쪽이든 개수 1)
    entries_l = [t for t in state.closed_trades if t.id == "L"] + (
        [state.open_trades["L"]] if "L" in state.open_trades else []
    )
    assert len(entries_l) == 1


def test_run_virtual_strategy_records_discrepancy_warning() -> None:
    """condition과 message가 충돌하면 warning 기록 (condition 우선)."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "bear = close < open\n"
        "alertcondition(bear, 'Buy', 'BUY')\n"  # message=BUY, condition=bear → SHORT
    )
    ohlcv = pd.DataFrame(
        {
            "open": [100.0, 100.0],
            "high": [101.0, 101.0],
            "low": [99.0, 89.0],
            "close": [100.0, 90.0],
            "volume": [100.0, 100.0],
        }
    )
    result = run_virtual_strategy(source, ohlcv)
    assert any("discrepancy" in w.lower() for w in result.warnings), (
        f"discrepancy warning 부재: {result.warnings}"
    )


def _next_open_candles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [100.0, 130.0, 150.0],
            "high": [111.0, 141.0, 161.0],
            "low": [99.0, 129.0, 149.0],
            "close": [110.0, 140.0, 160.0],
            "volume": [1.0] * 3,
        },
        index=pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC"),
    )


_FIRST_BAR_BUY = """//@version=5
indicator("t")
buy = bar_index == 0
alertcondition(buy, "Buy", "BUY")
"""


def test_virtual_default_bar_close_price_is_unchanged() -> None:
    state = run_virtual_strategy(_FIRST_BAR_BUY, _next_open_candles()).strategy_state
    assert state.open_trades["L"].entry_bar == 0
    assert state.open_trades["L"].entry_price == 110.0
    assert state.pending_market_intents == []


def test_virtual_next_open_uses_fill_price_for_default_sizing() -> None:
    result = run_virtual_strategy(
        _FIRST_BAR_BUY,
        _next_open_candles(),
        initial_capital=1300.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100.0,
        fill_timing="next_bar_open",
    )
    trade = result.strategy_state.open_trades["L"]
    assert trade.entry_bar == 1
    assert trade.entry_price == 130.0
    assert trade.qty == 10.0
    assert result.signal_trace == []
    assert result.degraded_calls_seen == []
    assert not any("미지원" in warning for warning in result.strategy_state.warnings)


def test_virtual_last_bar_next_open_signal_remains_pending() -> None:
    source = _FIRST_BAR_BUY.replace("bar_index == 0", "bar_index == 2")
    state = run_virtual_strategy(
        source, _next_open_candles(), fill_timing="next_bar_open"
    ).strategy_state
    assert state.open_trades == {}
    assert state.closed_trades == []
    assert len(state.pending_market_intents) == 1
    assert state.pending_market_intents[0].trade_id == "L"
    assert state.pending_market_intents[0].placed_bar == 2


def test_virtual_next_open_session_fill_is_carried_to_next_allowed_bar() -> None:
    frame = _next_open_candles()
    frame.index = pd.DatetimeIndex(
        ["2026-01-01T15:00:00Z", "2026-01-01T16:00:00Z", "2026-01-02T08:00:00Z"]
    )
    state = run_virtual_strategy(
        _FIRST_BAR_BUY,
        frame,
        fill_timing="next_bar_open",
        sessions_allowed=("london",),
    ).strategy_state
    assert state.open_trades["L"].entry_bar == 2
    assert state.open_trades["L"].entry_price == 150.0
