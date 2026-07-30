# 진입 시도 창 조회의 술어를 실 DB 로 고정한다 — 틀린 술어와 맞는 술어가 다른 값을 내야 한다

"""BL-536 — `OrderRepository.list_entry_attempts` 대조군.

★**서비스 mock 이 아니라 실 DB 다.** 리포지토리 SQL 을 겨눈 대조군을 리포지토리를 mock
하는 테스트로 재면 **영원히 통과한다** — 이 레포가 실측으로 밟은 실패 유형이다.
이 파일의 모든 단언은 진짜 SELECT 의 결과다.

고정하는 계약 넷.

1. 창은 **`created_at`** 이다. `filled_at`(terminal) 창이면 아직 종결되지 않은 시도가
   전부 사라져 분모가 "이미 끝난 것" 만 남는다.
2. **상태를 좁히지 않는다.** `submitted` 행(=`filled_at IS NULL`)이 결과에 있어야 한다.
3. **`reduce_only = false`.** 청산 체결은 진입이 아니다.
4. 스코프(전략·계정·심볼)는 `_session_scope_where` 재사용이라 기존 소비처와 **같은**
   정의다. 그리고 그 소비처들의 동작은 인자를 주지 않으면 **불변**이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.live_signal_session_repository import (
    LiveSignalSessionRepository,
)
from src.trading.repositories.order_repository import (
    OrderRepository,
    SessionScope,
    _session_scope_where,
)

T0 = datetime(2026, 7, 29, 0, 0, tzinfo=UTC)  # 세션 시작
SINCE = T0 + timedelta(hours=1)
UNTIL = T0 + timedelta(hours=9)

BTC = "BTC/USDT"
ETH = "ETH/USDT"


@dataclass(frozen=True, slots=True)
class _Seed:
    scope: SessionScope
    session_id: UUID
    orders: dict[str, Order]


async def _seed(db_session: AsyncSession) -> _Seed:
    user = User(
        clerk_user_id=f"entry-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    def _strategy(name: str) -> Strategy:
        return Strategy(
            user_id=user.id,
            name=name,
            pine_source="//@version=5\nstrategy('entry')",
            pine_version=PineVersion.v5,
            parse_status=ParseStatus.ok,
        )

    def _account() -> ExchangeAccount:
        return ExchangeAccount(
            user_id=user.id,
            exchange=ExchangeName.bybit,
            mode=ExchangeMode.demo,
            api_key_encrypted=b"k",
            api_secret_encrypted=b"s",
        )

    strategy = _strategy("entry target")
    other_strategy = _strategy("entry other")
    account = _account()
    other_account = _account()
    db_session.add_all([strategy, other_strategy, account, other_account])
    await db_session.flush()

    live_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=BTC,
        interval=LiveSignalInterval.m5,
        created_at=T0,
    )
    db_session.add(live_session)
    await db_session.flush()

    def _order(
        *,
        created_at: datetime,
        state: OrderState,
        filled_quantity: str | None = None,
        filled_at: datetime | None = None,
        reduce_only: bool = False,
        symbol: str = BTC,
        strategy_id: UUID | None = None,
        account_id: UUID | None = None,
        key: str | None = None,
    ) -> Order:
        return Order(
            strategy_id=strategy_id or strategy.id,
            exchange_account_id=account_id or account.id,
            symbol=symbol,
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.029"),
            state=state,
            filled_quantity=None if filled_quantity is None else Decimal(filled_quantity),
            filled_at=filled_at,
            created_at=created_at,
            reduce_only=reduce_only,
            trigger_price=None if reduce_only else Decimal("64000"),
            idempotency_key=key,
        )

    orders = {
        # ★M5 판별 — 세션 창 안이지만 `since` 직전. 하한을 지우면 이 행이 새어 들어온다.
        "before_window": _order(
            created_at=SINCE - timedelta(minutes=1),
            state=OrderState.filled,
            filled_quantity="0.029",
            filled_at=SINCE - timedelta(seconds=30),
            key=f"live:{live_session.id}:cond:1:64000:0.029:Early",
        ),
        "filled": _order(
            created_at=SINCE + timedelta(minutes=1),
            state=OrderState.filled,
            filled_quantity="0.029",
            filled_at=SINCE + timedelta(minutes=2),
            key=f"live:{live_session.id}:cond:2:64000:0.029:PivRevLE",
        ),
        # 부분체결을 보존한 채 취소된 행 — 체결분이 원장에 남아 있다.
        "cancelled_partial": _order(
            created_at=SINCE + timedelta(minutes=2),
            state=OrderState.cancelled,
            filled_quantity="0.011",
            filled_at=SINCE + timedelta(minutes=3),
            key=f"live:{live_session.id}:cond:3:64000:0.029:PivRevLE",
        ),
        "rejected": _order(
            created_at=SINCE + timedelta(minutes=3),
            state=OrderState.rejected,
            filled_at=SINCE + timedelta(minutes=4),
            key=f"live:{live_session.id}:cond:4:64000:0.029:PivRevSE",
        ),
        # ★상태 축 판별 — `filled_at IS NULL` 이라 terminal 창 술어로는 구조적으로 안 보인다.
        "submitted": _order(
            created_at=SINCE + timedelta(minutes=4),
            state=OrderState.submitted,
            key=f"live:{live_session.id}:cond:5:64000:0.029:PivRevSE",
        ),
        # ★M2 판별 — 같은 창의 청산 체결. 술어를 뒤집으면 이것만 남는다.
        "exit": _order(
            created_at=SINCE + timedelta(minutes=5),
            state=OrderState.filled,
            filled_quantity="0.029",
            filled_at=SINCE + timedelta(minutes=6),
            reduce_only=True,
        ),
        "after_until": _order(
            created_at=UNTIL + timedelta(minutes=1),
            state=OrderState.filled,
            filled_quantity="0.029",
            filled_at=UNTIL + timedelta(minutes=2),
        ),
        "other_strategy": _order(
            created_at=SINCE + timedelta(minutes=6),
            state=OrderState.filled,
            filled_quantity="0.029",
            filled_at=SINCE + timedelta(minutes=7),
            strategy_id=other_strategy.id,
        ),
        "other_account": _order(
            created_at=SINCE + timedelta(minutes=7),
            state=OrderState.filled,
            filled_quantity="0.029",
            filled_at=SINCE + timedelta(minutes=8),
            account_id=other_account.id,
        ),
        "other_symbol": _order(
            created_at=SINCE + timedelta(minutes=8),
            state=OrderState.filled,
            filled_quantity="0.029",
            filled_at=SINCE + timedelta(minutes=9),
            symbol=ETH,
        ),
    }
    db_session.add_all(list(orders.values()))
    await db_session.flush()
    return _Seed(
        scope=SessionScope.from_live_session(live_session),
        session_id=live_session.id,
        orders=orders,
    )


@pytest.mark.asyncio
async def test_entry_attempts_cover_every_state_in_the_created_window(
    db_session: AsyncSession,
) -> None:
    seed = await _seed(db_session)
    rows = await OrderRepository(db_session).list_entry_attempts(
        seed.scope, since=SINCE, until=UNTIL
    )

    ids = [row.order_id for row in rows]
    expected = [
        seed.orders["filled"].id,
        seed.orders["cancelled_partial"].id,
        seed.orders["rejected"].id,
        seed.orders["submitted"].id,
    ]
    assert ids == expected, "created_at 오름차순으로 창 안 진입 시도 전량"
    # 상태를 좁히지 않았다는 직접 증거 - filled_at 이 NULL 인 행이 결과에 있다.
    assert {row.state for row in rows} == {
        OrderState.filled,
        OrderState.cancelled,
        OrderState.rejected,
        OrderState.submitted,
    }
    assert [row.terminal_at for row in rows][-1] is None


@pytest.mark.asyncio
async def test_exit_rows_never_enter_the_entry_window(db_session: AsyncSession) -> None:
    """★M2 — `reduce_only` 술어를 뒤집으면 진입과 청산이 통째로 뒤바뀐다."""
    seed = await _seed(db_session)
    rows = await OrderRepository(db_session).list_entry_attempts(
        seed.scope, since=SINCE, until=UNTIL
    )
    assert seed.orders["exit"].id not in {row.order_id for row in rows}


@pytest.mark.asyncio
async def test_window_lower_bound_excludes_rows_created_before_since(
    db_session: AsyncSession,
) -> None:
    """★M5 — 하한을 지우면 창 직전 행이 새어 들어와 분모가 커진다."""
    seed = await _seed(db_session)
    repo = OrderRepository(db_session)

    inside = await repo.list_entry_attempts(seed.scope, since=SINCE, until=UNTIL)
    assert seed.orders["before_window"].id not in {row.order_id for row in inside}

    widened = await repo.list_entry_attempts(
        seed.scope, since=SINCE - timedelta(minutes=5), until=UNTIL
    )
    assert seed.orders["before_window"].id in {row.order_id for row in widened}
    assert len(widened) == len(inside) + 1


@pytest.mark.asyncio
async def test_window_upper_bound_is_optional_and_half_open(db_session: AsyncSession) -> None:
    seed = await _seed(db_session)
    repo = OrderRepository(db_session)

    bounded = await repo.list_entry_attempts(seed.scope, since=SINCE, until=UNTIL)
    unbounded = await repo.list_entry_attempts(seed.scope, since=SINCE)
    assert seed.orders["after_until"].id not in {row.order_id for row in bounded}
    assert seed.orders["after_until"].id in {row.order_id for row in unbounded}

    # 반열림 - `until` 과 정확히 같은 시각에 생성된 행은 들어오지 않는다.
    edge = await repo.list_entry_attempts(
        seed.scope, since=SINCE, until=SINCE + timedelta(minutes=1)
    )
    assert edge == []


@pytest.mark.asyncio
async def test_scope_predicates_are_the_shared_session_scope(db_session: AsyncSession) -> None:
    """전략·계정·심볼이 다른 행은 안 들어온다 — 술어를 복사하지 않았다는 증거."""
    seed = await _seed(db_session)
    rows = await OrderRepository(db_session).list_entry_attempts(
        seed.scope, since=SINCE, until=UNTIL
    )
    returned = {row.order_id for row in rows}
    for name in ("other_strategy", "other_account", "other_symbol"):
        assert seed.orders[name].id not in returned, f"{name} 이 스코프를 넘어 들어왔다"


@pytest.mark.asyncio
async def test_truncation_is_detectable_by_the_caller(db_session: AsyncSession) -> None:
    """`limit + 1` 을 준다 — 조용한 절단은 부분 원장을 온전한 원장으로 위장한다."""
    seed = await _seed(db_session)
    rows = await OrderRepository(db_session).list_entry_attempts(
        seed.scope, since=SINCE, until=UNTIL, limit=2
    )
    assert len(rows) == 3 > 2


# --- ①-c 기존 소비처 동작 불변 -------------------------------------------------


def test_default_scope_predicates_are_unchanged_by_the_new_parameters() -> None:
    """인자를 안 주면 오늘과 **똑같은** 술어여야 한다.

    새 파라미터가 기본값으로 새어 들어가면 `list_fills_since` 와 손익 집계가 조용히
    넓어진다 — 그건 머니-패스다.
    """
    scope = SessionScope(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol=BTC,
        started_at=T0,
        ended_at=UNTIL,
    )
    default = [str(predicate) for predicate in _session_scope_where(scope)]
    explicit = [
        str(predicate)
        for predicate in _session_scope_where(
            scope, states=(OrderState.filled,), window="terminal"
        )
    ]
    assert default == explicit
    joined = " ".join(default)
    assert "filled_at IS NOT NULL" in joined
    assert "orders.state IN" in joined
    assert "created_at" not in joined


def test_created_window_swaps_the_time_axis_and_drops_the_null_guard() -> None:
    scope = SessionScope(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol=BTC,
        started_at=T0,
        ended_at=UNTIL,
    )
    predicates = " ".join(
        str(predicate) for predicate in _session_scope_where(scope, states=None, window="created")
    )
    assert "orders.created_at >=" in predicates
    assert "orders.created_at <" in predicates
    assert "filled_at" not in predicates
    assert "orders.state IN" not in predicates


@pytest.mark.asyncio
async def test_existing_consumers_still_see_only_terminal_filled_rows(
    db_session: AsyncSession,
) -> None:
    """★기존 4 소비처의 동작 불변을 값으로 잠근다.

    `submitted` 행이 새 조회에는 있고 기존 조회에는 **없어야** 한다. 하나라도 새어
    들어오면 손익 합계와 공백 재개 seed 가 함께 틀어진다.
    """
    seed = await _seed(db_session)
    repo = OrderRepository(db_session)

    fills = await repo.list_fills_since(seed.scope, since=T0)
    fill_ids = {fill.order_id for fill in fills}
    assert seed.orders["submitted"].id not in fill_ids
    assert seed.orders["rejected"].id not in fill_ids, "체결분 없는 거절은 체결이 아니다"
    assert seed.orders["filled"].id in fill_ids
    assert seed.orders["cancelled_partial"].id in fill_ids, "부분체결 보존 행은 체결이다"
    # 청산도 순포지션의 뺄셈 항이므로 여기서는 일부러 보인다 (BL-544 계약).
    assert seed.orders["exit"].id in fill_ids

    realized = await repo.list_filled_realized_for_session(seed.scope)
    assert realized == [], "realized_pnl 이 없는 행은 이 조회에 안 들어온다"

    split = await repo.realized_pnl_split_for_session(seed.scope)
    # 세션이 활성이라 상한이 없다 - `state == filled` + `filled_at IS NOT NULL` 인 스코프 행은
    # before_window / filled / exit / after_until 넷이고 전부 realized_pnl 이 NULL 이다.
    assert (split.confirmed_count, split.estimated_count) == (0, 0)
    assert split.unrecorded_count == 4


# --- R3-⑥ 세션 집합 절단도 감지 가능해야 한다 ---------------------------------


@pytest.mark.asyncio
async def test_session_window_query_returns_limit_plus_one_for_truncation_detection(
    db_session: AsyncSession,
) -> None:
    """★주문 절단은 다뤘으면서 세션 집합 절단을 안 다루면 같은 PR 안의 불일치다 (R3-⑥).

    조용히 잘리면 리포트가 "이 창의 전부" 라고 말하면서 세션 몇 개를 통째로 빠뜨린다 —
    절단된 분모는 유실률을 낙관적으로 왜곡한다.
    """
    seed = await _seed(db_session)
    repo = LiveSignalSessionRepository(db_session)

    # 시드가 만든 세션 1 개는 창에 겹친다. limit=0 이면 `limit + 1` 로 1 건이 와야 한다.
    rows = await repo.list_overlapping_window(since=T0, until=UNTIL, limit=0)
    assert len(rows) == 1 > 0, "limit + 1 을 주지 않으면 호출부가 절단을 감지할 수 없다"
    assert rows[0].id == seed.session_id


@pytest.mark.asyncio
async def test_session_window_overlap_predicate(db_session: AsyncSession) -> None:
    """겹침 판정 자체 — 창 뒤에서 시작한 세션은 안 들어온다."""
    seed = await _seed(db_session)
    repo = LiveSignalSessionRepository(db_session)

    overlapping = await repo.list_overlapping_window(since=T0, until=UNTIL)
    assert seed.session_id in {row.id for row in overlapping}

    # 세션은 T0 에 시작해 아직 활성이다. 창을 세션 시작 **이전**으로만 잡으면 안 겹친다.
    before_session = await repo.list_overlapping_window(
        since=T0 - timedelta(days=2), until=T0 - timedelta(days=1)
    )
    assert seed.session_id not in {row.id for row in before_session}
