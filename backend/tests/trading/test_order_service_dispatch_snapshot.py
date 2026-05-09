"""Sprint 23 BL-102 — OrderService.execute snapshot fill spy.

codex G.0 P1 #3 verifier: exchange_service 가 주입된 경우 account fetch 후
(exchange, mode, has_leverage) snapshot 을 Order.dispatch_snapshot 에 저장.
exchange_service=None 이면 snapshot=None 으로 graceful (legacy fallback).

LESSON-019 commit-spy 의무 — snapshot 도 같은 outer commit 안 (별도 transaction X).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.schemas import OrderRequest
from src.trading.services.order_service import OrderService


@pytest.mark.asyncio
async def test_execute_fills_dispatch_snapshot_when_exchange_service_injected() -> None:
    """exchange_service 주입 시 account.exchange/mode + req.leverage → snapshot 채움."""
    session = AsyncMock(spec=AsyncSession)
    session.begin_nested = MagicMock(return_value=AsyncMock())

    account_id = uuid4()
    saved_order = Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
    )

    repo = AsyncMock()
    repo.save = AsyncMock(return_value=saved_order)
    repo.get_by_id = AsyncMock(return_value=saved_order)

    # exchange_service mock — _repo.get_by_id 가 ExchangeAccount 반환
    exchange_service = MagicMock()
    account = ExchangeAccount(
        id=account_id,
        user_id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"x",
    )
    exchange_service._repo = MagicMock()
    exchange_service._repo.get_by_id = AsyncMock(return_value=account)

    kill_switch = AsyncMock()
    kill_switch.ensure_not_gated = AsyncMock()
    dispatcher = AsyncMock()

    svc = OrderService(
        session=session,
        repo=repo,
        dispatcher=dispatcher,
        kill_switch=kill_switch,
        sessions_port=None,
        exchange_service=exchange_service,
    )

    req = OrderRequest(
        strategy_id=saved_order.strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )

    await svc.execute(req, idempotency_key=None, body_hash=None)

    # 핵심: account fetch 호출 + repo.save 가 dispatch_snapshot 채워진 Order 받음
    exchange_service._repo.get_by_id.assert_awaited_once_with(account_id)
    save_call = repo.save.call_args
    saved_arg: Order = save_call.args[0]
    assert saved_arg.dispatch_snapshot == {
        "exchange": "bybit",
        "mode": "demo",
        "has_leverage": False,
    }
    # LESSON-019: 같은 transaction 안 outer commit
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_fills_snapshot_with_futures_leverage() -> None:
    """req.leverage > 0 → has_leverage=True 로 snapshot 채움."""
    session = AsyncMock(spec=AsyncSession)
    session.begin_nested = MagicMock(return_value=AsyncMock())

    account_id = uuid4()
    saved_order = Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=Decimal("50000"),
        state=OrderState.pending,
        leverage=5,
        margin_mode="cross",
    )

    repo = AsyncMock()
    repo.save = AsyncMock(return_value=saved_order)
    repo.get_by_id = AsyncMock(return_value=saved_order)

    exchange_service = MagicMock()
    account = ExchangeAccount(
        id=account_id,
        user_id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"x",
    )
    exchange_service._repo = MagicMock()
    exchange_service._repo.get_by_id = AsyncMock(return_value=account)
    # notional check 우회 — fetch_balance_usdt None
    exchange_service.fetch_balance_usdt = AsyncMock(return_value=None)

    kill_switch = AsyncMock()
    dispatcher = AsyncMock()

    svc = OrderService(
        session=session,
        repo=repo,
        dispatcher=dispatcher,
        kill_switch=kill_switch,
        sessions_port=None,
        exchange_service=exchange_service,
    )

    req = OrderRequest(
        strategy_id=saved_order.strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=Decimal("50000"),
        leverage=5,
        margin_mode="cross",
    )

    await svc.execute(req, idempotency_key=None, body_hash=None)

    save_call = repo.save.call_args
    saved_arg: Order = save_call.args[0]
    assert saved_arg.dispatch_snapshot == {
        "exchange": "bybit",
        "mode": "demo",
        "has_leverage": True,
    }


@pytest.mark.asyncio
async def test_execute_snapshot_none_when_exchange_service_missing() -> None:
    """exchange_service=None (test 환경) → snapshot=None 으로 graceful (legacy fallback)."""
    session = AsyncMock(spec=AsyncSession)
    session.begin_nested = MagicMock(return_value=AsyncMock())

    saved_order = Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
    )

    repo = AsyncMock()
    repo.save = AsyncMock(return_value=saved_order)
    repo.get_by_id = AsyncMock(return_value=saved_order)

    kill_switch = AsyncMock()
    dispatcher = AsyncMock()

    svc = OrderService(
        session=session,
        repo=repo,
        dispatcher=dispatcher,
        kill_switch=kill_switch,
        sessions_port=None,
        exchange_service=None,  # 핵심
    )

    req = OrderRequest(
        strategy_id=saved_order.strategy_id,
        exchange_account_id=saved_order.exchange_account_id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )

    await svc.execute(req, idempotency_key=None, body_hash=None)

    save_call = repo.save.call_args
    saved_arg: Order = save_call.args[0]
    assert saved_arg.dispatch_snapshot is None  # legacy fallback path 보장
