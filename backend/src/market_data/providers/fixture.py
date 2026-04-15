"""FixtureProvider — Sprint 4 fixture CSV 기반 OHLCV."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pandas import DatetimeIndex

from src.backtest.exceptions import OHLCVFixtureNotFound
from src.core.config import settings


class FixtureProvider:
    """data/fixtures/ohlcv/{SYMBOL}_{TIMEFRAME}.csv 기반 provider.

    Sprint 5에서 TimescaleProvider로 교체 예정.
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path(settings.ohlcv_fixture_root)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> pd.DataFrame:
        path = self.root / f"{symbol}_{timeframe}.csv"
        if not path.exists():
            raise OHLCVFixtureNotFound(
                detail=f"No fixture for {symbol} {timeframe} at {path}"
            )

        # pandas async I/O는 없으므로 동기 read (fixture 크기 작음)
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df = df.set_index("timestamp")

        # timezone 정규화: index가 tz-aware(UTC)이면 비교 대상도 UTC로 맞춤
        start = period_start
        end = period_end
        if isinstance(df.index, DatetimeIndex) and df.index.tz is not None:
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            if end.tzinfo is None:
                end = end.replace(tzinfo=UTC)

        # period 필터
        mask = (df.index >= start) & (df.index <= end)
        return df.loc[mask]
