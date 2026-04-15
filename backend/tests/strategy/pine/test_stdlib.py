"""Pine stdlib (화이트리스트 + 참조 구현) 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine.stdlib import call_supported, is_supported


@pytest.fixture
def close() -> pd.Series:
    return pd.Series([10.0, 11.0, 12.0, 11.5, 10.8, 10.5, 11.2, 12.5, 13.0, 12.8], name="close")


def test_is_supported_known_functions():
    assert is_supported("ta.sma")
    assert is_supported("ta.ema")
    assert is_supported("ta.rsi")
    assert is_supported("ta.atr")
    assert is_supported("ta.stdev")
    assert is_supported("ta.crossover")
    assert is_supported("ta.crossunder")
    assert is_supported("ta.highest")
    assert is_supported("ta.lowest")
    assert is_supported("ta.change")
    assert is_supported("nz")
    assert is_supported("na")


def test_is_supported_rejects_unknown():
    assert not is_supported("ta.vwma")
    assert not is_supported("request.security")


def test_ta_sma_matches_rolling_mean(close):
    result = call_supported("ta.sma", close, 3)
    expected = close.rolling(3).mean()
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_ta_ema_basic(close):
    result = call_supported("ta.ema", close, 3)
    # pandas ewm span=3 (adjust=False) 와 일치 — Pine과 동일 공식
    expected = close.ewm(span=3, adjust=False).mean()
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_ta_crossover_detects_upward_cross():
    a = pd.Series([1.0, 2.0, 3.0, 4.0])
    b = pd.Series([2.0, 2.0, 2.0, 2.0])
    result = call_supported("ta.crossover", a, b)
    # a가 1→2→3→4로 오르고 b는 2 고정. a>b인 첫 bar(index=2, 값 3>2)에서 True.
    # ta.crossover는 "직전 bar에서 a<=b이고 현재 bar에서 a>b"인 시점만 True
    assert result.iloc[0] is False or result.iloc[0] == False  # noqa: E712
    assert result.iloc[2] == True  # noqa: E712


def test_ta_crossunder_detects_downward_cross():
    a = pd.Series([4.0, 3.0, 2.0, 1.0])
    b = pd.Series([2.0, 2.0, 2.0, 2.0])
    result = call_supported("ta.crossunder", a, b)
    # a가 4→3→2→1로 내려가고 b는 2 고정.
    # crossunder는 "직전 bar에서 a>=b이고 현재 bar에서 a<b"인 시점.
    # index=2: a=2==b=2 → a<b 불성립. index=3: a=1<b=2, prev_a=2>=prev_b=2 → True.
    assert result.iloc[3] == True  # noqa: E712


def test_ta_highest_lowest(close):
    hi = call_supported("ta.highest", close, 3)
    lo = call_supported("ta.lowest", close, 3)
    pd.testing.assert_series_equal(hi, close.rolling(3).max(), check_names=False)
    pd.testing.assert_series_equal(lo, close.rolling(3).min(), check_names=False)


def test_ta_change(close):
    result = call_supported("ta.change", close, 1)
    expected = close.diff(1)
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_nz_replaces_na_with_zero():
    s = pd.Series([1.0, np.nan, 3.0])
    result = call_supported("nz", s)
    expected = pd.Series([1.0, 0.0, 3.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_nz_with_replacement():
    s = pd.Series([1.0, np.nan, 3.0])
    result = call_supported("nz", s, -1.0)
    expected = pd.Series([1.0, -1.0, 3.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_na_checks_nan():
    s = pd.Series([1.0, np.nan, 3.0])
    result = call_supported("na", s)
    expected = pd.Series([False, True, False])
    pd.testing.assert_series_equal(result, expected, check_names=False)
