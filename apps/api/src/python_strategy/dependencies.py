"""Python 연구 도메인의 repository·provider·runner 조립."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.core.config import secret_value, settings
from src.market_data.dependencies import get_ohlcv_provider
from src.market_data.providers import OHLCVProvider
from src.python_strategy.repository import PythonStrategyRepository
from src.python_strategy.service import PythonStrategyService
from src.trading.repositories.funding_rate_repository import FundingRateRepository


def dispatch_python_run(run_id: str) -> None:
    from src.tasks.python_strategy import run_python_backtest_task

    run_python_backtest_task.delay(run_id)


def build_service(session: AsyncSession, provider: OHLCVProvider) -> PythonStrategyService:
    return PythonStrategyService(
        PythonStrategyRepository(session),
        provider,
        FundingRateRepository(session),
        runner_url=settings.python_runner_url,
        runner_token=secret_value(settings.python_runner_token),
        dispatch=dispatch_python_run,
    )


async def get_python_strategy_service(
    session: AsyncSession = Depends(get_async_session),
    provider: OHLCVProvider = Depends(get_ohlcv_provider),
) -> PythonStrategyService:
    return build_service(session, provider)


def build_service_for_worker(session: AsyncSession) -> PythonStrategyService:
    if settings.ohlcv_provider == "fixture":
        from src.market_data.providers.fixture import FixtureProvider

        return build_service(session, FixtureProvider(root=settings.ohlcv_fixture_root))
    from src.market_data.providers.timescale import TimescaleProvider
    from src.market_data.repository import OHLCVRepository
    from src.tasks.celery_app import get_ccxt_provider_for_worker

    return build_service(
        session,
        TimescaleProvider(
            OHLCVRepository(session),
            get_ccxt_provider_for_worker(),
            exchange_name=settings.default_exchange,
        ),
    )
