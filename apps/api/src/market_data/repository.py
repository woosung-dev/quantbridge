"""OHLCV Repository — TimescaleDB hypertable (ts.ohlcv) 접근.

AsyncSession 유일 보유. commit()은 Service 요청으로만.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.market_data.models import OHLCV


class OHLCVRepository:
    """ts.ohlcv 접근 전담. AsyncSession은 본 클래스만 보유 (3-Layer 규칙)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_range(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[OHLCV]:
        """[period_start, period_end] 양 끝 포함 ASC 정렬."""
        stmt = (
            select(OHLCV)
            .where(
                OHLCV.symbol == symbol,  # type: ignore[arg-type]
                OHLCV.timeframe == timeframe,  # type: ignore[arg-type]
                OHLCV.time >= period_start,  # type: ignore[arg-type]
                OHLCV.time <= period_end,  # type: ignore[arg-type]
            )
            .order_by(OHLCV.time)  # type: ignore[arg-type]
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def insert_bulk(self, ohlcv_rows: list[dict[str, Any]]) -> None:
        """ON CONFLICT DO NOTHING — 동일 PK 중복 row는 silently skip (idempotent)."""
        if not ohlcv_rows:
            return
        stmt = insert(OHLCV).on_conflict_do_nothing(
            index_elements=["time", "symbol", "timeframe"]
        )
        await self.session.execute(stmt, ohlcv_rows)

    async def find_gaps(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
        timeframe_seconds: int,
    ) -> list[tuple[datetime, datetime]]:
        """Postgres generate_series로 expected vs actual 차이를 인접 grouping해 gap 추출.

        ROW_NUMBER 기반 island grouping: 인접한 누락 timestamp는 하나의 gap으로 묶인다.
        """
        sql = text(
            """
            WITH expected AS (
                SELECT generate_series(:start, :end, make_interval(secs => :tf_sec)) AS t
            ),
            missing AS (
                SELECT t FROM expected
                EXCEPT
                SELECT time FROM ts.ohlcv
                WHERE symbol = :symbol AND timeframe = :timeframe
                  AND time BETWEEN :start AND :end
            ),
            grouped AS (
                SELECT t,
                       t - (ROW_NUMBER() OVER (ORDER BY t)
                            * make_interval(secs => :tf_sec)) AS grp
                FROM missing
            )
            SELECT MIN(t) AS gap_start, MAX(t) AS gap_end
            FROM grouped
            GROUP BY grp
            ORDER BY gap_start;
            """
        )
        result = await self.session.execute(
            sql,
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "start": period_start,
                "end": period_end,
                "tf_sec": timeframe_seconds,
            },
        )
        return [(row.gap_start, row.gap_end) for row in result.fetchall()]

    async def acquire_fetch_lock(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """동시 fetch race 방지 — pg_advisory_xact_lock (트랜잭션 종료 시 자동 해제)."""
        key = (
            f"ohlcv:{symbol}:{timeframe}:"
            f"{period_start.isoformat()}:{period_end.isoformat()}"
        )
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": key},
        )

    async def commit(self) -> None:
        await self.session.commit()
