"""trading Repository 레이어. AsyncSession 유일 보유. commit은 Service 요청으로만.

네이밍 컨벤션:
- `save()` = add + flush (ID/created_at 채워진 동일 인스턴스 반환). upsert-by-identity:
  수정 후 재저장도 같은 메서드. Sprint 4는 create/update 분리 — Sprint 6은 단일화.
- T8 OrderRepository에서 Sprint 4 BacktestRepository의 3-guard `transition_*` 패턴 계승 예정.
"""

from __future__ import annotations

import datetime as _dt_module
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import (
    ExchangeAccount,
    KillSwitchEvent,
    KillSwitchTriggerType,
    LiveSignalEvent,
    LiveSignalEventStatus,
    LiveSignalSession,
    LiveSignalState,
    Order,
    OrderState,
    WebhookSecret,
)


class ExchangeAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, account: ExchangeAccount) -> ExchangeAccount:
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_by_id(self, account_id: UUID) -> ExchangeAccount | None:
        result = await self.session.execute(
            select(ExchangeAccount).where(ExchangeAccount.id == account_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> Sequence[ExchangeAccount]:
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(ExchangeAccount.user_id == user_id)  # type: ignore[arg-type]
            .order_by(ExchangeAccount.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def delete(self, account_id: UUID) -> int:
        result = await self.session.execute(
            delete(ExchangeAccount).where(ExchangeAccount.id == account_id)  # type: ignore[arg-type]
        )
        return result.rowcount or 0  # type: ignore[attr-defined]


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.idempotency_key == key)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, *, limit: int, offset: int
    ) -> tuple[Sequence[Order], int]:
        """Join ExchangeAccount → user_id 매칭. Sprint 5 M4 pagination 스타일."""
        total_stmt = (
            select(func.count(Order.id))  # type: ignore[arg-type]
            .join(ExchangeAccount, Order.exchange_account_id == ExchangeAccount.id)  # type: ignore[arg-type]
            .where(ExchangeAccount.user_id == user_id)  # type: ignore[arg-type]
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(Order)
            .join(ExchangeAccount, Order.exchange_account_id == ExchangeAccount.id)  # type: ignore[arg-type]
            .where(ExchangeAccount.user_id == user_id)  # type: ignore[arg-type]
            .order_by(Order.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return (await self.session.execute(stmt)).scalars().all(), total

    # --- 3-guard 상태 전이 (Sprint 4 BacktestRepository 패턴 계승) ---

    async def transition_to_submitted(self, order_id: UUID, *, submitted_at: datetime) -> int:
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.pending)  # type: ignore[arg-type]
            .values(state=OrderState.submitted, submitted_at=submitted_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def transition_to_filled(
        self,
        order_id: UUID,
        *,
        exchange_order_id: str,
        filled_price: Decimal | None,
        filled_quantity: Decimal
        | None = None,  # NEW — CCXT partial fill 지원 (ADR-006 / autoplan Eng E7)
        filled_at: datetime,
        realized_pnl: Decimal | None = None,
    ) -> int:
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .values(
                state=OrderState.filled,
                exchange_order_id=exchange_order_id,
                filled_price=filled_price,
                filled_quantity=filled_quantity,
                filled_at=filled_at,
                realized_pnl=realized_pnl,
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def transition_to_rejected(
        self, order_id: UUID, *, error_message: str, failed_at: datetime
    ) -> int:
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state.in_([OrderState.pending, OrderState.submitted]))  # type: ignore[attr-defined]
            .values(
                state=OrderState.rejected,
                error_message=error_message[:2000],
                filled_at=failed_at,
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def transition_to_cancelled(self, order_id: UUID, *, cancelled_at: datetime) -> int:
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state.in_([OrderState.pending, OrderState.submitted]))  # type: ignore[attr-defined]
            .values(state=OrderState.cancelled, filled_at=cancelled_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def attach_exchange_order_id(
        self, order_id: UUID, exchange_order_id: str
    ) -> int:
        """Sprint 14 Phase C — submitted 상태 유지 + exchange_order_id 만 저장.

        Bybit Demo / Live 의 REST 주문 접수 후 receipt.status="submitted" 일 때
        DB filled 거짓 양성 회피. WS order event 또는 reconciler 가 terminal
        evidence 받을 때 transition_to_filled / transition_to_rejected 호출.
        """
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .values(exchange_order_id=exchange_order_id)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    # --- Sprint 15 Phase A.3: stuck order watchdog scope (BL-001 + BL-002) ---

    async def list_stuck_pending(self, cutoff: datetime) -> Sequence[Order]:
        """30분 이상 pending 주문 — dispatch 누락 (BL-002 day 2 stuck order 13705a91 패턴).

        scan_stuck_orders 가 execute_order_task 재enqueue 시도. LIMIT 100 으로 cardinality cap.
        """
        stmt = (
            select(Order)
            .where(Order.state == OrderState.pending)  # type: ignore[arg-type]
            .where(Order.created_at < cutoff)  # type: ignore[arg-type]
            .order_by(Order.created_at.asc())  # type: ignore[attr-defined]
            .limit(100)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_stuck_submitted(self, cutoff: datetime) -> Sequence[Order]:
        """30분 이상 submitted 주문 — terminal evidence 미수신 (BL-001 watchdog target).

        codex G.0 P1 #3 fix — exchange_order_id IS NOT NULL 필터. null 인 경우는
        list_stuck_submission_interrupted 가 별도 처리 (fetch 호출 불가).
        """
        stmt = (
            select(Order)
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .where(Order.submitted_at < cutoff)  # type: ignore[operator, arg-type]
            .where(Order.exchange_order_id.is_not(None))  # type: ignore[union-attr]
            .order_by(Order.submitted_at.asc())  # type: ignore[union-attr]
            .limit(100)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_stuck_submission_interrupted(
        self, cutoff: datetime
    ) -> Sequence[Order]:
        """submitted + exchange_order_id IS NULL — transition_to_submitted commit 후
        attach_exchange_order_id 전 worker crash 또는 race 윈도우.

        codex G.0 P1 #3 — fetch_order 호출 불가 (id 없음). scan_stuck_orders 가
        throttled alert 만 발화. 사용자 수동 cleanup (BL-028 force-reject script) 대상.
        """
        stmt = (
            select(Order)
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .where(Order.submitted_at < cutoff)  # type: ignore[operator, arg-type]
            .where(Order.exchange_order_id.is_(None))  # type: ignore[union-attr]
            .order_by(Order.submitted_at.asc())  # type: ignore[union-attr]
            .limit(100)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def get_daily_summary(self, date: _dt_module.date) -> tuple[Decimal, int, int]:
        """특정 날짜(UTC)의 일일 요약.

        Returns:
            (total_realized_pnl, filled_count, rejected_count)
        """
        day_start = datetime(date.year, date.month, date.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        pnl_result = await self.session.execute(
            select(func.coalesce(func.sum(Order.realized_pnl), 0))
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.filled_at >= day_start)  # type: ignore[operator, arg-type]
            .where(Order.filled_at < day_end)  # type: ignore[operator, arg-type]
        )
        total_pnl = Decimal(str(pnl_result.scalar_one() or 0))

        filled_result = await self.session.execute(
            select(func.count(Order.id))  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.filled_at >= day_start)  # type: ignore[operator, arg-type]
            .where(Order.filled_at < day_end)  # type: ignore[operator, arg-type]
        )
        filled_count = filled_result.scalar_one() or 0

        rejected_result = await self.session.execute(
            select(func.count(Order.id))  # type: ignore[arg-type]
            .where(Order.state == OrderState.rejected)  # type: ignore[arg-type]
            .where(Order.created_at >= day_start)  # type: ignore[arg-type]
            .where(Order.created_at < day_end)  # type: ignore[arg-type]
        )
        rejected_count = rejected_result.scalar_one() or 0

        return total_pnl, int(filled_count), int(rejected_count)

    # --- Idempotency 동시성 제어 (Sprint 5 M2 advisory lock 패턴) ---

    async def acquire_idempotency_lock(self, key: str) -> None:
        """PG advisory lock (tx-scoped). Sprint 11 Phase E 에서 Redis wrapping 은
        Service layer 로 이동 (`async with RedisLock(...): await service.execute(...)`).
        Repository 는 PG advisory 만 담당 — tx 경계 + UNIQUE 제약 + IntegrityError fallback.
        """
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": key},
        )


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


# ── Sprint 26: Live Signal Auto-Trading ────────────────────────────────────


# interval → seconds CASE expression (list_active_due 에서 SQL-side 필터)
_INTERVAL_SECONDS_CASE = (
    "CASE interval "
    "WHEN '1m'  THEN INTERVAL '60 seconds' "
    "WHEN '5m'  THEN INTERVAL '300 seconds' "
    "WHEN '15m' THEN INTERVAL '900 seconds' "
    "WHEN '1h'  THEN INTERVAL '3600 seconds' "
    "END"
)


class LiveSignalSessionRepository:
    """Sprint 26 — Pine signal evaluate session CRUD + race-safe bar claim.

    LESSON-019 commit-spy 의무 — Service mutation 메서드 마다 await commit().
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, sess: LiveSignalSession) -> LiveSignalSession:
        self.session.add(sess)
        await self.session.flush()
        return sess

    async def get_by_id(self, session_id: UUID) -> LiveSignalSession | None:
        result = await self.session.execute(
            select(LiveSignalSession).where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def list_active_by_user(self, user_id: UUID) -> Sequence[LiveSignalSession]:
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712  # type: ignore[arg-type]
            .order_by(LiveSignalSession.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def count_active_by_user(self, user_id: UUID) -> int:
        """Sprint 26 quota check — 사용자별 active session ≤ 5."""
        result = await self.session.execute(
            select(func.count(LiveSignalSession.id))  # type: ignore[arg-type]
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712  # type: ignore[arg-type]
        )
        return int(result.scalar_one() or 0)

    async def acquire_quota_lock(self, user_id: UUID) -> None:
        """PG advisory xact lock — quota race 방어 (codex G.0 P3 #3 + plan §3 A.4).

        partial unique index 와 함께 이중 방어 (Sprint 11 advisory pattern).
        """
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"live_session_quota:{user_id}"},
        )

    async def list_active_due(self, now: datetime) -> Sequence[LiveSignalSession]:
        """interval 별 due session list — codex G.0 P2 #3 패턴 + plan §3 A.4.

        is_active=true AND (last_evaluated_bar_time IS NULL
                            OR last_evaluated_bar_time + interval_seconds <= now).
        Beat task evaluate_live_signals 가 1분 fire 마다 호출.
        """
        # _INTERVAL_SECONDS_CASE 는 module-level constant (사용자 input X) — S608 false positive
        stmt = text(
            "SELECT * FROM trading.live_signal_sessions "  # noqa: S608
            "WHERE is_active = true "
            "AND (last_evaluated_bar_time IS NULL "
            f"     OR last_evaluated_bar_time + ({_INTERVAL_SECONDS_CASE}) <= :now) "
            "ORDER BY id"
        )
        result = await self.session.execute(stmt, {"now": now})
        rows = result.mappings().all()
        return [LiveSignalSession(**dict(row)) for row in rows]

    async def try_claim_bar(
        self, session_id: UUID, bar_time: datetime, claim_token: UUID
    ) -> bool:
        """codex G.0 P2 #3 — winner-only bar claim.

        UPDATE WHERE id=session_id AND is_active=true AND
        (last_evaluated_bar_time IS NULL OR last_evaluated_bar_time < bar_time).
        rowcount==1 → True (claim 성공). 0 → False (다른 task 가 이미 claim 또는 같은 bar).

        race-safe: 두 worker 가 같은 bar_time 으로 동시 호출해도 1번만 True 반환.
        """
        result = await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .where(
                or_(
                    LiveSignalSession.last_evaluated_bar_time.is_(None),  # type: ignore[union-attr]
                    LiveSignalSession.last_evaluated_bar_time < bar_time,  # type: ignore[operator,arg-type]
                )
            )
            .values(
                last_evaluated_bar_time=bar_time,
                bar_claim_token=claim_token,
                updated_at=datetime.now(UTC),
            )
        )
        return (result.rowcount or 0) == 1  # type: ignore[attr-defined]

    async def deactivate(self, session_id: UUID, *, at: datetime) -> int:
        """is_active=False + deactivated_at. Service 가 commit 책임."""
        result = await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .values(is_active=False, deactivated_at=at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def get_state(self, session_id: UUID) -> LiveSignalState | None:
        result = await self.session.execute(
            select(LiveSignalState).where(LiveSignalState.session_id == session_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def upsert_state(
        self,
        *,
        session_id: UUID,
        last_strategy_state_report: dict[str, object],
        last_open_trades_snapshot: dict[str, object],
        total_closed_trades: int,
        total_realized_pnl: Decimal,
    ) -> LiveSignalState:
        """INSERT ON CONFLICT DO UPDATE on session_id (1:1 with sessions).

        Service 가 같은 트랜잭션에서 events INSERT + state upsert + commit (codex G.0 P1 #3).
        """
        existing = await self.get_state(session_id)
        if existing is None:
            state = LiveSignalState(
                session_id=session_id,
                last_strategy_state_report=last_strategy_state_report,
                last_open_trades_snapshot=last_open_trades_snapshot,
                total_closed_trades=total_closed_trades,
                total_realized_pnl=total_realized_pnl,
                updated_at=datetime.now(UTC),
            )
            self.session.add(state)
            await self.session.flush()
            return state
        existing.last_strategy_state_report = last_strategy_state_report
        existing.last_open_trades_snapshot = last_open_trades_snapshot
        existing.total_closed_trades = total_closed_trades
        existing.total_realized_pnl = total_realized_pnl
        existing.updated_at = datetime.now(UTC)
        await self.session.flush()
        return existing


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
