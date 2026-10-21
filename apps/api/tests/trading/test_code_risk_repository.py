"""슬롯 테스트 DB에서 한 행·CAS·주문 귀속의 실제 SQL을 검증한다."""

from datetime import UTC, datetime
from decimal import Decimal as D
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
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
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.code_risk_service import CodeRiskService
from src.trading.services.websocket_order_event_service import WebSocketOrderEventService


@pytest.fixture
async def prepared(db_session: AsyncSession, user, strategy):
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"fake",
        api_secret_encrypted=b"fake",
    )
    db_session.add(account)
    await db_session.flush()
    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.h1,
    )
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D("2"),
        state=OrderState.pending,
    )
    db_session.add_all([session, order])
    await db_session.flush()
    repo = CodeRiskRepository(db_session)
    await CodeRiskService(repo).prepare_entry(
        session.id,
        order.id,
        direction="long",
        estimated_entry=D("100"),
        quantity=D("2"),
        previous_bars=[{"low": D("98"), "high": D("102")}, {"low": D("99"), "high": D("101")}],
        qty_step=D("0.1"),
        min_qty=D("0.1"),
    )
    return repo, session, order


@pytest.mark.asyncio
async def test_real_cas_has_one_winner_and_refreshes_identity_map(prepared):
    repo, session, _order = prepared
    original = await repo.get(session.id)
    assert original is not None
    first, second = type(original)(**original.model_dump()), type(original)(**original.model_dump())
    first.failure_reason, second.failure_reason = "winner", "loser"
    assert await repo.compare_and_swap(first, original.revision)
    assert not await repo.compare_and_swap(second, original.revision)
    await repo.commit()
    observed = await repo.get(session.id)
    assert observed is not None and observed.failure_reason == "winner" and observed.revision == 1
    assert not await repo.create_if_absent(original)


@pytest.mark.asyncio
async def test_entry_context_and_provisional_stop_share_persisted_generation(prepared, db_session):
    repo, session, order = prepared
    await db_session.refresh(order)
    assert order.risk_context == {"session_id": str(session.id), "generation": 1, "role": "entry"}
    assert order.stop_loss == D("97.8")
    assert session.execution_snapshot is None
    assert await repo.get_entry_order(uuid4(), order.id) is None
    state = await repo.get(session.id)
    assert state is not None and not await repo.attach_entry(state, D("97"))
    svc = CodeRiskService(repo)
    commands = await svc.record_entry_fill(
        session.id,
        1,
        order.id,
        cumulative_quantity=D("2"),
        cumulative_value=D("204"),
        terminal=True,
    )
    assert commands[0].kind == "apply_protection"
    recovered = await CodeRiskService(CodeRiskRepository(db_session)).recover(session.id)
    assert recovered == commands
    observed = await repo.get(session.id)
    assert observed is not None and observed.fixed_r == D("4.4") and observed.revision == 1
    assert (
        await svc.acknowledge_protection(
            session.id, 1, token=str(commands[0].payload["token"]), success=True
        )
        == []
    )


@pytest.mark.asyncio
async def test_real_ws_partial_and_terminal_fill_share_commit_and_survive_restart(
    prepared, db_session
):
    repo, session, order = prepared
    await db_session.refresh(order)
    order_repo = OrderRepository(db_session)
    await order_repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await order_repo.commit()
    order_repo.commit = AsyncMock(wraps=order_repo.commit)
    repo.commit = AsyncMock(wraps=repo.commit)
    handler = WebSocketOrderEventService(
        repo=order_repo, risk_service=CodeRiskService(repo), settings=MagicMock()
    )
    handler._after_committed_winner = AsyncMock()
    payload = {
        "orderLinkId": str(order.id),
        "orderId": "exchange-code",
        "orderStatus": "PartiallyFilled",
        "cumExecQty": "1",
        "cumExecValue": "100",
        "avgPrice": "100",
    }
    commands = await handler.handle_order_event(order.exchange_account_id, payload)
    assert commands and commands[0].kind == "apply_protection"
    repo.commit.assert_not_awaited()
    order_repo.commit.assert_awaited_once()
    state = await repo.get(session.id)
    assert state is not None and state.fixed_r is None and state.position_quantity == D("1")
    payload.update(orderStatus="Filled", cumExecQty="2", cumExecValue="204", avgPrice="102")
    commands = await handler.handle_order_event(order.exchange_account_id, payload)
    assert commands == await CodeRiskService(CodeRiskRepository(db_session)).recover(session.id)
    await db_session.refresh(order)
    assert order.state == OrderState.filled and order.filled_quantity == D("2")
    state = await repo.get(session.id)
    assert state is not None and state.fixed_r == D("4.4") and state.revision == 2


@pytest.mark.asyncio
async def test_outbox_lease_survives_restart_and_rejects_old_ack(prepared, db_session):
    from datetime import timedelta

    from sqlalchemy import func, select

    from src.trading.models import CodeRiskCommand

    repo, session, _ = prepared
    commands = await CodeRiskService(repo).recover(session.id)
    row = CodeRiskCommand(
        key=commands[0].key,
        session_id=session.id,
        generation=1,
        kind=commands[0].kind,
        payload=commands[0].payload,
    )
    await repo.enqueue_commands([row, row])
    await repo.commit()
    count = await db_session.scalar(select(func.count()).select_from(CodeRiskCommand))
    assert count == 1
    old_token, new_token = uuid4(), uuid4()
    claimed = await repo.claim_command(session.id, old_token)
    assert claimed is not None and claimed.attempts == 1
    await repo.commit()
    assert await CodeRiskRepository(db_session).claim_command(session.id, new_token) is None
    await repo.commit()
    persisted = await db_session.get(CodeRiskCommand, claimed.key)
    assert persisted is not None
    persisted.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    reclaimed = await repo.claim_command(session.id, new_token)
    assert reclaimed is not None and reclaimed.attempts == 2
    await repo.commit()
    assert not await repo.finish_command(claimed.key, old_token, status="applied")
    assert await repo.finish_command(
        claimed.key, new_token, status="applied", result={"accepted": True}
    )
    await repo.commit()
    assert await repo.claim_command(session.id, uuid4()) is None
    await repo.commit()


@pytest.mark.asyncio
async def test_legacy_orphan_dispatcher_cannot_claim_code_policy_orders(prepared, db_session):
    from datetime import timedelta

    _repo, session, entry = prepared
    legacy = Order(
        strategy_id=session.strategy_id,
        exchange_account_id=session.exchange_account_id,
        symbol=session.symbol,
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(1),
        state=OrderState.pending,
    )
    db_session.add(legacy)
    await db_session.flush()
    listed = await OrderRepository(db_session).list_stuck_pending(
        datetime.now(UTC) + timedelta(seconds=1)
    )
    assert legacy.id in {order.id for order in listed}
    assert entry.id not in {order.id for order in listed}


@pytest.mark.asyncio
@pytest.mark.parametrize("tp_filled", [True, False])
async def test_durable_venue_entry_tp_trailing_close_and_reversal_use_one_session(
    prepared, db_session, tp_filled
):
    from src.strategy.code_contract import CodeSnapshot
    from src.strategy.models import StrategyVersion
    from src.trading.code_execution_snapshot import build_code_snapshot
    from src.trading.providers import Credentials, OrderReceipt, OrderStatusFetch, PositionInfo
    from src.trading.services.code_risk_executor import CodeRiskExecutor
    from src.trading.services.code_risk_venue import BybitCodeRiskVenue

    repo, session, entry = prepared
    account = await repo.get_account(session.exchange_account_id)
    assert account is not None
    account.read_only = False
    entry.leverage = 1
    entry.margin_mode = "cross"
    code = CodeSnapshot(
        execution_policy="code_v1",
        language="python",
        source_code="def on_bar(ctx,state): return {'action':'long'}",
        warmup_bars=2,
        provenance={},
    )
    version = StrategyVersion(
        strategy_id=session.strategy_id,
        source_hash=code.source_hash,
        execution_hash=code.execution_hash,
        **code.model_dump(exclude={"schema_version"}),
    )
    db_session.add(version)
    await db_session.flush()
    session.strategy_version_id = version.id
    session.execution_snapshot = build_code_snapshot(
        version=version,
        account=account,
        settings={
            "schema_version": 1,
            "leverage": 1,
            "margin_mode": "cross",
            "position_size_pct": 100,
        },
    )
    await repo.commit()
    accounts = AsyncMock()
    accounts.get_credentials_for_order.return_value = Credentials("fake", "fake")
    provider = AsyncMock()
    statuses = {}
    position = {"size": D(0)}
    submissions = []

    async def by_client(_creds, identifier, _symbol):
        return statuses.get(identifier)

    async def fetch(_creds, identifier, _symbol):
        return statuses[identifier]

    async def submit(_creds, request):
        submissions.append(request)
        identifier = request.client_order_id
        if request.type == OrderType.limit:
            receipt = OrderReceipt(
                exchange_order_id=identifier,
                status="submitted",
                filled_price=None,
                filled_quantity=D(0),
                raw={},
            )
        else:
            position["size"] += -request.quantity if request.reduce_only else request.quantity
            receipt = OrderReceipt(
                exchange_order_id=identifier,
                status="filled",
                filled_price=D(100),
                filled_quantity=request.quantity,
                raw={},
            )
        statuses[identifier] = OrderStatusFetch(
            exchange_order_id=identifier,
            status=receipt.status,
            filled_price=receipt.filled_price,
            filled_quantity=receipt.filled_quantity,
            raw=receipt.raw,
        )
        return receipt

    async def cancel(_creds, identifier, _symbol):
        old = statuses[identifier]
        statuses[identifier] = OrderStatusFetch(
            exchange_order_id=identifier,
            status="cancelled",
            filled_quantity=old.filled_quantity,
            filled_price=old.filled_price,
        )

    provider.fetch_order_by_client_id.side_effect = by_client
    provider.fetch_order.side_effect = fetch
    provider.create_order.side_effect = submit
    provider.cancel_order.side_effect = cancel
    provider.fetch_position.side_effect = lambda *_: (
        PositionInfo(size=position["size"], side="long") if position["size"] > 0 else None
    )
    provider.fetch_open_conditional_orders.return_value = []
    risk = CodeRiskService(repo)
    venue = BybitCodeRiskVenue(repo, OrderRepository(db_session), risk, accounts, provider)
    executor = CodeRiskExecutor(repo, risk, venue)
    await executor.drain(session.id)
    state = await repo.get(session.id)
    assert state is not None and state.fixed_r == D("2.2") and state.position_quantity == D(2)
    assert state.protection_desired == state.protection_applied
    assert len(submissions) == 2 and submissions[0].stop_loss == D("97.8")
    tp = submissions[1]
    assert tp.reduce_only and tp.quantity == D(1) and tp.price == D("103.3")
    if tp_filled:
        # 실제 절반 TP를 흉내낸 REST 누적 체결을 새 실행기가 복구한다.
        position["size"] = D(1)
        statuses[tp.client_order_id] = OrderStatusFetch(
            exchange_order_id=tp.client_order_id,
            status="filled",
            filled_price=D("103.3"),
            filled_quantity=D(1),
        )
    restarted = CodeRiskExecutor(repo, CodeRiskService(repo), venue)
    await restarted.drain(session.id)
    state = await repo.get(session.id)
    assert state is not None and state.tp_filled_quantity == D(1 if tp_filled else 0)
    assert state.position_quantity == D(1 if tp_filled else 2)
    await risk.mark_price(session.id, 1, D(106))
    await restarted.drain(session.id)
    state = await repo.get(session.id)
    assert (
        state is not None
        and state.trailing_active
        and D(str(state.protection_applied["stop_loss"])) == D("101.6")
    )
    await risk.request_signal(session.id, 1, "short")
    ready = await restarted.drain(session.id)
    state = await repo.get(session.id)
    assert state is not None and state.position_quantity == 0 and state.cancels_confirmed
    assert state.pending_reversal == "short" and not state.new_entries_blocked
    assert [command.kind for command in ready] == ["ready_reversal"]
    count = len(submissions)
    await restarted.drain(session.id)
    assert len(submissions) == count


@pytest.mark.asyncio
async def test_sql_rollback_error_path_uses_detached_generation_and_halts(prepared):
    from src.trading.services.code_risk_executor import CodeRiskExecutor

    repo, session, _entry = prepared
    session_id = session.id
    venue = AsyncMock()
    await CodeRiskExecutor(repo, CodeRiskService(repo), venue).drain(session_id)
    state = await repo.get(session_id)
    assert state is not None and state.new_entries_blocked and state.close_requested
    assert state.failure_reason == "command_failed:CodeSnapshotError"
    venue.execute.assert_not_awaited()
