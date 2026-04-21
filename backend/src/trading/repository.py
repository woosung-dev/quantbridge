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
        filled_quantity: Decimal | None = None,  # NEW — CCXT partial fill 지원 (ADR-006 / autoplan Eng E7)
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

    async def get_daily_summary(
        self, date: _dt_module.date
    ) -> tuple[Decimal, int, int]:
        """특정 날짜(UTC)의 일일 요약.

        Returns:
            (total_realized_pnl, filled_count, rejected_count)
        """
        day_start = datetime(date.year, date.month, date.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)

        pnl_result = await self.session.execute(
            select(func.coalesce(func.sum(Order.realized_pnl), 0))  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.filled_at >= day_start)  # type: ignore[attr-defined]
            .where(Order.filled_at < day_end)  # type: ignore[attr-defined]
        )
        total_pnl = Decimal(str(pnl_result.scalar_one() or 0))

        filled_result = await self.session.execute(
            select(func.count(Order.id))  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.filled_at >= day_start)  # type: ignore[attr-defined]
            .where(Order.filled_at < day_end)  # type: ignore[attr-defined]
        )
        filled_count = filled_result.scalar_one() or 0

        rejected_result = await self.session.execute(
            select(func.count(Order.id))  # type: ignore[arg-type]
            .where(Order.state == OrderState.rejected)  # type: ignore[arg-type]
            .where(Order.created_at >= day_start)  # type: ignore[attr-defined]
            .where(Order.created_at < day_end)  # type: ignore[attr-defined]
        )
        rejected_count = rejected_result.scalar_one() or 0

        return total_pnl, int(filled_count), int(rejected_count)

    # --- Idempotency 동시성 제어 (Sprint 5 M2 advisory lock 패턴) ---

    async def acquire_idempotency_lock(self, key: str) -> None:
        """pg_advisory_xact_lock — 트랜잭션 종료 시 자동 해제."""
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

    async def get_active(
        self, *, strategy_id: UUID, account_id: UUID
    ) -> KillSwitchEvent | None:
        """spec §2.2 매칭 규칙:
        - cumulative_loss → strategy_id 매칭 (ADR-006 CEO F4)
        - daily_loss, api_error → account_id 매칭
        - resolved_at IS NULL
        """
        stmt = select(KillSwitchEvent).where(
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
        ).order_by(KillSwitchEvent.triggered_at.desc())  # type: ignore[attr-defined]
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

    async def list_recent(
        self, *, limit: int, offset: int
    ) -> Sequence[KillSwitchEvent]:
        result = await self.session.execute(
            select(KillSwitchEvent)
            .order_by(KillSwitchEvent.triggered_at.desc())  # type: ignore[attr-defined]
            .limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def list_by_date(self, date: _dt_module.date) -> Sequence[KillSwitchEvent]:
        """특정 날짜(UTC) 트리거된 Kill Switch 이벤트 목록."""
        day_start = datetime(date.year, date.month, date.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        result = await self.session.execute(
            select(KillSwitchEvent)
            .where(KillSwitchEvent.triggered_at >= day_start)  # type: ignore[attr-defined]
            .where(KillSwitchEvent.triggered_at < day_end)  # type: ignore[attr-defined]
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
