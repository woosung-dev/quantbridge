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

from src.market_data.constants import TIMEFRAME_SECONDS, to_ccxt_perpetual_symbol
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
        """cache-first 조회 — gap만 CCXT로 fetch 후 캐시 저장.

        ★BL-535 — 인자는 canonical 시장(`BTC/USDT`)이지만 **저장 키와 거래소 fetch 는 상품**
        (`BTC/USDT:USDT`)이다. 여기가 그 경계다 (`docs/domain/instrument-symbol-boundary.md`).

        `CCXTProvider` 는 `defaultType: "spot"` 이라 canonical 을 그대로 넘기면 **스팟 봉**이
        온다. 그런데 주문은 `BybitFuturesProvider`(defaultType "linear")로 무기한선물에 나간다.
        두 상품 가격은 붙어 있지 않아(실측 스팟이 perp 보다 25~42 USDT / 0.04~0.066% 높고 한쪽으로
        치우친다) 백테스트는 스팟 고가로 스톱을 체결시키는데 라이브는 그 근처도 안 간다.
        라이브는 BL-530 이 이미 perp 로 정렬했다 — 이 함수가 백테스트·옵티마이저·스트레스
        테스트 세 소비자를 같은 축에 올린다.

        저장 키가 달라지므로 기존 스팟 행은 **건드리지 않고 그대로 남는다**(PK 에 symbol 포함,
        마이그레이션 0). 캐시가 비어 있으면 첫 조회가 곧 perp 시딩이다.
        """
        symbol = to_ccxt_perpetual_symbol(symbol)
        tf_sec = TIMEFRAME_SECONDS[timeframe]

        # 1. advisory lock — 동시 fetch race 방지 (트랜잭션 종료 시 해제)
        await self.repo.acquire_fetch_lock(symbol, timeframe, period_start, period_end)

        # 2. lock 획득 후 gap 재조회 — 다른 트랜잭션이 이미 채웠을 수 있음
        gaps = await self.repo.find_gaps(symbol, timeframe, period_start, period_end, tf_sec)

        # 3. 빈 구간만 CCXT fetch
        for gap_start, gap_end in gaps:
            raw = await self.ccxt.fetch_ohlcv(symbol, timeframe, gap_start, gap_end)
            rows = self._to_db_rows(raw, symbol, timeframe)
            await self.repo.insert_bulk(rows)

        if gaps:
            await self.repo.commit()

        # 4. 최종 cache 조회 → DataFrame
        cached = await self.repo.get_range(symbol, timeframe, period_start, period_end)
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
