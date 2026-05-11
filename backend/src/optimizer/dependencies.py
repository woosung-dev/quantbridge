"""optimizer Depends() 조립. service / repository 에서 Depends import 금지.

stress_test/dependencies.py 패턴 1:1 mirror. Sprint 18 BL-080 prefork-safe worker
경로 + HTTP 경로 분리.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.repository import BacktestRepository
from src.common.database import get_async_session
from src.core.config import settings
from src.market_data.dependencies import get_ohlcv_provider
from src.market_data.providers import OHLCVProvider
from src.optimizer.dispatcher import (
    CeleryOptimizationTaskDispatcher,
    NoopOptimizationTaskDispatcher,
)
from src.optimizer.repository import OptimizationRepository
from src.optimizer.service import OptimizerService
from src.strategy.repository import StrategyRepository


async def get_optimizer_service(
    ohlcv_provider: OHLCVProvider = Depends(get_ohlcv_provider),
    session: AsyncSession = Depends(get_async_session),
) -> OptimizerService:
    """HTTP 경로 — Celery dispatcher 주입."""
    return OptimizerService(
        repo=OptimizationRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=CeleryOptimizationTaskDispatcher(),
    )


def build_optimizer_service_for_worker(
    session: AsyncSession,
) -> OptimizerService:
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

    return OptimizerService(
        repo=OptimizationRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        dispatcher=NoopOptimizationTaskDispatcher(),
    )
