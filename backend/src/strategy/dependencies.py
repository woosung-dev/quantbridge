"""strategy 도메인 Depends() 조립. Sprint 4부터 BacktestRepository cross-inject."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.strategy.repository import StrategyRepository
from src.strategy.service import StrategyService


async def get_strategy_repository(
    session: AsyncSession = Depends(get_async_session),
) -> StrategyRepository:
    return StrategyRepository(session)


async def get_strategy_service(
    session: AsyncSession = Depends(get_async_session),
) -> StrategyService:
    """동일 session에 양쪽 repo 주입 (cross-repo transaction)."""
    from src.backtest.repository import BacktestRepository  # 지연 import — circular 방지

    return StrategyService(
        repo=StrategyRepository(session),
        backtest_repo=BacktestRepository(session),
    )
