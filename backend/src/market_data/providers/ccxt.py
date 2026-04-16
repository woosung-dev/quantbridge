"""CCXTProvider — raw OHLCV fetch from exchange (pagination + tenacity 재시도)."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import ccxt.async_support as ccxt_async
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.market_data.constants import TIMEFRAME_SECONDS

logger = logging.getLogger(__name__)


class CCXTProvider:
    """CCXT raw OHLCV fetch — pagination + tenacity 재시도 + lifecycle 관리.

    TimescaleProvider가 gap 구간을 채울 때 내부 호출. FastAPI lifespan 또는
    Celery worker_shutdown에서 close()로 리소스 해제.
    """

    def __init__(self, exchange_name: str = "bybit") -> None:
        cls = getattr(ccxt_async, exchange_name)
        self.exchange = cls(
            {
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {"defaultType": "spot"},
            }
        )

    async def close(self) -> None:
        """리소스 해제 — lifespan 종료 또는 worker_shutdown에서 호출."""
        await self.exchange.close()

    @retry(
        retry=retry_if_exception_type(
            (
                ccxt_async.NetworkError,
                ccxt_async.RateLimitExceeded,
                ccxt_async.ExchangeNotAvailable,
            )
        ),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _fetch_page(
        self, symbol: str, timeframe: str, since_ms: int, limit: int
    ) -> list[list[Any]]:
        result = await self.exchange.fetch_ohlcv(
            symbol, timeframe, since=since_ms, limit=limit
        )
        return list(result)  # ccxt는 list[list[float|int]] 반환 (type stub 없음)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
        max_pages: int = 1000,
    ) -> list[list[Any]]:
        """전체 범위 fetch — pagination + 중복 제거 + closed bar 필터.

        반환: [[timestamp_ms, open, high, low, close, volume], ...]
        진행 중인 현재 bar는 제외 (last_closed_ts 기준).
        """
        tf_sec = TIMEFRAME_SECONDS[timeframe]
        now_ts = int(datetime.now(UTC).timestamp())
        last_closed_ts = (now_ts // tf_sec) * tf_sec - tf_sec
        actual_until_ms = min(
            int(until.timestamp() * 1000), last_closed_ts * 1000
        )

        since_ms = int(since.timestamp() * 1000)
        all_bars: list[list[Any]] = []
        seen_timestamps: set[int] = set()
        page_count = 0
        limit = 1000

        while since_ms <= actual_until_ms and page_count < max_pages:
            page = await self._fetch_page(symbol, timeframe, since_ms, limit)
            if not page:
                break

            new_bars = [
                b
                for b in page
                if b[0] not in seen_timestamps and b[0] <= actual_until_ms
            ]
            if not new_bars:
                break

            all_bars.extend(new_bars)
            seen_timestamps.update(b[0] for b in new_bars)

            last_ts = new_bars[-1][0]
            since_ms = last_ts + tf_sec * 1000
            page_count += 1

            # 보수적 throttle (exchange 정책 대응, 테스트에서는 mock)
            await asyncio.sleep(0.1)

        if page_count >= max_pages:
            logger.warning(
                "ccxt_fetch_max_pages_reached",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "pages": page_count,
                },
            )

        return all_bars
