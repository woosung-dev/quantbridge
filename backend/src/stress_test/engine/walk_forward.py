"""Walk-Forward Analysis — rolling IS/OOS 백테스트.

각 fold 에서 backtest.engine.run_backtest 호출 → IS/OOS 수익률 산출 → degradation ratio.
No-lookahead 는 test_start > train_end 불변으로 보장 (test 첫 bar 가 train 마지막 bar 이후).

`run_walk_forward` = 고정 config 전체 fold 적용(C13 fixed-param fallback).
`run_walk_forward_optimization` = fold별 train 구간에서 재최적화 → test 적용(진짜 WFO/OOS).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pandas as pd

from src.backtest.engine import run_backtest  # pine_v2 기반 (v2_adapter.run_backtest_v2 alias)
from src.backtest.engine.types import BacktestConfig, BacktestOutcome
from src.optimizer.engine._common import build_cell_config
from src.optimizer.engine.select import best_params_of, run_optimizer_by_kind
from src.optimizer.models import OptimizationKind
from src.optimizer.schemas import ParamSpace
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
    # 진짜 WFO 에서만 채움 — 해당 fold train 구간에서 재최적화된 파라미터 (Decimal→str).
    # fixed-param / plain walk-forward 경로는 None (회귀 0).
    selected_params: dict[str, str] | None = None


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
        was_truncated: max_folds 상한으로 fold 가 절단됐는가 (config 신호). degenerate
            skip 과는 분리 — `degenerate_folds_skipped` 참조. `aggregate_oos_return` 이
            전체 구간 대비 편향됐는지 소비자가 감지.
        reoptimized_per_fold: True = fold별 train 재최적화(진짜 OOS). False = 고정 파라미터.
        degenerate_folds_skipped: WFO 에서 train 구간 무거래로 재최적화 불가해 제외된 fold 수
            (strategy fragility 신호 — 전략이 해당 구간에서 거래를 못 냄). plain/fixed = 0.
    """

    folds: list[WalkForwardFold]
    aggregate_oos_return: Decimal  # OOS 평균 수익률
    degradation_ratio: Decimal  # avg(IS) / avg(OOS). >1 = OOS 악화. OOS=0 이면 Decimal("Infinity")
    valid_positive_regime: bool
    total_possible_folds: int
    was_truncated: bool
    reoptimized_per_fold: bool = False
    degenerate_folds_skipped: int = 0


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


def _prepare_walk_forward(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    step_bars: int | None,
) -> tuple[int, int]:
    """입력 검증 + pre-flight coverage + (step, total_possible_folds) 계산.

    run_walk_forward / run_walk_forward_optimization 공유 (회귀 0).

    Raises:
        ValueError: train/test ≤ 0, step ≤ 0, train+test > len(ohlcv),
                    또는 pine_source 미지원 built-in 포함.
    """
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive")
    if train_bars + test_bars > len(ohlcv):
        raise ValueError(
            f"train_bars + test_bars ({train_bars + test_bars}) exceeds ohlcv length ({len(ohlcv)})"
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
            f"See docs/reference/supported-indicators.md for the supported list."
        )

    n = len(ohlcv)
    total_possible_folds = (n - train_bars - test_bars) // step + 1
    return step, total_possible_folds


def _iter_folds(
    ohlcv: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    step: int,
    max_folds: int,
) -> Iterator[tuple[int, pd.DataFrame, pd.DataFrame]]:
    """rolling (fold_index, train_slice, test_slice) 생성. max_folds 상한 (무한 loop 가드)."""
    n = len(ohlcv)
    idx = 0
    fold_index = 0
    while idx + train_bars + test_bars <= n and fold_index < max_folds:
        train_slice = ohlcv.iloc[idx : idx + train_bars]
        test_slice = ohlcv.iloc[idx + train_bars : idx + train_bars + test_bars]
        yield fold_index, train_slice, test_slice
        idx += step
        fold_index += 1


def _build_fold(
    fold_index: int,
    train_slice: pd.DataFrame,
    test_slice: pd.DataFrame,
    is_outcome: BacktestOutcome,
    oos_outcome: BacktestOutcome,
    *,
    selected_params: dict[str, str] | None,
) -> WalkForwardFold:
    """IS/OOS outcome status 검증 + WalkForwardFold 생성 (run_walk_forward / WFO 공유)."""
    if is_outcome.status != "ok" or is_outcome.result is None:
        raise ValueError(f"IS backtest failed at fold {fold_index}: status={is_outcome.status}")
    if oos_outcome.status != "ok" or oos_outcome.result is None:
        raise ValueError(f"OOS backtest failed at fold {fold_index}: status={oos_outcome.status}")
    return WalkForwardFold(
        fold_index=fold_index,
        train_start=train_slice.index[0].to_pydatetime(),
        train_end=train_slice.index[-1].to_pydatetime(),
        test_start=test_slice.index[0].to_pydatetime(),
        test_end=test_slice.index[-1].to_pydatetime(),
        in_sample_return=is_outcome.result.metrics.total_return,
        out_of_sample_return=oos_outcome.result.metrics.total_return,
        oos_sharpe=oos_outcome.result.metrics.sharpe_ratio,
        num_trades_oos=oos_outcome.result.metrics.num_trades,
        selected_params=selected_params,
    )


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
    """Rolling walk-forward (고정 config). OHLCV index 는 tz-aware DatetimeIndex 여야 한다.

    Args:
        pine_source: strategy pine 소스.
        ohlcv: `run_backtest` 와 동일 shape (open/high/low/close/volume + tz-aware index).
        train_bars: 학습 구간 바 수.
        test_bars: 검증 구간 바 수.
        step_bars: rolling step. None → test_bars (non-overlapping test).
        backtest_config: None → BacktestConfig() 기본 (전 fold 동일 적용).
        max_folds: 상한. 초과 fold 는 drop (무한 loop 가드).

    Raises:
        ValueError: 입력 invalid / IS·OOS backtest 실패 / pine 미지원 built-in.
    """
    step, total_possible_folds = _prepare_walk_forward(
        pine_source, ohlcv, train_bars=train_bars, test_bars=test_bars, step_bars=step_bars
    )
    cfg = backtest_config or BacktestConfig()

    folds: list[WalkForwardFold] = []
    for fold_index, train_slice, test_slice in _iter_folds(
        ohlcv, train_bars=train_bars, test_bars=test_bars, step=step, max_folds=max_folds
    ):
        is_outcome = run_backtest(pine_source, train_slice, cfg)
        oos_outcome = run_backtest(pine_source, test_slice, cfg)
        folds.append(
            _build_fold(
                fold_index, train_slice, test_slice, is_outcome, oos_outcome, selected_params=None
            )
        )

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


def _optimize_fold(
    pine_source: str,
    train_slice: pd.DataFrame,
    *,
    param_space: ParamSpace,
    kind: OptimizationKind,
    backtest_config: BacktestConfig,
) -> dict[str, Decimal] | None:
    """fold train 윈도우에서만 옵티마이저 재실행 → best_params (없으면 None).

    monkeypatch seam (optimizer/service runner-name 패턴 mirror). train_slice 외 데이터
    절대 미수신 = no-lookahead 보장점.
    """
    result = run_optimizer_by_kind(
        kind, pine_source, train_slice, param_space=param_space, backtest_config=backtest_config
    )
    return best_params_of(result)


def run_walk_forward_optimization(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    param_space: ParamSpace,
    kind: OptimizationKind,
    backtest_config: BacktestConfig | None = None,
    max_folds: int = 20,
) -> WalkForwardResult:
    """진짜 Walk-Forward Optimization — fold별 train 구간에서 재최적화 후 OOS 적용.

    각 fold: (1) train_slice 에서만 옵티마이저 재실행 → fold best_params (no-lookahead),
    (2) IS = backtest(train, fold params), OOS = backtest(test, fold params).
    train 구간이 degenerate(전 cell 무거래) 인 fold 는 skip (was_truncated 로 신호).

    Args:
        param_space: 원본 옵티마이저 run 의 탐색공간 (objective/direction/parameters 포함).
        kind: 원본 옵티마이저 알고리즘 (grid/bayesian/genetic).
        backtest_config: parent backtest 비용/사이징 config (fold마다 input_overrides 만 교체).

    Raises:
        ValueError: 입력 invalid / IS·OOS backtest 실패 / pine 미지원 / 전 fold degenerate.
    """
    step, total_possible_folds = _prepare_walk_forward(
        pine_source, ohlcv, train_bars=train_bars, test_bars=test_bars, step_bars=step_bars
    )
    cfg = backtest_config or BacktestConfig()

    folds: list[WalkForwardFold] = []
    degenerate_skipped = 0
    for fold_index, train_slice, test_slice in _iter_folds(
        ohlcv, train_bars=train_bars, test_bars=test_bars, step=step, max_folds=max_folds
    ):
        best = _optimize_fold(
            pine_source, train_slice, param_space=param_space, kind=kind, backtest_config=cfg
        )
        if best is None:
            degenerate_skipped += 1  # train 구간 유효 파라미터 없음 → skip (fragility 신호).
            continue
        fold_cfg = build_cell_config(cfg, overrides=best)
        is_outcome = run_backtest(pine_source, train_slice, fold_cfg)
        oos_outcome = run_backtest(pine_source, test_slice, fold_cfg)
        folds.append(
            _build_fold(
                fold_index,
                train_slice,
                test_slice,
                is_outcome,
                oos_outcome,
                selected_params={k: str(v) for k, v in best.items()},
            )
        )

    if not folds:
        raise ValueError(
            "no folds produced — all folds degenerate or check train/test/step parameters"
        )

    oos_avg, degradation, valid_positive_regime = _compute_aggregates(folds)
    # attempted = 실행 fold + skip fold = min(total_possible, max_folds). was_truncated 는
    # max_folds 절단만 의미 (skip 은 degenerate_folds_skipped 로 분리).
    attempted = len(folds) + degenerate_skipped
    was_truncated = total_possible_folds > attempted

    return WalkForwardResult(
        folds=folds,
        aggregate_oos_return=oos_avg,
        degradation_ratio=degradation,
        valid_positive_regime=valid_positive_regime,
        total_possible_folds=total_possible_folds,
        was_truncated=was_truncated,
        reoptimized_per_fold=True,
        degenerate_folds_skipped=degenerate_skipped,
    )
