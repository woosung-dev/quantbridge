"""strategy Repository. AsyncSession 유일 보유. commit() 은 Service 요청으로만."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class StrategyRepository:
    """Task 9에서 전체 구현 예정. UserService.handle_clerk_event가 참조하는 stub."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def archive_all_by_owner(self, owner_id: UUID) -> None:
        """owner의 모든 전략을 soft-delete. Task 9에서 구현."""
        raise NotImplementedError
