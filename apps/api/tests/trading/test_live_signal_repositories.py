"""라이브 신호 세션·이벤트 저장소의 실제 DB 계약을 고정한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
    SessionDeactivationReason,
)
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository


async def _seed_account(db_session: AsyncSession, user: User) -> ExchangeAccount:
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def _seed_session(
    db_session: AsyncSession,
    *,
    user: User,
    strategy: Strategy,
    account: ExchangeAccount,
    symbol: str,
    is_active: bool = True,
    deactivated_at: datetime | None = None,
    created_at: datetime | None = None,
    interval: LiveSignalInterval = LiveSignalInterval.m5,
    last_evaluated_bar_time: datetime | None = None,
) -> LiveSignalSession:
    live_session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol=symbol,
        interval=interval,
        is_active=is_active,
        deactivated_at=deactivated_at,
        deactivated_reason=(SessionDeactivationReason.user_stopped if not is_active else None),
        created_at=created_at or datetime.now(UTC),
        last_evaluated_bar_time=last_evaluated_bar_time,
    )
    db_session.add(live_session)
    await db_session.flush()
    return live_session


@pytest.mark.asyncio
async def test_insert_pending_events_is_idempotent_and_keeps_signal_bar_times(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """같은 신호 재생은 중복 없이, 신호별 bar_time·Decimal 레벨은 보존한다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="BTCUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    fallback_bar_time = datetime(2026, 8, 22, 9, tzinfo=UTC)
    earlier_bar_time = fallback_bar_time - timedelta(minutes=5)
    signals = [
        {
            "sequence_no": 1,
            "action": "entry",
            "direction": "long",
            "trade_id": "entry-1",
            "qty": "1.25",
            "comment": "open",
            "take_profit": "110.5",
            "stop_loss": "99.5",
            "trailing_stop": "2.5",
            "bar_time": earlier_bar_time,
        },
        {
            "sequence_no": 2,
            "action": "close",
            "direction": "long",
            "trade_id": "close-1",
            "qty": "1.25",
            "realized_pnl": "3.75",
        },
    ]

    inserted = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=fallback_bar_time,
        signals=signals,
    )
    repeated = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=fallback_bar_time,
        signals=signals,
    )

    assert [event.id for event in repeated] == [event.id for event in inserted]
    by_trade_id = {event.trade_id: event for event in inserted}
    assert by_trade_id["entry-1"].bar_time == earlier_bar_time
    assert by_trade_id["entry-1"].qty == Decimal("1.25")
    assert by_trade_id["entry-1"].take_profit == Decimal("110.5")
    assert by_trade_id["entry-1"].stop_loss == Decimal("99.5")
    assert by_trade_id["entry-1"].trailing_stop == Decimal("2.5")
    assert by_trade_id["close-1"].bar_time == fallback_bar_time
    assert by_trade_id["close-1"].realized_pnl == Decimal("3.75")


@pytest.mark.asyncio
async def test_event_repository_handles_empty_input_and_pending_failure_transition(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """빈 신호는 쓰지 않고, pending 이벤트만 실패 상태로 한 번 전이한다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ETHUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    bar_time = datetime(2026, 8, 22, 10, tzinfo=UTC)

    assert (
        await repository.insert_pending_events(
            session_id=live_session.id,
            bar_time=bar_time,
            signals=[],
        )
        == []
    )
    [pending] = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=bar_time,
        signals=[
            {
                "sequence_no": 1,
                "action": "entry",
                "direction": "short",
                "trade_id": "failure-1",
                "qty": "2",
            }
        ],
    )

    assert [event.id for event in await repository.list_pending()] == [pending.id]
    assert await repository.mark_failed(pending.id, error="x" * 2101) == 1
    assert await repository.mark_failed(pending.id, error="second attempt") == 0

    stored = await repository.get_by_id(pending.id)
    assert stored is not None
    assert stored.status == LiveSignalEventStatus.failed
    assert stored.retry_count == 1
    assert stored.error_message == "x" * 2000
    assert await repository.list_pending() == []


@pytest.mark.asyncio
async def test_try_claim_bar_only_accepts_a_newer_bar_for_an_active_session(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """동일·과거 bar의 두 번째 worker는 claim winner가 될 수 없다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="SOLUSDT",
    )
    repository = LiveSignalSessionRepository(db_session)
    bar_time = datetime(2026, 8, 22, 11, tzinfo=UTC)
    claim_token = uuid4()

    assert await repository.try_claim_bar(live_session.id, bar_time, claim_token) is True
    assert await repository.try_claim_bar(live_session.id, bar_time, uuid4()) is False
    assert (
        await repository.try_claim_bar(
            live_session.id,
            bar_time - timedelta(minutes=5),
            uuid4(),
        )
        is False
    )

    await db_session.refresh(live_session)
    assert live_session.last_evaluated_bar_time == bar_time
    assert live_session.bar_claim_token == claim_token


@pytest.mark.asyncio
async def test_session_repository_lists_inactive_rows_and_upserts_state(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """최근 종료 목록의 limit과 1:1 상태 갱신의 기존 equity curve 보존을 검증한다."""
    account = await _seed_account(db_session, user)
    earlier = datetime(2026, 8, 22, 8, tzinfo=UTC)
    older = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="XRPUSDT",
        is_active=False,
        deactivated_at=earlier,
    )
    newer = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ADAUSDT",
        is_active=False,
        deactivated_at=earlier + timedelta(minutes=1),
    )
    active = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="DOGEUSDT",
    )
    repository = LiveSignalSessionRepository(db_session)

    assert await repository.list_recent_inactive_by_user(user.id, limit=0) == []
    assert [row.id for row in await repository.list_recent_inactive_by_user(user.id, limit=1)] == [
        newer.id
    ]
    assert (
        await repository.deactivate_all_by_owner(
            user.id,
            at=earlier + timedelta(minutes=2),
            reason=SessionDeactivationReason.user_stopped,
        )
        == 1
    )
    await db_session.refresh(active)
    assert active.is_active is False

    created = await repository.upsert_state(
        session_id=older.id,
        last_strategy_state_report={"bar": 1},
        total_closed_trades=2,
        total_realized_pnl=Decimal("4.50"),
        equity_curve=[{"timestamp_ms": 1, "cumulative_pnl": "4.50"}],
    )
    updated = await repository.upsert_state(
        session_id=older.id,
        last_strategy_state_report={"bar": 2},
        total_closed_trades=3,
        total_realized_pnl=Decimal("5.25"),
    )

    assert updated is created
    assert updated.last_strategy_state_report == {"bar": 2}
    assert updated.total_closed_trades == 3
    assert updated.total_realized_pnl == Decimal("5.25")
    assert updated.equity_curve == [{"timestamp_ms": 1, "cumulative_pnl": "4.50"}]


@pytest.mark.asyncio
async def test_session_repository_saves_and_reads_active_rows(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """저장한 활성 세션은 소유 조회와 최신순 목록에서 같은 행으로 읽힌다."""
    account = await _seed_account(db_session, user)
    repository = LiveSignalSessionRepository(db_session)
    created_at = datetime(2026, 8, 22, 12, tzinfo=UTC)
    earlier = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="BTCUSDT",
        created_at=created_at,
    )
    later = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="ETHUSDT",
        interval=LiveSignalInterval.m5,
        created_at=created_at + timedelta(minutes=1),
    )

    saved = await repository.save(later)

    assert saved is later
    assert (await repository.get_by_id(later.id)).id == later.id
    assert (await repository.get_by_id_for_user(later.id, user.id)).id == later.id
    assert [row.id for row in await repository.list_active_by_user(user.id)] == [
        later.id,
        earlier.id,
    ]


@pytest.mark.asyncio
async def test_session_repository_filters_account_strategy_and_symbol_rows(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """계정·전략·심볼 조회는 활성 여부와 요구한 스코프를 각각 보존한다."""
    account = await _seed_account(db_session, user)
    started_at = datetime(2026, 8, 22, 13, tzinfo=UTC)
    inactive = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="BTCUSDT",
        is_active=False,
        deactivated_at=started_at + timedelta(minutes=2),
        created_at=started_at,
    )
    active = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ETHUSDT",
        created_at=started_at + timedelta(minutes=1),
    )
    repository = LiveSignalSessionRepository(db_session)

    assert [row.id for row in await repository.list_active_by_account(account.id)] == [active.id]
    assert [row.id for row in await repository.list_by_account(account.id, user_id=user.id)] == [
        active.id,
        inactive.id,
    ]
    assert await repository.list_active_strategy_ids([strategy.id, uuid4()]) == {strategy.id}
    assert [
        row.id
        for row in await repository.list_by_strategy_account_symbol(
            user_id=user.id,
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="ETHUSDT",
        )
    ] == [active.id]


@pytest.mark.asyncio
async def test_session_repository_lists_due_and_overlapping_windows(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """due 조회와 생존 구간 조회는 시간 경계에 맞는 세션만 반환한다."""
    account = await _seed_account(db_session, user)
    repository = LiveSignalSessionRepository(db_session)
    now = datetime(2026, 8, 22, 14, tzinfo=UTC)
    window_start = now - timedelta(minutes=15)
    never_evaluated = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="BTCUSDT",
        created_at=now - timedelta(hours=3),
    )
    due = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ETHUSDT",
        created_at=now - timedelta(hours=2),
        last_evaluated_bar_time=now - timedelta(minutes=6),
    )
    not_due = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="SOLUSDT",
        created_at=now - timedelta(hours=1),
        interval=LiveSignalInterval.m1,
        last_evaluated_bar_time=now - timedelta(seconds=30),
    )
    await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="XRPUSDT",
        is_active=False,
        created_at=now - timedelta(hours=4),
        deactivated_at=window_start - timedelta(seconds=1),
    )

    due_rows = await repository.list_active_due(now)
    overlapping_rows = await repository.list_overlapping_window(
        since=window_start,
        until=now + timedelta(minutes=15),
        limit=2,
    )

    assert {row.id for row in due_rows} == {never_evaluated.id, due.id}
    assert [row.id for row in overlapping_rows] == [
        never_evaluated.id,
        due.id,
        not_due.id,
    ]


@pytest.mark.asyncio
async def test_session_repository_deactivates_one_row_and_recounts_symbols(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """단일 종료 뒤 활성 쿼터와 ticker 집합은 남은 세션만 반영한다."""
    account = await _seed_account(db_session, user)
    first = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="BTCUSDT",
    )
    await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ETHUSDT",
    )
    repository = LiveSignalSessionRepository(db_session)
    deactivated_at = datetime(2026, 8, 22, 15, tzinfo=UTC)

    assert await repository.count_active_by_user(user.id) == 2
    assert await repository.list_distinct_active_symbols() == ["BTCUSDT", "ETHUSDT"]
    assert (
        await repository.deactivate(
            first.id,
            at=deactivated_at,
            reason=SessionDeactivationReason.user_stopped,
        )
        == 1
    )

    await db_session.refresh(first)
    assert first.deactivated_at == deactivated_at
    assert first.deactivated_reason == SessionDeactivationReason.user_stopped
    assert await repository.count_active_by_user(user.id) == 1
    assert await repository.list_distinct_active_symbols() == ["ETHUSDT"]


@pytest.mark.asyncio
async def test_event_repository_dispatches_and_joins_order_state(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """발주 성공은 event 상태·주문 FK·세션 귀속 조회에 함께 반영된다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="BTCUSDT",
    )
    event_repository = LiveSignalEventRepository(db_session)
    [pending] = await event_repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=datetime(2026, 8, 22, 16, tzinfo=UTC),
        signals=[
            {
                "sequence_no": 1,
                "action": "entry",
                "direction": "long",
                "trade_id": "dispatch-1",
                "qty": "1.5",
            }
        ],
    )
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("1.5"),
        state=OrderState.submitted,
    )
    db_session.add(order)
    await db_session.flush()

    assert await event_repository.mark_dispatched(pending.id, order_id=order.id) == 1

    stored = await event_repository.get_by_id(pending.id)
    assert stored is not None
    assert stored.status == LiveSignalEventStatus.dispatched
    assert stored.order_id == order.id
    assert stored.dispatched_at is not None
    assert [row.id for row in await event_repository.list_by_session(live_session.id)] == [
        pending.id
    ]
    assert await event_repository.list_by_session_with_order_state(live_session.id) == [
        (pending, str(OrderState.submitted))
    ]
    found_session = await LiveSignalSessionRepository(db_session).find_active_by_order_id(order.id)
    assert found_session is not None
    assert found_session.id == live_session.id


@pytest.mark.asyncio
async def test_event_repository_sums_realized_pnl_for_all_and_prior_window(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """실현 손익 집계는 Decimal 합계와 창 이전 건수를 함께 반환한다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ETHUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    first_bar_time = datetime(2026, 8, 22, 17, tzinfo=UTC)
    second_bar_time = first_bar_time + timedelta(minutes=5)
    await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=first_bar_time,
        signals=[
            {
                "sequence_no": 1,
                "action": "close",
                "direction": "long",
                "trade_id": "close-profit",
                "qty": "1",
                "realized_pnl": "2.25",
            },
            {
                "sequence_no": 2,
                "action": "entry",
                "direction": "short",
                "trade_id": "entry-no-pnl",
                "qty": "1",
            },
            {
                "sequence_no": 3,
                "action": "close",
                "direction": "short",
                "trade_id": "close-loss",
                "qty": "1",
                "realized_pnl": "-0.75",
                "bar_time": second_bar_time,
            },
        ],
    )

    assert await repository.sum_realized_pnl_all(live_session.id) == (Decimal("1.50"), 2)
    assert await repository.sum_realized_pnl_before(
        live_session.id,
        bar_time=second_bar_time,
    ) == (Decimal("2.25"), 1)


@pytest.mark.asyncio
async def test_session_repository_acquires_quota_lock_and_commits_saved_session(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """쿼터 advisory lock과 명시적 commit 뒤에도 저장한 세션을 다시 읽는다."""
    account = await _seed_account(db_session, user)
    repository = LiveSignalSessionRepository(db_session)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="AVAXUSDT",
    )

    await repository.acquire_quota_lock(user.id)
    await repository.commit()

    stored = await repository.get_by_id(live_session.id)
    assert stored is not None
    assert stored.id == live_session.id


@pytest.mark.asyncio
async def test_session_repository_returns_empty_for_empty_or_unmatched_scopes(
    db_session: AsyncSession,
) -> None:
    """빈 전략 입력과 존재하지 않는 소유·세션 스코프는 빈 결과로 닫힌다."""
    repository = LiveSignalSessionRepository(db_session)
    unknown_id = uuid4()

    assert await repository.get_by_id(unknown_id) is None
    assert await repository.get_by_id_for_user(unknown_id, uuid4()) is None
    assert await repository.list_active_strategy_ids([]) == set()
    assert await repository.list_active_by_user(uuid4()) == []
    assert await repository.list_recent_inactive_by_user(uuid4(), limit=-1) == []
    assert await repository.count_active_by_user(uuid4()) == 0
    assert await repository.list_distinct_active_symbols() == []


@pytest.mark.asyncio
async def test_session_repository_keeps_unbounded_window_and_replaces_equity_curve(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """상한 없는 생존 창은 활성 세션을 포함하고, 명시 curve는 기존 상태를 교체한다."""
    account = await _seed_account(db_session, user)
    repository = LiveSignalSessionRepository(db_session)
    created_at = datetime(2026, 8, 22, 18, tzinfo=UTC)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="LINKUSDT",
        created_at=created_at,
    )

    rows = await repository.list_overlapping_window(
        since=created_at + timedelta(minutes=1),
        limit=1,
    )
    created = await repository.upsert_state(
        session_id=live_session.id,
        last_strategy_state_report={"bar": 1},
        total_closed_trades=0,
        total_realized_pnl=Decimal("0"),
    )
    assert created.equity_curve == []
    updated = await repository.upsert_state(
        session_id=live_session.id,
        last_strategy_state_report={"bar": 2},
        total_closed_trades=1,
        total_realized_pnl=Decimal("1.25"),
        equity_curve=[{"timestamp_ms": 2, "cumulative_pnl": "1.25"}],
    )

    assert [row.id for row in rows] == [live_session.id]
    assert updated.equity_curve == [{"timestamp_ms": 2, "cumulative_pnl": "1.25"}]


@pytest.mark.asyncio
async def test_session_repository_does_not_deactivate_inactive_or_missing_rows(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """이미 종료됐거나 없는 세션 종료는 0건이며 기존 종료 사유를 덮어쓰지 않는다."""
    account = await _seed_account(db_session, user)
    original_at = datetime(2026, 8, 22, 19, tzinfo=UTC)
    inactive = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="ATOMUSDT",
        is_active=False,
        deactivated_at=original_at,
    )
    repository = LiveSignalSessionRepository(db_session)

    assert (
        await repository.deactivate(
            inactive.id,
            at=original_at + timedelta(minutes=1),
            reason=SessionDeactivationReason.run_live_error,
        )
        == 0
    )
    assert (
        await repository.deactivate(
            uuid4(),
            at=original_at + timedelta(minutes=1),
            reason=SessionDeactivationReason.run_live_error,
        )
        == 0
    )

    await db_session.refresh(inactive)
    assert inactive.deactivated_at == original_at
    assert inactive.deactivated_reason == SessionDeactivationReason.user_stopped


@pytest.mark.asyncio
async def test_event_repository_commits_and_returns_zero_for_absent_realized_pnl(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """명시 commit은 pending event를 유지하고, 실현 손익 없는 원장은 0을 반환한다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="UNIUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    [event] = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=datetime(2026, 8, 22, 20, tzinfo=UTC),
        signals=[
            {
                "sequence_no": 1,
                "action": "entry",
                "direction": "long",
                "trade_id": "no-pnl",
                "qty": "1",
            }
        ],
    )

    await repository.commit()

    assert await repository.get_by_id(uuid4()) is None
    assert await repository.get_by_id(event.id) is not None
    assert await repository.sum_realized_pnl_all(live_session.id) == (Decimal("0"), 0)


@pytest.mark.asyncio
async def test_event_repository_applies_zero_limits_and_keeps_orderless_event_visible(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """0건 페이지는 비고, 주문 없는 event는 LEFT JOIN에서 None 상태로 보존된다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="MATICUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    [event] = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=datetime(2026, 8, 22, 21, tzinfo=UTC),
        signals=[
            {
                "sequence_no": 1,
                "action": "entry",
                "direction": "short",
                "trade_id": "orderless",
                "qty": "2",
            }
        ],
    )

    assert await repository.list_pending(limit=0) == []
    assert await repository.list_by_session(live_session.id, limit=0) == []
    assert await repository.list_by_session_with_order_state(live_session.id) == [(event, None)]


@pytest.mark.asyncio
async def test_event_repository_does_not_dispatch_failed_or_missing_event(
    db_session: AsyncSession, user: User, strategy: Strategy
) -> None:
    """terminal failed event와 없는 event는 dispatch 경쟁의 winner가 될 수 없다."""
    account = await _seed_account(db_session, user)
    live_session = await _seed_session(
        db_session,
        user=user,
        strategy=strategy,
        account=account,
        symbol="NEARUSDT",
    )
    repository = LiveSignalEventRepository(db_session)
    [event] = await repository.insert_pending_events(
        session_id=live_session.id,
        bar_time=datetime(2026, 8, 22, 22, tzinfo=UTC),
        signals=[
            {
                "sequence_no": 1,
                "action": "entry",
                "direction": "long",
                "trade_id": "failed-before-dispatch",
                "qty": "1",
            }
        ],
    )

    assert await repository.mark_failed(event.id, error="blocked") == 1
    assert await repository.mark_dispatched(event.id, order_id=uuid4()) == 0
    assert await repository.mark_dispatched(uuid4(), order_id=uuid4()) == 0
    assert await repository.mark_failed(uuid4(), error="missing") == 0
