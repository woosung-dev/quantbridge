# StressTestService 제출 게이트 — code 전략 Backtest 거부와 그 순서를 4개 제출 경로 전부에서 잰다
"""제출 4경로가 `_load_rerunnable_backtest` 한 곳을 지난다. 그 한 줄이 빠지면 넷이 함께 열린다.

순서가 계약이다: 소유 → COMPLETED → code 정책 거부. code 전략의 미완료 Backtest 는
정책 거부가 아니라 「미완료」를 받는다. DB 없이 mock repository 로 잰다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.backtest.models import Backtest, BacktestStatus
from src.strategy.code_contract import CODE_EXECUTION_POLICIES
from src.strategy.exceptions import CodeStrategyPolicyError
from src.stress_test.exceptions import BacktestNotCompletedForStressTest
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
from src.stress_test.service import StressTestService

_Submit = Callable[[StressTestService, UUID, UUID], Awaitable[Any]]


async def _monte_carlo(service: StressTestService, backtest_id: UUID, user_id: UUID) -> Any:
    return await service.submit_monte_carlo(
        MonteCarloSubmitRequest(backtest_id=backtest_id, params=MonteCarloParams()),
        user_id=user_id,
    )


async def _walk_forward(service: StressTestService, backtest_id: UUID, user_id: UUID) -> Any:
    return await service.submit_walk_forward(
        WalkForwardSubmitRequest(
            backtest_id=backtest_id, params=WalkForwardParams(train_bars=50, test_bars=10)
        ),
        user_id=user_id,
    )


async def _cost_assumption(service: StressTestService, backtest_id: UUID, user_id: UUID) -> Any:
    return await service.submit_cost_assumption_sensitivity(
        CostAssumptionSubmitRequest(
            backtest_id=backtest_id,
            params=CostAssumptionParams(
                param_grid={"fees": [Decimal("0.001")], "slippage": [Decimal("0.0005")]}
            ),
        ),
        user_id=user_id,
    )


async def _param_stability(service: StressTestService, backtest_id: UUID, user_id: UUID) -> Any:
    return await service.submit_param_stability(
        ParamStabilitySubmitRequest(
            backtest_id=backtest_id,
            params=ParamStabilityParams(
                param_grid={
                    "emaPeriod": [Decimal("10"), Decimal("20"), Decimal("30")],
                    "stopLossPct": [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")],
                }
            ),
        ),
        user_id=user_id,
    )


_SUBMITS: list[_Submit] = [_monte_carlo, _walk_forward, _cost_assumption, _param_stability]


def _make_service(*, status: BacktestStatus, engine_version: str | None) -> StressTestService:
    bt = MagicMock(spec=Backtest)
    bt.id = uuid4()
    bt.status = status
    bt.engine_version = engine_version
    backtest_repo = AsyncMock()
    backtest_repo.get_by_id.return_value = bt
    return StressTestService(
        repo=AsyncMock(),
        backtest_repo=backtest_repo,
        strategy_repo=AsyncMock(),
        ohlcv_provider=MagicMock(),
        dispatcher=MagicMock(),
    )


def _assert_nothing_submitted(service: StressTestService) -> None:
    service.repo.create.assert_not_awaited()  # type: ignore[attr-defined]
    service.dispatcher.dispatch_stress_test.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.parametrize("submit", _SUBMITS, ids=lambda fn: fn.__name__)
@pytest.mark.parametrize("policy", CODE_EXECUTION_POLICIES)
async def test_completed_code_backtest_is_rejected_by_policy(submit: _Submit, policy: str) -> None:
    service = _make_service(status=BacktestStatus.COMPLETED, engine_version=policy)

    with pytest.raises(CodeStrategyPolicyError):
        await submit(service, uuid4(), uuid4())

    _assert_nothing_submitted(service)


@pytest.mark.parametrize("submit", _SUBMITS, ids=lambda fn: fn.__name__)
@pytest.mark.parametrize("policy", CODE_EXECUTION_POLICIES)
async def test_incomplete_code_backtest_reports_not_completed_first(
    submit: _Submit, policy: str
) -> None:
    service = _make_service(status=BacktestStatus.RUNNING, engine_version=policy)

    with pytest.raises(BacktestNotCompletedForStressTest):
        await submit(service, uuid4(), uuid4())

    _assert_nothing_submitted(service)
