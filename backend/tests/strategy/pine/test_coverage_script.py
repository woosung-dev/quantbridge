"""Go/No-Go 판정 스크립트 테스트."""
from __future__ import annotations

import pandas as pd

from scripts.pine_coverage_report import (
    evaluate_case,
    run_report,
)


def _ohlcv(n: int = 30) -> pd.DataFrame:
    close = pd.Series([10.0 + i for i in range(n)])
    return pd.DataFrame({
        "open": close - 0.1, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": [100.0] * n,
    })


def test_evaluate_case_ok():
    src = """//@version=5
strategy("X")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
"""
    res = evaluate_case(case_id="S-01", tier="standard", source=src, ohlcv=_ohlcv())
    assert res.status == "ok"


def test_evaluate_case_unsupported():
    src = """//@version=5
x = ta.vwma(close, 20)
"""
    res = evaluate_case(case_id="S-02", tier="heavy", source=src, ohlcv=_ohlcv())
    assert res.status == "unsupported"


def test_coverage_report_ground_zero_failure_sets_flag():
    # 표준 티어 중 하나라도 실패하면 ground_zero_passed = False
    cases = [
        {"case_id": "S-01", "tier": "standard", "source": "x = ta.vwma(close, 20)\n"},
    ]
    report = run_report(cases, ohlcv_factory=lambda cid: _ohlcv())
    assert report.ground_zero_passed is False


def test_coverage_report_ground_zero_success():
    cases = [
        {"case_id": "S-01", "tier": "standard", "source": """//@version=5
strategy("X")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
"""},
    ]
    report = run_report(cases, ohlcv_factory=lambda cid: _ohlcv())
    assert report.ground_zero_passed is True


def test_coverage_report_tier_pass_rates():
    cases = [
        # 표준 2개 (둘 다 ok)
        {"case_id": "S-01", "tier": "standard", "source": "x = ta.sma(close, 5)\n"},
        {"case_id": "S-02", "tier": "standard", "source": "x = ta.ema(close, 5)\n"},
        # 중간 2개 (1개 ok, 1개 unsupported)
        {"case_id": "S-03", "tier": "medium", "source": "x = ta.rsi(close, 14)\n"},
        {"case_id": "S-04", "tier": "medium", "source": "x = ta.vwma(close, 20)\n"},
    ]
    report = run_report(cases, ohlcv_factory=lambda cid: _ohlcv())
    assert report.tier_pass_rate("standard") == 1.0
    assert report.tier_pass_rate("medium") == 0.5
