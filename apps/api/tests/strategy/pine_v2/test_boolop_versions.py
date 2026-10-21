"""미표기 기본 v1·v4/v5의 eager 평가와 v6 단축 평가를 구분한다.

UDF·배열 예제는 인터프리터의 버전별 평가 경로 검사이며, native v1 문법 검증은 아니다.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical


def _candles() -> pd.DataFrame:
    close = [90.0, 110.0, 90.0, 110.0]
    return pd.DataFrame(
        {
            "open": close,
            "high": [value + 1 for value in close],
            "low": [value - 1 for value in close],
            "close": close,
            "volume": [1.0] * len(close),
        }
    )


@pytest.mark.parametrize("version", [4, 5, 6, None])
def test_rhs_crossover_history_is_eager_before_v6(version: int | None) -> None:
    header = f"//@version={version}\n" if version else ""
    declaration = 'study("t")' if version in (4, None) else 'indicator("t")'
    crossover = "crossover" if version in (4, None) else "ta.crossover"
    source = (
        f"{header}{declaration}\n"
        f"signal = close > 100 and {crossover}(close, 100)\n"
        "plotshape(signal)\n"
    )
    result = run_historical(source, _candles(), strict=True, capture_signals=True)
    assert result.errors == []
    indices = [row.bar_index for row in result.signal_trace if row.value]
    assert indices == ([1, 3] if version != 6 else [])


@pytest.mark.parametrize("version", [4, 5, 6, None])
def test_rhs_user_function_barssince_tracks_every_bar_before_v6(version: int | None) -> None:
    """RSI divergence 원본의 _inRange 호출이 조건부 호출 시계를 쓰지 않도록 한다."""
    header = f"//@version={version}\n" if version else ""
    declaration = 'study("t")' if version in (4, None) else 'indicator("t")'
    barssince = "barssince" if version in (4, None) else "ta.barssince"
    source = (
        f"{header}{declaration}\n"
        "inRange(cond) =>\n"
        f"    bars = {barssince}(cond)\n"
        "    bars >= 1 and bars <= 2\n"
        "signal = close > 100 and inRange(bar_index == 0)\n"
        "plotshape(signal)\n"
    )
    result = run_historical(source, _candles(), strict=True, capture_signals=True)
    assert result.errors == []
    indices = [row.bar_index for row in result.signal_trace if row.value]
    assert indices == ([1] if version != 6 else [])


@pytest.mark.parametrize("version", [4, 5, 6, None])
def test_division_by_zero_rhs_runs_only_in_eager_versions(version: int | None) -> None:
    header = f"//@version={version}\n" if version else ""
    declaration = 'study("t")' if version in (4, None) else 'indicator("t")'
    source = (
        f"{header}{declaration}\n"
        "seen = array.new_float(0)\n"
        "divide() =>\n"
        "    array.push(seen, 1.0 / 0.0)\n"
        "    true\n"
        "a = false and divide()\n"
        "b = true or divide()\n"
        "n = array.size(seen)\n"
    )
    result = run_historical(source, _candles(), strict=True)
    assert result.errors == []
    assert result.final_state["a"] is False
    assert result.final_state["b"] is True
    expected = 2 if version != 6 else 0
    assert result.final_state["n"] == expected
    assert all(math.isnan(value) for value in result.final_state["seen"])
