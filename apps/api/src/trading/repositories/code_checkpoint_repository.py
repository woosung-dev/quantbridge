"""봉 입력·의도의 단일 세션 직렬화와 영속화. commit 경계는 service가 소유한다."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.trading.code_checkpoints import LiveCodeBar
from src.trading.models import LiveSignalSession


class CodeCheckpointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def acquire(self, session_id: UUID) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"code-evaluate:{session_id}"},
        )

    async def history(self, session_id: UUID) -> list[LiveCodeBar]:
        result = await self.session.execute(
            select(LiveCodeBar)
            .where(LiveCodeBar.session_id == session_id)  # type: ignore[arg-type]
            .order_by(LiveCodeBar.sequence)  # type: ignore[arg-type]
            .limit(50001)
        )
        return list(result.scalars().all())

    async def add(self, row: LiveCodeBar) -> None:
        self.session.add(row)
        await self.session.flush()

    async def delivered(self, row_id: UUID) -> None:
        await self.session.execute(
            update(LiveCodeBar)
            .where(LiveCodeBar.id == row_id)  # type: ignore[arg-type]
            .where(LiveCodeBar.status == "prepared")  # type: ignore[arg-type]
            .values(status="delivered")
        )

    async def record_evaluated(self, session_id: UUID, bar_time: datetime) -> None:
        await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(
                or_(
                    col(LiveSignalSession.last_evaluated_bar_time).is_(None),
                    col(LiveSignalSession.last_evaluated_bar_time) < bar_time,
                )
            )
            .values(last_evaluated_bar_time=bar_time)
        )

    async def commit(self) -> None:
        await self.session.commit()
