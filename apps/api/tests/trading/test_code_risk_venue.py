"""code_v1 공급자는 가짜 HTTP 응답으로만 검증한다. 실주문은 하지 않는다."""

from decimal import Decimal as D
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, ExchangeName, Order, OrderSide, OrderState, OrderType
from src.trading.providers import (
    BybitFuturesProvider,
    Credentials,
    OrderStatusFetch,
    PositionSnapshot,
)
from src.trading.services.code_risk_venue import BybitCodeRiskVenue


@pytest.mark.asyncio
async def test_native_protection_sends_activation_and_requires_independent_confirmation(
    monkeypatch,
):
    exchange = MagicMock()
    exchange.privatePostV5PositionTradingStop = AsyncMock(return_value={"retCode": 0, "result": {}})
    exchange.close = AsyncMock()
    monkeypatch.setattr("src.trading.providers.ccxt_async.bybit", lambda _: exchange)
    provider = BybitFuturesProvider()
    position = PositionSnapshot(
        side="long",
        size=D(2),
        entry_price=D(100),
        mark_price=D(101),
        unrealized_pnl=None,
        liquidation_price=None,
        leverage=D(1),
        take_profit_price=None,
        stop_loss_price=D("97.8"),
        position_idx=0,
        trailing_stop=D("4.4"),
    )
    provider.fetch_open_positions = AsyncMock(return_value=[position])
    creds = Credentials("fake-key", "fake-secret", ExchangeName.bybit, ExchangeMode.demo)
    await provider.set_code_protection(
        creds, symbol="BTC/USDT", stop_loss=D("97.8"), distance=D("4.4"), active_price=D("104.4")
    )
    request = exchange.privatePostV5PositionTradingStop.await_args.args[0]
    assert request == {
        "category": "linear",
        "symbol": "BTCUSDT",
        "positionIdx": 0,
        "tpslMode": "Full",
        "stopLoss": "97.8",
        "slTriggerBy": "LastPrice",
        "trailingStop": "4.4",
        "activePrice": "104.4",
    }
    exchange.close.assert_awaited_once()
    provider.fetch_open_positions.return_value = []
    with pytest.raises(ProviderError, match="independently confirmed"):
        await provider.set_code_protection(
            creds, symbol="BTC/USDT", stop_loss=D("97.8"), distance=None, active_price=None
        )


@pytest.mark.asyncio
async def test_lost_submit_response_is_recovered_by_same_uuid_without_duplicate_create():
    repo, orders, risk, accounts, provider = (AsyncMock() for _ in range(5))
    order = Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(2),
        state=OrderState.submitted,
        leverage=1,
        margin_mode="cross",
        risk_context={"session_id": str(uuid4()), "generation": 1, "role": "entry"},
    )
    provider.fetch_order_by_client_id.return_value = OrderStatusFetch(
        exchange_order_id="venue1",
        status="filled",
        filled_price=D(100),
        filled_quantity=D(2),
        raw={"info": {"cumExecValue": "200"}},
    )
    venue = BybitCodeRiskVenue(repo, orders, risk, accounts, provider)
    result = await venue._submit(Credentials("fake", "fake"), order)
    assert result["exchange_order_id"] == "venue1"
    provider.create_order.assert_not_awaited()
    provider.fetch_order_by_client_id.assert_awaited_once_with(
        Credentials("fake", "fake"), str(order.id), order.symbol
    )
    risk.record_entry_fill.assert_awaited_once_with(
        __import__("uuid").UUID(str(order.risk_context["session_id"])),
        1,
        order.id,
        cumulative_quantity=D(2),
        cumulative_value=D(200),
        terminal=True,
        commit=False,
    )
    repo.commit.assert_awaited()


@pytest.mark.asyncio
async def test_cancel_ack_is_not_terminal_evidence():
    repo, orders, risk, accounts, provider = (AsyncMock() for _ in range(5))
    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=D(2),
        state=OrderState.submitted,
        exchange_order_id="venue1",
    )
    provider.fetch_order_by_client_id.return_value = OrderStatusFetch(
        exchange_order_id="venue1", status="submitted"
    )
    provider.fetch_order.return_value = OrderStatusFetch(
        exchange_order_id="venue1", status="submitted"
    )
    venue = BybitCodeRiskVenue(repo, orders, risk, accounts, provider)
    with pytest.raises(ValueError, match="취소 확정"):
        await venue._cancel_confirm(Credentials("fake", "fake"), order)
    orders.transition_to_cancelled.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_partial_tp_halts_instead_of_acknowledging_protection():
    repo, orders, risk, accounts, provider = (AsyncMock() for _ in range(5))
    session_id = uuid4()
    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.limit,
        quantity=D(1),
        price=D(103),
        state=OrderState.submitted,
        risk_context={"session_id": str(session_id), "generation": 1, "role": "partial_tp"},
    )
    provider.fetch_order_by_client_id.return_value = OrderStatusFetch(
        exchange_order_id="tp1", status="cancelled", filled_quantity=D(0)
    )
    repo.get.return_value = SimpleNamespace(position_quantity=D(1), close_requested=False)
    venue = BybitCodeRiskVenue(repo, orders, risk, accounts, provider)
    with pytest.raises(ValueError):
        await venue._submit(Credentials("fake", "fake"), order)
    risk.halt.assert_awaited_once_with(session_id, 1, "partial_tp_protection_lost", commit=False)
    provider.create_order.assert_not_awaited()
