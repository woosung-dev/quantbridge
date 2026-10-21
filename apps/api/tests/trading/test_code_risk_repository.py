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
