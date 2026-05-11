"""Sprint 54 — LESSON-019 commit-spy 회귀 테스트.

backend.md §3 의무: service mutation 메서드 (save/update/delete + commit) 모두
spy 회귀 1건 의무. broken bug 재발 (Sprint 6 → 13 → 15-A 패턴) 방어.

표준 reference: backend/tests/trading/test_webhook_secret_commits.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pandas as pd
import pytest

from src.backtest.models import Backtest, BacktestStatus
from src.optimizer.dispatcher import FakeOptimizationTaskDispatcher
from src.optimizer.engine import (
    BayesianIteration,
    BayesianSearchResult,
    GeneticIndividual,
    GeneticSearchResult,
    GridSearchCell,
    GridSearchResult,
)
from src.optimizer.exceptions import (
    OptimizationExecutionError,
    OptimizationTaskDispatchError,
)
from src.optimizer.models import (
    OptimizationKind,
    OptimizationRun,
    OptimizationStatus,
)
from src.optimizer.schemas import (
    CreateOptimizationRunRequest,
    OptimizationKindOut,
    ParamSpace,
)
from src.optimizer.service import OptimizerService


def _make_param_space() -> ParamSpace:
    return ParamSpace.model_validate(
        {
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 4,
            "parameters": {
                "ema": {"kind": "integer", "min": 10, "max": 20, "step": 10},
                "stop": {"kind": "decimal", "min": "0.5", "max": "1.0", "step": "0.5"},
            },
        }
    )


def _make_backtest_row(
    *,
    user_id: UUID,
    status: BacktestStatus = BacktestStatus.COMPLETED,
) -> Backtest:
    """test fixture row — Backtest 필수 필드 최소 채움."""
    bt = MagicMock(spec=Backtest)
    bt.id = uuid4()
    bt.user_id = user_id
    bt.status = status
    bt.strategy_id = uuid4()
    bt.symbol = "BTCUSDT"
    bt.timeframe = "1h"
    bt.period_start = datetime(2024, 1, 1, tzinfo=UTC)
    bt.period_end = datetime(2024, 6, 1, tzinfo=UTC)
    bt.equity_curve = []
    return bt  # type: ignore[no-any-return]


def _make_optimization_run(
    *,
    user_id: UUID,
    backtest_id: UUID,
    status: OptimizationStatus = OptimizationStatus.QUEUED,
) -> OptimizationRun:
    return OptimizationRun(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=OptimizationKind.GRID_SEARCH,
        status=status,
        param_space=_make_param_space().model_dump(mode="json"),
    )


def _build_service(
    *,
    repo: AsyncMock,
    backtest_repo: AsyncMock,
    strategy_repo: AsyncMock,
    ohlcv_provider: AsyncMock,
    dispatcher: Any,
) -> OptimizerService:
    return OptimizerService(
        repo=repo,
        backtest_repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=ohlcv_provider,
        dispatcher=dispatcher,
    )


# ===========================================================================
# Test 1 — submit_grid_search 가 repo.create + repo.commit 호출
# ===========================================================================


@pytest.mark.asyncio
async def test_submit_grid_search_calls_repo_commit() -> None:
    """LESSON-019: submit_grid_search → repo.create + repo.commit 호출 강제."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)

    repo = AsyncMock()
    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    provider = AsyncMock()
    dispatcher = FakeOptimizationTaskDispatcher()

    svc = _build_service(
        repo=repo,
        backtest_repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=dispatcher,
    )

    req = CreateOptimizationRunRequest(
        backtest_id=bt.id,
        kind=OptimizationKindOut.GRID_SEARCH,
        param_space=_make_param_space(),
    )
    await svc.submit_grid_search(req, user_id=user_id)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← broken bug 재발 방어 (LESSON-019)
    assert len(dispatcher.dispatched) == 1


# ===========================================================================
# Test 2 — dispatcher raise → repo.rollback 호출 + commit 호출 안 함
# ===========================================================================


@pytest.mark.asyncio
async def test_submit_grid_search_dispatcher_raise_rolls_back() -> None:
    """LESSON-019: dispatch 실패 → repo.rollback + commit 호출 X (StressTest 패턴 mirror)."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)

    repo = AsyncMock()
    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    provider = AsyncMock()

    raising_dispatcher = MagicMock()
    raising_dispatcher.dispatch_optimization.side_effect = RuntimeError(
        "broker connection error"
    )

    svc = _build_service(
        repo=repo,
        backtest_repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=raising_dispatcher,
    )

    req = CreateOptimizationRunRequest(
        backtest_id=bt.id,
        kind=OptimizationKindOut.GRID_SEARCH,
        param_space=_make_param_space(),
    )

    with pytest.raises(OptimizationTaskDispatchError):
        await svc.submit_grid_search(req, user_id=user_id)

    repo.create.assert_awaited_once()
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_called()  # ← dispatch fail 후 commit 금지


# ===========================================================================
# Test 3 — Worker run() complete 분기 → repo.complete + repo.commit
# ===========================================================================


@pytest.mark.asyncio
async def test_run_complete_calls_repo_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """LESSON-019: run() complete 분기 → repo.complete + repo.commit 호출."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)
    run = _make_optimization_run(user_id=user_id, backtest_id=bt.id)

    repo = AsyncMock()
    repo.get_by_id.return_value = run
    repo.transition_to_running.return_value = 1
    repo.complete.return_value = 1

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_mock = MagicMock(pine_source="// fake pine")
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = strategy_mock
    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()

    # engine.run_grid_search 를 monkeypatch — 실제 backtest 미실행.
    fake_result = GridSearchResult(
        param_names=("ema", "stop"),
        param_values={
            "ema": (Decimal(10), Decimal(20)),
            "stop": (Decimal("0.5"), Decimal("1.0")),
        },
        cells=(
            GridSearchCell(
                param_values={"ema": Decimal(10), "stop": Decimal("0.5")},
                sharpe=Decimal("1.5"),
                total_return=Decimal("0.1"),
                max_drawdown=Decimal("-0.05"),
                num_trades=5,
                is_degenerate=False,
                objective_value=Decimal("1.5"),
            ),
        ),
        objective_metric="sharpe_ratio",
        direction="maximize",
        best_cell_index=0,
    )

    def _fake_run_grid_search(*args: Any, **kwargs: Any) -> GridSearchResult:
        return fake_result

    monkeypatch.setattr(
        "src.optimizer.service.run_grid_search", _fake_run_grid_search
    )
    # build_engine_config_from_db — Backtest mock 으로부터 호출됨. monkeypatch.
    monkeypatch.setattr(
        "src.optimizer.service.build_engine_config_from_db",
        lambda _bt: None,  # backtest_config None 도 executor 허용.
    )

    svc = _build_service(
        repo=repo,
        backtest_repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=FakeOptimizationTaskDispatcher(),
    )

    await svc.run(run.id)

    # transition → commit + complete → commit (2회 commit) — Service 명시 patterns.
    assert repo.commit.await_count == 2
    repo.transition_to_running.assert_awaited_once()
    repo.complete.assert_awaited_once()
    repo.fail.assert_not_called()


# ===========================================================================
# Test 4 — Worker run() execution failure → repo.fail + repo.commit
# ===========================================================================


@pytest.mark.asyncio
async def test_run_fail_calls_repo_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """LESSON-019: run() 실행 실패 → repo.fail + repo.commit (error truncate 적용)."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)
    run = _make_optimization_run(user_id=user_id, backtest_id=bt.id)

    repo = AsyncMock()
    repo.get_by_id.return_value = run
    repo.transition_to_running.return_value = 1
    repo.fail.return_value = 1

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_mock = MagicMock(pine_source="// fake pine")
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = strategy_mock
    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()

    def _failing_executor(*args: Any, **kwargs: Any) -> GridSearchResult:
        raise OptimizationExecutionError(
            message_public="cell exec failed",
            message_internal="long internal stack" * 100,
        )

    monkeypatch.setattr(
        "src.optimizer.service.run_grid_search", _failing_executor
    )
    monkeypatch.setattr(
        "src.optimizer.service.build_engine_config_from_db", lambda _bt: None
    )

    svc = _build_service(
        repo=repo,
        backtest_repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=FakeOptimizationTaskDispatcher(),
    )

    await svc.run(run.id)

    repo.fail.assert_awaited_once()
    # transition → commit + fail → commit (2회 commit).
    assert repo.commit.await_count == 2
    repo.complete.assert_not_called()

    # BL-230 truncation 검증 — fail 호출 시 error_message 길이 상한 적용.
    call_kwargs = repo.fail.await_args.kwargs
    assert "error_message" in call_kwargs
    from src.optimizer.exceptions import MAX_ERROR_MESSAGE_LEN
    assert len(call_kwargs["error_message"]) <= MAX_ERROR_MESSAGE_LEN


# ===========================================================================
# Sprint 55 — Bayesian commit-spy (4건 신규, ADR-013 §6 #5 + LESSON-019)
# ===========================================================================


def _make_bayesian_param_space() -> ParamSpace:
    return ParamSpace.model_validate(
        {
            "schema_version": 2,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 5,
            "parameters": {
                "ema": {
                    "kind": "bayesian", "min": "5", "max": "30",
                    "prior": "uniform", "log_scale": False,
                },
            },
            "bayesian_n_initial_random": 2,
            "bayesian_acquisition": "EI",
        }
    )


def _make_optimization_run_bayesian(
    *,
    user_id: UUID,
    backtest_id: UUID,
    status: OptimizationStatus = OptimizationStatus.QUEUED,
) -> OptimizationRun:
    return OptimizationRun(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=OptimizationKind.BAYESIAN,
        status=status,
        param_space=_make_bayesian_param_space().model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_submit_bayesian_calls_repo_commit() -> None:
    """LESSON-019: submit_bayesian → repo.create + repo.commit 호출 강제."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)

    repo = AsyncMock()
    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    provider = AsyncMock()
    dispatcher = FakeOptimizationTaskDispatcher()

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=dispatcher,
    )
    req = CreateOptimizationRunRequest(
        backtest_id=bt.id,
        kind=OptimizationKindOut.BAYESIAN,
        param_space=_make_bayesian_param_space(),
    )
    await svc.submit_bayesian(req, user_id=user_id)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()
    assert len(dispatcher.dispatched) == 1


@pytest.mark.asyncio
async def test_submit_bayesian_dispatcher_raise_rolls_back() -> None:
    """LESSON-019: bayesian dispatch 실패 → repo.rollback + commit X."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)

    repo = AsyncMock()
    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    provider = AsyncMock()
    raising = MagicMock()
    raising.dispatch_optimization.side_effect = RuntimeError("broker fail")

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=raising,
    )
    req = CreateOptimizationRunRequest(
        backtest_id=bt.id,
        kind=OptimizationKindOut.BAYESIAN,
        param_space=_make_bayesian_param_space(),
    )
    with pytest.raises(OptimizationTaskDispatchError):
        await svc.submit_bayesian(req, user_id=user_id)

    repo.create.assert_awaited_once()
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_bayesian_complete_calls_repo_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LESSON-019: kind=BAYESIAN run() complete → repo.complete + commit×2."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)
    run = _make_optimization_run_bayesian(user_id=user_id, backtest_id=bt.id)

    repo = AsyncMock()
    repo.get_by_id.return_value = run
    repo.transition_to_running.return_value = 1
    repo.complete.return_value = 1

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = MagicMock(pine_source="// fake")
    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()

    fake_result = BayesianSearchResult(
        param_names=("ema",),
        iterations=(
            BayesianIteration(
                idx=0, params={"ema": Decimal("14")},
                objective_value=Decimal("1.5"), best_so_far=Decimal("1.5"),
                is_degenerate=False, phase="random",
            ),
        ),
        best_params={"ema": Decimal("14")},
        best_objective_value=Decimal("1.5"),
        best_iteration_idx=0,
        objective_metric="sharpe_ratio", direction="maximize",
        bayesian_acquisition="EI", bayesian_n_initial_random=2,
        max_evaluations=5, degenerate_count=0, total_iterations=1,
    )
    monkeypatch.setattr(
        "src.optimizer.service.run_bayesian_search",
        lambda *a, **kw: fake_result,
    )
    monkeypatch.setattr(
        "src.optimizer.service.build_engine_config_from_db", lambda _bt: None
    )

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=FakeOptimizationTaskDispatcher(),
    )
    await svc.run(run.id)

    assert repo.commit.await_count == 2
    repo.transition_to_running.assert_awaited_once()
    repo.complete.assert_awaited_once()
    repo.fail.assert_not_called()
    # _execute_bayesian 가 result_jsonb 에 kind="bayesian" echo 했는지 검증.
    complete_kwargs = repo.complete.await_args.kwargs
    assert complete_kwargs["result"]["kind"] == "bayesian"
    assert complete_kwargs["result"]["schema_version"] == 2
    assert complete_kwargs["result"]["best_iteration_idx"] == 0


@pytest.mark.asyncio
async def test_run_bayesian_fail_calls_repo_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LESSON-019: kind=BAYESIAN run() 실패 → repo.fail + truncate."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)
    run = _make_optimization_run_bayesian(user_id=user_id, backtest_id=bt.id)

    repo = AsyncMock()
    repo.get_by_id.return_value = run
    repo.transition_to_running.return_value = 1
    repo.fail.return_value = 1

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = MagicMock(pine_source="// fake")
    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()

    def _failing_executor(*args: Any, **kwargs: Any) -> BayesianSearchResult:
        raise OptimizationExecutionError(
            message_public="bayesian iteration failed",
            message_internal="long bayesian internal stack" * 100,
        )

    monkeypatch.setattr(
        "src.optimizer.service.run_bayesian_search", _failing_executor
    )
    monkeypatch.setattr(
        "src.optimizer.service.build_engine_config_from_db", lambda _bt: None
    )

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=FakeOptimizationTaskDispatcher(),
    )
    await svc.run(run.id)

    repo.fail.assert_awaited_once()
    assert repo.commit.await_count == 2
    repo.complete.assert_not_called()

    call_kwargs = repo.fail.await_args.kwargs
    assert "error_message" in call_kwargs
    from src.optimizer.exceptions import MAX_ERROR_MESSAGE_LEN
    assert len(call_kwargs["error_message"]) <= MAX_ERROR_MESSAGE_LEN


# ===========================================================================
# Sprint 56 — Genetic commit-spy (4건 신규, BL-233 + LESSON-019 7차)
# ===========================================================================


def _make_genetic_param_space() -> ParamSpace:
    return ParamSpace.model_validate(
        {
            "schema_version": 2,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 12,
            "parameters": {
                "ema": {"kind": "integer", "min": 5, "max": 30, "step": 1},
            },
            "population_size": 4,
            "n_generations": 2,
            "mutation_rate": "0.2",
            "crossover_rate": "0.8",
        }
    )


def _make_optimization_run_genetic(
    *,
    user_id: UUID,
    backtest_id: UUID,
    status: OptimizationStatus = OptimizationStatus.QUEUED,
) -> OptimizationRun:
    return OptimizationRun(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=OptimizationKind.GENETIC,
        status=status,
        param_space=_make_genetic_param_space().model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_submit_genetic_calls_repo_commit() -> None:
    """LESSON-019 (Sprint 56 BL-233): submit_genetic → repo.create + repo.commit 강제."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)

    repo = AsyncMock()
    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    provider = AsyncMock()
    dispatcher = FakeOptimizationTaskDispatcher()

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=dispatcher,
    )
    req = CreateOptimizationRunRequest(
        backtest_id=bt.id,
        kind=OptimizationKindOut.GENETIC,
        param_space=_make_genetic_param_space(),
    )
    await svc.submit_genetic(req, user_id=user_id)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()
    assert len(dispatcher.dispatched) == 1


@pytest.mark.asyncio
async def test_submit_genetic_dispatcher_raise_rolls_back() -> None:
    """LESSON-019: genetic dispatch 실패 → repo.rollback + commit X."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)

    repo = AsyncMock()
    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    provider = AsyncMock()
    raising = MagicMock()
    raising.dispatch_optimization.side_effect = RuntimeError("broker fail")

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=raising,
    )
    req = CreateOptimizationRunRequest(
        backtest_id=bt.id,
        kind=OptimizationKindOut.GENETIC,
        param_space=_make_genetic_param_space(),
    )
    with pytest.raises(OptimizationTaskDispatchError):
        await svc.submit_genetic(req, user_id=user_id)

    repo.create.assert_awaited_once()
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_genetic_complete_calls_repo_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LESSON-019: kind=GENETIC run() complete → repo.complete + commit×2 + JSONB shape."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)
    run = _make_optimization_run_genetic(user_id=user_id, backtest_id=bt.id)

    repo = AsyncMock()
    repo.get_by_id.return_value = run
    repo.transition_to_running.return_value = 1
    repo.complete.return_value = 1

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = MagicMock(pine_source="// fake")
    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()

    fake_result = GeneticSearchResult(
        param_names=("ema",),
        iterations=(
            GeneticIndividual(
                idx=0, params={"ema": Decimal("14")},
                objective_value=Decimal("1.5"), best_so_far=Decimal("1.5"),
                is_degenerate=False, generation=0,
            ),
        ),
        best_params={"ema": Decimal("14")},
        best_objective_value=Decimal("1.5"),
        best_iteration_idx=0,
        objective_metric="sharpe_ratio", direction="maximize",
        population_size=4, n_generations=2,
        mutation_rate=Decimal("0.2"), crossover_rate=Decimal("0.8"),
        max_evaluations=12, degenerate_count=0, total_iterations=1,
    )
    monkeypatch.setattr(
        "src.optimizer.service.run_genetic_search",
        lambda *a, **kw: fake_result,
    )
    monkeypatch.setattr(
        "src.optimizer.service.build_engine_config_from_db", lambda _bt: None
    )

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=FakeOptimizationTaskDispatcher(),
    )
    await svc.run(run.id)

    assert repo.commit.await_count == 2
    repo.transition_to_running.assert_awaited_once()
    repo.complete.assert_awaited_once()
    repo.fail.assert_not_called()
    # _execute_genetic 가 result_jsonb 에 kind="genetic" + schema_version=2 echo.
    complete_kwargs = repo.complete.await_args.kwargs
    assert complete_kwargs["result"]["kind"] == "genetic"
    assert complete_kwargs["result"]["schema_version"] == 2
    assert complete_kwargs["result"]["best_iteration_idx"] == 0
    assert complete_kwargs["result"]["population_size"] == 4


@pytest.mark.asyncio
async def test_run_genetic_fail_calls_repo_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LESSON-019: kind=GENETIC run() 실패 → repo.fail + error_message truncate."""
    user_id = uuid4()
    bt = _make_backtest_row(user_id=user_id)
    run = _make_optimization_run_genetic(user_id=user_id, backtest_id=bt.id)

    repo = AsyncMock()
    repo.get_by_id.return_value = run
    repo.transition_to_running.return_value = 1
    repo.fail.return_value = 1

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = MagicMock(pine_source="// fake")
    provider = AsyncMock()
    provider.get_ohlcv.return_value = pd.DataFrame()

    def _failing_executor(*args: Any, **kwargs: Any) -> GeneticSearchResult:
        raise OptimizationExecutionError(
            message_public="genetic generation failed",
            message_internal="long genetic internal stack" * 100,
        )

    monkeypatch.setattr(
        "src.optimizer.service.run_genetic_search", _failing_executor
    )
    monkeypatch.setattr(
        "src.optimizer.service.build_engine_config_from_db", lambda _bt: None
    )

    svc = _build_service(
        repo=repo, backtest_repo=backtest_repo, strategy_repo=strategy_repo,
        ohlcv_provider=provider, dispatcher=FakeOptimizationTaskDispatcher(),
    )
    await svc.run(run.id)

    repo.fail.assert_awaited_once()
    assert repo.commit.await_count == 2
    repo.complete.assert_not_called()

    call_kwargs = repo.fail.await_args.kwargs
    assert "error_message" in call_kwargs
    from src.optimizer.exceptions import MAX_ERROR_MESSAGE_LEN
    assert len(call_kwargs["error_message"]) <= MAX_ERROR_MESSAGE_LEN
