"""새 정책 WS 체결은 누적 원장에 반영하고 legacy·commit 경계를 보존한다."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading.models import Order, OrderSide, OrderState, OrderType
from src.trading.services.code_risk_service import CodeRiskError, CodeRiskService, RiskCommand
from src.trading.services.websocket_order_event_service import WebSocketOrderEventService


def setup_handler(*, role="entry", legacy=False):
    session_id = uuid4()
    order = Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        state=OrderState.submitted,
        quantity=Decimal("2"),
        risk_context=None
        if legacy
        else {"session_id": str(session_id), "generation": 3, "role": role},
    )
    repo = AsyncMock()
    repo.get_by_id.return_value = order
    repo.transition_to_filled.return_value = 1
    repo.transition_to_cancelled.return_value = 1
    risk = AsyncMock(spec=CodeRiskService)
    commands = [RiskCommand("apply_protection", "risk:token", {"quantity": "1"})]
    risk.record_entry_fill.return_value = commands
    risk.record_exit_fill.return_value = commands
    handler = WebSocketOrderEventService(repo=repo, settings=MagicMock(), risk_service=risk)
    handler._after_committed_winner = AsyncMock()
    payload = {
        "orderLinkId": str(order.id),
        "orderId": "exchange",
        "orderStatus": "PartiallyFilled",
        "cumExecQty": "1",
        "cumExecValue": "100",
        "avgPrice": "100",
    }
    return handler, repo, risk, order, session_id, payload, commands


@pytest.mark.asyncio
async def test_partial_entry_updates_risk_without_terminal_state_or_legacy_effects():
    handler, repo, risk, order, session_id, payload, commands = setup_handler()
    assert await handler.handle_order_event(order.exchange_account_id, payload) == commands
    risk.record_entry_fill.assert_awaited_once_with(
        session_id,
        3,
        order.id,
        cumulative_quantity=Decimal("1"),
        cumulative_value=Decimal("100"),
        terminal=False,
        commit=False,
    )
    repo.commit.assert_awaited_once()
    repo.transition_to_filled.assert_not_awaited()
    handler._after_committed_winner.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_partial_order_still_has_no_state_transition_or_risk_callback():
    handler, repo, risk, order, _, payload, _ = setup_handler(legacy=True)
    assert await handler.handle_order_event(order.exchange_account_id, payload) is None
    repo.commit.assert_not_awaited()
    risk.record_entry_fill.assert_not_awaited()


@pytest.mark.asyncio
async def test_terminal_partial_cancel_finalizes_risk_in_same_commit():
    handler, repo, risk, order, session_id, payload, commands = setup_handler()
    payload["orderStatus"] = "PartiallyFilledCanceled"
    assert await handler.handle_order_event(order.exchange_account_id, payload) == commands
    risk.record_entry_fill.assert_awaited_once_with(
        session_id,
        3,
        order.id,
        cumulative_quantity=Decimal("1"),
        cumulative_value=Decimal("100"),
        terminal=True,
        commit=False,
    )
    repo.transition_to_cancelled.assert_awaited_once()
    repo.commit.assert_awaited_once()
    handler._after_committed_winner.assert_awaited_once()


@pytest.mark.asyncio
async def test_exit_partial_fill_uses_original_order_role_and_cumulative_quantity():
    handler, repo, risk, order, session_id, payload, commands = setup_handler(role="partial_tp")
    assert await handler.handle_order_event(order.exchange_account_id, payload) == commands
    risk.record_exit_fill.assert_awaited_once_with(
        session_id, 3, order.id, role="partial_tp", cumulative_quantity=Decimal("1"), commit=False
    )
    risk.record_entry_fill.assert_not_awaited()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_commit_never_returns_commands_or_runs_winner_effects():
    handler, repo, _risk, order, _, payload, _ = setup_handler()
    payload["orderStatus"] = "Filled"
    repo.commit.side_effect = RuntimeError("commit failed")
    with pytest.raises(RuntimeError, match="commit failed"):
        await handler.handle_order_event(order.exchange_account_id, payload)
    handler._after_committed_winner.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad", [{"cumExecQty": "NaN"}, {"cumExecValue": "Infinity"}, {"cumExecQty": "-1"}]
)
async def test_malformed_risk_fill_never_enters_either_ledger(bad):
    handler, repo, risk, order, _, payload, _ = setup_handler()
    payload.update(bad)
    with pytest.raises(CodeRiskError):
        await handler.handle_order_event(order.exchange_account_id, payload)
    repo.commit.assert_not_awaited()
    risk.record_entry_fill.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrong_account_cannot_mutate_bound_risk_ledger():
    handler, repo, risk, _order, _, payload, _ = setup_handler()
    with pytest.raises(CodeRiskError, match="계정"):
        await handler.handle_order_event(uuid4(), payload)
    repo.commit.assert_not_awaited()
    risk.record_entry_fill.assert_not_awaited()
