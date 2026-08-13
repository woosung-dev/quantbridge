# BL-180 골든 오라클 — 엔진 계산 함수 검증 (8 named test, 손 계산 fixture 대조)
from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import (
    _build_raw_trades,
    _compute_equity_curve,
    _compute_metrics,
)
from tests.fixtures.backtest_golden_minimal import (
    S1_EXPECTED_BH_VALS,
    S1_EXPECTED_ENTRIES,
    S1_EXPECTED_EQUITY_VALS,
    S1_EXPECTED_EXITS,
    S2_EXPECTED_BH_VALS,
    S2_EXPECTED_ENTRIES,
    S2_EXPECTED_EQUITY_VALS,
    S2_EXPECTED_EXITS,
    make_s1_ohlcv,
    make_s1_state,
    make_s2_ohlcv,
    make_s2_state,
)

_TOL = Decimal("0.0001")
_CFG = BacktestConfig(init_cash=Decimal("1000"), fees=0.0, slippage=0.0, freq="1D")


def assert_curve_matches(actual_series: pd.Series, expected_vals: list[str]) -> None:
    assert len(actual_series) == len(expected_vals)
    for i, exp in enumerate(expected_vals):
        actual: Decimal = actual_series.iloc[i]
        assert abs(actual - Decimal(exp)) <= _TOL, f"bar {i}: actual={actual} expected={exp}"


def assert_bh_matches(bh_curve: list[tuple[str, Decimal]] | None, expected_vals: list[str]) -> None:
    assert bh_curve is not None, "buy_and_hold_curve is None"
    assert len(bh_curve) == len(expected_vals)
    for i, ((_, actual), exp) in enumerate(zip(bh_curve, expected_vals)):
        assert abs(actual - Decimal(exp)) <= _TOL, f"bar {i}: actual={actual} expected={exp}"


@pytest.fixture(scope="module")
def _s1() -> tuple[Any, ...]:
    state = make_s1_state()
    ohlcv = make_s1_ohlcv()
    trades = _build_raw_trades(state, _CFG)
    equity = _compute_equity_curve(trades, ohlcv, _CFG)
    metrics = _compute_metrics(trades, equity, _CFG, ohlcv)
    return trades, equity, metrics


@pytest.fixture(scope="module")
def _s2() -> tuple[Any, ...]:
    state = make_s2_state()
    ohlcv = make_s2_ohlcv()
    trades = _build_raw_trades(state, _CFG)
    equity = _compute_equity_curve(trades, ohlcv, _CFG)
    metrics = _compute_metrics(trades, equity, _CFG, ohlcv)
    return trades, equity, metrics


class TestGoldenOracleS1:
    def test_golden_s1_entries_match(self, _s1: Any) -> None:
        trades, _, _ = _s1
        assert len(trades) == 1
        t = trades[0]
        exp = S1_EXPECTED_ENTRIES[0]
        assert t.entry_bar_index == exp["entry_bar_index"]
        assert abs(t.entry_price - Decimal(str(exp["entry_price"]))) <= _TOL
        assert abs(t.size - Decimal(str(exp["size"]))) <= _TOL
        assert t.direction == exp["direction"]

    def test_golden_s1_exits_match(self, _s1: Any) -> None:
        trades, _, _ = _s1
        t = trades[0]
        exp = S1_EXPECTED_EXITS[0]
        assert t.exit_bar_index == exp["exit_bar_index"]
        assert t.exit_price is not None
        assert abs(t.exit_price - Decimal(str(exp["exit_price"]))) <= _TOL
        assert abs(t.pnl - Decimal(str(exp["pnl"]))) <= _TOL

    def test_golden_s1_equity_curve_match(self, _s1: Any) -> None:
        _, equity, _ = _s1
        assert_curve_matches(equity, S1_EXPECTED_EQUITY_VALS)

    def test_golden_s1_bh_curve_match(self, _s1: Any) -> None:
        _, _, metrics = _s1
        assert_bh_matches(metrics.buy_and_hold_curve, S1_EXPECTED_BH_VALS)


class TestGoldenOracleS2:
    def test_golden_s2_entries_match(self, _s2: Any) -> None:
        trades, _, _ = _s2
        assert len(trades) == 2
        for t, exp in zip(trades, S2_EXPECTED_ENTRIES):
            assert t.entry_bar_index == exp["entry_bar_index"]
            assert abs(t.entry_price - Decimal(str(exp["entry_price"]))) <= _TOL
            assert abs(t.size - Decimal(str(exp["size"]))) <= _TOL
            assert t.direction == exp["direction"]

    def test_golden_s2_exits_match(self, _s2: Any) -> None:
        trades, _, _ = _s2
        for t, exp in zip(trades, S2_EXPECTED_EXITS):
            assert t.exit_bar_index == exp["exit_bar_index"]
            assert t.exit_price is not None
            assert abs(t.exit_price - Decimal(str(exp["exit_price"]))) <= _TOL
            assert abs(t.pnl - Decimal(str(exp["pnl"]))) <= _TOL

    def test_golden_s2_equity_curve_match(self, _s2: Any) -> None:
        _, equity, _ = _s2
        assert_curve_matches(equity, S2_EXPECTED_EQUITY_VALS)

    def test_golden_s2_bh_curve_match(self, _s2: Any) -> None:
        _, _, metrics = _s2
        assert_bh_matches(metrics.buy_and_hold_curve, S2_EXPECTED_BH_VALS)
