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
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

logger = logging.getLogger(__name__)


# Celery prefork 워커는 매 task마다 asyncio.run() 으로 새 event loop 를 만든다.
# asyncpg connection pool 은 생성 당시 loop 에 bind 되므로 전역 engine 을 캐시하면
# 두 번째 task 부터 "got Future attached to a different loop" 가 발생하고 이후
# "another operation is in progress" 가 연쇄 실패한다 (PR #51 참조).
# 따라서 engine/sessionmaker 는 _async_fetch 내부에서 매 호출마다 새로 만들고
# try/finally 로 engine.dispose() 한다.
def create_worker_engine_and_sm() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """매 호출마다 새 engine + async_sessionmaker 튜플 반환.

    호출자는 engine 을 finally 에서 dispose 해야 한다. 테스트에서는 이 함수를
    monkeypatch 로 대체하여 공유 세션/no-op engine 을 주입 가능.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm


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
