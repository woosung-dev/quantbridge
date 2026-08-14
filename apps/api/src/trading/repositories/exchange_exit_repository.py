# 거래소 원본 청산 원장의 행 단위 영속화와 집계를 담당하는 리포지터리

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import ExchangeExit

# asyncpg 쿼리 인자 상한 32767 을 컬럼 수로 나눈 보수적 배치 크기.
_UPSERT_CHUNK_ROWS = 500


class ExchangeExitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_rows(self, rows: Sequence[ExchangeExit]) -> list[str]:
        """원장에 행을 넣고 새로 들어간 행의 row_hash 목록을 돌려준다(중복은 조용히 무시)."""
        if not rows:
            return []
        inserted: list[str] = []
        # asyncpg 는 쿼리 인자 32767개가 상한이라 컬럼 수로 나눈 만큼만 한 번에 보낸다.
        # 지금 호출자는 창당 500행이라 못 넘지만, 상한을 리포지터리 안에 두어야
        # max_pages/limit 를 올리는 호출자가 생겨도 조용히 터지지 않는다.
        for start in range(0, len(rows), _UPSERT_CHUNK_ROWS):
            chunk = rows[start : start + _UPSERT_CHUNK_ROWS]
            stmt = (
                insert(ExchangeExit)
                .values([row.model_dump() for row in chunk])
                .on_conflict_do_nothing(index_elements=["exchange_account_id", "row_hash"])
            )
            stmt = stmt.returning(ExchangeExit.row_hash)  # type: ignore[call-overload]
            result = await self.session.execute(stmt)
            inserted.extend(str(row_hash) for row_hash in result.scalars().all())
        return inserted

    async def aggregate_closed_pnl(
        self, account_id: UUID, exchange_order_ids: Sequence[str]
    ) -> dict[str, Decimal]:
        """(계정, 거래소 주문 id) 별 closed_pnl 합계. 창을 나눠 적재해도 원장 전체를 집계하므로 부분합이 남지 않는다.

        ★[BL-725] 중복 290행에 대한 `DISTINCT ON (row_hash)` 는 **여기서 no-op 이라 넣지 않는다.**
        그 중복은 같은 Bybit uid 에 앱 계정 행이 둘(`0277c150`·`19a8166a`)이라 **계정 행 사이**로
        갈라져 있는데, 이 쿼리는 `exchange_account_id == account_id` 로 스코프되고 같은 계정
        안에서는 `Index("uq_exchange_exits_row", "exchange_account_id", "row_hash", unique=True)`
        (`models.py`)가 중복을 이미 막는다. 즉 이 SUM 이 한 행을 두 번 세는 경로가 없다.
        원장을 **계정 스코프 없이** 통계로 읽는 소비자가 생기면 그때는 필요하다.
        """
        if not exchange_order_ids:
            return {}
        stmt = (
            select(ExchangeExit.exchange_order_id, func.sum(ExchangeExit.closed_pnl))  # type: ignore[call-overload]
            .where(ExchangeExit.exchange_account_id == account_id)
            .where(ExchangeExit.exchange_order_id.in_(exchange_order_ids))  # type: ignore[attr-defined]
            .group_by(ExchangeExit.exchange_order_id)
        )
        result = await self.session.execute(stmt)
        return {
            str(exchange_order_id): Decimal(str(closed_pnl))
            for exchange_order_id, closed_pnl in result.all()
        }

    async def list_by_row_hashes(
        self, account_id: UUID, row_hashes: Sequence[str]
    ) -> Sequence[ExchangeExit]:
        """방금 새로 들어간 행을 알림용으로 되읽는다."""
        if not row_hashes:
            return []
        result = await self.session.execute(
            select(ExchangeExit)
            .where(ExchangeExit.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(ExchangeExit.row_hash.in_(row_hashes))  # type: ignore[attr-defined]
        )
        return result.scalars().all()
