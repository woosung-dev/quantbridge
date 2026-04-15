"""strategy Repository. AsyncSession 유일 보유. commit() 은 Service 요청으로만."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.strategy.models import ParseStatus, Strategy


class StrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, strategy: Strategy) -> Strategy:
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def find_by_id(self, strategy_id: UUID) -> Strategy | None:
        result = await self.session.execute(
            select(Strategy).where(Strategy.id == strategy_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def find_by_id_and_owner(
        self, strategy_id: UUID, owner_id: UUID
    ) -> Strategy | None:
        result = await self.session.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,  # type: ignore[arg-type]
                    Strategy.user_id == owner_id,  # type: ignore[arg-type]
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        page: int,
        limit: int,
        parse_status: ParseStatus | None = None,
        is_archived: bool = False,
    ) -> tuple[list[Strategy], int]:
        # and_() 로 조건 목록 조합 — *list[bool] arg-type 문제 회피
        filters = and_(
            Strategy.user_id == owner_id,  # type: ignore[arg-type]
            Strategy.is_archived == is_archived,  # type: ignore[arg-type]
        )
        if parse_status is not None:
            filters = and_(
                filters,
                Strategy.parse_status == parse_status,  # type: ignore[arg-type]
            )

        count_stmt = select(func.count()).select_from(Strategy).where(filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * limit
        items_stmt = (
            select(Strategy)
            .where(filters)
            .order_by(Strategy.updated_at.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return items, int(total)

    async def update(self, strategy: Strategy) -> Strategy:
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def delete(self, strategy_id: UUID) -> None:
        await self.session.execute(
            delete(Strategy).where(Strategy.id == strategy_id)  # type: ignore[arg-type]
        )

    async def archive_all_by_owner(self, owner_id: UUID) -> None:
        """user.deleted Webhook 시 해당 사용자의 모든 Strategy를 archive."""
        await self.session.execute(
            update(Strategy)
            .where(Strategy.user_id == owner_id)  # type: ignore[arg-type]
            .values(is_archived=True)
        )

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
