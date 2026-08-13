# 세션 알림 규칙의 영속화와 beat 조회를 담당하는 저장소

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import AlertRule, AlertRuleType, LiveSignalSession


class AlertRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def list_by_session(self, session_id: UUID) -> Sequence[AlertRule]:
        result = await self.session.execute(
            select(AlertRule)
            .where(AlertRule.session_id == session_id)  # type: ignore[arg-type]
            .where(AlertRule.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .order_by(AlertRule.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def create(self, rule: AlertRule) -> AlertRule:
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def get_active_by_id(self, rule_id: UUID) -> AlertRule | None:
        result = await self.session.execute(
            select(AlertRule)
            .where(AlertRule.id == rule_id)  # type: ignore[arg-type]
            .where(AlertRule.is_active == True)  # type: ignore[arg-type]  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def deactivate(self, rule_id: UUID) -> int:
        result = await self.session.execute(
            update(AlertRule)
            .where(AlertRule.id == rule_id)  # type: ignore[arg-type]
            .where(AlertRule.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def list_active_loss_rules_with_sessions(
        self,
    ) -> Sequence[tuple[AlertRule, LiveSignalSession]]:
        result = await self.session.execute(
            select(AlertRule, LiveSignalSession)
            .join(LiveSignalSession, AlertRule.session_id == LiveSignalSession.id)  # type: ignore[arg-type]
            .where(AlertRule.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .where(AlertRule.rule_type == AlertRuleType.loss_limit)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
        )
        return [(row[0], row[1]) for row in result.all()]

    async def find_active_watchdog_rules_for(self, session_id: UUID) -> Sequence[AlertRule]:
        result = await self.session.execute(
            select(AlertRule)
            .where(AlertRule.session_id == session_id)  # type: ignore[arg-type]
            .where(AlertRule.rule_type == AlertRuleType.watchdog)  # type: ignore[arg-type]
            .where(AlertRule.is_active == True)  # type: ignore[arg-type]  # noqa: E712
        )
        return result.scalars().all()
