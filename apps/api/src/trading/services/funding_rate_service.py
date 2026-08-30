"""Funding rate 수집 유스케이스.

CCXT 조회와 저장 경계를 함께 조립하되, ``AsyncSession`` 은 Repository 밖으로
나오지 않는다. 페이지 단위 backfill은 각 idempotent batch를 확정한 뒤 다음 외부
조회로 넘어가므로 DB 트랜잭션을 네트워크 왕복 동안 열어 두지 않는다.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, tzinfo
from decimal import Decimal
from typing import cast

from src.trading.models import ExchangeName, FundingRate
from src.trading.repositories.funding_rate_repository import FundingRateRepository

logger = logging.getLogger(__name__)


class FundingRateService:
    """Funding rate fetch/backfill의 비즈니스·트랜잭션 경계."""

    def __init__(self, repo: FundingRateRepository) -> None:
        self._repo = repo

    async def fetch_and_store(
        self,
        *,
        exchange_name: ExchangeName,
        symbol: str,
        since: datetime,
        limit: int = 100,
    ) -> int:
        """CCXT funding rate 기록을 한 batch로 멱등 저장한다."""
        exchange_name = ExchangeName(exchange_name)
        import ccxt.async_support as ccxt_async

        exchange_cls = getattr(ccxt_async, exchange_name, None)
        if exchange_cls is None:
            raise ValueError(f"Unknown CCXT exchange: {exchange_name!r}")

        exchange = exchange_cls()
        try:
            raw = await exchange.fetch_funding_rate_history(
                symbol,
                since=int(since.timestamp() * 1000),
                limit=limit,
            )
        finally:
            await exchange.close()

        rows = self._rows_from_raw(
            raw or [], exchange_name=exchange_name, symbol=symbol, tzinfo=since.tzinfo
        )
        inserted = await self._store_rows(rows)
        logger.info(
            "funding_rates_stored",
            extra={"exchange": exchange_name, "symbol": symbol, "inserted": inserted},
        )
        return inserted

    async def backfill(
        self,
        *,
        exchange_name: ExchangeName,
        symbol: str,
        start: datetime,
        end: datetime,
        page_limit: int = 200,
        max_pages: int = 200,
    ) -> int:
        """지정 기간을 페이지 단위 idempotent batch로 backfill한다."""
        exchange_name = ExchangeName(exchange_name)
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
                        exchange=exchange_name,
                        funding_rate=Decimal(str(item["fundingRate"])),
                        funding_timestamp=datetime.fromtimestamp(
                            timestamp / 1000, tz=start.tzinfo or None
                        ),
                    )
                    for item, timestamp in timestamped
                    if item.get("fundingRate") is not None and start_ms <= timestamp <= end_ms
                ]
                inserted += await self._store_rows(rows)
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

    async def _store_rows(self, rows: list[FundingRate]) -> int:
        """빈 batch는 DB를 열지 않고, 나머지는 정확히 한 번 확정한다."""
        if not rows:
            return 0
        inserted = await self._repo.upsert_many(rows)
        await self._repo.commit()
        return inserted

    @staticmethod
    def _rows_from_raw(
        raw: list[dict[str, object]],
        *,
        exchange_name: ExchangeName,
        symbol: str,
        tzinfo: tzinfo | None,
    ) -> list[FundingRate]:
        rows: list[FundingRate] = []
        for item in raw:
            funding_ts_ms = item.get("timestamp")
            rate = item.get("fundingRate")
            if funding_ts_ms is None or rate is None:
                continue
            rows.append(
                FundingRate(
                    symbol=symbol,
                    exchange=exchange_name,
                    funding_rate=Decimal(str(rate)),
                    funding_timestamp=datetime.fromtimestamp(
                        int(cast(str | int | float, funding_ts_ms)) / 1000, tz=tzinfo or None
                    ),
                )
            )
        return rows
