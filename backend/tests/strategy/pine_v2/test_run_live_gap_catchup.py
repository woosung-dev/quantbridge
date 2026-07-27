# run_live의 opt-in 평가 공백 catch-up 이벤트 발행 계약을 검증한다.
"""`run_live`의 기본 마지막-bar 계약과 opt-in catch-up을 검증한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.strategy.pine_v2.event_loop import run_live

_SOURCE = """//@version=5
strategy("gap catchup")
if bar_index == 0
    strategy.entry("A", strategy.long, qty=1)
if bar_index == 1
    strategy.close("A")
if bar_index == 2
    strategy.entry("B", strategy.long, qty=1)
"""


def _ohlcv() -> pd.DataFrame:
    start = datetime(2026, 5, 1, 12, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(minutes=minute) for minute in range(3)],
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [101.0, 99.0, 101.0],
            "volume": [100.0, 100.0, 100.0],
        }
    )


def test_default_call_keeps_last_bar_only_contract() -> None:
    """음성 대조군: opt-in 인자 없이는 마지막 bar B만 발행한다."""
    result = run_live(_SOURCE, _ohlcv())

    assert [signal.trade_id for signal in result.signals] == ["B"]
    assert result.signals[0].bar_time is None


def test_emit_from_bar_time_emits_missing_bars_with_own_times() -> None:
    """watermark 뒤 close와 entry가 각각 자기 bar_time을 보존한다."""
    ohlcv = _ohlcv()
    result = run_live(_SOURCE, ohlcv, emit_from_bar_time=ohlcv.iloc[0]["timestamp"])

    assert [signal.trade_id for signal in result.signals] == ["A", "B"]
    assert [signal.bar_time for signal in result.signals] == list(ohlcv["timestamp"].iloc[1:])
    assert result.signals[0].bar_time != result.signals[1].bar_time


def test_emit_from_bar_time_excludes_equal_and_earlier_bars() -> None:
    """watermark 이하의 이벤트는 재발행하지 않는다."""
    ohlcv = _ohlcv()
    result = run_live(_SOURCE, ohlcv, emit_from_bar_time=ohlcv.iloc[1]["timestamp"])

    assert [signal.trade_id for signal in result.signals] == ["B"]
    assert result.signals[0].bar_time == ohlcv.iloc[2]["timestamp"]
