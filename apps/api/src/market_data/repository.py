"""OHLCV Repository — TimescaleDB hypertable (ts.ohlcv) 접근.

AsyncSession 유일 보유. commit()은 Service 요청으로만.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlmodel import col

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
                col(OHLCV.symbol) == symbol,
                col(OHLCV.timeframe) == timeframe,
                col(OHLCV.time) >= period_start,
                col(OHLCV.time) <= period_end,
            )
            .order_by(col(OHLCV.time))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _range_filter(
        self, symbol: str, timeframe: str, period_start: datetime, period_end: datetime
    ) -> tuple[Any, ...]:
        return (
            col(OHLCV.symbol) == symbol,
            col(OHLCV.timeframe) == timeframe,
            col(OHLCV.time) >= period_start,
            col(OHLCV.time) <= period_end,
        )

    async def count_range(
        self, symbol: str, timeframe: str, period_start: datetime, period_end: datetime
    ) -> int:
        """[period_start, period_end] 의 봉 수. 행을 올리지 않는다."""
        stmt = (
            select(func.count())
            .select_from(OHLCV)
            .where(*self._range_filter(symbol, timeframe, period_start, period_end))
        )
        return int((await self.session.execute(stmt)).scalar_one())

    def _ranked(
        self, symbol: str, timeframe: str, period_start: datetime, period_end: datetime
    ) -> Any:
        rn = (func.row_number().over(order_by=col(OHLCV.time)) - 1).label("rn")
        return (
            select(OHLCV, rn)
            .where(*self._range_filter(symbol, timeframe, period_start, period_end))
            .subquery()
        )

    async def nearest_index(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
        target: datetime,
    ) -> int:
        """구간 안에서 target 과 가장 가까운 봉의 0-기반 위치. 동률이면 앞선 봉."""
        ranked = self._ranked(symbol, timeframe, period_start, period_end)
        distance = func.abs(func.extract("epoch", ranked.c.time - target))
        stmt = select(ranked.c.rn).order_by(distance, ranked.c.time).limit(1)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_range_sampled(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
        *,
        stride: int,
        keep_indices: set[int],
    ) -> list[OHLCV]:
        """위치가 stride 의 배수이거나 keep_indices 인 봉만 ASC 로 반환한다(DB 에서 솎는다)."""
        ranked = self._ranked(symbol, timeframe, period_start, period_end)
        row = aliased(OHLCV, ranked)
        stmt = (
            select(row)
            .where(or_(ranked.c.rn % stride == 0, ranked.c.rn.in_(sorted(keep_indices))))
            .order_by(ranked.c.time)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def insert_bulk(self, ohlcv_rows: list[dict[str, Any]]) -> None:
        """ON CONFLICT DO NOTHING — 동일 PK 중복 row는 silently skip (idempotent)."""
        if not ohlcv_rows:
            return
        stmt = insert(OHLCV).on_conflict_do_nothing(index_elements=["time", "symbol", "timeframe"])
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
        """동시 fetch 직렬화 — 획득 대기만 10초 제한, 트랜잭션 종료 시 자동 해제.

        획득 후 기존 lock_timeout을 복원해 후속 SQL의 대기 정책을 보존한다.
        설정 조회·적용·복원/락 SQL의 DB 오류는 rollback 후 전파한다.
        """
        key = f"ohlcv:{symbol}:{timeframe}:{period_start.isoformat()}:{period_end.isoformat()}"
        try:
            previous_timeout = (
                await self.session.execute(text("SELECT current_setting('lock_timeout')"))
            ).scalar_one()
            await self.session.execute(text("SET LOCAL lock_timeout = '10s'"))
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": key},
            )
            await self.session.execute(
                text("SELECT set_config('lock_timeout', :previous_timeout, true)"),
                {"previous_timeout": previous_timeout},
            )
        except DBAPIError:
            await self.session.rollback()
            raise

    async def commit(self) -> None:
        await self.session.commit()
