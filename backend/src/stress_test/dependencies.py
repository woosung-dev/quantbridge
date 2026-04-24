"""stress_test Depends() 조립. service / repository 에서 Depends import 금지."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.repository import BacktestRepository
from src.common.database import get_async_session
from src.core.config import settings
from src.market_data.dependencies import get_ohlcv_provider
from src.market_data.providers import OHLCVProvider
from src.strategy.repository import StrategyRepository
from src.stress_test.dispatcher import (
    CeleryStressTaskDispatcher,
    NoopStressTaskDispatcher,
)
from src.stress_test.repository import StressTestRepository
from src.stress_test.service import StressTestService


async def get_stress_test_service(
    ohlcv_provider: OHLCVProvider = Depends(get_ohlcv_provider),
    session: AsyncSession = Depends(get_async_session),
) -> StressTestService:
    """HTTP 경로 — Celery dispatcher 주입."""
    return StressTestService(
        repo=StressTestRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=CeleryStressTaskDispatcher(),
    )


def build_stress_test_service_for_worker(
    session: AsyncSession,
) -> StressTestService:
    """Worker 경로 — Noop dispatcher + config flag 기반 provider 조립."""
    ohlcv_provider: OHLCVProvider
    if settings.ohlcv_provider == "fixture":
        from src.market_data.providers.fixture import FixtureProvider

        ohlcv_provider = FixtureProvider(root=settings.ohlcv_fixture_root)
    else:
        from src.market_data.providers.timescale import TimescaleProvider
        from src.market_data.repository import OHLCVRepository
        from src.tasks.celery_app import get_ccxt_provider_for_worker

        ohlcv_provider = TimescaleProvider(
            OHLCVRepository(session),
            get_ccxt_provider_for_worker(),
            exchange_name=settings.default_exchange,
        )

    return StressTestService(
        repo=StressTestRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=NoopStressTaskDispatcher(),
    )
