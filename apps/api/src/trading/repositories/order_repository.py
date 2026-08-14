# trading repository — Order 영속화 + 상태 전이 단독 책임

from __future__ import annotations

import datetime as _dt_module
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import (
    ExchangeAccount,
    ExchangeExit,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
)

# 「이 주문이 청산했는가」의 정본 술어 — 거래소 원장이 그 주문의 청산 행을 갖고 있는가([BL-438]).
# ★`JOIN` 이 아니라 `EXISTS` 다. `Order : ExchangeExit` 는 1:N(분할 행 — 한 청산이 여러 행으로
#   쪼개져 적재된다)이라 JOIN 은 같은 Order 를 N번 돌려준다. 그러면 ⑴ `limit` 예산이 분할 행
#   수에 잠식돼 오래된 주문이 영영 안 돌아오고 ⑵ 스윕 루프가 같은 주문을 N번 돌아
#   `applied`/`already_synced` 계수가 부풀어 관측이 거짓말을 한다. EXISTS 는 행을 복제하지 않는다.
# ★계정 축을 함께 건다 — `exchange_order_id` 는 거래소가 발급하므로 계정 간 충돌이 가능하고,
#   `list_by_exchange_order_ids` 가 같은 이유로 계정 스코프를 쓴다.
_HAS_EXCHANGE_EXIT_ROW = (
    select(ExchangeExit.id)  # type: ignore[call-overload]
    .where(ExchangeExit.exchange_account_id == Order.exchange_account_id)
    .where(ExchangeExit.exchange_order_id == Order.exchange_order_id)
    .correlate(Order)
    .exists()
)

# 그 주문에 대한 **원장 청산 손익 합계** ([BL-731]). 분할 행을 합치므로 `SUM` 이다.
# ★계정 축이 걸려 있으므로 [BL-725] 의 중복 290행은 이 합계를 부풀리지 않는다 — 그 중복은
#   같은 Bybit uid 의 **앱 계정 행 둘** 사이로 갈라져 있고, 한 계정 안에서는
#   `Index("uq_exchange_exits_row", "exchange_account_id", "row_hash", unique=True)` 가 막는다.
#   같은 근거가 `exchange_exit_repository.aggregate_closed_pnl` 독스트링에 이미 적혀 있다.
# ★원장 행이 없으면 `NULL` 이다. `IS DISTINCT FROM` 은 그것을 「다르다」로 읽으므로
#   **반드시 `_HAS_EXCHANGE_EXIT_ROW` 와 함께** 써라 — 혼자 쓰면 원장에 증거가 없는 주문까지
#   재검증 대상이 되고 스윕은 `ledger_pnl is None` 으로 걸러 매 tick 헛돈다.
# ★`type: ignore` 자리가 위와 다르다 — `select(ExchangeExit.id)` 는 `call-overload` 를 눌러
#   뒤 체인이 `Any` 가 되지만, `select(func.sum(...))` 은 그 오버로드에 안 걸려 타입이 살아남고
#   `.where()` 인자에서 걸린다(SQLModel 속성이 인스턴스 타입으로 추론된다). 그래서 `arg-type` 이다.
_EXCHANGE_EXIT_PNL_SUM = (
    select(func.sum(ExchangeExit.closed_pnl))
    .where(ExchangeExit.exchange_account_id == Order.exchange_account_id)  # type: ignore[arg-type]
    .where(ExchangeExit.exchange_order_id == Order.exchange_order_id)  # type: ignore[arg-type]
    .correlate(Order)
    .scalar_subquery()
)

# ★`src.trading.services.*` 를 모듈 수준에서 import 하지 마라 — 순환이다.
#   `services/__init__` 이 `order_service` 를 물고, 그게 `kill_switch` 를 거쳐 이 파일로
#   되돌아온다(`ImportError: partially initialized module`). 그래서 이 파일의 기존
#   `list_orphan_conditional_entries` 도 함수 안에서 지연 import 한다. 같은 관용구를 따른다.

# 세션 스코프 창을 어느 시각 축에 걸 것인가. `terminal` 이 기존 동작이다.
ScopeWindow = Literal["terminal", "created"]


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


@dataclass(frozen=True, slots=True)
class LedgerFill:
    """세션 스코프 안에서 **관측된** 체결 1건 (BL-544).

    엔진 재생이 모르는 사실의 원천이다. 공백 동안 worker/beat 가 멈춰 있어도 `ws-stream`
    이 살아 있으면 체결은 원장에 남는다 — 실측에서 세션이 죽기 4분 36초 전에 이미
    `state=filled` 가 찍혀 있었다.

    ★`filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**이다(`SessionScope` 주석).
    그래서 이 값으로 "몇 번째 bar 에서 체결됐나" 를 정하면 관측 지연만큼 틀린 bar 를 고른다.
    이 타입이 답하는 질문은 **"그 창 안에 무엇이 체결됐나"** 하나뿐이다.
    """

    order_id: UUID
    idempotency_key: str | None
    side: OrderSide
    filled_quantity: Decimal | None
    filled_price: Decimal | None
    filled_at: datetime
    reduce_only: bool


@dataclass(frozen=True, slots=True)
class EntryAttemptRow:
    """진입 **발주 시도** 1건의 원장 사실 (BL-536).

    ★`LedgerFill` 과 다른 타입인 이유 — 저쪽은 "무엇이 체결됐나" 만 묻고 체결되지 않은
    행을 구조적으로 못 본다. 진입 완결성은 정반대로 **체결되지 않은 것**이 답이라,
    같은 타입을 재사용하면 분모가 조용히 틀린다.

    ★`terminal_at` 은 `Order.filled_at` 컬럼이다. 이름과 달리 체결 시각이 아니라
    **terminal 시각**이고 `rejected`/`cancelled` 전이도 여기에 쓴다. 창(`created_at`)
    밖의 terminal 을 "판정 유예" 로 세기 위해 싣는다.

    ★`error_message` 는 거래소 retCode 원문을 담는다. 거절 사유를 라벨이 아니라 원문에서
    읽어야 하는 이유는 `metrics._normalize_exchange_order_response_reason` 이 이미
    저카디널리티로 뭉갠 값만 metric 에 남기기 때문이다 — 원장이 원문의 유일한 보관처다.
    """

    order_id: UUID
    idempotency_key: str | None
    state: OrderState
    side: OrderSide
    quantity: Decimal
    filled_quantity: Decimal | None
    created_at: datetime
    terminal_at: datetime | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class RestingIntervalRow:
    """조건부 진입 주문이 resting 상태로 존재한 시간 구간의 원장 사실."""

    strategy_id: UUID
    exchange_account_id: UUID
    created_at: datetime
    closed_at: datetime | None


@dataclass(frozen=True, slots=True)
class LiveEntryKeyRow:
    """전 세션 라이브 진입 key 후보와 생성 시각."""

    idempotency_key: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EntryRejectionRow:
    """진입 거절 1건의 Python 판정 입력."""

    order_id: UUID
    idempotency_key: str | None
    error_message: str | None
    created_at: datetime


# 한 창에서 훑을 진입 시도 상한. 체결 조회와 같은 이유로 `limit + 1` 을 가져와 호출부가
# **절단을 감지**한다 — 조용히 잘린 원장은 분모를 작게 만들어 유실률을 낙관적으로 왜곡한다.
ENTRY_ATTEMPT_SCAN_LIMIT = 5000


# 한 공백 창에서 훑을 체결 상한. 호출부가 **절단을 감지**할 수 있어야 하므로 조회는
# 이 값 + 1 건을 가져온다 — 조용한 절단은 부분 원장으로 순포지션을 만들고, 그 값은
# 실제보다 작아 엔진을 실제보다 flat 하게 심는다.
LEDGER_FILL_SCAN_LIMIT = 200


# 체결분을 **보존한 채** 종결될 수 있는 상태들 (BL-544 R1).
#
# `filled` 만 보면 부분체결이 통째로 안 보인다. `transition_to_cancelled` 와
# `transition_to_rejected` 는 둘 다 `filled_quantity is not None and != 0` 일 때
# `filled_price`/`filled_quantity` 를 values 에 넣고, `conditional_entry_janitor.py:132-146`
# 이 거래소 probe 의 부분체결 수량을 그 두 전이 모두에 넘긴다. 즉 **거래소에는 포지션이
# 남았는데 상태는 `cancelled`** 인 행이 실재한다.
_STATES_THAT_CAN_CARRY_FILLS = (OrderState.filled, OrderState.cancelled, OrderState.rejected)


def _session_scope_where(
    scope: SessionScope,
    *,
    states: Sequence[OrderState] | None = (OrderState.filled,),
    window: ScopeWindow = "terminal",
) -> list[Any]:
    """세션 스코프를 SQL 술어로 번역하는 **유일한** 자리.

    기본값(`states=(filled,)`, `window="terminal"`)이 오늘의 동작 그대로라 기존 4 소비처
    (`list_filled_realized_for_session` · `list_fills_since` ·
    `realized_pnl_split_for_session` · `parity_repository`)는 인자를 주지 않아
    **동작이 불변**이다. 술어를 복사해 두 벌로 만드는 대신 파라미터로 연 이유가 그것이다 —
    스코프 SQL 번역은 계속 이 자리 하나다.

    ★`filled_at` 은 이름과 달리 **terminal 시각**이다. `transition_to_{filled,rejected,
    cancelled}` 가 모두 이 컬럼에 쓴다(`models.py:263-265` 주석이 명시한다). 그래서 창
    술어(`>= started_at` / `< ended_at`)는 상태 집합을 넓혀도 그대로 유효하다.

    두 파라미터가 여는 것 (BL-536):

    - `states=None` — 상태 술어를 아예 안 건다. 진입 **시도**의 분모에는 아직 종결되지
      않은 `pending`/`submitted` 도 들어가야 한다. 기본값으로는 구조적으로 못 본다.
    - `window="created"` — 창을 `created_at` 으로 옮기고 `filled_at IS NOT NULL` 을 뺀다.
      terminal 창으로는 **아직 종결되지 않은 행이 전부 사라져** 분모가 "이미 끝난 것" 만
      남는다. 진입 완결성은 "그 창에 **시도된** 것" 을 물으므로 생성 시각이 맞는 축이다.
      `created_at` 은 NOT NULL 이라 별도 null 검사가 필요 없다.
    """
    time_column = Order.created_at if window == "created" else Order.filled_at
    predicates: list[Any] = [
        Order.strategy_id == scope.strategy_id,
        Order.exchange_account_id == scope.exchange_account_id,
        Order.symbol == scope.symbol,
    ]
    if states is not None:
        predicates.append(Order.state.in_(states))  # type: ignore[attr-defined]
    if window == "terminal":
        predicates.append(Order.filled_at.is_not(None))  # type: ignore[union-attr]
    predicates.append(time_column >= scope.started_at)  # type: ignore[operator]
    # 활성 세션은 `deactivated_at IS NULL` 이라 상한이 없다.
    if scope.ended_at is not None:
        predicates.append(time_column < scope.ended_at)  # type: ignore[operator]
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

    async def has_recent_market_converted_entry(
        self,
        *,
        exchange_account_id: UUID,
        strategy_id: UUID,
        session_id: UUID,
        since: datetime,
    ) -> bool:
        """최근 2 bar 안에 등재된 세션 소유 시장가 전환 주문이 있는지 확인한다.

        거래소 응답 미확인 전환은 `rejected`로 종결돼도 실제 주문이 남아 있을 수 있어,
        상태와 무관하게 다음 전환을 억제한다.
        """
        from src.trading.services.conditional_entry_planner import conditional_entry_key_like

        key_prefix = conditional_entry_key_like(session_id, "condmkt")
        stmt = (
            select(cast(Any, Order.id))
            .where(cast(Any, Order.exchange_account_id) == exchange_account_id)
            .where(cast(Any, Order.strategy_id) == strategy_id)
            .where(cast(Any, Order.idempotency_key).like(key_prefix))
            .where(cast(Any, Order.created_at) >= since)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def list_live_entry_keys_in_window(
        self, *, since: datetime, until: datetime, limit: int
    ) -> Sequence[LiveEntryKeyRow]:
        """이 조회는 SessionScope를 걸지 않는다. 이 질문의 모집단이 전 세션이기 때문이다.

        key 형식의 정확한 판정은 호출부가 `parse_live_entry_key`로 한다. SQL은 라이브 key
        후보와 시간 창만 좁힌다.
        """
        from src.trading.services.conditional_entry_planner import LIVE_ENTRY_KEY_PREFIX

        stmt = (
            select(
                cast(Any, Order.idempotency_key),
                cast(Any, Order.created_at),
            )
            .where(Order.reduce_only.is_(False))  # type: ignore[attr-defined]
            .where(Order.idempotency_key.like(f"{LIVE_ENTRY_KEY_PREFIX}%"))  # type: ignore[union-attr]
            .where(Order.created_at >= since)  # type: ignore[arg-type]
            .where(Order.created_at < until)  # type: ignore[arg-type]
            .order_by(
                cast(Any, Order.created_at).asc(),
                cast(Any, Order.id).asc(),
            )
            .limit(limit + 1)
        )
        rows = (await self.session.execute(stmt)).all()
        return [LiveEntryKeyRow(idempotency_key=row[0], created_at=row[1]) for row in rows]

    async def list_resting_intervals(
        self, *, since: datetime, until: datetime, limit: int
    ) -> Sequence[RestingIntervalRow]:
        """창과 겹치는 조건부 진입 주문의 resting 시간 구간을 준다.

        창 시작 전에 만들어져 창 안에도 살아 있던 주문을 포함하려면 `created_at >= since`가
        아니라 종결 시각과의 겹침으로 판정해야 한다.
        """
        stmt = (
            select(
                cast(Any, Order.strategy_id),
                cast(Any, Order.exchange_account_id),
                cast(Any, Order.created_at),
                cast(Any, Order.filled_at),
            )
            .where(Order.trigger_price.is_not(None))  # type: ignore[union-attr]
            .where(Order.reduce_only.is_(False))  # type: ignore[attr-defined]
            .where(Order.created_at < until)  # type: ignore[arg-type]
            .where(func.coalesce(Order.filled_at, func.now()) >= since)
            .order_by(
                cast(Any, Order.created_at).asc(),
                cast(Any, Order.id).asc(),
            )
            .limit(limit + 1)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            RestingIntervalRow(
                strategy_id=row[0],
                exchange_account_id=row[1],
                created_at=row[2],
                closed_at=row[3],
            )
            for row in rows
        ]

    async def list_entry_rejections_in_window(
        self, *, since: datetime, until: datetime, limit: int
    ) -> Sequence[EntryRejectionRow]:
        """창 안에 생성된 비 reduce-only 거절 주문의 Python 판정 입력을 준다."""
        stmt = (
            select(
                cast(Any, Order.id),
                cast(Any, Order.idempotency_key),
                cast(Any, Order.error_message),
                cast(Any, Order.created_at),
            )
            .where(Order.reduce_only.is_(False))  # type: ignore[attr-defined]
            .where(Order.state == OrderState.rejected)  # type: ignore[arg-type]
            .where(Order.created_at >= since)  # type: ignore[arg-type]
            .where(Order.created_at < until)  # type: ignore[arg-type]
            .order_by(
                cast(Any, Order.created_at).asc(),
                cast(Any, Order.id).asc(),
            )
            .limit(limit + 1)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            EntryRejectionRow(
                order_id=row[0],
                idempotency_key=row[1],
                error_message=row[2],
                created_at=row[3],
            )
            for row in rows
        ]

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
        parsed_orders = [
            (order, parse_conditional_entry_key(order.idempotency_key)) for order in candidates
        ]
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

    async def list_fills_since(
        self, scope: SessionScope, *, since: datetime, limit: int = LEDGER_FILL_SCAN_LIMIT
    ) -> Sequence[LedgerFill]:
        """세션 스코프 안에서 `since` 이후 관측된 체결을 `(filled_at, id)` 오름차순으로 준다.

        BL-544 — 장기 공백 뒤 재개할 때 "재생이 모르는데 거래소에는 있는" 포지션의 근거를
        찾는 조회다. `list_filled_realized_for_session`(위)을 쓸 수 없다 —
        그쪽은 `realized_pnl IS NOT NULL` 을 더 걸어 **진입 주문을 구조적으로 못 본다**.
        그게 이 버그의 조회측 원인이다.

        ★`reduce_only` 를 필터하지 않는다. 청산 체결은 순포지션의 **뺄셈 항**이고, 빼면
        진입만 세어 포지션을 과대 계상한다. 부호는 `reduce_only` 가 아니라 `side` 가 정한다
        (라이브 close 는 long→sell / short→buy 로 매핑된다).

        ★경계는 `>= since` 다. `> since` 로 두면 watermark 와 **같은 시각**에 관측된 체결이
        조용히 빠진다. 이 조회는 "이미 반영됐다" 는 개념이 없으므로 한 건을 더 보는 쪽이
        언제나 안전하다.

        ★`limit + 1` 건을 가져온다. 호출부가 `len(rows) > limit` 으로 절단을 감지해
        fail-closed 하기 위한 것이다 — 조용한 절단은 부분 원장을 온전한 원장으로 위장한다.

        ★**`filled` 상태만 보면 안 된다** (R1). 부분체결 뒤 취소·거절된 조건부 진입은
        `filled` 이 아니면서 체결분을 보존한다(`_STATES_THAT_CAN_CARRY_FILLS` 주석 참조).
        그 행을 못 보면 거래소에는 부분 포지션이 남았는데 엔진은 flat 으로 seed 되어
        **BL-544 가 고치려던 그 사망이 형제 케이스로 되살아난다.**

        상태를 넓히는 대신 조건 하나를 함께 건다 — `filled` 이거나, **체결분이 실제로
        남아 있는** 종결 행이거나. `filled_quantity` 가 NULL·0 인 취소·거절은 체결이 아니라
        그냥 취소이므로 들어오지 않는다. 반대로 `filled` 인데 `filled_quantity` 가 NULL 인
        행은 **일부러 통과시킨다** — 호출부가 그것을 "판독 불가" 로 보고 seed 를 포기하는
        fail-closed 입력이며, 여기서 조용히 빼면 그 행은 "체결 없음" 으로 위장된다.
        """
        stmt = (
            select(
                cast(Any, Order.id),
                cast(Any, Order.idempotency_key),
                cast(Any, Order.side),
                cast(Any, Order.filled_quantity),
                cast(Any, Order.filled_price),
                cast(Any, Order.filled_at),
                cast(Any, Order.reduce_only),
            )
            .where(*_session_scope_where(scope, states=_STATES_THAT_CAN_CARRY_FILLS))
            .where(
                or_(
                    Order.state == OrderState.filled,  # type: ignore[arg-type]
                    and_(
                        Order.filled_quantity.is_not(None),  # type: ignore[union-attr]
                        Order.filled_quantity != 0,  # type: ignore[arg-type]
                    ),
                )
            )
            .where(Order.filled_at >= since)  # type: ignore[operator, arg-type]
            .order_by(
                Order.filled_at.asc(),  # type: ignore[union-attr]
                cast(Any, Order.id).asc(),
            )
            .limit(limit + 1)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            LedgerFill(
                order_id=row[0],
                idempotency_key=row[1],
                side=row[2],
                filled_quantity=row[3],
                filled_price=row[4],
                filled_at=row[5],
                reduce_only=row[6],
            )
            for row in rows
        ]

    async def list_entry_attempts(
        self,
        scope: SessionScope,
        *,
        since: datetime,
        until: datetime | None = None,
        limit: int = ENTRY_ATTEMPT_SCAN_LIMIT,
    ) -> Sequence[EntryAttemptRow]:
        """세션 스코프 안에서 `[since, until)` 에 **생성된** 진입 주문 전량 (BL-536).

        진입 유실의 크기를 재는 조회다. 기존 조회 넷과 술어가 다른 지점이 셋이고, 셋 다
        틀리면 분모가 조용히 거짓말한다.

        1. **창이 `created_at`** 이다. `filled_at`(terminal) 창으로 잡으면 아직 종결되지
           않은 시도가 전부 사라져 "이미 끝난 것" 만 분모에 남는다 — 유실을 재려는데
           유실 후보를 먼저 지우는 셈이다.
        2. **상태를 좁히지 않는다.** `pending`/`submitted` 도 시도다.
        3. **`reduce_only = false`.** 청산은 진입이 아니다. 이 술어를 뒤집으면 진입/청산이
           통째로 뒤바뀌므로 대조군 테스트가 이 축을 직접 겨눈다.

        ★스코프 술어는 `_session_scope_where` 를 그대로 재사용한다 — 복사하면 BL-444/445 가
        고친 그 병이 다시 두 벌이 된다. 세션 창(`[created, deactivated)`)과 `since/until`
        은 **둘 다** 걸린다. 세션이 생기기 전에 만들어진 주문은 그 세션 것일 수 없으므로
        세션 하한은 제약이 아니라 정의다.

        ★`limit + 1` 을 가져온다. 호출부가 `len(rows) > limit` 으로 절단을 감지해야 한다.
        """
        stmt = (
            select(
                cast(Any, Order.id),
                cast(Any, Order.idempotency_key),
                cast(Any, Order.state),
                cast(Any, Order.side),
                cast(Any, Order.quantity),
                cast(Any, Order.filled_quantity),
                cast(Any, Order.created_at),
                cast(Any, Order.filled_at),
                cast(Any, Order.error_message),
            )
            .where(*_session_scope_where(scope, states=None, window="created"))
            .where(Order.reduce_only.is_(False))  # type: ignore[attr-defined]
            .where(Order.created_at >= since)  # type: ignore[arg-type]
        )
        if until is not None:
            stmt = stmt.where(Order.created_at < until)  # type: ignore[arg-type]
        stmt = stmt.order_by(
            cast(Any, Order.created_at).asc(),
            cast(Any, Order.id).asc(),
        ).limit(limit + 1)
        rows = (await self.session.execute(stmt)).all()
        return [
            EntryAttemptRow(
                order_id=row[0],
                idempotency_key=row[1],
                state=row[2],
                side=row[3],
                quantity=row[4],
                filled_quantity=row[5],
                created_at=row[6],
                terminal_at=row[7],
                error_message=row[8],
            )
            for row in rows
        ]

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

    async def list_unsynced_with_exchange_exit(
        self, account_id: UUID, *, limit: int = 500
    ) -> Sequence[Order]:
        """시간창 없이 **원장이 청산으로 증언하는** 미동기화 체결 주문 전량을 조회한다.

        ★[BL-438] 2026-08-14 — 이 술어는 `reduce_only=true` 였고 그것이 실현손익의
        **93.1%(490건 / -1,023.87 USDT)를 백필에서 통째로 배제**하고 있었다. 소크 전략은
        **반전 주문**(`sell 0.058 = 2 x 0.029`)으로 청산하는데 반전에는 `reduce_only` 를
        걸 수 없다 — 걸면 거래소가 포지션 크기까지만 체결해 반전이 깨진다.

        `reduce_only` 는 「내가 요청한 안전장치」이지 「이 주문이 청산했는가」의 답이
        아니다([ADR-032](../../../../docs/decisions/032-no-hedge-mode.md)). Bybit one-way 는
        수량이 포지션을 넘으면 반전하고, OKX 의 `reduceOnly` 는 net mode 전용이며
        `sz > 포지션`이면 주문 자체를 거부한다 — 어느 계약에서도 등가가 성립하지 않는다.
        판정의 정본은 **거래소 원장이 그 주문의 청산 행을 갖고 있는가**이고, 그것이
        `_HAS_EXCHANGE_EXIT_ROW` 다.
        """
        stmt = (
            select(Order)
            .where(Order.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(_HAS_EXCHANGE_EXIT_ROW)
            .where(Order.exchange_order_id.is_not(None))  # type: ignore[union-attr]
            .where(Order.realized_pnl_synced_at.is_(None))  # type: ignore[union-attr]
            .order_by(Order.filled_at.asc())  # type: ignore[union-attr]
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_synced_with_exchange_exit(
        self, account_id: UUID, *, limit: int = 500
    ) -> Sequence[Order]:
        """이미 거래소 확정으로 표시된 체결 주문 중 원장에 청산 행이 있는 것.

        체결 직후 refresh 는 원장을 거치지 않고 **단일 조회 결과**를 CAS 한다. 분할 행
        중 일부만 보이는 순간에 걸리면 부분합이 synced 로 고정되고, 미동기화 술어를 쓰는
        스윕은 그 주문을 영영 건너뛴다. 원장 합계와 대조해 되돌릴 수 있게 따로 조회한다.

        ★[BL-438] — 술어를 위 미동기화 쪽과 **함께** 바꾼다. 한쪽만 원장 조인으로
        넓히면 새로 백필된 `reduce_only=false` 490건이 `synced_at` 은 갖는데 정정 경로에는
        영영 안 들어와, 부분합 고정을 되돌리는 이 안전망이 그 주문들에만 사라진다.

        ★★**[BL-731] — 「이미 일치하는 행」은 모집단에서 뺀다.** [BL-438] 이 대상 선정을 원장
        EXISTS 로 바꾸면서 모집단이 `reduce_only` 73건 → **563건**(서버 실측)이 됐다. 그중
        대다수는 이미 일치하는데도 `limit` 예산을 먹고, `filled_at desc` 정렬이라 **가장
        오래된 63건이 밀려난다** — 그리고 다음 tick 에도 같은 이유로 밀리므로 **영구 제외**다.

        미동기화 축과 성질이 다르다: 그쪽은 백필에 성공하면 모집단에서 빠져 **배수**되지만,
        동기화 축은 **단조 증가**라 한 번 상한을 넘으면 스스로 줄지 않는다.

        ⇒ 상한을 키우는 대신 `resync_exchange_realized_pnl` 이 이미 갖고 있는
        `IS DISTINCT FROM` 가드를 **SQL 술어로 끌어올린다**. 정정된 행은 다음 tick 에 술어에서
        빠지므로 모집단이 **0 으로 수렴**하고 상한이 무의미해진다 — 정렬을 바꿀 필요도 없다.
        """
        stmt = (
            select(Order)
            .where(Order.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(Order.state == OrderState.filled)  # type: ignore[arg-type]
            .where(_HAS_EXCHANGE_EXIT_ROW)
            .where(Order.exchange_order_id.is_not(None))  # type: ignore[union-attr]
            .where(Order.realized_pnl_synced_at.is_not(None))  # type: ignore[union-attr]
            .where(Order.realized_pnl.is_distinct_from(_EXCHANGE_EXIT_PNL_SUM))  # type: ignore[union-attr]
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
