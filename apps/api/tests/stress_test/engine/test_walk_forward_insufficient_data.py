"""Walk-Forward 입력 검증 — 데이터 부족 / 음수 bar 값."""

from __future__ import annotations

import pytest

from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import SIMPLE_PINE, make_sine_ohlcv


def test_train_plus_test_exceeds_length() -> None:
    ohlcv = make_sine_ohlcv(n_bars=100)
    with pytest.raises(ValueError, match="exceeds ohlcv length"):
        run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=80, test_bars=50)


def test_non_positive_bars_raises() -> None:
    ohlcv = make_sine_ohlcv(n_bars=500)
    with pytest.raises(ValueError):
        run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=0, test_bars=50)
    with pytest.raises(ValueError):
        run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=100, test_bars=-1)


def test_non_positive_step_raises() -> None:
    ohlcv = make_sine_ohlcv(n_bars=500)
    with pytest.raises(ValueError, match="step_bars must be positive"):
        run_walk_forward(
            SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=0
        )
