# 거래소 원본 청산 원장의 행 단위 영속화와 집계를 담당하는 리포지터리

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import ExchangeExit, ExchangeExitSyncState

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

    async def get_backfilled_from(self, account_id: UUID) -> datetime | None:
        """과거 스캔을 마친 가장 이른 경계. 없으면 아직 한 번도 과거로 훑지 않은 계정이다."""
        stmt = select(ExchangeExitSyncState.backfilled_from).where(  # type: ignore[call-overload]
            ExchangeExitSyncState.exchange_account_id == account_id
        )
        return cast(datetime | None, (await self.session.execute(stmt)).scalar_one_or_none())

    async def set_backfilled_from(self, account_id: UUID, boundary: datetime) -> None:
        """스캔 경계를 과거로만 전진시킨다.

        행이 하나도 없던 창도 전진시켜야 한다 — 그러지 않으면 청산이 없던 구간에서
        같은 빈 창을 영원히 재조회한다. 단조 감소만 허용해 재실행이 경계를 되돌리지 않는다.
        """
        stmt = (
            insert(ExchangeExitSyncState)
            .values(exchange_account_id=account_id, backfilled_from=boundary)
            .on_conflict_do_update(
                index_elements=["exchange_account_id"],
                set_={"backfilled_from": boundary, "updated_at": datetime.now(UTC)},
                where=(
                    (ExchangeExitSyncState.backfilled_from.is_(None))  # type: ignore[union-attr]
                    | (ExchangeExitSyncState.backfilled_from > boundary)  # type: ignore[operator]
                ),
            )
        )
        await self.session.execute(stmt)

    async def aggregate_closed_pnl(
        self, account_id: UUID, exchange_order_ids: Sequence[str]
    ) -> dict[str, Decimal]:
        """(계정, 거래소 주문 id) 별 closed_pnl 합계. 창을 나눠 적재해도 원장 전체를 집계하므로 부분합이 남지 않는다."""
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

    async def created_at_bounds(
        self, account_id: UUID
    ) -> tuple[datetime | None, datetime | None]:
        """계정별 원장의 (가장 오래된, 가장 최근) exchange_created_at. 스윕의 과거 전진 상태를 여기서 파생한다."""
        stmt = select(
            func.min(ExchangeExit.exchange_created_at),
            func.max(ExchangeExit.exchange_created_at),
        ).where(ExchangeExit.exchange_account_id == account_id)  # type: ignore[arg-type]
        oldest, newest = (await self.session.execute(stmt)).one()
        return cast(datetime | None, oldest), cast(datetime | None, newest)

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
