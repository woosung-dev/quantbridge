# trading.funding_rates read 전용 — backtest perp funding 차감용 시계열 조회.
"""FundingRateRepository — funding_rates read (Slice 4 perp funding 배선).

backtest 엔진이 [period_start, period_end] window 의 funding 시계열을 8h 정산 경계
차감에 사용한다(`get_funding_series`).

★**쓰기도 이 층이 갖는다**(2026-08-30) — 종전에는 멱등 INSERT 가 `trading/funding.py` 안에서
raw `text()` + `session.commit()` 로 돌아 Repository 층을 통째로 우회했다(`apps/api/AGENTS.md` §3).
게이트 = `tests/common/test_repository_boundary_guard.py` 의 raw-SQL 축.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import pandas as pd
from sqlalchemy import String, cast, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import FundingRate


class FundingRateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        """서비스가 요청한 저장 경계를 확정한다."""
        await self.session.commit()

    async def upsert_many(self, rows: Sequence[FundingRate]) -> int:
        """FundingRate 행을 멱등 저장하고 **새로 삽입된 수**를 반환한다.

        중복 방지 = `(exchange, symbol, funding_timestamp)` UNIQUE index +
        `ON CONFLICT DO NOTHING`. 그래서 재실행이 안전하고 반환값이 「신규」만 센다.
        """
        if not rows:
            return 0

        inserted = 0
        for row in rows:
            result = await self.session.execute(
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
        return inserted

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
