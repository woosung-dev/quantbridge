# trading.funding_rates read 전용 — backtest perp funding 차감용 시계열 조회.
"""FundingRateRepository — funding_rates read (Slice 4 perp funding 배선).

raw-SQL 인제스션(`trading/funding.py`)만 있던 trading.funding_rates 에 read 메서드를
추가한다. backtest 엔진이 [period_start, period_end] window 의 funding 시계열을 8h
정산 경계 차감에 사용한다. read-only — commit/mutation 없음(cross-domain read).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import FundingRate


class FundingRateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_funding_series(
        self, exchange: str, symbol: str, start: datetime, end: datetime
    ) -> pd.Series:
        """[start, end] (inclusive) funding rate 시계열 — 거래소/심볼 필터 + 시각 오름차순.

        반환 = tz-aware DatetimeIndex(funding_timestamp) + Decimal value(object dtype,
        float drift 방지). 결과 없으면 빈 Series. window clip = SQL BETWEEN.
        """
        result = await self.session.execute(
            select(FundingRate)
            # exchange 컬럼은 마이그레이션 상 VARCHAR(32) 이지만 모델은 ExchangeName
            # enum 으로 매핑돼 ORM 비교가 param 을 `::exchangename` 으로 캐스팅한다.
            # alembic(VARCHAR) vs create_all(native enum) 스키마 분기에서 VARCHAR 컬럼이면
            # `varchar = exchangename` 연산자 부재 에러 → 컬럼을 text 로 캐스팅해 양쪽 호환.
            .where(cast(FundingRate.exchange, String) == exchange)
            .where(FundingRate.symbol == symbol)  # type: ignore[arg-type]
            .where(FundingRate.funding_timestamp >= start)  # type: ignore[arg-type]
            .where(FundingRate.funding_timestamp <= end)  # type: ignore[arg-type]
            .order_by(FundingRate.funding_timestamp.asc())  # type: ignore[attr-defined]
        )
        records = result.scalars().all()
        if not records:
            return pd.Series(dtype=object)
        timestamps = [r.funding_timestamp for r in records]
        rates = [r.funding_rate for r in records]
        return pd.Series(rates, index=pd.DatetimeIndex(timestamps), dtype=object)
