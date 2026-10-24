"""전송을 교차해도 누적 원장은 한 번만 반영되고 commit 뒤에만 명령을 반환한다."""

from datetime import UTC, datetime
from decimal import Decimal as D
from unittest.mock import AsyncMock

import pytest

from src.trading.models import Order, OrderSide, OrderState, OrderType
from src.trading.providers import OrderStatusFetch
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.code_order_observation_service import (
    CodeOrderObservation,
    CodeOrderObservationService,
)
from src.trading.services.code_risk_service import CodeRiskService, RiskCommand
from tests.trading import test_code_risk_repository as risk_tests

prepared = risk_tests.prepared


def observation(source, order, quantity, *, state="filled"):
    if source == "rest":
        return CodeOrderObservation.from_rest(
            order.exchange_account_id,
            OrderStatusFetch(
                exchange_order_id="observed-order",
                status=state,
                filled_quantity=quantity,
                filled_price=D(100) if quantity else None,
                cumulative_value=quantity * 100,
            ),
        )
    return CodeOrderObservation.from_websocket(
        order.exchange_account_id,
        {
            "orderId": "observed-order",
            "orderStatus": {
                "filled": "Filled",
                "submitted": "PartiallyFilled",
                "rejected": "Rejected",
            }[state],
            "cumExecQty": str(quantity),
            "cumExecValue": str(quantity * 100),
            "avgPrice": "100" if quantity else "",
        },
    )


@pytest.mark.parametrize("first,second", [("rest", "ws"), ("ws", "rest")])
async def test_cross_transport_duplicates_and_stale_fills_never_double_credit(
    prepared, db_session, first, second
):
    repo, session, entry = prepared
    orders = OrderRepository(db_session)
    await orders.transition_to_submitted(entry.id, submitted_at=datetime.now(UTC))
    await orders.commit()
    await db_session.refresh(entry)
    observer = CodeOrderObservationService(orders, CodeRiskService(repo), risk_repo=repo)

    partial = observation(first, entry, D(1), state="submitted")
    await observer.apply(entry, partial)
    revision = (await repo.get(session.id)).revision
    await observer.apply(entry, partial)
    assert (await repo.get(session.id)).revision == revision

    terminal = observation(second, entry, D(2))
    result = await observer.apply(entry, terminal)
    assert result.transition_won
    revision = (await repo.get(session.id)).revision
    assert not (await observer.apply(entry, terminal)).transition_won
    await observer.apply(entry, partial)
    state = await repo.get(session.id)
    assert state.revision == revision
    assert state.cumulative_quantity == state.position_quantity == D(2)
    assert state.cumulative_value == D(200) and state.entry_terminal
    await db_session.refresh(entry)
    assert entry.state == OrderState.filled and entry.filled_quantity == D(2)


@pytest.mark.parametrize("source", ["rest", "ws"])
async def test_one_commit_owns_risk_and_order_mutations(source):
    from uuid import uuid4

    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(2),
        risk_context={"session_id": str(uuid4()), "generation": 1, "role": "entry"},
    )
    orders, risk = AsyncMock(), AsyncMock(spec=CodeRiskService)
    orders.transition_to_filled.return_value = 1
    commands = [RiskCommand("apply_protection", "confirmed", {})]
    risk.record_entry_fill.return_value = commands
    observer = CodeOrderObservationService(orders, risk)
    result = await observer.apply(order, observation(source, order, D(2)))
    orders.commit.assert_awaited_once()
    assert risk.record_entry_fill.await_args.kwargs["commit"] is False
    assert result.commands == commands and result.transition_won

    orders.commit.side_effect = RuntimeError("commit failed")
    with pytest.raises(RuntimeError, match="commit failed"):
        await observer.apply(order, observation(source, order, D(2)))


async def test_ws_zero_close_is_completed_by_rest_before_next_flatten_key(prepared, db_session):
    repo, session, entry = prepared
    risk = CodeRiskService(repo)
    orders = OrderRepository(db_session)
    await risk.record_entry_fill(
        session.id,
        1,
        entry.id,
        cumulative_quantity=D(2),
        cumulative_value=D(200),
        terminal=True,
    )
    before = next(
        command
        for command in await risk.request_signal(session.id, 1, "close")
        if command.kind == "flatten"
    )
    close = Order(
        strategy_id=entry.strategy_id,
        exchange_account_id=entry.exchange_account_id,
        symbol=entry.symbol,
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=D(2),
        reduce_only=True,
        state=OrderState.submitted,
        risk_context={"session_id": str(session.id), "generation": 1, "role": "close"},
    )
    await orders.save(close)
    await orders.commit()
    observer = CodeOrderObservationService(orders, risk, risk_repo=repo)
    await observer.apply(close, observation("ws", close, D(0), state="rejected"))
    after_ws = next(
        command for command in await risk.recover(session.id) if command.kind == "flatten"
    )
    assert after_ws.key == before.key

    await observer.apply(close, observation("rest", close, D(0), state="rejected"))
    after_rest = next(
        command for command in await risk.recover(session.id) if command.kind == "flatten"
    )
    assert after_rest.key != before.key
    state = await repo.get(session.id)
    assert state.position_quantity == D(2) and state.exit_fills[str(close.id)] == "0"
