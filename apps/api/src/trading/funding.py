"""Funding rate 수집 유틸.

FundingRate 모델은 trading/models.py에 정의.
이 모듈은 CCXT fetch + DB 저장 한 함수를 담당.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import FundingRate

logger = logging.getLogger(__name__)


async def _store_rows(session: AsyncSession, rows: list[FundingRate]) -> int:
    """FundingRate 행을 멱등 저장하고 새로 삽입된 수를 반환한다."""
    if not rows:
        return 0

    inserted = 0
    for row in rows:
        result = await session.execute(
            text(
                "INSERT INTO trading.funding_rates "
                "(id, symbol, exchange, funding_rate, funding_timestamp, fetched_at) "
                "VALUES (:id, :symbol, :exchange, :funding_rate, :funding_timestamp, NOW()) "
                "ON CONFLICT (exchange, symbol, funding_timestamp) DO NOTHING"
            ),
            {
                "id": str(row.id),
                "symbol": row.symbol,
                "exchange": row.exchange,
                "funding_rate": str(row.funding_rate),
                "funding_timestamp": row.funding_timestamp,
            },
        )
        inserted += result.rowcount  # type: ignore[attr-defined]
    await session.commit()
    return inserted


async def fetch_and_store_funding_rates(
    *,
    exchange_name: str,
    symbol: str,
    since: datetime,
    limit: int = 100,
    session: AsyncSession,
) -> int:
    """CCXT로 funding rate 기록을 가져와 DB에 저장.

    중복 방지: (exchange, symbol, funding_timestamp) UNIQUE index.
    중복 레코드는 INSERT 시 무시(ON CONFLICT DO NOTHING).

    Returns:
        저장된 신규 레코드 수.
    """
    import ccxt.async_support as ccxt_async

    exchange_cls = getattr(ccxt_async, exchange_name, None)
    if exchange_cls is None:
        raise ValueError(f"Unknown CCXT exchange: {exchange_name!r}")

    exchange = exchange_cls()
    try:
        since_ms = int(since.timestamp() * 1000)
        raw = await exchange.fetch_funding_rate_history(symbol, since=since_ms, limit=limit)
    finally:
        await exchange.close()

    if not raw:
        return 0

    rows: list[FundingRate] = []
    for item in raw:
        funding_ts_ms = item.get("timestamp")
        rate = item.get("fundingRate")
        if funding_ts_ms is None or rate is None:
            continue
        funding_ts = datetime.fromtimestamp(funding_ts_ms / 1000, tz=since.tzinfo or None)
        rows.append(
            FundingRate(
                symbol=symbol,
                exchange=exchange_name,  # type: ignore[arg-type]
                funding_rate=Decimal(str(rate)),
                funding_timestamp=funding_ts,
            )
        )

    inserted = await _store_rows(session, rows)
    logger.info(
        "funding_rates_stored",
        extra={"exchange": exchange_name, "symbol": symbol, "inserted": inserted},
    )
    return inserted


async def backfill_funding_rate_history(
    *,
    exchange_name: str,
    symbol: str,
    start: datetime,
    end: datetime,
    session: AsyncSession,
    page_limit: int = 200,
    max_pages: int = 200,
) -> int:
    """지정 기간의 funding 이력을 페이지 단위로 멱등 backfill 한다."""
    import ccxt.async_support as ccxt_async

    exchange_cls = getattr(ccxt_async, exchange_name, None)
    if exchange_cls is None:
        raise ValueError(f"Unknown CCXT exchange: {exchange_name!r}")

    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    since_ms = start_ms
    inserted = 0
    page_count = 0
    exchange = exchange_cls()
    try:
        while since_ms <= end_ms and page_count < max_pages:
            raw = await exchange.fetch_funding_rate_history(
                symbol, since=since_ms, limit=page_limit
            )
            if not raw:
                break

            timestamped = [
                (item, timestamp)
                for item in raw
                if (timestamp := item.get("timestamp")) is not None
            ]
            if not timestamped:
                break
            last_ts = max(timestamp for _, timestamp in timestamped)
            rows = [
                FundingRate(
                    symbol=symbol,
                    exchange=exchange_name,  # type: ignore[arg-type]
                    funding_rate=Decimal(str(item["fundingRate"])),
                    funding_timestamp=datetime.fromtimestamp(
                        timestamp / 1000, tz=start.tzinfo or None
                    ),
                )
                for item, timestamp in timestamped
                if item.get("fundingRate") is not None and start_ms <= timestamp <= end_ms
            ]
            inserted += await _store_rows(session, rows)
            page_count += 1
            if last_ts >= end_ms:
                break
            since_ms = last_ts + 1
            if page_count < max_pages:
                await asyncio.sleep(0.1)
    finally:
        await exchange.close()

    if page_count >= max_pages:
        logger.warning(
            "funding_rate_backfill_max_pages_reached",
            extra={"exchange": exchange_name, "symbol": symbol, "pages": page_count},
        )
    logger.info(
        "funding_rate_history_backfilled",
        extra={"exchange": exchange_name, "symbol": symbol, "inserted": inserted},
    )
    return inserted
