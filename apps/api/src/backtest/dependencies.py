"""Backtest DI 조립. Depends는 여기서만."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.dispatcher import CeleryTaskDispatcher, NoopTaskDispatcher
from src.backtest.repository import BacktestRepository
from src.backtest.service import BacktestService
from src.common.database import get_async_session
from src.market_data.dependencies import (
    build_ohlcv_provider_for_worker,
    get_ohlcv_provider,
)
from src.market_data.providers import OHLCVProvider
from src.market_data.repository import OHLCVRepository
from src.strategy.repository import StrategyRepository
from src.trading.repositories.funding_rate_repository import FundingRateRepository


async def get_backtest_service(
    ohlcv_provider: Annotated[OHLCVProvider, Depends(get_ohlcv_provider)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> BacktestService:
    """HTTP 경로용 — CeleryTaskDispatcher + config flag 기반 OHLCVProvider 주입."""
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        ohlcv_repo=OHLCVRepository(session),
        dispatcher=CeleryTaskDispatcher(),
        funding_repo=FundingRateRepository(session),
    )


# 라우터 공용 별칭 — `get_backtest_service` 주입을 한 줄로.
BacktestServiceDep = Annotated[BacktestService, Depends(get_backtest_service)]


def build_backtest_service_for_worker(session: AsyncSession) -> BacktestService:
    """Worker _execute() 용 — NoopTaskDispatcher + config flag 기반 provider 조립.

    HTTP 경로의 get_ohlcv_provider는 FastAPI Request에 의존하므로 worker에서는
    사용 불가. provider 조립은 market_data 의 build_ohlcv_provider_for_worker 가 한다.
    """
    ohlcv_provider = build_ohlcv_provider_for_worker(session)

    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        ohlcv_repo=OHLCVRepository(session),
        dispatcher=NoopTaskDispatcher(),
        funding_repo=FundingRateRepository(session),
    )
