"""Walk-Forward Analysis — rolling IS/OOS 백테스트.

각 fold 에서 backtest.engine.run_backtest 호출 → IS/OOS 수익률 산출 → degradation ratio.
No-lookahead 는 test_start > train_end 불변으로 보장 (test 첫 bar 가 train 마지막 bar 이후).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pandas as pd

from src.backtest.engine import run_backtest  # pine_v2 기반 (v2_adapter.run_backtest_v2 alias)
from src.backtest.engine.types import BacktestConfig


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold_index: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    in_sample_return: Decimal
    out_of_sample_return: Decimal
    oos_sharpe: Decimal | None
    num_trades_oos: int


@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    folds: list[WalkForwardFold]
    aggregate_oos_return: Decimal  # OOS 평균 수익률
    degradation_ratio: Decimal  # avg(IS) / avg(OOS). >1 = OOS 악화. OOS=0 이면 Decimal("Infinity")


def run_walk_forward(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    backtest_config: BacktestConfig | None = None,
    max_folds: int = 20,
) -> WalkForwardResult:
    """Rolling walk-forward. OHLCV index 는 tz-aware DatetimeIndex 여야 한다.

    Args:
        pine_source: strategy pine 소스.
        ohlcv: `run_backtest` 와 동일 shape (open/high/low/close/volume + tz-aware index).
        train_bars: 학습 구간 바 수.
        test_bars: 검증 구간 바 수.
        step_bars: rolling step. None → test_bars (non-overlapping test).
        backtest_config: None → BacktestConfig() 기본.
        max_folds: 상한. 초과 fold 는 drop (무한 loop 가드).

    Raises:
        ValueError: train_bars / test_bars ≤ 0, step_bars ≤ 0,
                    train_bars+test_bars > len(ohlcv), 또는 IS/OOS backtest 실패.
    """
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive")
    if train_bars + test_bars > len(ohlcv):
        raise ValueError(
            f"train_bars + test_bars ({train_bars + test_bars}) "
            f"exceeds ohlcv length ({len(ohlcv)})"
        )
    step = step_bars if step_bars is not None else test_bars
    if step <= 0:
        raise ValueError("step_bars must be positive")

    cfg = backtest_config or BacktestConfig()

    folds: list[WalkForwardFold] = []
    idx = 0
    fold_index = 0
    n = len(ohlcv)
    while idx + train_bars + test_bars <= n and fold_index < max_folds:
        train_slice = ohlcv.iloc[idx : idx + train_bars]
        test_slice = ohlcv.iloc[idx + train_bars : idx + train_bars + test_bars]

        is_outcome = run_backtest(pine_source, train_slice, cfg)
        oos_outcome = run_backtest(pine_source, test_slice, cfg)

        if is_outcome.status != "ok" or is_outcome.result is None:
            raise ValueError(
                f"IS backtest failed at fold {fold_index}: status={is_outcome.status}"
            )
        if oos_outcome.status != "ok" or oos_outcome.result is None:
            raise ValueError(
                f"OOS backtest failed at fold {fold_index}: status={oos_outcome.status}"
            )

        folds.append(
            WalkForwardFold(
                fold_index=fold_index,
                train_start=train_slice.index[0].to_pydatetime(),
                train_end=train_slice.index[-1].to_pydatetime(),
                test_start=test_slice.index[0].to_pydatetime(),
                test_end=test_slice.index[-1].to_pydatetime(),
                in_sample_return=is_outcome.result.metrics.total_return,
                out_of_sample_return=oos_outcome.result.metrics.total_return,
                oos_sharpe=oos_outcome.result.metrics.sharpe_ratio,
                num_trades_oos=oos_outcome.result.metrics.num_trades,
            )
        )
        idx += step
        fold_index += 1

    if not folds:
        raise ValueError("no folds produced — check train/test/step parameters")

    # Decimal-first 합산 (Sprint 4 D8) — Decimal 끼리만 누적.
    is_sum = sum((f.in_sample_return for f in folds), start=Decimal("0"))
    oos_sum = sum((f.out_of_sample_return for f in folds), start=Decimal("0"))
    is_avg = is_sum / Decimal(len(folds))
    oos_avg = oos_sum / Decimal(len(folds))

    degradation: Decimal
    if oos_avg == 0:
        degradation = Decimal("Infinity") if is_avg != 0 else Decimal("1")
    else:
        degradation = is_avg / oos_avg

    return WalkForwardResult(
        folds=folds,
        aggregate_oos_return=oos_avg,
        degradation_ratio=degradation,
    )
