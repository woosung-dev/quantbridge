"""Sprint 12 Phase C — Reconciler TDD.

4 시나리오 (M2 Slim):
1. terminal status (Filled/Cancelled/Rejected) → state transition
2. open 에 없음 + recent 에 없음 → state 유지 + alert + qb_ws_reconcile_unknown_total
3. exchange status 가 Cancelled 명시 → cancelled 로 transition
4. local active 가 0 이면 fetch 호출 없음 (early return)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.config import Settings
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.websocket.reconciliation import Reconciler


@pytest.fixture
def session_factory(db_session):
    @asynccontextmanager
    async def factory():
        yield db_session

    return factory


@pytest.fixture
async def submitted_order(db_session, strategy, user):
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=acc.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.submitted,
    )
    db_session.add(order)
    await db_session.flush()
    return order, acc


def _make_fetcher(open_orders=None, recent_orders=None):
    fetcher = AsyncMock()
    fetcher.fetch_open_orders = AsyncMock(return_value=open_orders or [])
    fetcher.fetch_recent_orders = AsyncMock(return_value=recent_orders or [])
    return fetcher


async def test_terminal_status_transitions_to_filled(
    submitted_order, session_factory, db_session, monkeypatch
):
    order, acc = submitted_order
    fetcher = _make_fetcher(
        recent_orders=[
            {
                "clientOrderId": str(order.id),
                "status": "Filled",
                "average": "50000.00",
                "id": "EX-100",
            }
        ]
    )
    # alert silent skip
    monkeypatch.setattr(
        "src.trading.websocket.reconciliation.send_critical_alert",
        AsyncMock(return_value=False),
    )
    reconciler = Reconciler(
        session_factory=session_factory, fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.filled
    assert refreshed.filled_price == Decimal("50000.00")


async def test_unknown_order_state_unchanged_with_alert(
    submitted_order, session_factory, db_session, monkeypatch
):
    """codex G3 #10 — exchange 에 없음 → state 유지 + alert."""
    order, acc = submitted_order
    fetcher = _make_fetcher()  # 빈 list
    mock_alert = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.trading.websocket.reconciliation.send_critical_alert", mock_alert
    )
    reconciler = Reconciler(
        session_factory=session_factory, fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    # state 유지!
    assert refreshed.state == OrderState.submitted
    # alert 호출됨
    mock_alert.assert_called_once()
    args = mock_alert.call_args
    title = args[0][1] if len(args[0]) > 1 else args.kwargs["title"]
    assert "Reconcile Unknown" in title


async def test_cancelled_status_transitions(
    submitted_order, session_factory, db_session, monkeypatch
):
    order, acc = submitted_order
    fetcher = _make_fetcher(
        open_orders=[
            {"clientOrderId": str(order.id), "status": "Cancelled", "id": "EX-1"}
        ]
    )
    monkeypatch.setattr(
        "src.trading.websocket.reconciliation.send_critical_alert",
        AsyncMock(return_value=False),
    )
    reconciler = Reconciler(
        session_factory=session_factory, fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.cancelled


async def test_no_local_active_orders_skips_fetch(session_factory):
    """local active 가 없으면 fetch 호출 없음 (early return)."""
    fetcher = _make_fetcher()
    reconciler = Reconciler(
        session_factory=session_factory, fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=uuid4())
    fetcher.fetch_open_orders.assert_not_called()
    fetcher.fetch_recent_orders.assert_not_called()


async def test_ccxt_unified_status_closed_transitions_to_filled(
    submitted_order, session_factory, db_session, monkeypatch
):
    """G4 revisit #11 — CCXT unified status 'closed' 도 filled 로 매핑."""
    order, acc = submitted_order
    fetcher = _make_fetcher(
        recent_orders=[
            {
                "clientOrderId": str(order.id),
                "status": "closed",  # CCXT unified
                "average": "50100.00",
                "id": "EX-200",
            }
        ]
    )
    monkeypatch.setattr(
        "src.trading.websocket.reconciliation.send_critical_alert",
        AsyncMock(return_value=False),
    )
    reconciler = Reconciler(
        session_factory=session_factory, fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.filled
    assert refreshed.filled_price == Decimal("50100.00")


async def test_ccxt_unified_canceled_transitions(
    submitted_order, session_factory, db_session, monkeypatch
):
    """CCXT 'canceled' (single-l) → cancelled."""
    order, acc = submitted_order
    fetcher = _make_fetcher(
        open_orders=[
            {"clientOrderId": str(order.id), "status": "canceled", "id": "EX-201"}
        ]
    )
    monkeypatch.setattr(
        "src.trading.websocket.reconciliation.send_critical_alert",
        AsyncMock(return_value=False),
    )
    reconciler = Reconciler(
        session_factory=session_factory, fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.cancelled
