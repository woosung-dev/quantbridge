"""Walk-Forward fold 개수 — rolling step + max_folds 상한."""

from __future__ import annotations

from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import SIMPLE_PINE, make_sine_ohlcv


def test_fold_count_matches_expected() -> None:
    ohlcv = make_sine_ohlcv(n_bars=500)
    result = run_walk_forward(
        SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50
    )
    # (500 - 150) / 50 + 1 = 8 folds (idx 0, 50, 100, ..., 350)
    assert len(result.folds) == (500 - 100 - 50) // 50 + 1


def test_max_folds_caps_output() -> None:
    ohlcv = make_sine_ohlcv(n_bars=2000)
    result = run_walk_forward(
        SIMPLE_PINE,
        ohlcv,
        train_bars=100,
        test_bars=50,
        step_bars=10,
        max_folds=5,
    )
    assert len(result.folds) == 5
