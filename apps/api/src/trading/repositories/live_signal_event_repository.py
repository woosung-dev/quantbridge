# trading repository — LiveSignalEvent (시그널 이력) 영속화 단독 책임

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import LiveSignalEvent, LiveSignalEventStatus, Order


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

        signals 각 dict: {action, direction, trade_id, qty, sequence_no, comment,
        realized_pnl, take_profit, stop_loss, trailing_stop, bar_time}. `bar_time`이 없거나
        None이면 기존 인자 `bar_time`으로 폴백한다. exit 레벨은 entry 만 set.
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
                "bar_time": sig.get("bar_time") or bar_time,
                "sequence_no": int(sig["sequence_no"]),  # type: ignore[call-overload]
                "action": str(sig["action"]),
                "direction": str(sig["direction"]),
                "trade_id": str(sig["trade_id"]),
                "qty": Decimal(str(sig["qty"])),
                "comment": str(sig.get("comment", "")),
                # MP-1 — close signal 의 청산 realized PnL (entry 는 None).
                "realized_pnl": (
                    Decimal(str(sig["realized_pnl"]))
                    if sig.get("realized_pnl") is not None
                    else None
                ),
                # Phase 3 — entry signal 의 exit 레벨 (bracket placement + trailing).
                "take_profit": (
                    Decimal(str(sig["take_profit"]))
                    if sig.get("take_profit") is not None
                    else None
                ),
                "stop_loss": (
                    Decimal(str(sig["stop_loss"]))
                    if sig.get("stop_loss") is not None
                    else None
                ),
                "trailing_stop": (
                    Decimal(str(sig["trailing_stop"]))
                    if sig.get("trailing_stop") is not None
                    else None
                ),
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
        # 최종 상태 조회 (이미 존재하던 + 신규 모두 반환). catch-up은 여러 bar를 한 번에
        # 넣으므로 signal별 bar_time 전체를 조회한다.
        event_bar_times = list(
            dict.fromkeys(cast(datetime, row["bar_time"]) for row in rows)
        )
        result = await self.session.execute(
            select(LiveSignalEvent)
            .where(LiveSignalEvent.session_id == session_id)  # type: ignore[arg-type]
            .where(cast(Any, LiveSignalEvent.bar_time).in_(event_bar_times))
            .order_by(
                cast(Any, LiveSignalEvent.bar_time).asc(),
                cast(Any, LiveSignalEvent.sequence_no).asc(),
            )
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

    async def list_by_session_with_order_state(
        self, session_id: UUID, *, limit: int = 100
    ) -> Sequence[tuple[LiveSignalEvent, str | None]]:
        """UI 이벤트 목록에 연결된 주문 상태를 단일 LEFT JOIN으로 함께 조회한다."""
        result = await self.session.execute(
            select(LiveSignalEvent, cast(Any, Order.state))
            .outerjoin(
                Order,
                cast(Any, LiveSignalEvent.order_id) == Order.id,
            )
            .where(cast(Any, LiveSignalEvent.session_id) == session_id)
            .order_by(LiveSignalEvent.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        return [
            (live_event, str(order_state) if order_state is not None else None)
            for live_event, order_state in result.tuples().all()
        ]

    async def sum_realized_pnl_before(
        self, session_id: UUID, *, bar_time: datetime
    ) -> tuple[Decimal, int]:
        """사이징 자본 경계용으로 창 시작 전 발주 청산의 Pine 추정 손익을 반환한다.

        엔진은 kill switch, 거래소 거부, 발주 실패를 모르므로 창 안 청산은 dispatch 결과와
        무관하게 모두 누적한다. 여기만 status로 거르면 창 경계의 계산 규칙이 달라진다.
        거래소 확정 순손익은 gross 시뮬레이션 누적기와 단위가 다르고 event에는 backfill되지
        않는다. 따라서 이 값은 의도적으로 pine_v2가 계산한 realized_pnl을 사용한다.
        """
        return await self._sum_realized_pnl(session_id, before=bar_time)

    async def sum_realized_pnl_all(self, session_id: UUID) -> tuple[Decimal, int]:
        """화면 총계용으로 창과 무관한 세션 원장 전체의 Pine 추정 손익을 반환한다."""
        return await self._sum_realized_pnl(session_id)

    async def _sum_realized_pnl(
        self, session_id: UUID, *, before: datetime | None = None
    ) -> tuple[Decimal, int]:
        """세션 원장의 non-null realized PnL 합계와 건수를 반환한다."""
        stmt = (
            select(
                func.sum(LiveSignalEvent.realized_pnl),
                func.count(LiveSignalEvent.id),  # type: ignore[arg-type]
            )
            .where(LiveSignalEvent.session_id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalEvent.realized_pnl.is_not(None))  # type: ignore[union-attr]
        )
        if before is not None:
            stmt = stmt.where(LiveSignalEvent.bar_time < before)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        total_pnl, closed_count = result.one()
        return Decimal(str(total_pnl)) if total_pnl is not None else Decimal("0"), int(
            closed_count or 0
        )

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
