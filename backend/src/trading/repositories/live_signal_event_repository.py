# trading repository — LiveSignalEvent (시그널 이력) 영속화 단독 책임

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import LiveSignalEvent, LiveSignalEventStatus


class LiveSignalEventRepository:
    """Sprint 26 — Transactional outbox repository (codex G.0 P1 #3).

    insert_pending_events 가 같은 트랜잭션에서 events INSERT + state upsert + commit.
    dispatch task 가 list_pending → OrderService.execute → mark_dispatched.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def get_by_id(self, event_id: UUID) -> LiveSignalEvent | None:
        result = await self.session.execute(
            select(LiveSignalEvent).where(LiveSignalEvent.id == event_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def insert_pending_events(
        self,
        *,
        session_id: UUID,
        bar_time: datetime,
        signals: Sequence[dict[str, object]],
    ) -> Sequence[LiveSignalEvent]:
        """Pine signals → LiveSignalEvent INSERT (status=pending).

        signals 각 dict: {action, direction, trade_id, qty, sequence_no, comment}.
        UNIQUE (session_id, bar_time, sequence_no, action, trade_id) 가 idempotency 보장
        — 같은 evaluate 가 두 번 fire 해도 INSERT 1번만 성공 (다른 INSERT 는 IntegrityError
        대신 ON CONFLICT DO NOTHING 으로 silent skip).

        codex G.0 P2 #5 sequence_no idempotency.
        """
        if not signals:
            return []
        # ON CONFLICT DO NOTHING — IntegrityError 회피하면서 idempotent INSERT
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        rows = [
            {
                "session_id": session_id,
                "bar_time": bar_time,
                "sequence_no": int(sig["sequence_no"]),  # type: ignore[call-overload]
                "action": str(sig["action"]),
                "direction": str(sig["direction"]),
                "trade_id": str(sig["trade_id"]),
                "qty": Decimal(str(sig["qty"])),
                "comment": str(sig.get("comment", "")),
            }
            for sig in signals
        ]
        stmt = (
            pg_insert(LiveSignalEvent)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_live_signal_events_idempotency")
        )
        await self.session.execute(stmt)
        await self.session.flush()
        # 최종 상태 조회 (이미 존재하던 + 신규 모두 반환)
        result = await self.session.execute(
            select(LiveSignalEvent)
            .where(LiveSignalEvent.session_id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalEvent.bar_time == bar_time)  # type: ignore[arg-type]
            .order_by(LiveSignalEvent.sequence_no.asc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def list_pending(self, *, limit: int = 50) -> Sequence[LiveSignalEvent]:
        """status=pending 만 — partial pending index 활용. dispatch worker 가 폴링용."""
        result = await self.session.execute(
            select(LiveSignalEvent)
            .where(LiveSignalEvent.status == LiveSignalEventStatus.pending)  # type: ignore[arg-type]
            .order_by(LiveSignalEvent.created_at.asc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return result.scalars().all()

    async def list_by_session(
        self, session_id: UUID, *, limit: int = 100
    ) -> Sequence[LiveSignalEvent]:
        """UI 용 event log 조회 — 최신 순."""
        result = await self.session.execute(
            select(LiveSignalEvent)
            .where(LiveSignalEvent.session_id == session_id)  # type: ignore[arg-type]
            .order_by(LiveSignalEvent.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_dispatched(self, event_id: UUID, *, order_id: UUID) -> int:
        """dispatch_task 가 broker 발주 성공 시 호출. status=dispatched + order_id."""
        result = await self.session.execute(
            update(LiveSignalEvent)
            .where(LiveSignalEvent.id == event_id)  # type: ignore[arg-type]
            .where(LiveSignalEvent.status == LiveSignalEventStatus.pending)  # type: ignore[arg-type]
            .values(
                status=LiveSignalEventStatus.dispatched,
                order_id=order_id,
                dispatched_at=datetime.now(UTC),
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def mark_failed(self, event_id: UUID, *, error: str) -> int:
        """KillSwitch / NotionalCap / 기타 실패 시 status=failed + retry_count+1."""
        result = await self.session.execute(
            update(LiveSignalEvent)
            .where(LiveSignalEvent.id == event_id)  # type: ignore[arg-type]
            .where(LiveSignalEvent.status == LiveSignalEventStatus.pending)  # type: ignore[arg-type]
            .values(
                status=LiveSignalEventStatus.failed,
                error_message=error[:2000],
                retry_count=LiveSignalEvent.retry_count + 1,
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]
