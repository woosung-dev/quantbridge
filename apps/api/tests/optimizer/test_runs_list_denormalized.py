# 최적화 실행 조회의 백테스트 비정규화 필드를 검증하는 테스트.
from datetime import UTC, datetime
from uuid import uuid4

import pytest
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
