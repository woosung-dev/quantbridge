"""Funding rate 수집 Celery 태스크.

Beat schedule: celery_app.py에 등록 (매 1시간).
지원 거래소: Bybit USDT Perpetual (`ExchangeAccount.exchange == bybit` AND
Order/Position 의 leverage IS NOT NULL — Sprint 22 BL-091 dispatch 기준).
Sprint 22 이전: settings.exchange_provider == "bybit_*" 기반 (deprecated).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task

from src.tasks._worker_engine import create_worker_engine_and_sm
from src.trading.models import ExchangeName

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@shared_task(name="trading.fetch_funding_rates", max_retries=2)  # type: ignore[untyped-decorator]
def fetch_funding_rates_task(
    exchange_name: str = "bybit",
    symbol: str = "BTC/USDT:USDT",
    lookback_hours: int = 2,
) -> dict[str, Any]:
    """최근 lookback_hours 내 funding rate 수집 + DB 저장.

    Sprint 18 BL-080: asyncio.run → run_in_worker_loop (Option C).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_fetch(exchange_name, symbol, lookback_hours))


@shared_task(name="trading.backfill_funding_rates")  # type: ignore[untyped-decorator]
def backfill_funding_rates_task(
    exchange_name: str,
    symbol: str,
    start_iso: str,
    end_iso: str,
) -> dict[str, Any]:
    """수동 요청한 기간의 funding rate 이력을 backfill 한다."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_backfill(exchange_name, symbol, start_iso, end_iso))


async def _async_fetch(exchange_name: str, symbol: str, lookback_hours: int) -> dict[str, Any]:
    from src.trading import funding as funding_service
    from src.trading.repositories.funding_rate_repository import FundingRateRepository

    since = datetime.now(UTC) - timedelta(hours=lookback_hours)
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            inserted = await funding_service.fetch_and_store_funding_rates(
                repo=FundingRateRepository(session),
                exchange_name=ExchangeName(exchange_name),
                symbol=symbol,
                since=since,
            )
        return {"exchange": exchange_name, "symbol": symbol, "inserted": inserted}
    finally:
        await engine.dispose()


async def _async_backfill(
    exchange_name: str, symbol: str, start_iso: str, end_iso: str
) -> dict[str, Any]:
    from src.trading import funding as funding_service
    from src.trading.repositories.funding_rate_repository import FundingRateRepository

    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            inserted = await funding_service.backfill_funding_rate_history(
                repo=FundingRateRepository(session),
                exchange_name=ExchangeName(exchange_name),
                symbol=symbol,
                start=start,
                end=end,
            )
        return {"exchange": exchange_name, "symbol": symbol, "inserted": inserted}
    finally:
        await engine.dispose()
