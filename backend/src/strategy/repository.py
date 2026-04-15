"""strategy Repository. AsyncSession 유일 보유. commit() 은 Service 요청으로만."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.strategy.models import Strategy


class StrategyRepository:
    """Sprint 3 Task 8에서 archive_all_by_owner 선행 구현.
    전체 CRUD는 Task 9에서 추가."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def archive_all_by_owner(self, owner_id: UUID) -> None:
        """user.deleted Webhook 시 해당 사용자의 모든 Strategy를 archive."""
        stmt = (
            update(Strategy)
            .where(Strategy.user_id == owner_id)  # type: ignore[arg-type]
            .values(is_archived=True)
        )
        await self.session.execute(stmt)

    async def commit(self) -> None:
        await self.session.commit()
