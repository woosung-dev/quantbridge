"""waitlist Repository. AsyncSession 전용, commit() 은 Service 가 호출."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.waitlist.models import WaitlistApplication, WaitlistStatus


class WaitlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, application: WaitlistApplication) -> WaitlistApplication:
        self.session.add(application)
        await self.session.flush()
        await self.session.refresh(application)
        return application

    async def find_by_id(self, application_id: UUID) -> WaitlistApplication | None:
        result = await self.session.execute(
            select(WaitlistApplication).where(
                WaitlistApplication.id == application_id  # type: ignore[arg-type]
            )
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> WaitlistApplication | None:
        normalized = email.strip().lower()
        result = await self.session.execute(
            select(WaitlistApplication).where(
                WaitlistApplication.email == normalized  # type: ignore[arg-type]
            )
        )
        return result.scalar_one_or_none()

    async def find_by_invite_token(self, token: str) -> WaitlistApplication | None:
        result = await self.session.execute(
            select(WaitlistApplication).where(
                WaitlistApplication.invite_token == token  # type: ignore[arg-type]
            )
        )
        return result.scalar_one_or_none()

    async def list_by_status(
        self,
        *,
        status: WaitlistStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[WaitlistApplication], int]:
        stmt = select(WaitlistApplication)
        if status is not None:
            stmt = stmt.where(WaitlistApplication.status == status)  # type: ignore[arg-type]

        count_stmt = select(func.count()).select_from(WaitlistApplication)
        if status is not None:
            count_stmt = count_stmt.where(
                WaitlistApplication.status == status  # type: ignore[arg-type]
            )
        total = (await self.session.execute(count_stmt)).scalar_one()

        items_stmt = (
            stmt.order_by(WaitlistApplication.created_at.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return items, int(total)

    async def mark_invited(
        self,
        application: WaitlistApplication,
        *,
        invite_token: str,
    ) -> WaitlistApplication:
        application.invite_token = invite_token
        application.status = WaitlistStatus.invited
        now = datetime.now(UTC)
        application.invited_at = now
        application.invite_sent_at = now
        self.session.add(application)
        await self.session.flush()
        await self.session.refresh(application)
        return application

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
