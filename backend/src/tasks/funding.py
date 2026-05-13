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


async def _async_fetch(exchange_name: str, symbol: str, lookback_hours: int) -> dict[str, Any]:
    from src.trading.funding import fetch_and_store_funding_rates

    since = datetime.now(UTC) - timedelta(hours=lookback_hours)
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            inserted = await fetch_and_store_funding_rates(
                exchange_name=exchange_name,
                symbol=symbol,
                since=since,
                session=session,
            )
        return {"exchange": exchange_name, "symbol": symbol, "inserted": inserted}
    finally:
        await engine.dispose()
