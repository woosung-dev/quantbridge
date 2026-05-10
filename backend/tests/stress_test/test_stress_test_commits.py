"""Sprint 16 BL-010 — StressTest mutation commit-spy (LESSON-019 backfill).

submit_monte_carlo / submit_walk_forward 모두 _submit() 경유 → repo.commit() 호출.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backtest.models import Backtest, BacktestStatus
from src.stress_test.schemas import (
    CostAssumptionParams,
    CostAssumptionSubmitRequest,
    MonteCarloParams,
    MonteCarloSubmitRequest,
    ParamStabilityParams,
    ParamStabilitySubmitRequest,
    WalkForwardParams,
    WalkForwardSubmitRequest,
)


def _completed_backtest() -> Backtest:
    return Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
    )


def _make_service(repo, *, backtest_repo, dispatcher=None):
    from src.stress_test.service import StressTestService

    disp = dispatcher or AsyncMock()
    disp.dispatch_stress_test = lambda _: "task-id-stress-123"  # sync
    return StressTestService(
        repo=repo,
        backtest_repo=backtest_repo,
        strategy_repo=AsyncMock(),
        ohlcv_provider=AsyncMock(),
        dispatcher=disp,
    )


@pytest.mark.asyncio
async def test_submit_monte_carlo_calls_repo_commit() -> None:
    """LESSON-019 spy: submit_monte_carlo() 가 repo.commit() 호출 강제."""
    bt = _completed_backtest()

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id = AsyncMock(return_value=bt)

    repo = AsyncMock()
    repo.create = AsyncMock(return_value=None)

    svc = _make_service(repo, backtest_repo=backtest_repo)

    req = MonteCarloSubmitRequest(
        backtest_id=bt.id,
        params=MonteCarloParams(n_samples=100, seed=42),
    )
    await svc.submit_monte_carlo(req, user_id=bt.user_id)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_walk_forward_calls_repo_commit() -> None:
    """LESSON-019 spy: submit_walk_forward() 가 repo.commit() 호출 강제."""
    bt = _completed_backtest()

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id = AsyncMock(return_value=bt)

    repo = AsyncMock()
    repo.create = AsyncMock(return_value=None)

    svc = _make_service(repo, backtest_repo=backtest_repo)

    req = WalkForwardSubmitRequest(
        backtest_id=bt.id,
        params=WalkForwardParams(
            train_bars=200, test_bars=50, step_bars=50, max_folds=5
        ),
    )
    await svc.submit_walk_forward(req, user_id=bt.user_id)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_cost_assumption_sensitivity_calls_repo_commit() -> None:
    """LESSON-019 spy: submit_cost_assumption_sensitivity() 가 repo.commit() 호출 강제 (Sprint 50)."""
    bt = _completed_backtest()

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id = AsyncMock(return_value=bt)

    repo = AsyncMock()
    repo.create = AsyncMock(return_value=None)

    svc = _make_service(repo, backtest_repo=backtest_repo)

    req = CostAssumptionSubmitRequest(
        backtest_id=bt.id,
        params=CostAssumptionParams(
            param_grid={
                "fees": [Decimal("0.001")],
                "slippage": [Decimal("0.0005")],
            },
        ),
    )
    await svc.submit_cost_assumption_sensitivity(req, user_id=bt.user_id)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_param_stability_calls_repo_commit() -> None:
    """LESSON-019 spy: submit_param_stability() 가 repo.commit() 호출 강제 (Sprint 51 BL-220)."""
    bt = _completed_backtest()

    backtest_repo = AsyncMock()
    backtest_repo.get_by_id = AsyncMock(return_value=bt)

    repo = AsyncMock()
    repo.create = AsyncMock(return_value=None)

    svc = _make_service(repo, backtest_repo=backtest_repo)

    req = ParamStabilitySubmitRequest(
        backtest_id=bt.id,
        params=ParamStabilityParams(
            param_grid={
                "emaPeriod": [Decimal("10"), Decimal("20"), Decimal("30")],
                "stopLossPct": [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")],
            },
        ),
    )
    await svc.submit_param_stability(req, user_id=bt.user_id)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()
