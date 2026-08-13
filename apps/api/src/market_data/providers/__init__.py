"""OHLCVProvider Protocol — backtest 도메인이 OHLCV를 조회하는 추상 경계.

Sprint 4: FixtureProvider (backend/data/fixtures/ohlcv/).
Sprint 5: TimescaleProvider 추가 예정 (TimescaleDB hypertable).
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd


class OHLCVProvider(Protocol):
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> pd.DataFrame:
        """DatetimeIndex + [open, high, low, close, volume] 컬럼 DataFrame.

        Raises:
            OHLCVFixtureNotFound (또는 Sprint 5 equivalent): 데이터 미존재.
        """
        ...
