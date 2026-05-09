# trading repository — KillSwitch event 영속화 단독 책임

from __future__ import annotations

import datetime as _dt_module
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import KillSwitchEvent, KillSwitchTriggerType


class KillSwitchEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, event: KillSwitchEvent) -> KillSwitchEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_by_id(self, event_id: UUID) -> KillSwitchEvent | None:
        result = await self.session.execute(
            select(KillSwitchEvent).where(KillSwitchEvent.id == event_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_active(self, *, strategy_id: UUID, account_id: UUID) -> KillSwitchEvent | None:
        """spec §2.2 매칭 규칙:
        - cumulative_loss → strategy_id 매칭 (ADR-006 CEO F4)
        - daily_loss, api_error → account_id 매칭
        - resolved_at IS NULL
        """
        stmt = (
            select(KillSwitchEvent)
            .where(
                KillSwitchEvent.resolved_at.is_(None),  # type: ignore[union-attr]
                or_(
                    and_(
                        KillSwitchEvent.trigger_type == KillSwitchTriggerType.cumulative_loss,  # type: ignore[arg-type]
                        KillSwitchEvent.strategy_id == strategy_id,  # type: ignore[arg-type]
                    ),
                    and_(
                        KillSwitchEvent.trigger_type.in_(  # type: ignore[attr-defined]
                            [KillSwitchTriggerType.daily_loss, KillSwitchTriggerType.api_error]
                        ),
                        KillSwitchEvent.exchange_account_id == account_id,  # type: ignore[arg-type]
                    ),
                ),
            )
            .order_by(KillSwitchEvent.triggered_at.desc())  # type: ignore[attr-defined]
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def resolve(self, event_id: UUID, *, note: str | None = None) -> int:
        result = await self.session.execute(
            update(KillSwitchEvent)
            .where(KillSwitchEvent.id == event_id)  # type: ignore[arg-type]
            .where(KillSwitchEvent.resolved_at.is_(None))  # type: ignore[union-attr]
            .values(
                resolved_at=datetime.now(UTC),
                resolution_note=(note[:500] if note else None),
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def list_recent(self, *, limit: int, offset: int) -> Sequence[KillSwitchEvent]:
        result = await self.session.execute(
            select(KillSwitchEvent)
            .order_by(KillSwitchEvent.triggered_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_by_date(self, date: _dt_module.date) -> Sequence[KillSwitchEvent]:
        """특정 날짜(UTC) 트리거된 Kill Switch 이벤트 목록."""
        day_start = datetime(date.year, date.month, date.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        result = await self.session.execute(
            select(KillSwitchEvent)
            .where(KillSwitchEvent.triggered_at >= day_start)  # type: ignore[arg-type]
            .where(KillSwitchEvent.triggered_at < day_end)  # type: ignore[arg-type]
            .order_by(KillSwitchEvent.triggered_at.asc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()
