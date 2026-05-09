# trading repository — webhook HMAC secret 영속화 단독 책임

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import WebhookSecret


class WebhookSecretRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, ws: WebhookSecret) -> WebhookSecret:
        self.session.add(ws)
        await self.session.flush()
        return ws

    async def get_by_id(self, secret_id: UUID) -> WebhookSecret | None:
        result = await self.session.execute(
            select(WebhookSecret).where(WebhookSecret.id == secret_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def list_valid_secrets(
        self, strategy_id: UUID, *, grace_cutoff: datetime
    ) -> Sequence[WebhookSecret]:
        """revoked_at IS NULL OR revoked_at > grace_cutoff.

        T11 Service layer는 반환된 암호문(bytes)을 EncryptionService.decrypt로 풀어 HMAC 비교.
        """
        result = await self.session.execute(
            select(WebhookSecret)
            .where(WebhookSecret.strategy_id == strategy_id)  # type: ignore[arg-type]
            .where(
                or_(
                    WebhookSecret.revoked_at.is_(None),  # type: ignore[union-attr]
                    WebhookSecret.revoked_at > grace_cutoff,  # type: ignore[arg-type,operator]
                )
            )
            .order_by(WebhookSecret.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def mark_revoked(self, secret_id: UUID, *, at: datetime) -> int:
        result = await self.session.execute(
            update(WebhookSecret)
            .where(WebhookSecret.id == secret_id)  # type: ignore[arg-type]
            .where(WebhookSecret.revoked_at.is_(None))  # type: ignore[union-attr]
            .values(revoked_at=at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def revoke_all_active(self, strategy_id: UUID, *, at: datetime) -> int:
        """rotate 시점에 해당 strategy의 모든 active secret을 일괄 revoke."""
        result = await self.session.execute(
            update(WebhookSecret)
            .where(WebhookSecret.strategy_id == strategy_id)  # type: ignore[arg-type]
            .where(WebhookSecret.revoked_at.is_(None))  # type: ignore[union-attr]
            .values(revoked_at=at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]
