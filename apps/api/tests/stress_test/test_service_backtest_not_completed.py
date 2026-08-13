"""StressTestService.submit_* — backtest.status != COMPLETED → 409."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import BacktestStatus
from src.stress_test.exceptions import BacktestNotCompletedForStressTest
from src.stress_test.schemas import (
    MonteCarloParams,
    MonteCarloSubmitRequest,
    WalkForwardParams,
    WalkForwardSubmitRequest,
)
from tests.stress_test.helpers import make_service, seed_user_strategy_backtest


@pytest.mark.asyncio
async def test_monte_carlo_rejected_when_backtest_queued(
    db_session: AsyncSession,
) -> None:
    user, _, backtest = await seed_user_strategy_backtest(
        db_session, backtest_status=BacktestStatus.QUEUED
    )
    service, _ = make_service(db_session)

    with pytest.raises(BacktestNotCompletedForStressTest):
        await service.submit_monte_carlo(
            MonteCarloSubmitRequest(
                backtest_id=backtest.id, params=MonteCarloParams()
            ),
            user_id=user.id,
        )


@pytest.mark.asyncio
async def test_walk_forward_rejected_when_backtest_running(
    db_session: AsyncSession,
) -> None:
    user, _, backtest = await seed_user_strategy_backtest(
        db_session, backtest_status=BacktestStatus.RUNNING
    )
    service, _ = make_service(db_session)

    with pytest.raises(BacktestNotCompletedForStressTest):
        await service.submit_walk_forward(
            WalkForwardSubmitRequest(
                backtest_id=backtest.id,
                params=WalkForwardParams(train_bars=50, test_bars=10),
            ),
            user_id=user.id,
        )


@pytest.mark.asyncio
async def test_monte_carlo_backtest_not_found_returns_404_equivalent(
    db_session: AsyncSession,
) -> None:
    from uuid import uuid4

    from src.backtest.exceptions import BacktestNotFound

    user, _, _ = await seed_user_strategy_backtest(db_session)
    service, _ = make_service(db_session)

    with pytest.raises(BacktestNotFound):
        await service.submit_monte_carlo(
            MonteCarloSubmitRequest(
                backtest_id=uuid4(), params=MonteCarloParams()
            ),
            user_id=user.id,
        )
