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
from src.strategy.pine_v2.coverage import analyze_coverage


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
    """Walk-Forward Analysis 결과.

    Fields:
        folds: 실제 실행된 fold 목록 (max_folds 로 truncate 될 수 있음).
        aggregate_oos_return: OOS 평균 수익률.
        degradation_ratio: avg(IS) / avg(OOS). Only meaningful when
            `valid_positive_regime=True`. In negative regimes the ratio sign-flips;
            consumers should show 'N/A' when `valid_positive_regime=False`.
        valid_positive_regime: IS/OOS 평균이 모두 양수인가. False 면 degradation_ratio
            는 해석 불가 (부호 반전/0 근처 불안정). UI/API 는 이 flag 로 "N/A" 표시.
        total_possible_folds: ohlcv/train/test/step 조합으로 계산 가능한 fold 총 개수
            (max_folds 적용 이전). truncation 여부 판단에 사용.
        was_truncated: max_folds 상한으로 인해 일부 fold 가 drop 된 경우 True.
            `aggregate_oos_return` 이 전체 구간 대비 편향됐는지 소비자가 감지.
    """

    folds: list[WalkForwardFold]
    aggregate_oos_return: Decimal  # OOS 평균 수익률
    degradation_ratio: Decimal  # avg(IS) / avg(OOS). >1 = OOS 악화. OOS=0 이면 Decimal("Infinity")
    valid_positive_regime: bool
    total_possible_folds: int
    was_truncated: bool


def _compute_aggregates(
    folds: list[WalkForwardFold],
) -> tuple[Decimal, Decimal, bool]:
    """Folds → (aggregate_oos_return, degradation_ratio, valid_positive_regime).

    - Decimal-first 합산 (Sprint 4 D8) — Decimal 끼리만 누적.
    - OOS=0 이면 degradation = Infinity (IS != 0) 또는 1 (IS == 0).
    - valid_positive_regime = IS_avg > 0 and OOS_avg > 0. False 일 때 ratio 해석 불가.

    Raises:
        ValueError: folds 가 비어있음.
    """
    if not folds:
        raise ValueError("folds must not be empty")

    is_sum = sum((f.in_sample_return for f in folds), start=Decimal("0"))
    oos_sum = sum((f.out_of_sample_return for f in folds), start=Decimal("0"))
    is_avg = is_sum / Decimal(len(folds))
    oos_avg = oos_sum / Decimal(len(folds))

    degradation: Decimal
    if oos_avg == 0:
        degradation = Decimal("Infinity") if is_avg != 0 else Decimal("1")
    else:
        degradation = is_avg / oos_avg

    valid_positive_regime = is_avg > 0 and oos_avg > 0
    return oos_avg, degradation, valid_positive_regime


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
                    train_bars+test_bars > len(ohlcv), IS/OOS backtest 실패,
                    또는 pine_source 에 미지원 built-in 포함 (pre-flight coverage 차단).
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

    # Sprint Y1 pre-flight coverage (BacktestService.submit 와 동일 정책):
    # run_backtest v2 경로는 unsupported 를 반환하지 않으므로 여기서 명시 차단.
    # 미지원 1개라도 있으면 WFA 전체 reject (부분 실행 금지 — Golden Rule).
    coverage = analyze_coverage(pine_source)
    if not coverage.is_runnable:
        unsupported = ", ".join(coverage.all_unsupported)
        raise ValueError(
            f"Strategy contains unsupported Pine built-ins: {unsupported}. "
            f"See docs/02_domain/supported-indicators.md for the supported list."
        )

    cfg = backtest_config or BacktestConfig()

    n = len(ohlcv)
    # 전체 가능 fold 수 (max_folds 적용 이전) — truncation 감지용.
    # idx ∈ {0, step, 2*step, ...} 중 idx + train_bars + test_bars ≤ n 인 개수.
    if train_bars + test_bars > n:
        total_possible_folds = 0
    else:
        total_possible_folds = (n - train_bars - test_bars) // step + 1

    folds: list[WalkForwardFold] = []
    idx = 0
    fold_index = 0
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

    oos_avg, degradation, valid_positive_regime = _compute_aggregates(folds)
    was_truncated = total_possible_folds > len(folds)

    return WalkForwardResult(
        folds=folds,
        aggregate_oos_return=oos_avg,
        degradation_ratio=degradation,
        valid_positive_regime=valid_positive_regime,
        total_possible_folds=total_possible_folds,
        was_truncated=was_truncated,
    )
