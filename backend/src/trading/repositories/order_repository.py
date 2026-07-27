# trading repository — Order 영속화 + 상태 전이 단독 책임

from __future__ import annotations

import datetime as _dt_module
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
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

    - `symbol` 은 **정확 문자열 동등**이다. 예전에는 두 ingress 가 심볼을 정규화하지
      않아 표기가 다른 웹훅 주문이 스코프에서 조용히 빠지는 구멍이 있었다. BL-454 가
      두 ingress(`RegisterLiveSessionRequest.symbol` = `NormalizedSymbol`,
      `parse_tv_payload`)를 canonical(`BTC/USDT`)로 정규화해 **그 표기가 들어올 경로를
      닫았다**. dispatch 와 수동 청산은 세션 심볼을 그대로 복사하므로 구조적으로 항상
      일치한다. 술어를 느슨하게 바꿀 이유는 없다.

    수용한 트레이드오프 1 종 — 되돌리기 전에 `docs/archive/sprints/exit-money-path/` 를 읽을 것.

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


@dataclass(frozen=True, slots=True)
class SessionRealizedPnl:
    """세션 스코프 실현 손익을 출처별로 쪼갠 값 (BL-458).

    `Order.realized_pnl_synced_at` 이 출처 마커다 — NULL = pine_v2 추정, 값 있음 =
    거래소 확정 `closedPnl`.

    세 카운트는 스코프를 **정확히 분할**한다. `unrecorded_count` 는 체결됐지만
    `realized_pnl` 이 아직 NULL 인 주문이다(수동 청산은 값 없이 들어오고 스윕이 나중에
    채운다). 그 행은 확정도 추정도 아니라 **셀 숫자가 없으므로** 금액이 아니라 개수로만
    표면화한다 — 두 값 라벨 체계로는 표현할 수 없는 세 번째 상태다.
    """

    confirmed: Decimal
    estimated: Decimal
    confirmed_count: int
    estimated_count: int
    unrecorded_count: int

    @property
    def total(self) -> Decimal:
        """확정 + 추정. 게이트가 쓰는 값은 여전히 이 합계다 — 라벨은 가산적이다."""
        return Decimal(str(self.confirmed)) + Decimal(str(self.estimated))


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

    async def get_state_and_exchange_id_fresh(
        self, order_id: UUID
    ) -> tuple[OrderState, str | None] | None:
        """BL-499 — 식별맵을 우회해 DB 의 현재 `state` 와 `exchange_order_id` 를 읽는다.

        `exchange_order_id` 가 함께 필요한 이유 — `submitted` 인데 거래소 id 가 없는
        행은 **경합 패배가 아니라 제출 중단**이다(dispatch 가 `pending → submitted` 를
        커밋한 뒤 거래소 왕복에서 죽으면 그 상태로 영구 고착한다). 둘을 같은 라벨로
        묶으면 영구 장애가 1회성 경합 카운터에 섞여 사라진다.
        """
        result = await self.session.execute(
            select(cast(Any, Order.state), cast(Any, Order.exchange_order_id)).where(
                Order.id == order_id  # type: ignore[arg-type]
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def get_state_fresh(self, order_id: UUID) -> OrderState | None:
        """BL-499 — 식별맵을 우회해 DB 의 현재 `state` 를 읽는다. 행이 없으면 None.

        ★`get_by_id` 로는 안 된다. 같은 세션이 이미 그 행을 적재했다면 SQLAlchemy
        식별맵이 **적재 당시의 인스턴스**를 그대로 돌려주므로 경합 상대가 커밋한
        최신 상태를 못 본다. 컬럼 하나만 select 하면 ORM 객체를 거치지 않아
        READ COMMITTED 아래에서 항상 최신 커밋 값을 본다.
        """
        result = await self.session.execute(
            select(cast(Any, Order.state)).where(Order.id == order_id)  # type: ignore[arg-type]
        )
        state: OrderState | None = result.scalar_one_or_none()
        return state

    async def get_by_idempotency_key(self, key: str) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.idempotency_key == key)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def list_resting_conditional_entries(
        self, strategy_id: UUID, exchange_account_id: UUID
    ) -> Sequence[Order]:
        """한 전략·계정의 미체결 조건부 진입 주문만 최대 100건 조회한다."""
        stmt = (
            select(Order)
            .where(Order.state.in_([OrderState.pending, OrderState.submitted]))  # type: ignore[attr-defined]
            .where(Order.trigger_price.is_not(None))  # type: ignore[union-attr]
            .where(Order.reduce_only.is_(False))  # type: ignore[attr-defined]
            .where(Order.strategy_id == strategy_id)  # type: ignore[arg-type]
            .where(Order.exchange_account_id == exchange_account_id)  # type: ignore[arg-type]
            .order_by(Order.submitted_at.asc())  # type: ignore[union-attr]
            .limit(100)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_orphan_conditional_entries(self) -> Sequence[Order]:
        """비활성 또는 없는 라이브 세션 소유의 조건부 진입 주문을 찾는다."""
        from src.trading.services.conditional_entry_planner import parse_conditional_entry_key

        stmt = (
            select(Order)
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .where(Order.trigger_price.is_not(None))  # type: ignore[union-attr]
            .where(Order.reduce_only.is_(False))  # type: ignore[attr-defined]
            .order_by(Order.submitted_at.asc())  # type: ignore[union-attr]
        )
        candidates = (await self.session.execute(stmt)).scalars().all()
        parsed_orders = [(order, parse_conditional_entry_key(order.idempotency_key)) for order in candidates]
        session_ids = {parsed[0] for _, parsed in parsed_orders if parsed is not None}
        if not session_ids:
            return []

        active_session_ids = set(
            (
                await self.session.execute(
                    select(cast(Any, LiveSignalSession.id))
                    .where(cast(Any, LiveSignalSession.id).in_(session_ids))
                    .where(cast(Any, LiveSignalSession.is_active) == True)  # noqa: E712
                )
            ).scalars()
        )
        return [
            order
            for order, parsed in parsed_orders
            if parsed is not None and parsed[0] not in active_session_ids
        ]

    async def list_stale_conditional_entries(self, cutoff: datetime) -> Sequence[Order]:
        """활성 여부와 무관하게 오래된 submitted 조건부 진입을 최대 100건 찾는다."""
        stmt = (
            select(Order)
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .where(Order.trigger_price.is_not(None))  # type: ignore[union-attr]
            .where(Order.reduce_only.is_(False))  # type: ignore[attr-defined]
            .where(Order.submitted_at < cutoff)  # type: ignore[operator, arg-type]
            .order_by(Order.submitted_at.asc())  # type: ignore[union-attr]
            .limit(100)
        )
        return (await self.session.execute(stmt)).scalars().all()

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

    async def realized_pnl_split_for_session(self, scope: SessionScope) -> SessionRealizedPnl:
        """세션 스코프 안의 체결 주문 실현 손익을 **출처별로 쪼개서** 돌려준다.

        BL-444 — 예전에는 `live_signal_events.order_id` 서브셀렉트였다. 이벤트는
        dispatch 경로에서만 생기므로 수동 청산(`ClosePositionService`)과 TV 웹훅
        주문의 손익을 loss-limit 알림이 **구조적으로 못 봤다**. 스코프 기준으로
        바꿔 세 쓰기 경로를 모두 덮는다.

        BL-458 — 합계 하나만 돌려주던 시그니처를 바꾼 이유. `Decimal` 을 돌려주는
        메서드를 남겨두면 "출처를 안 보고 합산" 이 계속 가능하고, 그게 BL-458 이 지적한
        결함 그 자체다. 타입으로 표현 불가하게 만든다 — `SessionScope`/`from_live_session`
        이 이 파일에서 이미 쓴 수와 같다.

        ★**술어는 하나도 좁히지 않는다.** 출처별 값은 같은 스코프 위의 두 번째 집계
        (`FILTER`)이지 필터가 아니다. `synced_at IS NOT NULL` 로 합계를 좁히면 체결부터
        스윕 도착까지의 손실이 통째로 사라져 자본 보호 게이트가 fail-open 한다.
        """
        synced_at_col = Order.realized_pnl_synced_at
        pnl_col = Order.realized_pnl
        recorded = pnl_col.is_not(None)  # type: ignore[union-attr]
        confirmed = synced_at_col.is_not(None)  # type: ignore[union-attr]
        stmt = select(
            func.coalesce(func.sum(pnl_col).filter(confirmed), 0),
            func.coalesce(func.sum(pnl_col).filter(synced_at_col.is_(None)), 0),  # type: ignore[union-attr]
            func.count().filter(recorded, confirmed),
            func.count().filter(recorded, synced_at_col.is_(None)),  # type: ignore[union-attr]
            func.count().filter(pnl_col.is_(None)),  # type: ignore[union-attr]
        ).where(*_session_scope_where(scope))
        row = (await self.session.execute(stmt)).one()
        return SessionRealizedPnl(
            confirmed=Decimal(str(row[0] or 0)),
            estimated=Decimal(str(row[1] or 0)),
            confirmed_count=int(row[2] or 0),
            estimated_count=int(row[3] or 0),
            unrecorded_count=int(row[4] or 0),
        )

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

    async def list_existing_ids(
        self, account_id: UUID, order_ids: Collection[UUID]
    ) -> frozenset[UUID]:
        """계정 스코프로 우리 `Order.id` 의 **실재**만 확인한다 (BL-457).

        묻는 것이 membership 하나뿐이므로 최종 형태를 그대로 돌려준다 — 호출부에서
        변환할 일이 없고, 인덱싱해 쓰고 싶은 유혹도 없앤다.

        ★**`state` 필터를 넣지 않는다.** `list_by_exchange_order_ids` 가 이미
        `state == filled` 로 매칭을 시도하므로, link-id 실재 확인이 필요한 행은
        **정의상 그 매칭에 실패한 주문**이다 — `submitted`(종결 증거 미관측) ·
        부분체결 후 `cancelled` · `pending` 중 프로세스 사망. `state` 필터는 이 확인이
        존재하는 이유인 모집단을 정확히 배제해 **진짜 우리 청산을 외부 청산으로 뒤집고
        운영자를 호출한다.** 같은 이유로 `list_filled_for_attribution`(= `filled` +
        `limit=500`)의 결과를 재사용하는 것도 틀린 해법이다.

        계정 스코프인 이유 — `Order.id` 는 UUID4 라 전역 충돌이 위험한 게 아니다.
        **다른 계정의 주문 id 를 이 계정의 청산으로 주장하는 것**이 위험하다.
        """
        if not order_ids:
            return frozenset()
        stmt = (
            select(Order.id)  # type: ignore[call-overload]
            .where(Order.exchange_account_id == account_id)
            .where(Order.id.in_(order_ids))  # type: ignore[attr-defined]
        )
        return frozenset((await self.session.execute(stmt)).scalars().all())

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
        self,
        order_id: UUID,
        *,
        error_message: str,
        failed_at: datetime,
        filled_price: Decimal | None = None,
        filled_quantity: Decimal | None = None,
    ) -> int:
        values: dict[str, object] = {
            "state": OrderState.rejected,
            "error_message": error_message[:2000],
            "filled_at": failed_at,
        }
        if filled_quantity is not None and filled_quantity != 0:
            values["filled_price"] = filled_price
            values["filled_quantity"] = filled_quantity
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state.in_([OrderState.pending, OrderState.submitted]))  # type: ignore[attr-defined]
            .values(**values)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def transition_submitted_without_exchange_id_to_rejected(
        self, order_id: UUID, *, error_message: str, failed_at: datetime
    ) -> int:
        """Janitor 전용 CAS. 늦은 attach 와 경합하면 DB 상태를 바꾸지 않는다."""
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.submitted)  # type: ignore[arg-type]
            .where(Order.exchange_order_id.is_(None))  # type: ignore[union-attr]
            .values(
                state=OrderState.rejected,
                error_message=error_message[:2000],
                filled_at=failed_at,
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def transition_to_cancelled(
        self,
        order_id: UUID,
        *,
        cancelled_at: datetime,
        filled_price: Decimal | None = None,
        filled_quantity: Decimal | None = None,
    ) -> int:
        values: dict[str, object] = {
            "state": OrderState.cancelled,
            "filled_at": cancelled_at,
        }
        if filled_quantity is not None and filled_quantity != 0:
            values["filled_price"] = filled_price
            values["filled_quantity"] = filled_quantity
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id)  # type: ignore[arg-type]
            .where(Order.state.in_([OrderState.pending, OrderState.submitted]))  # type: ignore[attr-defined]
            .values(**values)
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
            .where(Order.trigger_price.is_(None))  # type: ignore[union-attr]
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
            .where(Order.trigger_price.is_(None))  # type: ignore[union-attr]
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
