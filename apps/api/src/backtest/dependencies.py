"""Backtest DI 조립. Depends는 여기서만."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.dispatcher import CeleryTaskDispatcher, NoopTaskDispatcher
from src.backtest.repository import BacktestRepository
from src.backtest.service import BacktestService
from src.common.database import get_async_session
from src.core.config import settings
from src.market_data.dependencies import get_ohlcv_provider
from src.market_data.providers import OHLCVProvider
from src.market_data.repository import OHLCVRepository
from src.strategy.repository import StrategyRepository
from src.trading.repositories.funding_rate_repository import FundingRateRepository


async def get_backtest_service(
    ohlcv_provider: OHLCVProvider = Depends(get_ohlcv_provider),
    session: AsyncSession = Depends(get_async_session),
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


def build_backtest_service_for_worker(session: AsyncSession) -> BacktestService:
    """Worker _execute() 용 — NoopTaskDispatcher + config flag 기반 provider 조립.

    HTTP 경로의 get_ohlcv_provider는 FastAPI Request에 의존하므로 worker에서는
    사용 불가. 대신 config.ohlcv_provider를 직접 읽어 provider를 조립한다.
    - fixture: FixtureProvider
    - timescale: TimescaleProvider(OHLCVRepository, worker singleton CCXTProvider)
    """
    ohlcv_provider: OHLCVProvider
    if settings.ohlcv_provider == "fixture":
        from src.market_data.providers.fixture import FixtureProvider

        ohlcv_provider = FixtureProvider(root=settings.ohlcv_fixture_root)
    else:
        # ★[BL-819] `OHLCVRepository` 를 여기서 다시 import 하지 마라 — 15행에 이미 있다.
        #   함수 안 어디서든 그 이름을 바인딩하면 **함수 전체에서 지역**이 되어,
        #   fixture 갈래(이 else 를 안 타는 경로)의 63행 사용이 `UnboundLocalError` 로 죽는다.
        from src.market_data.providers.timescale import TimescaleProvider
        from src.tasks.celery_app import get_ccxt_provider_for_worker

        ohlcv_provider = TimescaleProvider(
            OHLCVRepository(session),
            get_ccxt_provider_for_worker(),
            exchange_name=settings.default_exchange,
        )

    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=ohlcv_provider,
        ohlcv_repo=OHLCVRepository(session),
        dispatcher=NoopTaskDispatcher(),
        funding_repo=FundingRateRepository(session),
    )
