"""OrderRepository — 3-guard 상태 전이 + idempotency 조회."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.trading.repositories.order_repository import SessionScope
from src.trading.services.conditional_entry_planner import build_market_converted_entry_key


@pytest.fixture
async def account(db_session: AsyncSession, user) -> ExchangeAccount:
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


async def _make_order(db_session, strategy, account, *, idem: str | None = None):
    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.pending,
        idempotency_key=idem,
    )
    saved = await repo.save(order)  # Sprint 6 naming — NOT create
    await repo.commit()
    return repo, saved


async def test_create_order_starts_in_pending(db_session, strategy, account):
    _repo, order = await _make_order(db_session, strategy, account)
    assert order.state == OrderState.pending


async def test_transition_to_submitted_3_guard_success(db_session, strategy, account):
    repo, order = await _make_order(db_session, strategy, account)

    rowcount = await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched.state == OrderState.submitted
    assert fetched.submitted_at is not None


async def test_transition_to_submitted_guard_blocks_wrong_state(db_session, strategy, account):
    """pending이 아닌 상태에서 submitted 전이 시도 → rowcount 0."""
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    # 이미 submitted인 상태에서 재시도 → 0
    rowcount = await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()
    assert rowcount == 0


async def test_transition_to_filled_records_exchange_order_id_and_price(
    db_session, strategy, account
):
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    rowcount = await repo.transition_to_filled(
        order.id,
        exchange_order_id="bybit-42",
        filled_price=Decimal("50000"),
        filled_at=datetime.now(UTC),
    )
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched.state == OrderState.filled
    assert fetched.exchange_order_id == "bybit-42"
    assert fetched.filled_price == Decimal("50000")


async def test_backfill_exchange_realized_pnl_is_filled_only_and_idempotent(
    db_session, strategy, account
):
    """확정 closedPnl은 filled 행에서 한 번만 추정 손익을 교체한다."""
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.transition_to_filled(
        order.id,
        exchange_order_id="bybit-close-1",
        filled_price=Decimal("50000"),
        filled_at=datetime.now(UTC),
    )
    await repo.commit()

    synced_at = datetime.now(UTC)
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=Decimal("-12.34567890"), synced_at=synced_at
        )
        == 1
    )
    await repo.commit()
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.realized_pnl == Decimal("-12.34567890")
    assert fetched.realized_pnl_synced_at is not None
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=Decimal("-1"), synced_at=datetime.now(UTC)
        )
        == 0
    )


async def test_backfill_exchange_realized_pnl_rejects_non_filled(db_session, strategy, account):
    """submitted 등 비체결 주문에는 확정 손익을 기록하지 않는다."""
    repo, order = await _make_order(db_session, strategy, account)
    assert (
        await repo.backfill_exchange_realized_pnl(
            order.id, realized_pnl=Decimal("-1"), synced_at=datetime.now(UTC)
        )
        == 0
    )


async def test_transition_to_rejected_records_error_message(db_session, strategy, account):
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    rowcount = await repo.transition_to_rejected(
        order.id, error_message="InsufficientFunds", failed_at=datetime.now(UTC)
    )
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched.state == OrderState.rejected
    assert fetched.error_message == "InsufficientFunds"


async def test_janitor_reject_cas_loses_to_late_exchange_id_attach(db_session, strategy, account):
    """Janitor는 exchange_order_id가 붙은 submitted 행을 reject하면 안 된다."""
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.attach_exchange_order_id(order.id, "late-exchange-id")
    await repo.commit()

    rowcount = await repo.transition_submitted_without_exchange_id_to_rejected(
        order.id,
        error_message="not found",
        failed_at=datetime.now(UTC),
    )
    await repo.commit()
    await db_session.refresh(order)

    assert rowcount == 0
    assert order.state == OrderState.submitted
    assert order.exchange_order_id == "late-exchange-id"


async def test_get_by_idempotency_key_returns_order(db_session, strategy, account):
    repo, order = await _make_order(db_session, strategy, account, idem="tv-signal-001")
    fetched = await repo.get_by_idempotency_key("tv-signal-001")
    assert fetched is not None
    assert fetched.id == order.id


async def test_get_by_idempotency_key_miss_returns_none(db_session, strategy, account):
    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)
    assert await repo.get_by_idempotency_key("never-seen") is None


async def test_rejected_market_conversion_still_suppresses_within_two_bars(
    db_session, strategy, account
):
    """응답 미확인 전환은 rejected여도 거래소에 남았을 수 있어 억제한다."""
    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)
    session_id = uuid4()
    created_at = datetime.now(UTC)
    key = build_market_converted_entry_key(
        session_id,
        "entry",
        created_at,
        Decimal("100"),
        Decimal("0.01"),
    )
    assert key is not None
    await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.01"),
            state=OrderState.rejected,
            idempotency_key=key,
            created_at=created_at,
        )
    )
    await repo.commit()

    assert await repo.has_recent_market_converted_entry(
        exchange_account_id=account.id,
        strategy_id=strategy.id,
        session_id=session_id,
        since=created_at - timedelta(minutes=2),
    )


async def test_transition_to_filled_records_partial_quantity(db_session, strategy, account):
    """CCXT 부분체결 — filled_quantity < quantity. ADR-006 / autoplan Eng E7."""
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    rowcount = await repo.transition_to_filled(
        order.id,
        exchange_order_id="bybit-partial-1",
        filled_price=Decimal("50000"),
        filled_quantity=Decimal("0.005"),  # ordered 0.01, partial fill 0.005
        filled_at=datetime.now(UTC),
    )
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.filled_quantity == Decimal("0.005")
    assert fetched.quantity == Decimal("0.01")  # 원 주문 수량 유지


async def test_order_persists_leverage_and_margin_mode(db_session, strategy, account):
    """Sprint 7a T1 — leverage/margin_mode 컬럼 round-trip 저장/조회."""
    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)
    order = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT:USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            price=None,
            state=OrderState.pending,
            leverage=5,
            margin_mode="cross",
        )
    )
    await repo.commit()

    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.leverage == 5
    assert fetched.margin_mode == "cross"


async def test_advisory_lock_acquire_and_release(db_session, strategy, account):
    """pg_advisory_xact_lock 트랜잭션 범위 내 동작 검증 (Sprint 5 M2 패턴).

    savepoint 격리 fixture가 이미 outer tx를 보유하므로 `session.begin()` 재호출 불가.
    advisory lock은 해당 tx 범위 내에서 걸리고 tx 종료 시 자동 해제됨.
    """
    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)
    await repo.acquire_idempotency_lock("test-key-abc")
    result = await db_session.execute(
        text("SELECT pg_try_advisory_xact_lock(hashtext(:k))"),
        {"k": "test-key-abc"},
    )
    # 동일 트랜잭션에서는 재진입 가능이라 True — 실제 경쟁은 별도 connection 필요
    # 이 테스트는 쿼리 실행 자체가 에러 없이 완료됨을 확인
    assert result.scalar() is not None


async def test_list_filled_realized_excludes_rejected_and_entry_only_orders(
    db_session, strategy, account
):
    """2026-07-01 dogfood 발견 — live-session 대시보드 실현손익이 rejected 주문의
    시뮬레이션 pnl까지 반영하던 문제. filled+realized_pnl 있는 주문만 조회한다."""
    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)

    rejected = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.rejected,
            realized_pnl=Decimal("-111.70"),  # 시뮬레이션 pnl이 리젝트에도 남는 케이스
            filled_at=datetime(2026, 7, 1, 8, 34, 27, tzinfo=UTC),
        )
    )
    entry_filled_no_pnl = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=None,  # entry 는 realized_pnl 없음
            filled_at=datetime(2026, 7, 1, 8, 35, 0, tzinfo=UTC),
        )
    )
    close_filled_with_pnl = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            realized_pnl=Decimal("42.50"),
            filled_at=datetime(2026, 7, 1, 8, 36, 0, tzinfo=UTC),
        )
    )
    await repo.commit()

    # BL-445 — 조회 스코프가 (strategy, account) 튜플에서 세션 스코프로 바뀌었다.
    # 세션 창은 위 주문들을 모두 덮으므로 이 테스트의 원래 관심사(state/realized_pnl
    # 필터)는 그대로 검증된다.
    live_session = LiveSignalSession(
        user_id=account.user_id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m5,
        created_at=datetime(2026, 7, 1, 8, 0, 0, tzinfo=UTC),
    )
    db_session.add(live_session)
    await db_session.flush()

    result = await repo.list_filled_realized_for_session(
        SessionScope.from_live_session(live_session)
    )

    result_ids = [o.id for o in result]
    assert rejected.id not in result_ids
    assert entry_filled_no_pnl.id not in result_ids
    assert result_ids == [close_filled_with_pnl.id]


async def test_list_existing_ids_is_state_agnostic_and_account_scoped(
    db_session, strategy, account, user
):
    """BL-457 — link-id 실재 확인은 상태를 묻지 않고 계정만 묻는다.

    ★`state` 필터를 넣으면 안 되는 이유가 여기 고정된다. 이 확인이 필요한 행은 정의상
    `state == filled` 매칭에 실패한 주문(`pending`/`submitted`)이므로, 상태를 거르면
    **진짜 우리 청산이 외부 청산으로 뒤집혀** 운영자 알림이 헛발화한다.

    그리고 계정 스코프여야 하는 이유 — `Order.id` 는 UUID4 라 전역 충돌이 문제가 아니고,
    **다른 계정의 주문 id 를 이 계정의 청산으로 주장하는 것**이 문제다.
    """
    from uuid import uuid4

    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)
    _repo, pending_order = await _make_order(db_session, strategy, account)
    assert pending_order.state == OrderState.pending

    other_account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k2",
        api_secret_encrypted=b"s2",
    )
    db_session.add(other_account)
    await db_session.flush()
    _repo2, other_order = await _make_order(db_session, strategy, other_account)

    unknown_id = uuid4()
    found = await repo.list_existing_ids(account.id, [pending_order.id, other_order.id, unknown_id])

    # 상태 무필터 — pending 주문도 우리 것이다.
    assert pending_order.id in found
    # 다른 계정의 주문은 이 계정 것이 아니다.
    assert other_order.id not in found
    assert unknown_id not in found
    assert found == frozenset({pending_order.id})


async def test_list_existing_ids_short_circuits_on_empty_input(db_session, account):
    """후보가 없으면 쿼리 없이 빈 집합이다 — 스윕의 왕복이 늘지 않는다."""
    from src.trading.repositories.order_repository import OrderRepository

    assert await OrderRepository(db_session).list_existing_ids(account.id, []) == frozenset()


async def test_realized_pnl_split_partitions_the_scope_by_provenance(db_session, strategy, account):
    """BL-458 — 확정·추정·미기록 세 카운트가 스코프를 **정확히 분할**한다.

    `realized_pnl_synced_at` 이 출처 마커다 — NULL = pine_v2 추정, 값 있음 = 거래소
    확정 `closedPnl`. 셋을 합치면 스코프 안 체결 주문 전체가 되어야 한다. 하나라도
    겹치거나 빠지면 화면의 "확정 N · 추정 M" 이 거짓이 된다.

    금액은 서로 다른 2의 거듭제곱으로 심어 어떤 부분집합 합계도 유일하게 만든다 —
    틀린 답이 나오면 그 숫자가 어느 술어를 잘못 넣었는지 스스로 지목한다.
    """
    from src.trading.repositories.order_repository import OrderRepository

    repo = OrderRepository(db_session)
    base = datetime(2026, 7, 1, 8, 0, 0, tzinfo=UTC)

    def _o(**kw):
        return Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.sell,
            type=OrderType.market,
            quantity=Decimal("1"),
            state=OrderState.filled,
            **kw,
        )

    # 거래소 확정 −2, 추정 −4, 손익 미도착(수동 청산 직후) 1건.
    await repo.save(
        _o(
            realized_pnl=Decimal("-2"),
            realized_pnl_synced_at=base,
            filled_at=base + timedelta(minutes=1),
        )
    )
    await repo.save(_o(realized_pnl=Decimal("-4"), filled_at=base + timedelta(minutes=2)))
    await repo.save(_o(realized_pnl=None, filled_at=base + timedelta(minutes=3)))
    await repo.commit()

    live_session = LiveSignalSession(
        user_id=account.user_id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m5,
        created_at=base,
    )
    db_session.add(live_session)
    await db_session.flush()

    split = await repo.realized_pnl_split_for_session(SessionScope.from_live_session(live_session))

    assert split.confirmed == Decimal("-2")
    assert split.estimated == Decimal("-4")
    # ★게이트가 쓰는 값은 여전히 둘의 합이다 — 라벨은 가산적이고 필터가 아니다.
    assert split.total == Decimal("-6")
    assert (split.confirmed_count, split.estimated_count) == (1, 1)
    # 손익이 아직 안 온 체결은 확정도 추정도 아니다 — 개수로만 표면화한다.
    assert split.unrecorded_count == 1


# ── [BL-438] 백필 대상 선정 = 원장 조인 (reduce_only 가 아니다) ───────────────


async def _filled_order(
    db_session,
    strategy,
    account,
    *,
    exchange_order_id: str | None,
    reduce_only: bool,
    filled_at: datetime,
    synced_at: datetime | None = None,
) -> Order:
    """`state=filled` 주문 하나. 상태 전이 가드를 우회하려고 직접 만든다."""
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.sell if reduce_only else OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.029"),
        state=OrderState.filled,
        reduce_only=reduce_only,
        exchange_order_id=exchange_order_id,
        filled_price=Decimal("50000"),
        filled_at=filled_at,
        realized_pnl_synced_at=synced_at,
        realized_pnl=Decimal("-1") if synced_at is not None else None,
    )
    db_session.add(order)
    await db_session.flush()
    return order


async def _exit_row(db_session, account, *, exchange_order_id: str, row_hash: str) -> None:
    from src.trading.models import ExchangeExit, ExitAttribution, ExitClassification

    db_session.add(
        ExchangeExit(
            exchange_account_id=account.id,
            exchange_order_id=exchange_order_id,
            row_hash=row_hash,
            symbol="BTC/USDT",
            side="Sell",
            closed_pnl=Decimal("-1.5"),
            exchange_created_at=datetime.now(UTC),
            classification=ExitClassification.ours,
            attribution_confidence=ExitAttribution.exact,
            raw={"orderId": exchange_order_id},
        )
    )
    await db_session.flush()


async def test_unsynced_selection_follows_the_ledger_not_the_reduce_only_flag(
    db_session, strategy, account
):
    """[BL-438] 수리의 핵심 — 반전 청산(`reduce_only=false`)이 백필 후보가 된다.

    소크 전략은 반전 주문(`sell 0.058 = 2×0.029`)으로 청산하는데 반전에는 `reduce_only`
    를 걸 수 없다. 종전 술어(`reduce_only IS TRUE`)는 이 주문을 후보에서 배제했고
    실현손익의 93.1%(490건 / −1,023.87 USDT)가 그렇게 새고 있었다.
    """
    from src.trading.repositories.order_repository import OrderRepository

    base = datetime.now(UTC)
    reversal = await _filled_order(
        db_session,
        strategy,
        account,
        exchange_order_id="reversal-close-1",
        reduce_only=False,
        filled_at=base,
    )
    await _exit_row(db_session, account, exchange_order_id="reversal-close-1", row_hash="h-rev")
    await db_session.commit()

    rows = await OrderRepository(db_session).list_unsynced_with_exchange_exit(account.id)

    assert [o.id for o in rows] == [reversal.id]


async def test_unsynced_selection_excludes_orders_the_ledger_never_saw(
    db_session, strategy, account
):
    """[BL-438] 진입 주문은 원장에 청산 행이 없으므로 후보가 아니다.

    ★이 케이스가 술어의 **상관 조건**을 재는 자리다. `EXISTS` 안의
    `exchange_order_id` 동등을 빼면 「계정에 원장 행이 하나라도 있으면 참」이 되어
    진입 주문까지 후보로 올라오고, 스윕이 남의 `closed_pnl` 을 그 주문에 얹어
    계정 SUM 이 원장 총계를 넘는다(= 이중계상).
    """
    from src.trading.repositories.order_repository import OrderRepository

    base = datetime.now(UTC)
    await _filled_order(
        db_session,
        strategy,
        account,
        exchange_order_id="entry-1",
        reduce_only=False,
        filled_at=base,
    )
    close = await _filled_order(
        db_session,
        strategy,
        account,
        exchange_order_id="close-1",
        reduce_only=False,
        filled_at=base + timedelta(minutes=1),
    )
    # 원장은 청산 주문 하나만 증언한다.
    await _exit_row(db_session, account, exchange_order_id="close-1", row_hash="h-close")
    await db_session.commit()

    rows = await OrderRepository(db_session).list_unsynced_with_exchange_exit(account.id)

    assert [o.id for o in rows] == [close.id]


async def test_unsynced_selection_does_not_duplicate_orders_with_split_ledger_rows(
    db_session, strategy, account
):
    """[BL-438] 분할 행 N개여도 Order 는 1행이다 — JOIN 이 아니라 EXISTS 인 이유.

    JOIN 이면 같은 주문이 N번 나와 `limit` 예산이 잠식되고 스윕의 `applied` 계수가
    부풀어 관측이 거짓말을 한다.
    """
    from src.trading.repositories.order_repository import OrderRepository

    order = await _filled_order(
        db_session,
        strategy,
        account,
        exchange_order_id="split-close",
        reduce_only=False,
        filled_at=datetime.now(UTC),
    )
    await _exit_row(db_session, account, exchange_order_id="split-close", row_hash="h-a")
    await _exit_row(db_session, account, exchange_order_id="split-close", row_hash="h-b")
    await db_session.commit()

    rows = await OrderRepository(db_session).list_unsynced_with_exchange_exit(account.id)

    assert [o.id for o in rows] == [order.id]


async def test_unsynced_selection_is_account_scoped(db_session, strategy, account, user):
    """[BL-438] 다른 계정의 원장 행으로는 안 걸린다.

    `exchange_order_id` 는 거래소가 발급하므로 계정 간 충돌이 가능하다. 계정 축을 빼면
    남의 청산을 내 주문의 손익으로 주장하게 된다(`list_by_exchange_order_ids` 와 같은 이유).
    """
    from src.trading.repositories.order_repository import OrderRepository

    other = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k2",
        api_secret_encrypted=b"s2",
    )
    db_session.add(other)
    await db_session.flush()

    await _filled_order(
        db_session,
        strategy,
        account,
        exchange_order_id="shared-id",
        reduce_only=False,
        filled_at=datetime.now(UTC),
    )
    # 원장 행은 **다른 계정** 아래에만 있다.
    await _exit_row(db_session, other, exchange_order_id="shared-id", row_hash="h-other")
    await db_session.commit()

    rows = await OrderRepository(db_session).list_unsynced_with_exchange_exit(account.id)

    assert rows == []


async def test_synced_selection_follows_the_same_ledger_predicate(db_session, strategy, account):
    """[BL-438] 정정(resync) 경로도 같은 술어여야 한다.

    미동기화 쪽만 원장 조인으로 넓히면, 새로 백필된 `reduce_only=false` 주문은
    `synced_at` 은 갖는데 정정 경로에는 영영 안 들어온다 — 부분합 고정을 되돌리는
    안전망이 정확히 그 490건에만 사라진다.
    """
    from src.trading.repositories.order_repository import OrderRepository

    now = datetime.now(UTC)
    synced = await _filled_order(
        db_session,
        strategy,
        account,
        exchange_order_id="synced-reversal",
        reduce_only=False,
        filled_at=now,
        synced_at=now,
    )
    await _exit_row(db_session, account, exchange_order_id="synced-reversal", row_hash="h-sync")
    await db_session.commit()

    rows = await OrderRepository(db_session).list_synced_with_exchange_exit(account.id)

    assert [o.id for o in rows] == [synced.id]
