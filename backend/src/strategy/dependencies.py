"""strategy 도메인 Depends() 조립."""
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
    repo: StrategyRepository = Depends(get_strategy_repository),
) -> StrategyService:
    return StrategyService(repo)
