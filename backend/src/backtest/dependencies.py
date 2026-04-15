"""Backtest DI 조립. Depends는 여기서만."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.dispatcher import CeleryTaskDispatcher, NoopTaskDispatcher
from src.backtest.repository import BacktestRepository
from src.backtest.service import BacktestService
from src.common.database import get_async_session
from src.market_data.providers import OHLCVProvider
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.repository import StrategyRepository


def _ohlcv_provider() -> OHLCVProvider:
    return FixtureProvider()


async def get_backtest_service(
    session: AsyncSession = Depends(get_async_session),
) -> BacktestService:
    """HTTP 경로용 — CeleryTaskDispatcher 주입."""
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=_ohlcv_provider(),
        dispatcher=CeleryTaskDispatcher(),
    )


def build_backtest_service_for_worker(session: AsyncSession) -> BacktestService:
    """Worker _execute() 용 — NoopTaskDispatcher (dispatch 호출 금지)."""
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=_ohlcv_provider(),
        dispatcher=NoopTaskDispatcher(),
    )
