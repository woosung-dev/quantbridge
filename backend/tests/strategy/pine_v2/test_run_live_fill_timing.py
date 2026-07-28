"""`run_live`의 시장가 체결 시점 배선을 검증한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_live

_OPENS = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]
_CLOSES = [105.0, 115.0, 125.0, 135.0, 145.0, 155.0]


def _ohlcv() -> pd.DataFrame:
    start = datetime(2026, 5, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=index) for index in range(len(_OPENS))],
            "open": _OPENS,
            "high": [close + 1.0 for close in _CLOSES],
            "low": [open_ - 1.0 for open_ in _OPENS],
            "close": _CLOSES,
            "volume": [100.0] * len(_OPENS),
        }
    )


_ENTRY_ON_LAST_BAR = """//@version=5
strategy("default bar close")
if bar_index == 5
    strategy.entry("L", strategy.long, qty=1)
"""


_ENTRY_AND_CLOSE = """//@version=5
strategy("entry and close")
if bar_index == 2
    strategy.entry("L", strategy.long, qty=1)
if bar_index == 4
    strategy.close("L")
"""


_ENTRY_ONLY = """//@version=5
strategy("entry only")
if bar_index == 2
    strategy.entry("L", strategy.long, qty=1)
"""


_STOP_ENTRY = """//@version=5
strategy("stop entry")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1, stop=125)
"""


def test_bar_close_is_default_and_unchanged() -> None:
    """인자 미지정은 기존 bar 종가 체결 결과와 동일하다."""
    default = run_live(_ENTRY_ON_LAST_BAR, _ohlcv())
    explicit = run_live(_ENTRY_ON_LAST_BAR, _ohlcv(), fill_timing="bar_close")

    assert default.signals == explicit.signals
    assert default.strategy_state_report == explicit.strategy_state_report
    assert [(signal.action, signal.trade_id) for signal in default.signals] == [("entry", "L")]
    open_trade = default.strategy_state_report["open_trades"][0]
    assert open_trade["entry_bar"] == 5
    assert open_trade["entry_price"] == pytest.approx(_CLOSES[5])


def test_next_bar_open_delays_entry_by_exactly_one_bar() -> None:
    """bar 2 진입 신호는 bar 3 시가 체결 이벤트로 나온다."""
    ohlcv = _ohlcv()
    result = run_live(
        _ENTRY_ONLY,
        ohlcv,
        fill_timing="next_bar_open",
        emit_from_bar_time=ohlcv.iloc[0]["timestamp"] - timedelta(seconds=1),
    )

    entries = [signal for signal in result.signals if signal.action == "entry"]
    assert len(entries) == 1
    assert entries[0].bar_time == ohlcv.iloc[3]["timestamp"]
    open_trade = result.strategy_state_report["open_trades"][0]
    assert open_trade["entry_bar"] == 3
    assert open_trade["entry_price"] == pytest.approx(_OPENS[3])


def test_next_bar_open_does_not_lose_the_signal() -> None:
    """연속 평가에서는 지연된 진입 신호가 다음 bar에 정확히 한 번 발행된다."""
    ohlcv = _ohlcv()

    before_fill = run_live(_ENTRY_ONLY, ohlcv.iloc[:3], fill_timing="next_bar_open")
    at_fill = run_live(_ENTRY_ONLY, ohlcv.iloc[:4], fill_timing="next_bar_open")
    after_fill = run_live(_ENTRY_ONLY, ohlcv.iloc[:5], fill_timing="next_bar_open")

    signals = [*before_fill.signals, *at_fill.signals, *after_fill.signals]
    assert [(signal.action, signal.trade_id) for signal in signals] == [("entry", "L")]


def test_next_bar_open_also_delays_exit() -> None:
    """next_bar_open은 close도 신호 bar 다음 시가로 지연한다."""
    ohlcv = _ohlcv()
    result = run_live(
        _ENTRY_AND_CLOSE,
        ohlcv,
        fill_timing="next_bar_open",
        emit_from_bar_time=ohlcv.iloc[0]["timestamp"] - timedelta(seconds=1),
    )

    assert [(signal.action, signal.bar_time) for signal in result.signals] == [
        ("entry", ohlcv.iloc[3]["timestamp"]),
        ("close", ohlcv.iloc[5]["timestamp"]),
    ]
    closed_trade = result.strategy_state_report["closed_trades"][0]
    assert closed_trade["exit_bar"] == 5
    assert closed_trade["exit_price"] == pytest.approx(_OPENS[5])


def test_stop_entry_is_unaffected_by_fill_timing() -> None:
    """stop 진입은 시장가 인텐트 큐를 거치지 않아 두 설정이 동일하다."""
    bar_close = run_live(_STOP_ENTRY, _ohlcv())
    next_bar_open = run_live(_STOP_ENTRY, _ohlcv(), fill_timing="next_bar_open")

    assert bar_close.signals == next_bar_open.signals == []
    assert bar_close.pending_orders == next_bar_open.pending_orders == []
    assert bar_close.strategy_state_report == next_bar_open.strategy_state_report
    assert bar_close.strategy_state_report["open_trades"][0]["entry_bar"] == 2
