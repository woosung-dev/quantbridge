# _execute_walk_forward 모드 라우팅 — WFO(재최적화) vs fixed-param vs plain (DB-free).
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pandas as pd
import pytest

from src.optimizer.models import OptimizationKind
from src.optimizer.schemas import ParamSpace
from src.stress_test import service as service_mod
from src.stress_test.engine import WalkForwardFold, WalkForwardResult
from src.stress_test.service import StressTestService
from tests.stress_test.helpers import SIMPLE_PINE


def _ps_dict() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "objective_metric": "sharpe_ratio",
        "direction": "maximize",
        "max_evaluations": 9,
        "parameters": {"emaPeriod": {"kind": "integer", "min": 5, "max": 10, "step": 5}},
    }


def _wf_result() -> WalkForwardResult:
    dt = datetime(2024, 1, 1, tzinfo=UTC)
    fold = WalkForwardFold(
        fold_index=0,
        train_start=dt,
        train_end=dt,
        test_start=dt,
        test_end=dt,
        in_sample_return=Decimal("0.1"),
        out_of_sample_return=Decimal("0.05"),
        oos_sharpe=Decimal("1.0"),
        num_trades_oos=5,
    )
    return WalkForwardResult(
        folds=[fold],
        aggregate_oos_return=Decimal("0.05"),
        degradation_ratio=Decimal("2"),
        valid_positive_regime=True,
        total_possible_folds=1,
        was_truncated=False,
    )


def _service() -> StressTestService:
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(pine_source=SIMPLE_PINE)
    )
    provider = AsyncMock()
    provider.get_ohlcv = AsyncMock(
        return_value=pd.DataFrame(
            {"open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0]},
            index=pd.date_range("2024-01-01", periods=1, freq="h", tz="UTC"),
        )
    )
    return StressTestService(
        repo=AsyncMock(),
        backtest_repo=AsyncMock(),
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=AsyncMock(),
    )


def _bt() -> SimpleNamespace:
    return SimpleNamespace(
        strategy_id=uuid4(),
        user_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
    )


def _patch_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backtest.engine.types import BacktestConfig

    monkeypatch.setattr(
        service_mod, "build_engine_config_from_db", lambda bt: BacktestConfig()
    )


@pytest.mark.asyncio
async def test_routes_to_wfo_when_optimizer_spec_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_config(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_wfo(pine, ohlcv, *, param_space, kind, backtest_config, **kw):  # type: ignore[no-untyped-def]
        captured["param_space"] = param_space
        captured["kind"] = kind
        return _wf_result()

    def fake_plain(*a, **k):  # type: ignore[no-untyped-def]
        captured["plain_called"] = True
        return _wf_result()

    monkeypatch.setattr(service_mod, "run_walk_forward_optimization", fake_wfo)
    monkeypatch.setattr(service_mod, "run_walk_forward", fake_plain)

    st = SimpleNamespace(
        params={
            "train_bars": 100,
            "test_bars": 50,
            "step_bars": 50,
            "max_folds": 20,
            "optimizer_param_space": _ps_dict(),
            "optimizer_kind": "grid_search",
        }
    )
    out = await _service()._execute_walk_forward(st, _bt())  # type: ignore[arg-type]

    assert "plain_called" not in captured  # plain WF 미호출.
    assert isinstance(captured["param_space"], ParamSpace)
    assert captured["kind"] == OptimizationKind.GRID_SEARCH
    assert out["reoptimized_per_fold"] is False  # spy 결과(_wf_result) 그대로 직렬화.
    assert "folds" in out


@pytest.mark.asyncio
async def test_routes_to_fixed_param_when_best_params_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_config(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_plain(pine, ohlcv, *, backtest_config, **kw):  # type: ignore[no-untyped-def]
        captured["input_overrides"] = backtest_config.input_overrides
        return _wf_result()

    def fake_wfo(*a, **k):  # type: ignore[no-untyped-def]
        captured["wfo_called"] = True
        return _wf_result()

    monkeypatch.setattr(service_mod, "run_walk_forward", fake_plain)
    monkeypatch.setattr(service_mod, "run_walk_forward_optimization", fake_wfo)

    st = SimpleNamespace(
        params={
            "train_bars": 100,
            "test_bars": 50,
            "step_bars": None,
            "max_folds": 20,
            "best_params": {"emaPeriod": "7"},
        }
    )
    await _service()._execute_walk_forward(st, _bt())  # type: ignore[arg-type]

    assert "wfo_called" not in captured
    assert captured["input_overrides"] == {"emaPeriod": Decimal("7")}


@pytest.mark.asyncio
async def test_routes_to_plain_when_no_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_config(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_plain(pine, ohlcv, *, backtest_config, **kw):  # type: ignore[no-untyped-def]
        captured["input_overrides"] = backtest_config.input_overrides
        return _wf_result()

    monkeypatch.setattr(service_mod, "run_walk_forward", fake_plain)

    st = SimpleNamespace(
        params={"train_bars": 100, "test_bars": 50, "step_bars": None, "max_folds": 20}
    )
    await _service()._execute_walk_forward(st, _bt())  # type: ignore[arg-type]

    assert captured["input_overrides"] is None  # 기본 config (override 없음).
