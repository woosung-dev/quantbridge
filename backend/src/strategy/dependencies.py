"""strategy 도메인 Depends() 조립. Sprint 4부터 BacktestRepository cross-inject.

Sprint 13 Phase A.1.3: WebhookSecretService 도 동일 session 으로 주입 — Strategy
create 시 atomic auto-issue 를 위해 cross-repo transaction 확장.
"""

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
    """동일 session에 strategy + backtest + webhook_secret repo 주입 (cross-repo transaction)."""
    # 지연 import — circular 방지
    from src.backtest.repository import BacktestRepository
    from src.trading.dependencies import get_encryption_service
    from src.trading.repository import WebhookSecretRepository
    from src.trading.service import WebhookSecretService

    crypto = get_encryption_service()
    secret_svc = WebhookSecretService(
        repo=WebhookSecretRepository(session),
        crypto=crypto,
    )
    return StrategyService(
        repo=StrategyRepository(session),
        backtest_repo=BacktestRepository(session),
        secret_svc=secret_svc,
    )
