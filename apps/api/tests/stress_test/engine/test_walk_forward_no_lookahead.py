"""No-lookahead 불변: test_start > train_end 모든 fold.

Walk-Forward 의 핵심 invariant — train 구간이 test 구간보다 항상 이전이어야 한다.
"""

from __future__ import annotations

from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import SIMPLE_PINE, make_sine_ohlcv


def test_test_window_after_train_window() -> None:
    ohlcv = make_sine_ohlcv(n_bars=500)
    result = run_walk_forward(
        SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50
    )
    for fold in result.folds:
        assert fold.test_start > fold.train_end, f"lookahead at fold {fold.fold_index}"


def test_no_bar_overlap_between_train_and_test() -> None:
    ohlcv = make_sine_ohlcv(n_bars=500)
    result = run_walk_forward(
        SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50
    )
    for fold in result.folds:
        # train_end 는 train 마지막 bar, test_start 는 test 첫 bar — 서로 다른 bar 여야 함.
        assert fold.train_end < fold.test_start
