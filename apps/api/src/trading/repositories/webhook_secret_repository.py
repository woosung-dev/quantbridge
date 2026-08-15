# trading repository — webhook HMAC secret 영속화 단독 책임

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.strategy.models import Strategy
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

    async def revoke_all_by_owner(self, user_id: UUID, *, at: datetime) -> int:
        """소유자의 **모든 전략**의 active secret 을 일괄 revoke (2026-08-15 surface-truth · S3).

        ★탈퇴 처리 전용이다. `revoke_all_active` 는 전략 하나를 대상으로 하고 rotate 가
        그것을 쓴다 — 탈퇴는 「전략 목록을 먼저 읽고 하나씩」이 아니라 **소유 관계 자체**로
        닫아야 한다. 그 사이에 전략이 추가되는 경합을 코드로 막지 못하기 때문이다.

        ★`at` 은 **revoke 시각**이고 grace 가 아니다. `list_valid_secrets` 는
        `revoked_at > grace_cutoff` 인 시크릿을 아직 유효로 세므로, 즉시 폐기를 원하면
        호출부가 `at` 을 **과거**로 줘야 한다(`WEBHOOK_SECRET_ROTATE_GRACE` 만큼).
        탈퇴 경로가 정확히 그렇게 한다 — 유출/탈퇴에 1시간 유예를 줄 이유가 없다.

        commit 책임은 호출한 Service 에 있다.
        """
        # ★서브쿼리로 **한 문장**에 닫는다 — 전략 목록을 먼저 읽고 루프를 돌면 그 사이에
        #   추가된 전략을 놓친다. 탈퇴는 「하나도 남으면 안 되는」 경계다.
        #   `type: ignore` 두 개는 SQLModel 이 컬럼 속성을 파이썬 타입(UUID)으로 노출해
        #   mypy 가 `select` overload 와 `.in_` 를 못 보는 것이라, 런타임 의미와 무관하다.
        owned = select(Strategy.id).where(Strategy.user_id == user_id)  # type: ignore[call-overload]
        result = await self.session.execute(
            update(WebhookSecret)
            .where(WebhookSecret.strategy_id.in_(owned))  # type: ignore[attr-defined]
            .where(WebhookSecret.revoked_at.is_(None))  # type: ignore[union-attr]
            .values(revoked_at=at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]
