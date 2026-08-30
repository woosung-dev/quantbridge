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

from src.common.metrics import qb_metrics_mutation_failed_total
from src.trading.models import (
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.schemas import OrderRequest
from src.trading.services.account_service import ExecutionAccount
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

    # exchange_service mock — public capability 반환
    exchange_service = MagicMock()
    account = ExecutionAccount(
        id=account_id,
        user_id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
    )
    exchange_service.get_execution_account = AsyncMock(return_value=account)

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
    exchange_service.get_execution_account.assert_awaited_once_with(account_id)
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
    account = ExecutionAccount(
        id=account_id,
        user_id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
    )
    exchange_service.get_execution_account = AsyncMock(return_value=account)
    # notional check 우회 — fetch_balance_usdt None
    exchange_service.fetch_balance_usdt = AsyncMock(return_value=None)
    # Wave 1 C5 — min-notional 가드 기본 skip(None=fail-open).
    exchange_service.fetch_min_notional = AsyncMock(return_value=None)

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


@pytest.mark.asyncio
async def test_execute_dispatches_and_counts_metric_mutation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V1/V2: commit 뒤 관측 실패는 발주를 막지 않고 운영 metric으로 남긴다."""
    from src.trading.services import order_service as order_service_module

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
    dispatcher = AsyncMock()
    svc = OrderService(session=session, repo=repo, dispatcher=dispatcher, kill_switch=AsyncMock())
    req = OrderRequest(
        strategy_id=saved_order.strategy_id,
        exchange_account_id=saved_order.exchange_account_id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    before = qb_metrics_mutation_failed_total._value.get()
    monkeypatch.setattr(
        order_service_module.qb_active_orders,
        "inc",
        lambda: (_ for _ in ()).throw(OSError("metrics mmap is read-only")),
    )

    await svc.execute(req, idempotency_key=None)

    dispatcher.dispatch_order_execution.assert_awaited_once_with(saved_order.id)
    assert qb_metrics_mutation_failed_total._value.get() == before + 1
