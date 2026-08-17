# 최적화 실행 조회의 백테스트 비정규화 필드를 검증하는 테스트.
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.repository import BacktestRepository
from src.market_data.providers.fixture import FixtureProvider
from src.optimizer.dispatcher import FakeOptimizationTaskDispatcher
from src.optimizer.models import OptimizationKind, OptimizationRun, OptimizationStatus
from src.optimizer.repository import OptimizationRepository
from src.optimizer.service import OptimizerService
from src.strategy.repository import StrategyRepository
from tests.stress_test.helpers import seed_user_strategy_backtest


@pytest.mark.asyncio
async def test_list_and_get_include_denormalized_backtest_fields(
    db_session: AsyncSession,
) -> None:
    user, strategy, backtest = await seed_user_strategy_backtest(db_session)
    run = OptimizationRun(
        id=uuid4(),
        user_id=user.id,
        backtest_id=backtest.id,
        kind=OptimizationKind.GRID_SEARCH,
        status=OptimizationStatus.COMPLETED,
        param_space={
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 1,
            "parameters": {},
        },
        created_at=datetime.now(UTC),
    )
    await OptimizationRepository(db_session).create(run)
    service = OptimizerService(
        repo=OptimizationRepository(db_session),
        backtest_repo=BacktestRepository(db_session),
        strategy_repo=StrategyRepository(db_session),
        ohlcv_provider=FixtureProvider(root="/dev/null"),
        dispatcher=FakeOptimizationTaskDispatcher(),
    )

    listed = await service.list(user_id=user.id, limit=10, offset=0)
    fetched = await service.get(run.id, user_id=user.id)

    for response in (listed.items[0], fetched):
        assert response.strategy_id == strategy.id
        assert response.backtest_symbol == backtest.symbol
        assert response.backtest_timeframe == backtest.timeframe
        assert response.backtest_period_start == backtest.period_start
        assert response.backtest_period_end == backtest.period_end


# --- [BL-429] best 조합의 성과를 목록 응답에 싣는다 ---


def _grid_result_jsonb(*, best_cell_index: int | None) -> dict[str, object]:
    """완료된 grid run 의 result JSONB. cell 1 이 best 이고 cell 0 은 미끼다."""
    return {
        "schema_version": 1,
        "kind": "grid_search",
        "param_names": ["ema"],
        "param_values": {"ema": ["10", "20"]},
        "cells": [
            {
                "param_values": {"ema": "10"},
                "sharpe": "0.4",
                "total_return": "0.01",
                "max_drawdown": "-0.40",
                "num_trades": 3,
                "is_degenerate": False,
                "objective_value": "0.4",
            },
            {
                "param_values": {"ema": "20"},
                "sharpe": "1.9",
                "total_return": "0.1842",
                "max_drawdown": "-0.0731",
                "num_trades": 7,
                "is_degenerate": False,
                "objective_value": "1.9",
            },
        ],
        "objective_metric": "sharpe_ratio",
        "direction": "maximize",
        "best_cell_index": best_cell_index,
    }


async def _seed_run(
    db_session: AsyncSession,
    *,
    user_id: UUID,
    backtest_id: UUID,
    status: OptimizationStatus,
    result: dict[str, object] | None,
) -> OptimizationRun:
    run = OptimizationRun(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=OptimizationKind.GRID_SEARCH,
        status=status,
        param_space={
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 2,
            "parameters": {},
        },
        result=result,
        created_at=datetime.now(UTC),
    )
    await OptimizationRepository(db_session).create(run)
    return run


def _service(db_session: AsyncSession) -> OptimizerService:
    return OptimizerService(
        repo=OptimizationRepository(db_session),
        backtest_repo=BacktestRepository(db_session),
        strategy_repo=StrategyRepository(db_session),
        ohlcv_provider=FixtureProvider(root="/dev/null"),
        dispatcher=FakeOptimizationTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_list_carries_best_metrics_and_distinguishes_absent_from_zero(
    db_session: AsyncSession,
) -> None:
    """⑴ best 가 있는 완료 실행은 숫자를, ⑵ 없는 실행은 None 을 싣는다 (0 아님)."""
    user, _strategy, backtest = await seed_user_strategy_backtest(db_session)
    completed = await _seed_run(
        db_session,
        user_id=user.id,
        backtest_id=backtest.id,
        status=OptimizationStatus.COMPLETED,
        result=_grid_result_jsonb(best_cell_index=1),
    )
    no_best = await _seed_run(
        db_session,
        user_id=user.id,
        backtest_id=backtest.id,
        status=OptimizationStatus.COMPLETED,
        result=_grid_result_jsonb(best_cell_index=None),
    )
    running = await _seed_run(
        db_session,
        user_id=user.id,
        backtest_id=backtest.id,
        status=OptimizationStatus.RUNNING,
        result=None,
    )

    listed = await _service(db_session).list(user_id=user.id, limit=10, offset=0)
    by_id = {item.id: item for item in listed.items}

    # ⑴ best cell(index=1)의 값이다 — cell 0 의 미끼 값이 아니다.
    assert by_id[completed.id].best_total_return == Decimal("0.1842")
    assert by_id[completed.id].best_max_drawdown == Decimal("-0.0731")

    # ⑵ 값이 없는 두 실행은 None 이다. 0 이면 화면이 「손익 없음」이라 거짓말한다.
    for run_id in (no_best.id, running.id):
        assert by_id[run_id].best_total_return is None
        assert by_id[run_id].best_max_drawdown is None


@pytest.mark.asyncio
async def test_list_best_metrics_serialize_as_decimal_strings(
    db_session: AsyncSession,
) -> None:
    """FE `decimalString` 파서 parity — backtest metrics_summary 와 같은 표기다."""
    user, _strategy, backtest = await seed_user_strategy_backtest(db_session)
    await _seed_run(
        db_session,
        user_id=user.id,
        backtest_id=backtest.id,
        status=OptimizationStatus.COMPLETED,
        result=_grid_result_jsonb(best_cell_index=1),
    )

    listed = await _service(db_session).list(user_id=user.id, limit=10, offset=0)
    dumped = listed.items[0].model_dump(mode="json")

    assert dumped["best_total_return"] == "0.1842"
    assert dumped["best_max_drawdown"] == "-0.0731"


@pytest.mark.asyncio
async def test_list_best_metrics_add_no_per_row_query(db_session: AsyncSession) -> None:
    """★AC-3 — 목록 한 줄마다 왕복이 생기면 [BL-710] 의 규모 비용을 그대로 받는다.

    행 수를 1 → 4 로 늘려도 optimization_runs 를 치는 쿼리 수가 같아야 한다
    (count 1 + rows 1 = 2). 행 수에 비례해 늘면 N+1 이다.
    """
    user, _strategy, backtest = await seed_user_strategy_backtest(db_session)

    async def count_run_queries() -> int:
        statements: list[str] = []

        def capture(conn, cursor, statement, parameters, context, executemany) -> None:
            # ★`optimization_runs` 만 세면 **다른 테이블의 per-row 쿼리를 통째로 놓친다** —
            #   행마다 `backtests`/`strategies` 를 치는 회귀가 생겨도 이 수는 2 로 남는다
            #   (codex 적대 리뷰 P2, 2026-08-17). 재려는 것은 「행 수에 비례한 왕복이 없다」이므로
            #   SELECT 전량을 센다.
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        connection = db_session.sync_session.bind
        event.listen(connection, "before_cursor_execute", capture)
        try:
            await _service(db_session).list(user_id=user.id, limit=10, offset=0)
        finally:
            event.remove(connection, "before_cursor_execute", capture)
        return len(statements)

    await _seed_run(
        db_session,
        user_id=user.id,
        backtest_id=backtest.id,
        status=OptimizationStatus.COMPLETED,
        result=_grid_result_jsonb(best_cell_index=1),
    )
    one_row = await count_run_queries()

    for _ in range(3):
        await _seed_run(
            db_session,
            user_id=user.id,
            backtest_id=backtest.id,
            status=OptimizationStatus.COMPLETED,
            result=_grid_result_jsonb(best_cell_index=1),
        )
    four_rows = await count_run_queries()

    assert one_row == 2, f"count + rows 2회여야 한다 (got {one_row})"
    assert four_rows == one_row, f"행이 늘자 쿼리도 늘었다 — N+1 (1행 {one_row} → 4행 {four_rows})"
