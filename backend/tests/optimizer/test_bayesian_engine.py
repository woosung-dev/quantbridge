# Sprint 55 — Optimizer Bayesian engine unit tests (skopt ask-tell, mocked run_backtest).

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from skopt.space import Categorical, Integer, Real

import numpy as np

from src.optimizer.engine.bayesian import (
    _BAYESIAN_RANDOM_STATE,
    _DEGENERATE_PENALTY,
    _MAX_BAYESIAN_EVALUATIONS,
    BayesianIteration,
    _coerce_skopt_to_decimal,
    _has_normal_prior,
    _inject_normal_prior_values,
    _objective_from_metrics,
    _param_space_to_skopt_dimensions,
    _pick_best_iteration_idx,
    _y_from_objective,
    run_bayesian_search,
)
from src.optimizer.schemas import BayesianHyperparamsField, CategoricalField, ParamSpace
from src.optimizer.serializers import (
    bayesian_search_result_from_jsonb,
    bayesian_search_result_to_jsonb,
)

PINE_WITH_INPUTS = """
//@version=5
strategy("Sprint 55 Bayesian test")
emaPeriod = input.int(14, "EMA Period")
stopLossPct = input.float(1.0, "Stop Loss %")
ema = ta.ema(close, emaPeriod)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
"""


def _make_ohlcv(n: int = 100) -> pd.DataFrame:
    """tz-aware DatetimeIndex OHLCV (param_stability test mirror)."""
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(n)],
            "high": [101.0 + i * 0.1 for i in range(n)],
            "low": [99.0 + i * 0.1 for i in range(n)],
            "close": [100.5 + i * 0.1 for i in range(n)],
            "volume": [1000.0] * n,
        },
        index=idx,
    )


def _build_param_space(
    parameters: dict[str, Any],
    *,
    objective_metric: str = "sharpe_ratio",
    direction: str = "maximize",
    max_evaluations: int = 10,
    bayesian_n_initial_random: int | None = 3,
    bayesian_acquisition: str | None = "EI",
    schema_version: int = 2,
) -> ParamSpace:
    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "objective_metric": objective_metric,
        "direction": direction,
        "max_evaluations": max_evaluations,
        "parameters": parameters,
    }
    if bayesian_n_initial_random is not None:
        payload["bayesian_n_initial_random"] = bayesian_n_initial_random
    if bayesian_acquisition is not None:
        payload["bayesian_acquisition"] = bayesian_acquisition
    return ParamSpace.model_validate(payload)


def _fake_outcome(
    *,
    sharpe: Decimal | None = Decimal("1.5"),
    total_return: Decimal = Decimal("0.2"),
    max_drawdown: Decimal = Decimal("0.05"),
    num_trades: int = 5,
) -> SimpleNamespace:
    """SimpleNamespace 로 BacktestOutcome 의 status + result.metrics 만 제공."""
    metrics = SimpleNamespace(
        sharpe_ratio=sharpe,
        total_return=total_return,
        max_drawdown=max_drawdown,
        num_trades=num_trades,
    )
    result = SimpleNamespace(metrics=metrics)
    return SimpleNamespace(status="ok", result=result)


# === Section 1 — _param_space_to_skopt_dimensions ===


class TestParamSpaceToSkoptDimensions:
    def test_bayesian_uniform_prior_maps_to_real(self) -> None:
        """BayesianHyperparamsField prior=uniform → skopt Real(prior='uniform')."""
        space = _build_param_space(
            {
                "x": {
                    "kind": "bayesian",
                    "min": "1",
                    "max": "10",
                    "prior": "uniform",
                    "log_scale": False,
                }
            }
        )
        dims, names = _param_space_to_skopt_dimensions(space)
        assert names == ("x",)
        assert isinstance(dims[0], Real)
        assert dims[0].low == 1.0
        assert dims[0].high == 10.0
        assert dims[0].prior == "uniform"

    def test_bayesian_log_uniform_prior_maps_to_skopt_hyphen(self) -> None:
        """ADR-013 underscore 'log_uniform' → skopt hyphen 'log-uniform' 변환."""
        space = _build_param_space(
            {
                "x": {
                    "kind": "bayesian",
                    "min": "0.001",
                    "max": "1.0",
                    "prior": "log_uniform",
                    "log_scale": False,
                }
            }
        )
        dims, _ = _param_space_to_skopt_dimensions(space)
        assert isinstance(dims[0], Real)
        assert dims[0].prior == "log-uniform"

    def test_bayesian_normal_prior_maps_to_real_uniform_for_skopt(self) -> None:
        """Sprint 57 BL-234 — prior='normal' 은 skopt에 'uniform'으로 등록 (inject가 처리)."""
        # Sprint 55: NotImplementedError → Sprint 57: skopt Real(uniform)으로 등록
        field = BayesianHyperparamsField(
            kind="bayesian",
            min=Decimal("1"),
            max=Decimal("10"),
            prior="normal",
            log_scale=False,
        )
        space = ParamSpace(
            schema_version=2,
            objective_metric="sharpe_ratio",
            direction="maximize",
            max_evaluations=10,
            parameters={"x": field},
            bayesian_n_initial_random=3,
            bayesian_acquisition="EI",
        )
        dims, _ = _param_space_to_skopt_dimensions(space)
        assert isinstance(dims[0], Real)
        assert dims[0].prior == "uniform"  # skopt는 uniform; inject가 normal sampling

    def test_integer_field_maps_to_integer(self) -> None:
        space = _build_param_space(
            {"emaPeriod": {"kind": "integer", "min": 5, "max": 30, "step": 1}}
        )
        dims, names = _param_space_to_skopt_dimensions(space)
        assert names == ("emaPeriod",)
        assert isinstance(dims[0], Integer)
        assert dims[0].low == 5
        assert dims[0].high == 30

    def test_categorical_field_maps_to_categorical_label_transform(self) -> None:
        """ADR-013 §2.4 Sprint 55 = ordinal only ('label' transform)."""
        space = _build_param_space(
            {"mode": {"kind": "categorical", "values": ["fast", "slow"]}},
            bayesian_acquisition="EI",
        )
        dims, _ = _param_space_to_skopt_dimensions(space)
        assert isinstance(dims[0], Categorical)
        assert tuple(dims[0].categories) == ("fast", "slow")
        assert dims[0].transform_ == "label"


# === Section 2 — helpers (_coerce / _objective / _y / _pick_best) ===


class TestCoerceSkoptToDecimal:
    def test_int_and_float_to_decimal(self) -> None:
        out = _coerce_skopt_to_decimal([14, 1.5], ("emaPeriod", "stopLossPct"))
        assert out == {"emaPeriod": Decimal(14), "stopLossPct": Decimal("1.5")}


class TestObjectiveFromMetrics:
    def test_zero_trades_returns_none(self) -> None:
        metrics = SimpleNamespace(
            sharpe_ratio=Decimal("1.0"), total_return=Decimal("0"),
            max_drawdown=Decimal("0"), num_trades=0,
        )
        assert _objective_from_metrics(metrics, objective_metric="sharpe_ratio") is None

    def test_sharpe_ratio_returns_decimal(self) -> None:
        metrics = SimpleNamespace(
            sharpe_ratio=Decimal("1.85"), total_return=Decimal("0.3"),
            max_drawdown=Decimal("0.1"), num_trades=10,
        )
        assert _objective_from_metrics(metrics, objective_metric="sharpe_ratio") == Decimal("1.85")


class TestYFromObjective:
    def test_maximize_negates(self) -> None:
        assert _y_from_objective(Decimal("1.5"), direction="maximize") == -1.5

    def test_minimize_keeps_sign(self) -> None:
        assert _y_from_objective(Decimal("0.05"), direction="minimize") == 0.05

    def test_degenerate_returns_penalty(self) -> None:
        assert _y_from_objective(None, direction="maximize") == _DEGENERATE_PENALTY
        assert _y_from_objective(None, direction="minimize") == _DEGENERATE_PENALTY


class TestPickBestIterationIdx:
    def _it(self, idx: int, obj: Decimal | None) -> BayesianIteration:
        return BayesianIteration(
            idx=idx,
            params={"x": Decimal(idx)},
            objective_value=obj,
            best_so_far=obj,
            is_degenerate=obj is None,
            phase="random",
        )

    def test_maximize_picks_largest(self) -> None:
        its = (
            self._it(0, Decimal("1.0")),
            self._it(1, Decimal("2.5")),
            self._it(2, Decimal("0.5")),
        )
        assert _pick_best_iteration_idx(its, direction="maximize") == 1

    def test_minimize_picks_smallest(self) -> None:
        its = (
            self._it(0, Decimal("1.0")),
            self._it(1, Decimal("2.5")),
            self._it(2, Decimal("0.5")),
        )
        assert _pick_best_iteration_idx(its, direction="minimize") == 2

    def test_all_degenerate_returns_none(self) -> None:
        its = (self._it(0, None), self._it(1, None))
        assert _pick_best_iteration_idx(its, direction="maximize") is None


# === Section 3 — run_bayesian_search end-to-end (mocked run_backtest) ===


class TestRunBayesianSearchEndToEnd:
    def test_end_to_end_with_mocked_backtest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """5 iteration mock = sharpe=cell idx → maximize 시 last cell best."""
        call_count = {"n": 0}

        def fake_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            call_count["n"] += 1
            sharpe = Decimal(call_count["n"])  # 1, 2, 3, 4, 5
            return _fake_outcome(sharpe=sharpe)

        monkeypatch.setattr(
            "src.optimizer.engine.bayesian.run_backtest", fake_run_backtest
        )
        space = _build_param_space(
            {
                "emaPeriod": {
                    "kind": "bayesian",
                    "min": "5",
                    "max": "30",
                    "prior": "uniform",
                    "log_scale": False,
                }
            },
            max_evaluations=5,
            bayesian_n_initial_random=2,
            bayesian_acquisition="EI",
        )
        result = run_bayesian_search(
            PINE_WITH_INPUTS, _make_ohlcv(), param_space=space
        )
        assert len(result.iterations) == 5
        assert result.degenerate_count == 0
        # maximize sharpe = 1,2,3,4,5 → last iteration best.
        assert result.best_iteration_idx == 4
        assert result.best_objective_value == Decimal("5")
        # phase split — 첫 2 random, 나머지 3 acquisition.
        assert [it.phase for it in result.iterations[:2]] == ["random", "random"]
        assert [it.phase for it in result.iterations[2:]] == [
            "acquisition", "acquisition", "acquisition",
        ]

    def test_degenerate_iteration_objective_none_best_preserved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """odd iteration = degenerate (num_trades=0). best_so_far 는 even iteration 으로부터 보존."""
        call_count = {"n": 0}

        def fake_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            call_count["n"] += 1
            n = call_count["n"]
            if n % 2 == 1:  # 1, 3, 5 = degenerate
                return _fake_outcome(num_trades=0, sharpe=None)
            return _fake_outcome(sharpe=Decimal(n))  # 2, 4 = sharpe 2, 4

        monkeypatch.setattr(
            "src.optimizer.engine.bayesian.run_backtest", fake_run_backtest
        )
        space = _build_param_space(
            {
                "emaPeriod": {
                    "kind": "bayesian", "min": "5", "max": "30",
                    "prior": "uniform", "log_scale": False,
                }
            },
            max_evaluations=5, bayesian_n_initial_random=2,
        )
        result = run_bayesian_search(
            PINE_WITH_INPUTS, _make_ohlcv(), param_space=space
        )
        assert result.degenerate_count == 3
        # best = sharpe=4 at idx 3 (call n=4).
        assert result.best_iteration_idx == 3
        assert result.best_objective_value == Decimal("4")
        # iteration 0 (call n=1) degenerate → objective_value=None / is_degenerate=True.
        assert result.iterations[0].objective_value is None
        assert result.iterations[0].is_degenerate
        # iteration 0 best_so_far = None (없음). iteration 1 best_so_far = 2.
        assert result.iterations[0].best_so_far is None
        assert result.iterations[1].best_so_far == Decimal("2")

    def test_random_state_reproducibility(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """random_state=42 고정 → 동일 input 두번 실행 시 동일 best_params."""
        sharpe_log: list[list[Decimal]] = []

        def fake_run_backtest_factory() -> Any:
            cell_log: list[Decimal] = []
            sharpe_log.append(cell_log)

            def fake(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
                # sharpe = -(emaPeriod - 17.5)^2 (peaked at 17.5, max 0).
                # 첫 사용된 input_overrides emaPeriod 추출.
                ema = float(cfg.input_overrides["emaPeriod"])
                sharpe = Decimal(str(-((ema - 17.5) ** 2)))
                cell_log.append(sharpe)
                return _fake_outcome(sharpe=sharpe)

            return fake

        space = _build_param_space(
            {
                "emaPeriod": {
                    "kind": "bayesian", "min": "5", "max": "30",
                    "prior": "uniform", "log_scale": False,
                }
            },
            max_evaluations=8, bayesian_n_initial_random=3,
        )

        monkeypatch.setattr(
            "src.optimizer.engine.bayesian.run_backtest", fake_run_backtest_factory()
        )
        result1 = run_bayesian_search(
            PINE_WITH_INPUTS, _make_ohlcv(), param_space=space
        )

        monkeypatch.setattr(
            "src.optimizer.engine.bayesian.run_backtest", fake_run_backtest_factory()
        )
        result2 = run_bayesian_search(
            PINE_WITH_INPUTS, _make_ohlcv(), param_space=space
        )

        # 동일 random_state → 동일 sample sequence.
        assert _BAYESIAN_RANDOM_STATE == 42  # sanity
        assert result1.best_iteration_idx == result2.best_iteration_idx
        assert result1.best_params == result2.best_params

    def test_max_evaluations_above_cap_rejected(self) -> None:
        """ParamSpace.max_evaluations 자체는 schema 상한 X — run_bayesian_search 가 reject."""
        space = _build_param_space(
            {
                "emaPeriod": {
                    "kind": "bayesian", "min": "1", "max": "10",
                    "prior": "uniform", "log_scale": False,
                }
            },
            max_evaluations=_MAX_BAYESIAN_EVALUATIONS + 1,
        )
        with pytest.raises(ValueError, match=f"exceeds server cap {_MAX_BAYESIAN_EVALUATIONS}"):
            run_bayesian_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)

    def test_max_evaluations_at_cap_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """max_evaluations=50 정상 진행 (cap 동등)."""
        def fake(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            return _fake_outcome(sharpe=Decimal("1.0"))

        monkeypatch.setattr("src.optimizer.engine.bayesian.run_backtest", fake)
        space = _build_param_space(
            {
                "emaPeriod": {
                    "kind": "bayesian", "min": "1", "max": "10",
                    "prior": "uniform", "log_scale": False,
                }
            },
            max_evaluations=_MAX_BAYESIAN_EVALUATIONS,
            bayesian_n_initial_random=10,
        )
        # smoke — 50 iteration 실행 (mocked = ms 수준).
        result = run_bayesian_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)
        assert result.total_iterations == _MAX_BAYESIAN_EVALUATIONS


# === Section 4 — bayesian_search_result_to_jsonb / from_jsonb round-trip ===


class TestSerializerRoundTrip:
    def test_to_jsonb_and_back_preserves_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """end-to-end + round-trip — JSONB shape Sprint 50/51/52 retro-incorrect 차단 4종 검증."""
        call_count = {"n": 0}

        def fake(pine: str, ohlcv: pd.DataFrame, cfg: Any) -> SimpleNamespace:
            call_count["n"] += 1
            n = call_count["n"]
            if n == 2:  # idx 1 = degenerate
                return _fake_outcome(num_trades=0, sharpe=None)
            return _fake_outcome(sharpe=Decimal(str(n * 0.5)))

        monkeypatch.setattr("src.optimizer.engine.bayesian.run_backtest", fake)
        space = _build_param_space(
            {
                "emaPeriod": {
                    "kind": "bayesian", "min": "1", "max": "5",
                    "prior": "uniform", "log_scale": False,
                }
            },
            max_evaluations=4, bayesian_n_initial_random=2,
            bayesian_acquisition="EI",
        )
        result = run_bayesian_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=space)
        jsonb = bayesian_search_result_to_jsonb(result)

        # Sprint 55 plan §6.2 차단 4종 검증.
        # (1) Decimal → str.
        assert isinstance(jsonb["iterations"][0]["params"]["emaPeriod"], str)
        assert jsonb["iterations"][0]["objective_value"] == "0.5"
        # (2) None 보존 (degenerate idx=1).
        assert jsonb["iterations"][1]["objective_value"] is None
        assert jsonb["iterations"][1]["is_degenerate"] is True
        # (3) iteration row insertion order.
        assert [it["idx"] for it in jsonb["iterations"]] == [0, 1, 2, 3]
        # (4) best_iteration_idx 명시.
        assert "best_iteration_idx" in jsonb
        assert jsonb["best_iteration_idx"] == 3  # sharpe 가 가장 큰 iteration (n=4 → 2.0)
        # top-level kind echo (FE z.discriminatedUnion 의무).
        assert jsonb["kind"] == "bayesian"
        assert jsonb["schema_version"] == 2

        # round-trip.
        restored = bayesian_search_result_from_jsonb(jsonb)
        assert restored.best_iteration_idx == result.best_iteration_idx
        assert restored.best_objective_value == result.best_objective_value
        assert restored.iterations[1].objective_value is None
        assert restored.iterations[1].is_degenerate
        assert restored.degenerate_count == result.degenerate_count
        assert restored.bayesian_acquisition == "EI"


# === Sprint 57 BL-234 — normal prior + one_hot transform ===


class TestSlice57BayesianNormalPriorAndOneHot:
    """BL-234: Bayesian prior=normal inject sampler + CategoricalField one_hot transform."""

    # ── one_hot transform ──────────────────────────────────────────────────

    def test_categorical_onehot_transformed_size(self) -> None:
        """encoding=one_hot → skopt Categorical.transformed_size == n_categories."""
        ps = _build_param_space(
            {
                "mode": {
                    "kind": "categorical",
                    "values": ["SMA", "EMA", "WMA"],
                    "encoding": "one_hot",
                }
            },
            bayesian_n_initial_random=2,
        )
        dims, _ = _param_space_to_skopt_dimensions(ps)
        assert isinstance(dims[0], Categorical)
        assert dims[0].transformed_size == 3  # one_hot: 3 categories → 3-dim

    def test_categorical_label_transformed_size(self) -> None:
        """encoding=label (default) → transformed_size == 1 (ordinal)."""
        ps = _build_param_space(
            {"mode": {"kind": "categorical", "values": ["A", "B", "C"]}},
            bayesian_n_initial_random=2,
        )
        dims, _ = _param_space_to_skopt_dimensions(ps)
        assert isinstance(dims[0], Categorical)
        assert dims[0].transformed_size == 1

    # ── _has_normal_prior ─────────────────────────────────────────────────

    def test_has_normal_prior_true(self) -> None:
        ps = _build_param_space(
            {
                "x": {
                    "kind": "bayesian",
                    "min": "0",
                    "max": "1",
                    "prior": "normal",
                }
            },
        )
        assert _has_normal_prior(ps) is True

    def test_has_normal_prior_false_for_uniform(self) -> None:
        ps = _build_param_space(
            {
                "x": {
                    "kind": "bayesian",
                    "min": "0",
                    "max": "1",
                    "prior": "uniform",
                }
            },
        )
        assert _has_normal_prior(ps) is False

    def test_has_normal_prior_false_for_integer_field(self) -> None:
        ps = _build_param_space({"p": {"kind": "integer", "min": 1, "max": 5}})
        assert _has_normal_prior(ps) is False

    # ── _inject_normal_prior_values ────────────────────────────────────────

    def test_inject_clips_to_range(self) -> None:
        """inject 함수는 [min, max] 범위 밖 값을 clip해야 함."""
        ps = _build_param_space(
            {
                "x": {
                    "kind": "bayesian",
                    "min": "0.4",
                    "max": "0.6",
                    "prior": "normal",
                }
            },
        )
        rng = np.random.RandomState(seed=42)
        result = _inject_normal_prior_values([999.0], ["x"], ps, rng)
        assert 0.4 <= result[0] <= 0.6

    def test_inject_only_replaces_normal_prior_dims(self) -> None:
        """non-normal 차원은 skopt 값 그대로 유지."""
        ps = _build_param_space(
            {
                "normal_x": {
                    "kind": "bayesian",
                    "min": "0",
                    "max": "1",
                    "prior": "normal",
                },
                "uniform_y": {
                    "kind": "bayesian",
                    "min": "5",
                    "max": "10",
                    "prior": "uniform",
                },
            },
        )
        rng = np.random.RandomState(seed=42)
        original_uniform_val = 7.0
        result = _inject_normal_prior_values(
            [999.0, original_uniform_val], ["normal_x", "uniform_y"], ps, rng
        )
        # normal_x 는 inject → [0, 1] 범위 안
        assert 0.0 <= result[0] <= 1.0
        # uniform_y 는 원래 skopt 값 유지
        assert result[1] == original_uniform_val

    # ── run_bayesian_search with normal prior ─────────────────────────────

    def test_normal_prior_no_longer_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prior=normal → NotImplementedError 대신 정상 실행.

        PINE_WITH_INPUTS 의 stopLossPct(float) 변수명 사용.
        """
        monkeypatch.setattr(
            "src.optimizer.engine.bayesian.run_backtest",
            lambda *a, **kw: _fake_outcome(),
        )
        ps = _build_param_space(
            {
                "stopLossPct": {
                    "kind": "bayesian",
                    "min": "0.5",
                    "max": "3.0",
                    "prior": "normal",
                }
            },
            max_evaluations=3,
            bayesian_n_initial_random=2,
        )
        result = run_bayesian_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=ps)
        assert len(result.iterations) == 3

    def test_normal_prior_initial_points_in_range(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """normal prior 초기 포인트는 [min, max] clip 후 범위 내에 있어야 함."""
        monkeypatch.setattr(
            "src.optimizer.engine.bayesian.run_backtest",
            lambda *a, **kw: _fake_outcome(),
        )
        ps = _build_param_space(
            {
                "stopLossPct": {
                    "kind": "bayesian",
                    "min": "0.5",
                    "max": "5.0",
                    "prior": "normal",
                }
            },
            max_evaluations=5,
            bayesian_n_initial_random=4,
        )
        result = run_bayesian_search(PINE_WITH_INPUTS, _make_ohlcv(), param_space=ps)
        for it in result.iterations[:4]:  # random phase only
            assert Decimal("0.5") <= it.params["stopLossPct"] <= Decimal("5.0")
