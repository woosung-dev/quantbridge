# trading repository — Order 영속화 + 상태 전이 단독 책임

from __future__ import annotations

import datetime as _dt_module
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import ExchangeAccount, LiveSignalSession, Order, OrderState


@dataclass(frozen=True, slots=True)
class SessionScope:
    """한 라이브 세션이 소유하는 주문의 범위. 생성 경로는 `from_live_session` 하나뿐이다.

    왜 값 객체인가 — BL-444(loss-limit 알림)와 BL-445(세션 에쿼티 커브)는 서로 다른
    두 버그가 아니라 **같은 스코프 버그가 두 군데 있는 것**이었다. 두 소비처가 각자
    술어를 조립하면 그 병이 그대로 재생산되므로, 스코프 정의를 이 타입 하나로 막고
    `_session_scope_where` 한 곳에서만 SQL 로 번역한다.

    수용한 트레이드오프 2 종 — 되돌리기 전에 `docs/exit-money-path/` 를 읽을 것.

    - `symbol` 은 **정확 문자열 동등**이다. 세션 등록(`RegisterLiveSessionRequest`)도
      TV 웹훅(`parse_tv_payload`)도 심볼을 정규화하지 않으므로, 표기가 다른 웹훅
      주문은 스코프에서 조용히 빠진다. dispatch 와 수동 청산은 세션 심볼을 그대로
      복사하므로 구조적으로 항상 일치한다.
    - 창은 `filled_at` 기준 반열림 `[started_at, ended_at)` 이다. 세션 종료 뒤에
      체결된 주문(늦은 체결)은 인접 세션이 있으면 그쪽으로, 없으면 어디에도 안
      잡힌다. `filled_at` 은 거래소 체결시각이 아니라 우리 관측시각이다.
    """

    strategy_id: UUID
    exchange_account_id: UUID
    symbol: str
    started_at: datetime
    ended_at: datetime | None

    @classmethod
    def from_live_session(cls, session: LiveSignalSession) -> SessionScope:
        """세션 행에서 스코프를 뽑는다. 호출부가 필드를 임의 조합하지 못하게 막는 유일 입구."""
        return cls(
            strategy_id=session.strategy_id,
            exchange_account_id=session.exchange_account_id,
            symbol=session.symbol,
            started_at=session.created_at,
            ended_at=session.deactivated_at,
        )


def _session_scope_where(scope: SessionScope) -> list[Any]:
    """세션 스코프를 SQL 술어로 번역하는 **유일한** 자리."""
    predicates: list[Any] = [
        Order.strategy_id == scope.strategy_id,
        Order.exchange_account_id == scope.exchange_account_id,
        Order.symbol == scope.symbol,
        Order.state == OrderState.filled,
        Order.filled_at.is_not(None),  # type: ignore[union-attr]
        Order.filled_at >= scope.started_at,  # type: ignore[operator]
    ]
    # 활성 세션은 `deactivated_at IS NULL` 이라 상한이 없다.
    if scope.ended_at is not None:
        predicates.append(Order.filled_at < scope.ended_at)  # type: ignore[operator]
    return predicates


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
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        states: Sequence[OrderState] | None = None,
    ) -> tuple[Sequence[Order], int]:
        """Join ExchangeAccount → user_id 매칭. Sprint 5 M4 pagination 스타일."""
        total_stmt = (
            select(func.count(Order.id))  # type: ignore[arg-type]
            .join(ExchangeAccount, Order.exchange_account_id == ExchangeAccount.id)  # type: ignore[arg-type]
            .where(ExchangeAccount.user_id == user_id)  # type: ignore[arg-type]
        )
        if states:
            total_stmt = total_stmt.where(Order.state.in_(states))  # type: ignore[attr-defined]
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(Order)
            .join(ExchangeAccount, Order.exchange_account_id == ExchangeAccount.id)  # type: ignore[arg-type]
            .where(ExchangeAccount.user_id == user_id)  # type: ignore[arg-type]
            .order_by(Order.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        if states:
            stmt = stmt.where(Order.state.in_(states))  # type: ignore[attr-defined]
        return (await self.session.execute(stmt)).scalars().all(), total

    async def list_filled_realized_for_session(self, scope: SessionScope) -> Sequence[Order]:
        """세션 스코프 안의 체결 + realized_pnl 보유 주문만 filled_at ASC.

        live-session 대시보드의 "실현 손익" 이 Pine 시뮬레이션 재생이 아니라
        실제 거래소 체결 결과를 반영하도록 하는 조회 (2026-07-01 dogfood 발견).
        BL-445 — 예전에는 `(strategy, account)` 튜플만 봐서 같은 튜플 위의 비활성
        세션들이 하나의 커브를 공유했다. 이제 세션 창과 심볼이 함께 걸린다.
        """
        stmt = (
            select(Order)
            .where(*_session_scope_where(scope))
            .where(Order.realized_pnl.is_not(None))  # type: ignore[union-attr]
            .order_by(Order.filled_at.asc())  # type: ignore[union-attr]
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def sum_filled_realized_pnl_for_session(self, scope: SessionScope) -> Decimal:
        """세션 스코프 안의 체결 주문 실현 손익 합계.

        BL-444 — 예전에는 `live_signal_events.order_id` 서브셀렉트였다. 이벤트는
        dispatch 경로에서만 생기므로 수동 청산(`ClosePositionService`)과 TV 웹훅
        주문의 손익을 loss-limit 알림이 **구조적으로 못 봤다**. 스코프 기준으로
        바꿔 세 쓰기 경로를 모두 덮는다.
        """
        stmt = select(func.coalesce(func.sum(Order.realized_pnl), 0)).where(
            *_session_scope_where(scope)
        )
        return Decimal(str((await self.session.execute(stmt)).scalar_one() or 0))

    # --- 3-guard 상태 전이 (Sprint 4 BacktestRepository 패턴 계승) ---

    async def transition_to_submitted(self, order_id: UUID, *, submitted_at: datetime) -> int:
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.pending)  # type: ignore[arg-type]
            .values(state=OrderState.submitted, submitted_at=submitted_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def backfill_exchange_realized_pnl(
        self, order_id: UUID, *, realized_pnl: Decimal, synced_at: datetime
    ) -> int:
        """거래소 확정 손익만 기록한다. 실패 조회가 kill-switch 입력을 NULL로 만들 수 없어야 한다."""
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.realized_pnl_synced_at.is_(None))  # type: ignore[union-attr]
            .values(realized_pnl=realized_pnl, realized_pnl_synced_at=synced_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def list_unsynced_reduce_only_since(
        self, cutoff: datetime, *, limit: int = 200
    ) -> Sequence[Order]:
        """거래소 확정 손익이 아직 없는 최근 reduce-only 체결 주문을 계정·심볼 순으로 조회한다."""
        stmt = (
            select(Order)
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.reduce_only.is_(True))  # type: ignore[attr-defined]
            .where(Order.filled_at >= cutoff)  # type: ignore[operator, arg-type]
            .where(Order.exchange_order_id.is_not(None))  # type: ignore[union-attr]
            .where(Order.realized_pnl_synced_at.is_(None))  # type: ignore[union-attr]
            .order_by(
                Order.exchange_account_id,  # type: ignore[arg-type]
                Order.symbol,
                Order.filled_at,  # type: ignore[arg-type]
            )
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_by_exchange_order_ids(
        self, account_id: UUID, exchange_order_ids: Sequence[str]
    ) -> Sequence[Order]:
        """계정 스코프로 거래소 주문 id를 역조회한다. 전역 조회는 계정 간 id 충돌에 취약하다."""
        if not exchange_order_ids:
            return []
        stmt = (
            select(Order)
            .where(Order.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(Order.exchange_order_id.in_(exchange_order_ids))  # type: ignore[union-attr]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_unsynced_reduce_only(
        self, account_id: UUID, *, limit: int = 500
    ) -> Sequence[Order]:
        """시간창 없이 미동기화 reduce-only 체결 주문 전량을 조회한다."""
        stmt = (
            select(Order)
            .where(Order.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.reduce_only.is_(True))  # type: ignore[attr-defined]
            .where(Order.exchange_order_id.is_not(None))  # type: ignore[union-attr]
            .where(Order.realized_pnl_synced_at.is_(None))  # type: ignore[union-attr]
            .order_by(Order.filled_at.asc())  # type: ignore[union-attr]
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_synced_reduce_only(
        self, account_id: UUID, *, limit: int = 500
    ) -> Sequence[Order]:
        """이미 거래소 확정으로 표시된 reduce-only 체결 주문.

        체결 직후 refresh 는 원장을 거치지 않고 **단일 조회 결과**를 CAS 한다. 분할 행
        중 일부만 보이는 순간에 걸리면 부분합이 synced 로 고정되고, 미동기화 술어를 쓰는
        스윕은 그 주문을 영영 건너뛴다. 원장 합계와 대조해 되돌릴 수 있게 따로 조회한다.
        """
        stmt = (
            select(Order)
            .where(Order.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.reduce_only.is_(True))  # type: ignore[attr-defined]
            .where(Order.exchange_order_id.is_not(None))  # type: ignore[union-attr]
            .where(Order.realized_pnl_synced_at.is_not(None))  # type: ignore[union-attr]
            .order_by(Order.filled_at.desc())  # type: ignore[union-attr]
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def resync_exchange_realized_pnl(
        self, order_id: UUID, *, realized_pnl: Decimal, synced_at: datetime
    ) -> int:
        """원장 합계가 저장값과 다를 때만 확정 손익을 정정한다.

        값이 같으면 rowcount 0 이라 멱등하다. 이미 확정된 행을 건드리는 유일한 경로이므로
        `state == filled` 와 `realized_pnl_synced_at IS NOT NULL` 을 함께 요구해
        미동기화 행의 정상 백필 경로(`backfill_exchange_realized_pnl`)와 겹치지 않게 한다.
        """
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.realized_pnl_synced_at.is_not(None))  # type: ignore[union-attr]
            .where(Order.realized_pnl.is_distinct_from(realized_pnl))  # type: ignore[union-attr]
            .values(realized_pnl=realized_pnl, realized_pnl_synced_at=synced_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def list_filled_for_attribution(
        self, account_id: UUID, *, limit: int = 500
    ) -> Sequence[Order]:
        """귀속 추정 입력으로 해당 계정의 filled 주문을 시간순으로 조회한다.

        ★가장 **최근** limit 건을 가져온 뒤 시간 오름차순으로 되돌린다. 오름차순 LIMIT 로
        자르면 오래된 주문만 남아 최근 청산의 진입이 표본 밖으로 밀리고, 순포지션 합산이
        절단 부산물이 돼 엉뚱한 전략으로 inferred 가 나간다.
        """
        stmt = (
            select(Order)
            .where(Order.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(Order.filled_at.is_not(None))  # type: ignore[union-attr]
            .order_by(Order.filled_at.desc())  # type: ignore[union-attr]
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return sorted(rows, key=lambda order: order.filled_at or datetime.min.replace(tzinfo=UTC))

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
        # MP-1: realized_pnl 은 주문 생성(close 이벤트) 시점에 이미 기록되어 있다.
        # 명시 인자가 있을 때만 갱신 (exchange-reported closedPnl 등 follow-up A 경로).
        # None 이면 생성 시점 값을 보존 — 이전엔 무조건 NULL 로 덮어써서 kill-switch
        # CumulativeLoss/DailyLoss 평가기가 SUM=0 으로 영구 inert 였다.
        # filled_quantity 무조건 갱신은 submitted 상태 CAS가 단일 winner를 보장하므로 안전하다.
        values: dict[str, object] = {
            "state": OrderState.filled,
            "exchange_order_id": exchange_order_id,
            "filled_price": filled_price,
            "filled_quantity": filled_quantity,
            "filled_at": filled_at,
        }
        if realized_pnl is not None:
            values["realized_pnl"] = realized_pnl
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .values(**values)
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

    async def transition_pending_to_cancelled(
        self, order_id: UUID, *, cancelled_at: datetime
    ) -> int:
        """CF4 — pending(거래소 미발주) 주문만 DB-cancel. submitted(거래소 live) 는 제외.

        router 의 cancel 경로에서 pending→submitted race 시에도 거래소에 live 한 주문을
        DB-only cancel (orphan) 하지 않도록 state==pending 조건부 UPDATE. submitted 는
        cancel_order_task 가 거래소 취소 성공 후 transition_to_cancelled 로 처리.
        """
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.pending)  # type: ignore[arg-type]
            .values(state=OrderState.cancelled, filled_at=cancelled_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def attach_exchange_order_id(self, order_id: UUID, exchange_order_id: str) -> int:
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

    async def list_stuck_submission_interrupted(self, cutoff: datetime) -> Sequence[Order]:
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
