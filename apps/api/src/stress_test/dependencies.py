"""stress_test Depends() 조립. service / repository 에서 Depends import 금지."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.repository import BacktestRepository
from src.common.database import get_async_session
from src.market_data.dependencies import (
    build_ohlcv_provider_for_worker,
    get_ohlcv_provider,
)
from src.market_data.providers import OHLCVProvider
from src.strategy.repository import StrategyRepository
from src.stress_test.dispatcher import (
    CeleryStressTaskDispatcher,
    NoopStressTaskDispatcher,
)
from src.stress_test.repository import StressTestRepository
from src.stress_test.service import StressTestService


async def get_stress_test_service(
    ohlcv_provider: Annotated[OHLCVProvider, Depends(get_ohlcv_provider)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> StressTestService:
    """HTTP 경로 — Celery dispatcher 주입."""
    return StressTestService(
        repo=StressTestRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=CeleryStressTaskDispatcher(),
    )


# 라우터 공용 별칭 — `get_stress_test_service` 주입을 한 줄로.
StressTestServiceDep = Annotated[StressTestService, Depends(get_stress_test_service)]


def build_stress_test_service_for_worker(
    session: AsyncSession,
) -> StressTestService:
    """Worker 경로 — Noop dispatcher + config flag 기반 provider 조립."""
    ohlcv_provider = build_ohlcv_provider_for_worker(session)

    return StressTestService(
        repo=StressTestRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=NoopStressTaskDispatcher(),
    )
