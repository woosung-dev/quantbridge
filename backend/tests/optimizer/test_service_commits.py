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
from src.optimizer.engine import GridSearchCell, GridSearchResult
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
