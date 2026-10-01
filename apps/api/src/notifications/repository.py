"""notifications Repository. AsyncSession 전용, commit() 은 Service 가 호출."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.models import PushSubscription


class PushSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        result = await self.session.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == endpoint  # type: ignore[arg-type]
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[PushSubscription]:
        result = await self.session.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == user_id  # type: ignore[arg-type]
            )
        )
        return list(result.scalars().all())

    async def create(self, subscription: PushSubscription) -> PushSubscription:
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def reassign(
        self,
        subscription: PushSubscription,
        *,
        user_id: UUID,
        p256dh: str,
        auth: str,
        user_agent: str | None,
    ) -> PushSubscription:
        """같은 endpoint 의 재구독 — 소유자·키를 현재 요청 값으로 덮는다."""
        subscription.user_id = user_id
        subscription.p256dh = p256dh
        subscription.auth = auth
        subscription.user_agent = user_agent
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def delete(self, subscription: PushSubscription) -> None:
        await self.session.delete(subscription)
        await self.session.flush()

    async def mark_success(self, subscription: PushSubscription, *, at: datetime) -> None:
        subscription.last_success_at = at
        self.session.add(subscription)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
