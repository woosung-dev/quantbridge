"""명시 attached SL 귀속의 SQL·체결·PnL 경계. 거래소/작업 큐는 대역만 사용한다."""

from datetime import UTC, datetime
from decimal import Decimal as D
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.trading.models import Order, OrderSide, OrderState, OrderType
from src.trading.providers import Credentials, _build_bybit_v5_order_status_fetch
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.code_risk_service import (
    CodeRiskError,
    CodeRiskReconciliationPending,
    CodeRiskService,
)
from src.trading.services.code_risk_venue import BybitCodeRiskVenue
from src.trading.services.native_sl_observation_service import NativeSLObservationService
from src.trading.services.websocket_order_event_service import WebSocketOrderEventService
from tests.trading import test_code_risk_repository as risk_tests

prepared = risk_tests.prepared


@pytest.fixture
async def native(prepared, db_session):
    repo, session, entry = prepared
    session.execution_snapshot = {"source_policy": "code_v1"}
    orders, risk = OrderRepository(db_session), CodeRiskService(repo)
    await orders.transition_to_submitted(entry.id, submitted_at=datetime.now(UTC))
    await orders.attach_exchange_order_id(entry.id, "parent-external")
    await risk.record_entry_fill(
        session.id, 1, entry.id, cumulative_quantity=D(2), cumulative_value=D(200), terminal=True
    )
    await orders.transition_to_filled(
        entry.id,
        exchange_order_id="parent-external",
        filled_price=D(100),
        filled_quantity=D(2),
        filled_at=datetime.now(UTC),
    )
    await repo.commit()
    await db_session.refresh(entry)
    handler = WebSocketOrderEventService(repo=orders, settings=AsyncMock(), risk_service=risk)
    handler._after_committed_winner = AsyncMock()
    raw = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "orderId": "native-child",
        "orderLinkId": "",
        "parentOrderLinkId": str(entry.id),
        "side": "Sell",
        "positionIdx": 0,
        "reduceOnly": True,
        "stopOrderType": "StopLoss",
        "createType": "CreateByStopLoss",
        "qty": "2",
        "orderStatus": "Filled",
        "cumExecQty": "2",
        "cumExecValue": "196",
        "avgPrice": "98.1",
        "closedPnl": "-4.01",
    }
    return repo, session, entry, orders, risk, handler, raw


async def child_rows(db_session):
    return list(
        (
            await db_session.execute(select(Order).where(Order.exchange_order_id == "native-child"))
        ).scalars()
    )


async def test_ws_exact_parent_creates_distinct_child_and_duplicate_credit_is_once(
    native, db_session
):
    repo, session, entry, orders, risk, handler, raw = native
    parent_before = entry.model_dump()
    await risk.confirm_flat_and_cancelled(
        session.id, 1, flat=True, cancelled=True, unexplained=True
    )
    await handler.handle_order_event(session.exchange_account_id, raw)
    (child,) = await child_rows(db_session)
    assert child.id != entry.id and child.reduce_only and child.state == OrderState.filled
    assert child.filled_price == D(98) and child.filled_quantity == 2
    assert child.realized_pnl == D("-4.01") and child.realized_pnl_synced_at is not None
    state = await repo.get(session.id)
    assert state.unsettled_exit_quantity == 0 and state.position_quantity == 0
    assert state.exit_fills[str(child.id)]["quantity"] == "2"
    revision = state.revision
    await handler.handle_order_event(session.exchange_account_id, raw)
    assert len(await child_rows(db_session)) == 1
    assert (await repo.get(session.id)).revision == revision
    await db_session.refresh(entry)
    assert entry.model_dump() == parent_before
    handler._after_committed_winner.assert_awaited_once()
    # 기존 불완전 aggregate 경로는 native 손익을 덮어쓸 수 없다.
    assert (
        await orders.backfill_exchange_realized_pnl(
            child.id, realized_pnl=D(999), synced_at=datetime.now(UTC)
        )
        == 0
    )
    assert (
        await orders.resync_exchange_realized_pnl(
            child.id, realized_pnl=D(999), synced_at=datetime.now(UTC)
        )
        == 0
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"parentOrderLinkId": ""},
        {"parentOrderLinkId": str(uuid4())},
        {"category": "spot"},
        {"symbol": "ETHUSDT"},
        {"side": "Buy"},
        {"positionIdx": 1},
        {"positionIdx": False},
        {"reduceOnly": False},
        {"stopOrderType": "TrailingStop"},
        {"createType": "CreateByTrailingStop"},
    ],
)
async def test_inexact_native_chain_never_updates_parent_or_consumes_exit(native, db_session, bad):
    repo, session, entry, _, _, handler, raw = native
    raw = {**raw, **bad, "orderLinkId": str(entry.id)}
    before = (await repo.get(session.id)).model_dump()
    # parent 필드가 빠졌어도 SL형식은 부모 entry를 갱신하면 안 된다.
    await handler.handle_order_event(session.exchange_account_id, raw)
    assert await child_rows(db_session) == []
    assert (await repo.get(session.id)).model_dump() == before
    await db_session.refresh(entry)
    assert entry.filled_quantity == 2 and entry.filled_price == 100


async def test_other_account_and_existing_external_binding_fail_closed(native, db_session):
    repo, session, entry, orders, _, handler, raw = native
    await handler.handle_order_event(uuid4(), raw)
    assert await child_rows(db_session) == []
    conflict = Order(
        strategy_id=entry.strategy_id,
        exchange_account_id=entry.exchange_account_id,
        symbol=entry.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(2),
        state=OrderState.submitted,
        exchange_order_id=raw["orderId"],
    )
    await orders.save(conflict)
    await repo.commit()
    with pytest.raises(CodeRiskError, match="기존 귀속"):
        await handler.handle_order_event(session.exchange_account_id, raw)
    assert not (await repo.get(session.id)).exit_fills


async def test_rest_quantity_recovery_preserves_unknown_pnl_then_late_ws_backfills(
    native, db_session
):
    repo, session, _, orders, risk, handler, raw = native
    venue = BybitCodeRiskVenue(repo, orders, risk, AsyncMock(), AsyncMock())
    rest = {k: v for k, v in raw.items() if k != "closedPnl"}
    binding = await NativeSLObservationService(orders).bind(session.exchange_account_id, rest)
    await venue._sync(binding[0], _build_bybit_v5_order_status_fetch(binding[1]))
    (child,) = await child_rows(db_session)
    assert child.realized_pnl is None and child.realized_pnl_synced_at is None
    assert (await repo.get(session.id)).position_quantity == 0
    # Order terminal CAS는 이미0이어도 새 WS의 exact closedPnl를 수집한다.
    await handler.handle_order_event(session.exchange_account_id, raw)
    await db_session.refresh(child)
    assert child.realized_pnl == D("-4.01")
    handler._after_committed_winner.assert_not_awaited()


async def test_observed_child_submit_forbidden_and_cancel_uses_external_id(native, db_session):
    repo, session, _, orders, risk, _, raw = native
    raw = {**raw, "orderStatus": "Untriggered", "cumExecQty": "0", "cumExecValue": "0"}
    child, _ = await NativeSLObservationService(orders).bind(session.exchange_account_id, raw)
    await repo.commit()
    provider = AsyncMock()
    venue = BybitCodeRiskVenue(repo, orders, risk, AsyncMock(), provider)
    with pytest.raises(CodeRiskError, match="새로 발주"):
        await venue._submit(Credentials("fake", "fake"), child)
    provider.create_order.assert_not_awaited()
    provider.fetch_order_by_client_id.assert_not_awaited()
    cancelled = {**raw, "orderStatus": "Cancelled"}
    provider.fetch_order.side_effect = [
        _build_bybit_v5_order_status_fetch(raw),
        _build_bybit_v5_order_status_fetch(cancelled),
    ]
    await venue._cancel_confirm(Credentials("fake", "fake"), child)
    provider.cancel_order.assert_awaited_once_with(
        Credentials("fake", "fake"), "native-child", session.symbol
    )
    provider.fetch_order_by_client_id.assert_not_awaited()


@pytest.mark.parametrize(
    "field,value", [("cumExecValue", None), ("cumExecValue", "NaN"), ("cumExecQty", "3")]
)
async def test_native_exact_value_required_without_quantity_times_average(
    native, db_session, field, value
):
    repo, session, _, _, _, handler, raw = native
    with pytest.raises(CodeRiskReconciliationPending):
        await handler.handle_order_event(session.exchange_account_id, {**raw, field: value})
    assert not (await repo.get(session.id)).exit_fills
    assert await child_rows(db_session) == []


async def test_partial_native_fill_is_unpriced_until_terminal_exact_ws_pnl(native, db_session):
    from src.trading.repositories.order_repository import SessionScope

    repo, session, _, orders, _, handler, raw = native
    partial = {**raw, "orderStatus": "PartiallyFilled", "cumExecQty": "0.5", "cumExecValue": "49"}
    partial.pop("closedPnl")
    await handler.handle_order_event(session.exchange_account_id, partial)
    assert (await repo.get(session.id)).position_quantity == D("1.5")
    assert (
        await orders.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(session))
        == 1
    )
    cancelled = {**partial, "orderStatus": "Cancelled"}
    await handler.handle_order_event(session.exchange_account_id, cancelled)
    assert (
        await orders.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(session))
        == 1
    )
    await handler.handle_order_event(
        session.exchange_account_id, {**cancelled, "closedPnl": "-1.02"}
    )
    assert (
        await orders.count_unpriced_exit_fills_for_session(SessionScope.from_live_session(session))
        == 0
    )


async def test_known_historical_native_order_only_backfills_pnl_in_later_generation(
    native, db_session
):
    from src.trading.models import LiveRiskState

    repo, session, entry, orders, risk, handler, raw = native
    rest = {k: v for k, v in raw.items() if k != "closedPnl"}
    venue = BybitCodeRiskVenue(repo, orders, risk, AsyncMock(), AsyncMock())
    child, normalized = await NativeSLObservationService(orders).bind(
        session.exchange_account_id, rest
    )
    await venue._sync(child, _build_bybit_v5_order_status_fetch(normalized))
    old = await repo.get(session.id)
    newer = LiveRiskState(
        **{
            **old.model_dump(),
            "generation": 2,
            "entry_order_id": uuid4(),
            "position_quantity": D(1),
            "direction": "short",
        }
    )
    # 새 세대의 실재 entry FK를 만들어 현재 원장과 과거 관측행을 분리한다.
    later = Order(
        id=newer.entry_order_id,
        strategy_id=entry.strategy_id,
        exchange_account_id=entry.exchange_account_id,
        symbol=entry.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(1),
        state=OrderState.pending,
    )
    await orders.save(later)
    assert await repo.compare_and_swap(newer, old.revision)
    await repo.commit()
    before = (await repo.get(session.id)).model_dump()
    await handler.handle_order_event(session.exchange_account_id, raw)
    assert (await repo.get(session.id)).model_dump() == before
    await db_session.refresh(child)
    assert child.realized_pnl == D("-4.01")
    with pytest.raises(CodeRiskError, match="귀속"):
        await handler.handle_order_event(
            session.exchange_account_id, {**raw, "parentOrderLinkId": str(uuid4())}
        )
    await handler.handle_order_event(
        session.exchange_account_id, {**raw, "orderId": "unbound-old-child"}
    )
    assert len(await child_rows(db_session)) == 1


@pytest.mark.parametrize("known_quantity", [D(0), D(1)])
async def test_child_fill_before_terminal_parent_defers_exit_and_requests_close(
    prepared, db_session, known_quantity
):
    repo, session, entry = prepared
    session.execution_snapshot = {"source_policy": "code_v1"}
    orders, risk = OrderRepository(db_session), CodeRiskService(repo)
    await orders.transition_to_submitted(entry.id, submitted_at=datetime.now(UTC))
    await orders.attach_exchange_order_id(entry.id, "parent-external")
    await risk.record_entry_fill(
        session.id,
        1,
        entry.id,
        cumulative_quantity=known_quantity,
        cumulative_value=known_quantity * D(100),
        terminal=False,
    )
    raw = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "orderId": "native-child",
        "parentOrderLinkId": str(entry.id),
        "side": "Sell",
        "positionIdx": 0,
        "reduceOnly": True,
        "stopOrderType": "StopLoss",
        "createType": "CreateByStopLoss",
        "qty": "2",
        "orderStatus": "Filled",
        "cumExecQty": "2",
        "cumExecValue": "196",
    }
    handler = WebSocketOrderEventService(repo=orders, settings=AsyncMock(), risk_service=risk)
    handler._after_committed_winner = AsyncMock()
    commands = await handler.handle_order_event(session.exchange_account_id, raw)
    before = await repo.get(session.id)
    assert not before.exit_fills and before.close_requested
    assert {"cancel_entry", "flatten"} <= {c.kind for c in commands}
    assert await child_rows(db_session) == []
    await risk.record_entry_fill(
        session.id, 1, entry.id, cumulative_quantity=D(2), cumulative_value=D(200), terminal=True
    )
    await risk.confirm_flat_and_cancelled(
        session.id, 1, flat=True, cancelled=True, unexplained=True
    )
    await handler.handle_order_event(session.exchange_account_id, raw)
    state = await repo.get(session.id)
    assert (
        state.position_quantity == 0
        and state.unsettled_exit_quantity == 0
        and not state.new_entries_blocked
    )


async def test_untriggered_sl_does_not_cancel_nonterminal_partial_entry(prepared, db_session):
    repo, session, entry = prepared
    session.execution_snapshot = {"source_policy": "code_v1"}
    orders, risk = OrderRepository(db_session), CodeRiskService(repo)
    await orders.attach_exchange_order_id(entry.id, "parent-external")
    await risk.record_entry_fill(
        session.id, 1, entry.id, cumulative_quantity=D(1), cumulative_value=D(100), terminal=False
    )
    handler = WebSocketOrderEventService(repo=orders, settings=AsyncMock(), risk_service=risk)
    raw = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "orderId": "native-child",
        "parentOrderLinkId": str(entry.id),
        "side": "Sell",
        "positionIdx": 0,
        "reduceOnly": True,
        "stopOrderType": "StopLoss",
        "createType": "CreateByStopLoss",
        "qty": "1",
        "orderStatus": "Untriggered",
        "cumExecQty": "0",
        "cumExecValue": "0",
    }
    before = (await repo.get(session.id)).model_dump()
    await handler.handle_order_event(session.exchange_account_id, raw)
    assert (await repo.get(session.id)).model_dump() == before
    assert await child_rows(db_session) == []


async def test_current_payload_cannot_select_historical_pnl_only(native, db_session):
    repo, session, _entry, _orders, _risk, handler, raw = native
    await handler.handle_order_event(
        session.exchange_account_id, {**raw, "_native_historical": True}
    )
    assert (await repo.get(session.id)).position_quantity == 0
    (child,) = await child_rows(db_session)
    assert child.filled_quantity == 2 and child.realized_pnl == D("-4.01")


async def test_observed_partial_quantity_is_persisted_and_never_resubmitted(native, db_session):
    _repo, session, _entry, _orders, _risk, handler, raw = native
    partial = {**raw, "orderStatus": "PartiallyFilled", "cumExecQty": ".5", "cumExecValue": "49"}
    await handler.handle_order_event(session.exchange_account_id, partial)
    (child,) = await child_rows(db_session)
    assert child.state == OrderState.submitted
    assert child.filled_quantity == D(".5") and child.filled_price == D(98)


async def test_invalid_or_missing_identity_does_not_bind(native):
    _repo, session, _entry, orders, _risk, _handler, raw = native
    for payload in ({k: v for k, v in raw.items() if k != "symbol"}, {**raw, "orderId": "x" * 121}):
        assert (
            await NativeSLObservationService(orders).bind(session.exchange_account_id, payload)
            is None
        )


async def test_native_cancel_revalidates_child_id_before_external_call(native):
    repo, session, _entry, orders, risk, _handler, raw = native
    active = {**raw, "orderStatus": "Untriggered", "cumExecQty": "0", "cumExecValue": "0"}
    child, _ = await NativeSLObservationService(orders).bind(session.exchange_account_id, active)
    await repo.commit()
    provider = AsyncMock()
    provider.fetch_order.return_value = _build_bybit_v5_order_status_fetch(
        {**active, "orderId": "another-child"}
    )
    venue = BybitCodeRiskVenue(repo, orders, risk, AsyncMock(), provider)
    with pytest.raises(CodeRiskReconciliationPending):
        await venue._cancel_confirm(Credentials("fake", "fake"), child)
    provider.cancel_order.assert_not_awaited()
    provider.create_order.assert_not_awaited()


async def test_observation_rollback_keeps_order_risk_and_pnl_atomic(
    native, db_session, monkeypatch
):
    repo, session, _entry, orders, _risk, handler, raw = native
    session_id = session.id
    before = (await repo.get(session_id)).model_dump()
    commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    monkeypatch.setattr(orders, "commit", commit)
    with pytest.raises(RuntimeError, match="commit failed"):
        await handler.handle_order_event(session.exchange_account_id, raw)
    commit.assert_awaited_once()
    handler._after_committed_winner.assert_not_awaited()
    await db_session.rollback()
    assert await child_rows(db_session) == []
    assert (await repo.get(session_id)).model_dump() == before


async def test_two_sql_transactions_ws_rest_bind_one_child_and_credit_once(
    _test_engine, monkeypatch
):
    import asyncio

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from src.auth.models import User
    from src.strategy.models import ParseStatus, Strategy
    from src.trading.models import (
        CodeRiskCommand,
        ExchangeAccount,
        ExchangeMode,
        ExchangeName,
        LiveRiskState,
        LiveSignalInterval,
        LiveSignalSession,
    )

    maker = async_sessionmaker(_test_engine, expire_on_commit=False)
    user = User(auth_subject=f"native-race-{uuid4()}")
    strategy = Strategy(user_id=user.id, name="native race", parse_status=ParseStatus.ok)
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"fake",
        api_secret_encrypted=b"fake",
    )
    live = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.h1,
        execution_snapshot={"source_policy": "code_v1"},
    )
    entry = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(2),
        state=OrderState.pending,
    )
    raw = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "orderId": f"race-{uuid4()}",
        "parentOrderLinkId": str(entry.id),
        "side": "Sell",
        "positionIdx": 0,
        "reduceOnly": True,
        "stopOrderType": "StopLoss",
        "createType": "CreateByStopLoss",
        "qty": "2",
        "orderStatus": "Filled",
        "cumExecQty": "2",
        "cumExecValue": "196",
        "closedPnl": "-4.01",
    }
    try:
        async with maker() as sql:
            sql.add(user)
            await sql.flush()
            sql.add_all([strategy, account])
            await sql.flush()
            sql.add_all([live, entry])
            await sql.flush()
            repo = CodeRiskRepository(sql)
            risk = CodeRiskService(repo)
            await risk.prepare_entry(
                live.id,
                entry.id,
                direction="long",
                estimated_entry=D(100),
                quantity=D(2),
                previous_bars=[{"low": D(98), "high": D(102)}] * 2,
                qty_step=D(".1"),
                min_qty=D(".1"),
            )
            await OrderRepository(sql).attach_exchange_order_id(entry.id, "race-parent")
            await risk.record_entry_fill(
                live.id,
                1,
                entry.id,
                cumulative_quantity=D(2),
                cumulative_value=D(200),
                terminal=True,
            )
            await risk.confirm_flat_and_cancelled(
                live.id, 1, flat=True, cancelled=True, unexplained=True
            )
        acquired, release = asyncio.Event(), asyncio.Event()
        original = NativeSLObservationService.bind

        async def paused_bind(self, account_id, payload):
            result = await original(self, account_id, payload)
            if asyncio.current_task().get_name() == "native-ws":
                acquired.set()
                await release.wait()
            return result

        monkeypatch.setattr(NativeSLObservationService, "bind", paused_bind)

        async def ws():
            async with maker() as sql:
                orders, risk = OrderRepository(sql), CodeRiskService(CodeRiskRepository(sql))
                orders.commit = AsyncMock(wraps=orders.commit)
                service = WebSocketOrderEventService(
                    repo=orders, settings=AsyncMock(), risk_service=risk
                )
                service._after_committed_winner = AsyncMock()
                await service.handle_order_event(account.id, raw)
                orders.commit.assert_awaited_once()

        async def rest():
            async with maker() as sql:
                orders, repo = OrderRepository(sql), CodeRiskRepository(sql)
                binding = await NativeSLObservationService(orders).bind(
                    account.id, {k: v for k, v in raw.items() if k != "closedPnl"}
                )
                child, normalized = binding
                await BybitCodeRiskVenue(
                    repo, orders, CodeRiskService(repo), AsyncMock(), AsyncMock()
                )._sync(child, _build_bybit_v5_order_status_fetch(normalized))

        first = asyncio.create_task(ws(), name="native-ws")
        second = None
        try:
            await asyncio.wait_for(acquired.wait(), 5)
            second = asyncio.create_task(rest(), name="native-rest")
            await asyncio.sleep(0.05)
            assert not second.done(), "second transaction must wait for account+child advisory lock"
            release.set()
            await asyncio.wait_for(asyncio.gather(first, second), 10)
        finally:
            release.set()
            pending = [task for task in (first, second) if task is not None and not task.done()]
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        async with maker() as sql:
            rows = list(
                (
                    await sql.execute(
                        select(Order).where(
                            Order.exchange_account_id == account.id, Order.reduce_only.is_(True)
                        )
                    )
                ).scalars()
            )
            assert len(rows) == 1
            assert rows[0].filled_quantity == 2 and rows[0].realized_pnl == D("-4.01")
            state = await CodeRiskRepository(sql).get(live.id)
            assert state.position_quantity == state.unsettled_exit_quantity == 0
            assert state.exit_fills[str(rows[0].id)]["quantity"] == "2"
            assert (
                state.revision == 3
            )  # entry, flat marker, one exit credit; REST duplicate adds none
    finally:
        async with maker() as sql:
            for model, predicate in (
                (CodeRiskCommand, CodeRiskCommand.session_id == live.id),
                (LiveRiskState, LiveRiskState.session_id == live.id),
                (Order, Order.exchange_account_id == account.id),
                (LiveSignalSession, LiveSignalSession.id == live.id),
                (ExchangeAccount, ExchangeAccount.id == account.id),
                (Strategy, Strategy.id == strategy.id),
                (User, User.id == user.id),
            ):
                await sql.execute(delete(model).where(predicate))
            await sql.commit()


async def test_bind_and_atomic_close_do_not_commit_without_caller(native, monkeypatch):
    repo, session, _entry, orders, risk, _handler, raw = native
    commit = AsyncMock(wraps=orders.commit)
    monkeypatch.setattr(orders, "commit", commit)
    await NativeSLObservationService(orders).bind(session.exchange_account_id, raw)
    commit.assert_not_awaited()
    risk_commit = AsyncMock(wraps=repo.commit)
    monkeypatch.setattr(repo, "commit", risk_commit)
    await risk.request_signal(session.id, 1, "close", commit=False)
    risk_commit.assert_not_awaited()
    await orders.commit()
    commit.assert_awaited_once()


async def test_native_generic_cancel_and_submit_workers_cannot_reach_exchange(
    native, db_session, monkeypatch
):
    from contextlib import asynccontextmanager

    from src.tasks import trading
    from src.trading.services.order_service import OrderService

    repo, session, _entry, orders, _risk, _handler, raw = native
    active = {**raw, "orderStatus": "Untriggered", "cumExecQty": "0", "cumExecValue": "0"}
    child, _ = await NativeSLObservationService(orders).bind(session.exchange_account_id, active)
    await repo.commit()
    delay = MagicMock()
    monkeypatch.setattr(trading.cancel_order_task, "delay", delay)
    service = OrderService(db_session, orders, AsyncMock(), AsyncMock())
    assert (await service.cancel_for_user(child.id, session.user_id)).kind == "conflict"
    delay.assert_not_called()

    @asynccontextmanager
    async def sm():
        yield db_session

    provider_factory = MagicMock(side_effect=AssertionError("external provider forbidden"))
    monkeypatch.setattr(trading, "_provider_from_order_snapshot_or_fallback", provider_factory)
    assert (await trading._cancel_order_with_session(child.id, sm))[
        "skipped"
    ] == "native_risk_cancel_required"
    assert (await trading._execute_with_session(child.id, sm))[
        "skipped"
    ] == "native_observation_only"
    provider_factory.assert_not_called()
    await db_session.refresh(child)
    assert child.state == OrderState.submitted


async def test_rest_recovery_loads_entry_before_explicit_child_and_never_confirms_pnl(
    native, db_session
):
    repo, session, _entry, orders, risk, _handler, raw = native
    provider, accounts = AsyncMock(), AsyncMock()
    accounts.get_credentials_for_order.return_value = Credentials("fake", "fake")
    calls = []

    async def parent_status(*args):
        calls.append("parent")
        return _build_bybit_v5_order_status_fetch(
            {
                "orderId": "parent-external",
                "orderStatus": "Filled",
                "cumExecQty": "2",
                "cumExecValue": "200",
                "avgPrice": "100",
            }
        )

    async def history(*args, **kwargs):
        calls.append("history")
        return [{k: v for k, v in raw.items() if k != "closedPnl"}]

    provider.fetch_order_by_client_id.side_effect = parent_status
    provider.fetch_attached_sl_orders.side_effect = history
    provider.fetch_position.return_value = None
    assert await BybitCodeRiskVenue(repo, orders, risk, accounts, provider).reconcile(
        session, await repo.get(session.id)
    )
    assert calls == ["parent", "history"]
    (child,) = await child_rows(db_session)
    assert child.exchange_order_id == raw["orderId"] and child.filled_quantity == 2
    assert child.realized_pnl is None
    state = await repo.get(session.id)
    assert state.position_quantity == state.unsettled_exit_quantity == 0
    provider.create_order.assert_not_awaited()


async def test_known_partial_tp_then_native_sl_only_debits_remaining(native, db_session):
    repo, session, _entry, _orders, risk, handler, raw = native
    tp_id = uuid4()
    await risk.record_exit_fill(
        session.id, 1, tp_id, role="partial_tp", cumulative_quantity=D(1), terminal=True
    )
    await handler.handle_order_event(
        session.exchange_account_id,
        {**raw, "qty": "1", "cumExecQty": "1", "cumExecValue": "98", "closedPnl": "-2.01"},
    )
    state = await repo.get(session.id)
    assert state.position_quantity == 0 and not state.failure_reason
    assert state.tp_filled_quantity == 1
    assert state.exit_fills[str(tp_id)]["quantity"] == "1"
    (child,) = await child_rows(db_session)
    assert state.exit_fills[str(child.id)]["quantity"] == "1"
