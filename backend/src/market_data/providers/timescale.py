"""TimescaleProvider — DB cache → CCXT fallback fetch + advisory lock.

실제 사용 패턴 (M3 이후):
    provider = TimescaleProvider(repo, ccxt, exchange_name=settings.default_exchange)
    df = await provider.get_ohlcv(symbol, timeframe, start, end)
    # 1) advisory lock (동시 fetch race 방지)
    # 2) gap 재조회 (lock 획득 후)
    # 3) 빈 구간만 CCXT fetch → insert_bulk
    # 4) 최종 cache get_range → pd.DataFrame
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from src.market_data.constants import TIMEFRAME_SECONDS, normalize_symbol
from src.market_data.models import OHLCV
from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.repository import OHLCVRepository


class TimescaleProvider:
    """OHLCVProvider 구현 — DB cache → CCXT fallback fetch + advisory lock."""

    def __init__(
        self,
        repo: OHLCVRepository,
        ccxt_provider: CCXTProvider,
        exchange_name: str = "bybit",
    ) -> None:
        self.repo = repo
        self.ccxt = ccxt_provider
        self.exchange_name = exchange_name

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> pd.DataFrame:
        """cache-first 조회 — gap만 CCXT로 fetch 후 캐시 저장."""
        symbol = normalize_symbol(symbol)
        tf_sec = TIMEFRAME_SECONDS[timeframe]

        # 1. advisory lock — 동시 fetch race 방지 (트랜잭션 종료 시 해제)
        await self.repo.acquire_fetch_lock(
            symbol, timeframe, period_start, period_end
        )

        # 2. lock 획득 후 gap 재조회 — 다른 트랜잭션이 이미 채웠을 수 있음
        gaps = await self.repo.find_gaps(
            symbol, timeframe, period_start, period_end, tf_sec
        )

        # 3. 빈 구간만 CCXT fetch
        for gap_start, gap_end in gaps:
            raw = await self.ccxt.fetch_ohlcv(
                symbol, timeframe, gap_start, gap_end
            )
            rows = self._to_db_rows(raw, symbol, timeframe)
            await self.repo.insert_bulk(rows)

        if gaps:
            await self.repo.commit()

        # 4. 최종 cache 조회 → DataFrame
        cached = await self.repo.get_range(
            symbol, timeframe, period_start, period_end
        )
        return self._to_dataframe(cached)

    def _to_db_rows(
        self, raw: list[list[Any]], symbol: str, timeframe: str
    ) -> list[dict[str, Any]]:
        """CCXT raw → DB row dict (Decimal 변환 + tz-aware datetime)."""
        return [
            {
                "time": datetime.fromtimestamp(b[0] / 1000, tz=UTC),
                "symbol": symbol,
                "timeframe": timeframe,
                "exchange": self.exchange_name,
                "open": b[1],
                "high": b[2],
                "low": b[3],
                "close": b[4],
                "volume": b[5],
            }
            for b in raw
        ]

    @staticmethod
    def _to_dataframe(rows: list[OHLCV]) -> pd.DataFrame:
        """OHLCV ORM rows → pandas DataFrame (time index, float 값).

        빈 rows 시에도 column 순서를 보장.
        """
        cols = ["open", "high", "low", "close", "volume"]
        if not rows:
            return pd.DataFrame(columns=cols).astype(float)
        df = pd.DataFrame(
            [
                {
                    "time": r.time,
                    "open": float(r.open),
                    "high": float(r.high),
                    "low": float(r.low),
                    "close": float(r.close),
                    "volume": float(r.volume),
                }
                for r in rows
            ]
        )
        df = df.set_index("time").sort_index()
        return df[cols]
