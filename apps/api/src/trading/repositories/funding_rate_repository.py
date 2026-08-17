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
            # ★이 캐스트는 alembic(VARCHAR 32) vs create_all(native enum) 스키마 분기 때문에
            # 있었다. [BL-782] 가 그 분기를 닫았으므로(20260817_0002 가 컬럼을 exchangename
            # 으로 올린다) 새로 만든 DB 에서는 더 이상 필요 없다. 그래도 남기는 이유는
            # **아직 그 migration 이 안 닿은 DB**(서버 소크 등)가 존재할 수 있어서다 —
            # 거기서는 컬럼이 VARCHAR 라 `varchar = exchangename` 연산자 부재로 죽는다.
            # 전 배포처가 head 에 도달한 뒤 걷어내라(인덱스 ix_funding_rates_exchange_symbol
            # 을 못 쓰게 만드는 비용이 있다).
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
