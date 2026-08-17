"""Stress test 실행은 부모 Backtest의 지원 엔진 버전만 허용한다."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.backtest.engine import PINE_V2_ENGINE_VERSION
from src.backtest.models import Backtest
from src.stress_test.exceptions import StressTestError
from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from src.stress_test.service import StressTestService


def _make_backtest(*, engine_version: str | None) -> Backtest:
    """_execute의 Monte Carlo 입력만 채운 DB 비의존 parent Backtest."""
    backtest = MagicMock(spec=Backtest)
    backtest.id = uuid4()
    backtest.engine_version = engine_version
    backtest.equity_curve = [
        ["2024-01-01T00:00:00+00:00", "10000"],
        ["2024-01-01T01:00:00+00:00", "10010"],
        ["2024-01-01T02:00:00+00:00", "10005"],
    ]
    return cast(Backtest, backtest)


def _queued_monte_carlo(*, user_id: UUID, backtest_id: UUID) -> StressTest:
    return StressTest(
        id=uuid4(),
        user_id=user_id,
        backtest_id=backtest_id,
        kind=StressTestKind.MONTE_CARLO,
        status=StressTestStatus.QUEUED,
        params={"n_samples": 50, "seed": 42},
    )


def _make_service() -> StressTestService:
    """이 테스트의 Monte Carlo 경로는 외부 repository/provider를 사용하지 않는다."""
    return StressTestService(
        repo=AsyncMock(),
        backtest_repo=AsyncMock(),
        strategy_repo=AsyncMock(),
        ohlcv_provider=MagicMock(),
        dispatcher=MagicMock(),
    )


@pytest.mark.asyncio
async def test_execute_rejects_unsupported_parent_backtest_engine() -> None:
    """비-pine_v2 parent는 executor 진입 직후 internal 식별자와 함께 거부한다."""
    user_id = uuid4()
    backtest = _make_backtest(engine_version="pine_v1")
    service = _make_service()

    with pytest.raises(StressTestError) as exc_info:
        await service._execute(
            _queued_monte_carlo(user_id=user_id, backtest_id=backtest.id), backtest
        )

    assert exc_info.value.message_public == (
        "Backtest engine version is not supported for stress testing."
    )
    assert f"backtest_id={backtest.id}" in exc_info.value.message_internal
    assert "engine_version=pine_v1" in exc_info.value.message_internal


@pytest.mark.asyncio
@pytest.mark.parametrize("engine_version", [None, PINE_V2_ENGINE_VERSION])
async def test_execute_accepts_legacy_or_pine_v2_parent_backtest_engine(
    engine_version: str | None,
) -> None:
    """legacy NULL과 현재 pine_v2 모두 guard를 지나 Monte Carlo를 실행한다."""
    user_id = uuid4()
    backtest = _make_backtest(engine_version=engine_version)
    service = _make_service()

    result = await service._execute(
        _queued_monte_carlo(user_id=user_id, backtest_id=backtest.id), backtest
    )

    assert "ci_lower_95" in result
