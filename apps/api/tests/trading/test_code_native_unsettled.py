"""native 청산 미귀속은 실현손익으로 추정하지 않고 계정 범위 진입을 막는다."""

from datetime import UTC, datetime
from decimal import Decimal as D
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from src.trading.models import (
    ExchangeAccount,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.providers import OrderStatusFetch
from src.trading.repositories.code_checkpoint_repository import CodeCheckpointRepository
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import RegisterLiveSessionRequest
from src.trading.services.code_risk_service import CodeRiskService
from src.trading.services.code_risk_venue import BybitCodeRiskVenue
from src.trading.services.live_session_query_service import LiveSessionQueryService
from src.trading.services.live_session_service import LiveSignalSessionService
from tests.trading import test_code_risk_repository as risk_tests

prepared = risk_tests.prepared


async def unexplained_flat(prepared, db_session):
    repo, session, entry = prepared
    risk = CodeRiskService(repo)
    await risk.record_entry_fill(
        session.id, 1, entry.id, cumulative_quantity=D(2), cumulative_value=D(200), terminal=True
    )
    await OrderRepository(db_session).transition_to_submitted(
        entry.id, submitted_at=datetime.now(UTC)
    )
    await db_session.commit()
    provider = AsyncMock()
    provider.fetch_order_by_client_id.return_value = OrderStatusFetch(
        exchange_order_id="entry",
        status="filled",
        filled_quantity=D(2),
        filled_price=D(100),
        cumulative_value=D(200),
    )
    provider.fetch_position.return_value = None
    venue = BybitCodeRiskVenue(repo, OrderRepository(db_session), risk, AsyncMock(), provider)
    await venue.reconcile(session, await repo.get(session.id))
    return repo, session, entry, risk, venue


@pytest.mark.asyncio
async def test_unknown_native_flat_is_durable_inactive_archived_and_legacy_registration_cannot_bypass(
    prepared, db_session
):
    from src.strategy.repository import StrategyRepository
    from src.trading.exceptions import InvalidStrategySettings

    repo, session, _entry, risk, _ = await unexplained_flat(prepared, db_session)
    account_repo = ExchangeAccountRepository(db_session)
    state = await repo.get(session.id)
    assert state.unsettled_exit_quantity == D(2) and state.position_quantity == 0
    assert state.new_entries_blocked and state.failure_reason == "native_exit_unsettled"
    # 5초 복구·중복 flat도 금액을 합성하거나 marker를 지우지 않는다.
    await risk.confirm_flat_and_cancelled(
        session.id, 1, flat=True, cancelled=True, unexplained=True
    )
    assert (await repo.get(session.id)).unsettled_exit_quantity == D(2)
    session.is_active = False
    session.deactivated_at = datetime.now(UTC)
    await StrategyRepository(db_session).archive_all_by_owner(session.user_id)
    await db_session.commit()
    assert await account_repo.has_unsettled_code_exit(session.exchange_account_id)
    assert await CodeRiskRepository(db_session).has_unsettled_exit_for_account(
        session.exchange_account_id
    )
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = SimpleNamespace(
        id=session.strategy_id,
        execution_policy=None,
        settings={
            "schema_version": 1,
            "leverage": 1,
            "margin_mode": "cross",
            "position_size_pct": 10,
        },
    )
    balance, exclusive = AsyncMock(), AsyncMock()
    service = LiveSignalSessionService(
        LiveSignalSessionRepository(db_session),
        account_repo,
        strategy_repo,
        balance_service=balance,
        exclusivity_service=exclusive,
    )
    with pytest.raises(InvalidStrategySettings, match="미정산"):
        await service.register(
            session.user_id,
            RegisterLiveSessionRequest(
                strategy_id=session.strategy_id,
                exchange_account_id=session.exchange_account_id,
                symbol="BTC/USDT",
                interval="1h",
            ),
        )
    balance.get_balance.assert_not_awaited()
    exclusive.ensure_exclusive.assert_not_awaited()
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(
                delete(LiveSignalSession).where(LiveSignalSession.id == session.id)
            )
    from src.strategy.models import Strategy

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(delete(Strategy).where(Strategy.id == session.strategy_id))
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await account_repo.delete(session.exchange_account_id)
    assert await account_repo.has_unsettled_code_exit(session.exchange_account_id)
    # 새 모델 인스턴스로 읽어도 권위 marker가 남는다.
    assert (await CodeRiskRepository(db_session).get(session.id)).unsettled_exit_quantity == 2


@pytest.mark.asyncio
async def test_known_uid_sibling_is_blocked_but_unrelated_and_unknown_uid_are_not_assumed_equal(
    prepared, db_session
):
    repo, session, _, _, _ = await unexplained_flat(prepared, db_session)
    account = await repo.get_account(session.exchange_account_id)
    account.exchange_uid = "known-physical-account"
    siblings = []
    for uid in (account.exchange_uid, "different-account", None):
        sibling = ExchangeAccount(
            user_id=account.user_id,
            exchange=account.exchange,
            mode=account.mode,
            exchange_uid=uid,
            api_key_encrypted=b"fake",
            api_secret_encrypted=b"fake",
        )
        db_session.add(sibling)
        siblings.append(sibling)
    await db_session.commit()
    accounts = ExchangeAccountRepository(db_session)
    assert await accounts.has_unsettled_code_exit(siblings[0].id)
    assert not await accounts.has_unsettled_code_exit(siblings[1].id)
    assert not await accounts.has_unsettled_code_exit(siblings[2].id)


@pytest.mark.asyncio
async def test_late_exact_local_terminal_fill_offsets_marker_once_without_inventing_native_order(
    prepared, db_session
):
    repo, session, _entry, _risk, venue = await unexplained_flat(prepared, db_session)
    order = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(2),
        reduce_only=True,
        state=OrderState.submitted,
        risk_context={"session_id": str(session.id), "generation": 1, "role": "close"},
    )
    db_session.add(order)
    await db_session.commit()
    status = OrderStatusFetch(
        exchange_order_id="local-close", status="filled", filled_quantity=D(2), filled_price=D(99)
    )
    await venue._sync(order, status)
    state = await repo.get(session.id)
    assert state.position_quantity == 0 and state.unsettled_exit_quantity == 0
    assert not state.new_entries_blocked and state.failure_reason is None
    revision = state.revision
    await venue._sync(order, status)
    assert (await repo.get(session.id)).revision == revision
    assert (await repo.get(session.id)).exit_fills[str(order.id)]["quantity"] == "2"
    assert not await repo.has_unsettled_exit_for_account(session.exchange_account_id)


@pytest.mark.asyncio
async def test_unknown_order_cannot_clear_native_marker(prepared, db_session):
    repo, session, _, risk, _ = await unexplained_flat(prepared, db_session)
    await risk.record_exit_fill(
        session.id, 1, uuid4(), role="stop_loss", cumulative_quantity=D("0.5"), terminal=True
    )
    state = await repo.get(session.id)
    assert state.unsettled_exit_quantity == 2 and state.new_entries_blocked


@pytest.mark.asyncio
async def test_code_pnl_response_is_known_order_subtotal_and_incomplete_for_native_or_unpriced_exit(
    prepared, db_session
):
    repo, session, _entry, risk, _ = await unexplained_flat(prepared, db_session)
    session.execution_snapshot = {"source_policy": "code_v1"}
    await db_session.commit()
    orders = OrderRepository(db_session)
    query = LiveSessionQueryService(
        LiveSignalSessionRepository(db_session),
        orders,
        LiveSignalEventRepository(db_session),
        CodeCheckpointRepository(db_session),
        repo,
    )
    state = await query.get_state_for_user(session.id, session.user_id)
    assert state.pnl_complete is False and state.pnl_scope == "known_order_subtotal"
    assert state.total_realized_pnl == 0 and state.code_execution.unsettled_exit_quantity == 2
    # unknown native는 거래소 Order 없이도 불완전이다. 단순 0 confirmed로 해석하면 안 된다.
    assert state.unpriced_exit_orders == 0
    child = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(2),
        reduce_only=True,
        state=OrderState.submitted,
        risk_context={"session_id": str(session.id), "generation": 1, "role": "close"},
    )
    db_session.add(child)
    await db_session.commit()
    await risk.record_exit_fill(
        session.id, 1, child.id, role="close", cumulative_quantity=D(2), terminal=True
    )
    await orders.transition_to_filled(
        child.id,
        exchange_order_id="actual-local",
        filled_price=D(99),
        filled_quantity=D(2),
        filled_at=datetime.now(UTC),
    )
    await db_session.commit()
    state = await query.get_state_for_user(session.id, session.user_id)
    assert state.pnl_complete is False and state.unpriced_exit_orders == 1
    await orders.backfill_exchange_realized_pnl(
        child.id, realized_pnl=D(-2), synced_at=datetime.now(UTC)
    )
    await db_session.commit()
    state = await query.get_state_for_user(session.id, session.user_id)
    assert state.pnl_complete is True and state.total_realized_pnl == -2


@pytest.mark.parametrize("reduce_only", [False, True])
async def test_manual_and_webhook_order_service_cannot_bypass_account_marker(
    prepared, db_session, reduce_only
):
    from src.trading.exceptions import NativeExitUnsettled
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    _, session, _, _, _ = await unexplained_flat(prepared, db_session)
    dispatcher = AsyncMock()
    kill_switch = AsyncMock()
    service = OrderService(db_session, OrderRepository(db_session), dispatcher, kill_switch)
    request = OrderRequest(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol="BTCUSDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D("0.2"),
        reduce_only=reduce_only,
    )
    if reduce_only:
        response, replayed = await service.execute(request, idempotency_key=None)
        assert response.reduce_only and not replayed
        dispatcher.dispatch_order_execution.assert_awaited_once()
    else:
        with pytest.raises(NativeExitUnsettled) as exc:
            await service.execute(request, idempotency_key=None)
        assert exc.value.code == "native_exit_unsettled"
        dispatcher.dispatch_order_execution.assert_not_awaited()
        kill_switch.ensure_not_gated.assert_not_awaited()


@pytest.mark.parametrize("evidence", ["not_reduce_only", "wrong_generation"])
async def test_inexact_local_order_cannot_release_marker(prepared, db_session, evidence):
    repo, session, _, risk, _ = await unexplained_flat(prepared, db_session)
    child = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(2),
        reduce_only=evidence != "not_reduce_only",
        state=OrderState.submitted,
        risk_context={
            "session_id": str(session.id),
            "generation": 2 if evidence == "wrong_generation" else 1,
            "role": "close",
        },
    )
    db_session.add(child)
    await db_session.commit()
    await risk.record_exit_fill(
        session.id,
        1,
        child.id,
        role="close",
        cumulative_quantity=D(2),
        terminal=evidence != "nonterminal",
    )
    assert (await repo.get(session.id)).unsettled_exit_quantity == 2


@pytest.mark.parametrize("unknown_uid", [None, "", "   ", "\t\r\n"])
async def test_blank_uid_is_unknown_and_never_binds_unrelated_account(
    prepared, db_session, unknown_uid
):
    repo, session, _, _, _ = await unexplained_flat(prepared, db_session)
    account = await repo.get_account(session.exchange_account_id)
    account.exchange_uid = unknown_uid
    sibling = ExchangeAccount(
        user_id=account.user_id,
        exchange=account.exchange,
        mode=account.mode,
        exchange_uid=unknown_uid,
        api_key_encrypted=b"fake",
        api_secret_encrypted=b"fake",
    )
    db_session.add(sibling)
    await db_session.commit()
    accounts = ExchangeAccountRepository(db_session)
    assert await accounts.has_unsettled_code_exit(account.id)
    assert not await accounts.has_unsettled_code_exit(sibling.id)


async def test_post_marker_partial_evidence_survives_restart_and_terminal_offsets_once(
    prepared, db_session
):
    repo, session, _, risk, _ = await unexplained_flat(prepared, db_session)
    child = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(2),
        reduce_only=True,
        state=OrderState.submitted,
        risk_context={"session_id": str(session.id), "generation": 1, "role": "close"},
    )
    db_session.add(child)
    await db_session.commit()
    await risk.record_exit_fill(
        session.id, 1, child.id, role="close", cumulative_quantity=D(1), terminal=False
    )
    assert (await repo.get(session.id)).unsettled_exit_quantity == 2
    assert (await repo.get(session.id)).exit_fills[str(child.id)]["unsettled_pending"] == "1"
    restarted = CodeRiskService(CodeRiskRepository(db_session))
    await restarted.record_exit_fill(
        session.id, 1, child.id, role="close", cumulative_quantity=D(1), terminal=True
    )
    state = await repo.get(session.id)
    assert state.unsettled_exit_quantity == 1 and state.new_entries_blocked
    assert state.exit_fills[str(child.id)]["unsettled_pending"] == "0"
    revision = state.revision
    await restarted.record_exit_fill(
        session.id, 1, child.id, role="close", cumulative_quantity=D(1), terminal=True
    )
    assert (await repo.get(session.id)).revision == revision
    await restarted.record_exit_fill(
        session.id, 1, child.id, role="close", cumulative_quantity=D(2), terminal=True
    )
    state = await repo.get(session.id)
    assert state.unsettled_exit_quantity == 0 and not state.new_entries_blocked


async def test_pre_marker_partial_fill_is_not_credited_again_by_terminal_reobservation(
    prepared, db_session
):
    repo, session, entry = prepared
    risk = CodeRiskService(repo)
    await risk.record_entry_fill(
        session.id, 1, entry.id, cumulative_quantity=D(2), cumulative_value=D(200), terminal=True
    )
    child = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.sell,
        type=OrderType.limit,
        quantity=D(1),
        reduce_only=True,
        state=OrderState.submitted,
        risk_context={"session_id": str(session.id), "generation": 1, "role": "partial_tp"},
    )
    db_session.add(child)
    await db_session.commit()
    await risk.record_exit_fill(
        session.id, 1, child.id, role="partial_tp", cumulative_quantity=D(1), terminal=False
    )
    await risk.confirm_flat_and_cancelled(
        session.id, 1, flat=True, cancelled=True, unexplained=True
    )
    assert (await repo.get(session.id)).unsettled_exit_quantity == 1
    await CodeRiskService(CodeRiskRepository(db_session)).record_exit_fill(
        session.id, 1, child.id, role="partial_tp", cumulative_quantity=D(1), terminal=True
    )
    assert (await repo.get(session.id)).unsettled_exit_quantity == 1
    assert (await repo.get(session.id)).new_entries_blocked


async def test_downgrade_refuses_to_drop_unsettled_evidence_on_disposable_sql_database(
    prepared, db_session
):
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory

    from tests import _db_guard

    _db_guard.assert_disposable(_db_guard.resolve_test_dsn())
    repo, session, _, _, _ = await unexplained_flat(prepared, db_session)
    migration = (
        ScriptDirectory.from_config(Config("alembic.ini")).get_revision("20261022_0005").module
    )

    def downgrade(connection):
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()

    connection = await db_session.connection()
    with pytest.raises(RuntimeError, match="미정산 native 청산"):
        await connection.run_sync(downgrade)
    assert (await repo.get(session.id)).unsettled_exit_quantity == 2
    assert await repo.has_unsettled_exit_for_account(session.exchange_account_id)
