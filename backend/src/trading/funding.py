"""Funding rate 수집 유틸.

FundingRate 모델은 trading/models.py에 정의.
이 모듈은 CCXT fetch + DB 저장 한 함수를 담당.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import FundingRate

logger = logging.getLogger(__name__)


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
    logger.info(
        "funding_rates_stored",
        extra={"exchange": exchange_name, "symbol": symbol, "inserted": inserted},
    )
    return inserted
