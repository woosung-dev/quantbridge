# True Walk-Forward Optimization 엔진 테스트 — fold별 재최적화(진짜 OOS).
"""핵심: orchestration(fold 윈도잉 + train-only 재최적화 + test 적용)을 주입 가능한
fake optimizer(_optimize_fold seam) + fake run_backtest 로 정밀 검증(anti-circular,
엔진 자기검증 회피). 별도로 실 grid 옵티마이저 end-to-end 1건으로 실배선 확인.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from src.optimizer.models import OptimizationKind
from src.optimizer.schemas import ParamSpace
from src.stress_test.engine import walk_forward as wf_mod
from src.stress_test.engine.walk_forward import (
    run_walk_forward,
    run_walk_forward_optimization,
)
from tests.backtest.helpers import SIMPLE_PINE, make_sine_ohlcv

PINE_WITH_INPUTS = """
//@version=5
strategy("WFO test")
emaPeriod = input.int(10, "EMA Period")
ema = ta.ema(close, emaPeriod)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
if ta.crossunder(close, ema)
    strategy.close("L")
"""


def _ohlcv(n: int) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.5 + i * 0.1 for i in range(n)],
            "volume": [1000.0] * n,
        },
        index=idx,
    )


def _grid_space() -> ParamSpace:
    return ParamSpace.model_validate(
        {
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 9,
            "parameters": {"emaPeriod": {"kind": "integer", "min": 5, "max": 10, "step": 5}},
        }
    )


def _ok_outcome(total_return: str = "0.1") -> SimpleNamespace:
    return SimpleNamespace(
        status="ok",
        result=SimpleNamespace(
            metrics=SimpleNamespace(
                total_return=Decimal(total_return),
                sharpe_ratio=Decimal("1.0"),
                num_trades=5,
            )
        ),
    )


class TestOrchestration:
    """fake _optimize_fold + fake run_backtest 로 windowing/no-lookahead/적용 정밀 검증."""

    def test_optimizer_receives_train_only_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ohlcv = _ohlcv(300)
        seen_lengths: list[int] = []

        def fake_optimize(pine, train_slice, *, param_space, kind, backtest_config):  # type: ignore[no-untyped-def]
            seen_lengths.append(len(train_slice))
            return {"emaPeriod": Decimal(int(train_slice.index[0].value))}

        monkeypatch.setattr(wf_mod, "_optimize_fold", fake_optimize)
        monkeypatch.setattr(wf_mod, "run_backtest", lambda *a, **k: _ok_outcome())

        result = run_walk_forward_optimization(
            SIMPLE_PINE,
            ohlcv,
            train_bars=100,
            test_bars=50,
            step_bars=50,
            param_space=_grid_space(),
            kind=OptimizationKind.GRID_SEARCH,
        )

        # 옵티마이저는 매 fold train_bars 길이 윈도우만 받음 (test bar 미포함 = no-lookahead).
        assert seen_lengths and all(length == 100 for length in seen_lengths)
        # 기하학적 no-lookahead 불변.
        for fold in result.folds:
            assert fold.test_start > fold.train_end
        assert result.reoptimized_per_fold is True

    def test_each_fold_reoptimized_with_distinct_params(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ohlcv = _ohlcv(300)

        def fake_optimize(pine, train_slice, *, param_space, kind, backtest_config):  # type: ignore[no-untyped-def]
            # train 시작 시각에 따라 fold마다 다른 param → 재최적화 발생 증명.
            return {"emaPeriod": Decimal(int(train_slice.index[0].value))}

        monkeypatch.setattr(wf_mod, "_optimize_fold", fake_optimize)
        monkeypatch.setattr(wf_mod, "run_backtest", lambda *a, **k: _ok_outcome())

        result = run_walk_forward_optimization(
            SIMPLE_PINE,
            ohlcv,
            train_bars=100,
            test_bars=50,
            step_bars=50,
            param_space=_grid_space(),
            kind=OptimizationKind.GRID_SEARCH,
        )

        assert len(result.folds) >= 2
        selected = [f.selected_params for f in result.folds]
        assert all(s is not None for s in selected)
        # 모든 fold 의 선택 파라미터가 서로 다름 (fold별 재최적화).
        keys = {tuple(sorted(s.items())) for s in selected}  # type: ignore[union-attr]
        assert len(keys) == len(selected)

    def test_oos_backtest_uses_fold_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ohlcv = _ohlcv(250)
        fixed = {"emaPeriod": Decimal("7")}
        oos_overrides: list[dict | None] = []

        monkeypatch.setattr(
            wf_mod, "_optimize_fold", lambda *a, **k: dict(fixed)
        )

        def fake_bt(pine, slice_, cfg):  # type: ignore[no-untyped-def]
            # test slice(len 50) 백테스트의 config override 만 수집.
            if len(slice_) == 50:
                oos_overrides.append(cfg.input_overrides)
            return _ok_outcome()

        monkeypatch.setattr(wf_mod, "run_backtest", fake_bt)

        run_walk_forward_optimization(
            SIMPLE_PINE,
            ohlcv,
            train_bars=100,
            test_bars=50,
            step_bars=50,
            param_space=_grid_space(),
            kind=OptimizationKind.GRID_SEARCH,
        )

        assert oos_overrides
        # OOS 백테스트가 fold 재최적화 파라미터(Decimal)로 실행됨.
        for ov in oos_overrides:
            assert ov == {"emaPeriod": Decimal("7")}

    def test_all_degenerate_train_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ohlcv = _ohlcv(300)
        monkeypatch.setattr(wf_mod, "_optimize_fold", lambda *a, **k: None)
        monkeypatch.setattr(wf_mod, "run_backtest", lambda *a, **k: _ok_outcome())

        with pytest.raises(ValueError, match="no folds"):
            run_walk_forward_optimization(
                SIMPLE_PINE,
                ohlcv,
                train_bars=100,
                test_bars=50,
                step_bars=50,
                param_space=_grid_space(),
                kind=OptimizationKind.GRID_SEARCH,
            )

    def test_degenerate_fold_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ohlcv = _ohlcv(300)  # folds at idx 0,50,100,150 → 4 folds
        calls = {"n": 0}

        def fake_optimize(pine, train_slice, *, param_space, kind, backtest_config):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            # 2번째 fold 만 degenerate(None) → skip.
            if calls["n"] == 2:
                return None
            return {"emaPeriod": Decimal(int(train_slice.index[0].value))}

        monkeypatch.setattr(wf_mod, "_optimize_fold", fake_optimize)
        monkeypatch.setattr(wf_mod, "run_backtest", lambda *a, **k: _ok_outcome())

        result = run_walk_forward_optimization(
            SIMPLE_PINE,
            ohlcv,
            train_bars=100,
            test_bars=50,
            step_bars=50,
            param_space=_grid_space(),
            kind=OptimizationKind.GRID_SEARCH,
        )
        # 4 시도 - 1 skip = 3 fold. skip 은 degenerate_folds_skipped 로 신호 (was_truncated 와 분리).
        assert len(result.folds) == 3
        assert result.degenerate_folds_skipped == 1
        assert result.was_truncated is False  # max_folds 미도달 (4 attempted == total_possible 4).

    def test_truncation_and_skip_are_independent_signals(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ohlcv = _ohlcv(300)  # total_possible=4, but max_folds=2 → 2 attempted.
        calls = {"n": 0}

        def fake_optimize(pine, train_slice, *, param_space, kind, backtest_config):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            if calls["n"] == 2:  # 2nd attempted fold degenerate.
                return None
            return {"emaPeriod": Decimal(int(train_slice.index[0].value))}

        monkeypatch.setattr(wf_mod, "_optimize_fold", fake_optimize)
        monkeypatch.setattr(wf_mod, "run_backtest", lambda *a, **k: _ok_outcome())

        result = run_walk_forward_optimization(
            SIMPLE_PINE,
            ohlcv,
            train_bars=100,
            test_bars=50,
            step_bars=50,
            max_folds=2,
            param_space=_grid_space(),
            kind=OptimizationKind.GRID_SEARCH,
        )
        assert len(result.folds) == 1
        assert result.degenerate_folds_skipped == 1  # skip 신호.
        assert result.was_truncated is True  # total_possible 4 > attempted 2 = max_folds 절단 신호.


def test_real_grid_wfo_end_to_end() -> None:
    """실 grid 옵티마이저 + 실 pine_v2 backtest — 실배선 + 독립 오라클 검증.

    LOW-1(Evaluator gate 1): 실 경로에서도 fold별 재최적화를 독립 오라클로 증명.
    fold-0 의 selected_params == 동일 train slice(iloc[0:100])만으로 독립 실행한
    옵티마이저 best_params (no-lookahead + 올바른 윈도잉을 실 경로에서 입증).
    """
    from src.backtest.engine.types import BacktestConfig
    from src.optimizer.engine.dispatch import best_params_of
    from src.optimizer.engine.grid_search import run_grid_search

    ohlcv = make_sine_ohlcv(n_bars=300)
    ps = _grid_space()
    result = run_walk_forward_optimization(
        PINE_WITH_INPUTS,
        ohlcv,
        train_bars=100,
        test_bars=50,
        step_bars=50,
        param_space=ps,
        kind=OptimizationKind.GRID_SEARCH,
    )
    assert result.folds, "최소 1 fold 생성"
    assert result.reoptimized_per_fold is True
    for fold in result.folds:
        assert fold.selected_params is not None
        assert "emaPeriod" in fold.selected_params
        assert fold.test_start > fold.train_end
    assert isinstance(result.degradation_ratio, Decimal)

    # 독립 오라클 — fold-0(fold_index=0) train slice 만으로 옵티마이저 재실행.
    fold0 = next(f for f in result.folds if f.fold_index == 0)
    oracle_best = best_params_of(
        run_grid_search(
            PINE_WITH_INPUTS,
            ohlcv.iloc[0:100],
            param_space=ps,
            backtest_config=BacktestConfig(),
        )
    )
    assert oracle_best is not None
    assert fold0.selected_params == {k: str(v) for k, v in oracle_best.items()}


def test_plain_run_walk_forward_not_reoptimized() -> None:
    """회귀 0 — 기존 run_walk_forward 는 reoptimized_per_fold=False + selected_params=None."""
    ohlcv = make_sine_ohlcv(n_bars=300)
    result = run_walk_forward(
        SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50
    )
    assert result.reoptimized_per_fold is False
    for fold in result.folds:
        assert fold.selected_params is None
