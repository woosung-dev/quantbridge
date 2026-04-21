"""Funding rate 수집 Celery 태스크.

Beat schedule: celery_app.py에 등록 (매 1시간).
지원 거래소: Bybit USDT Perpetual (설정 exchange_provider가 bybit_* 계열일 때).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Worker-local lazy sessionmaker (prefork-safe, D3 교훈)
# ---------------------------------------------------------------------------
_worker_engine = None
_sessionmaker_cache: async_sessionmaker[AsyncSession] | None = None


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _worker_engine, _sessionmaker_cache
    if _sessionmaker_cache is None:
        _worker_engine = create_async_engine(settings.database_url, echo=False)
        _sessionmaker_cache = async_sessionmaker(_worker_engine, expire_on_commit=False)
    return _sessionmaker_cache


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@shared_task(name="trading.fetch_funding_rates", max_retries=2)  # type: ignore[untyped-decorator]
def fetch_funding_rates_task(
    exchange_name: str = "bybit",
    symbol: str = "BTC/USDT:USDT",
    lookback_hours: int = 2,
) -> dict[str, Any]:
    """최근 lookback_hours 내 funding rate 수집 + DB 저장."""
    return asyncio.run(_async_fetch(exchange_name, symbol, lookback_hours))


async def _async_fetch(exchange_name: str, symbol: str, lookback_hours: int) -> dict[str, Any]:
    from src.trading.funding import fetch_and_store_funding_rates

    since = datetime.now(UTC) - timedelta(hours=lookback_hours)
    sm = _get_sessionmaker()
    async with sm() as session:
        inserted = await fetch_and_store_funding_rates(
            exchange_name=exchange_name,
            symbol=symbol,
            since=since,
            session=session,
        )
    return {"exchange": exchange_name, "symbol": symbol, "inserted": inserted}
