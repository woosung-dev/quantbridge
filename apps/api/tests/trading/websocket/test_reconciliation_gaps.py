# Reconciler 의 미커버 머니패스 분기(_find_match 키 fallback / Rejected 전이 / 비종료 skip / alert 예외) 보강
"""Reconciler 잔여 분기 TDD (BL-308, W3 — G1 codex P1-5 발견).

기존 test_reconciliation.py 는 clientOrderId 매칭 + Filled/Cancelled 전이 + unknown
alert + ccxt status 매핑을 덮는다. baseline term-missing(90%) + G1 codex 가 가리킨
잔여 머니패스 분기:
- _find_match 의 orderLinkId / clOrdId 키 fallback (reconciliation.py:150-162) —
  clientOrderId 만 테스트됨. 키가 drift 하면 fill/cancel 이 'unknown' 으로 오분류.
- Rejected 종료 전이 (reconciliation.py:219-221) — 헤더는 주장하나 실제 미커버.
- 비종료 status(New) → 전이 없음 (reconciliation.py:107 분기 False path).
- _handle_unknown 의 alert 예외 swallow (reconciliation.py:188-189).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

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
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.websocket_reconciliation_service import WebSocketReconciliationService


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


def _silence_alert(monkeypatch):
    monkeypatch.setattr(
        "src.trading.services.websocket_reconciliation_service.send_critical_alert",
        AsyncMock(return_value=False),
    )


async def test_find_match_via_orderLinkId_key_transitions(submitted_order, db_session, monkeypatch):
    """exch order 가 clientOrderId 대신 orderLinkId 키 사용 → 매칭 + Filled 전이.

    _find_match fallback chain (clientOrderId → orderLinkId → clOrdId) 의 2번째 키.
    """
    order, acc = submitted_order
    _silence_alert(monkeypatch)
    fetcher = _make_fetcher(
        recent_orders=[
            {"orderLinkId": str(order.id), "status": "Filled", "average": "50000.00", "id": "EX-OL"}
        ]
    )
    reconciler = WebSocketReconciliationService(
        repo=OrderRepository(db_session), fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.filled


async def test_find_match_via_clOrdId_key_transitions(submitted_order, db_session, monkeypatch):
    """exch order 가 clOrdId 키(OKX 스타일) 사용 → 매칭 + Cancelled 전이.

    _find_match fallback chain 의 3번째 키. drift 시 cancel 이 unknown 오분류.
    """
    order, acc = submitted_order
    _silence_alert(monkeypatch)
    fetcher = _make_fetcher(
        open_orders=[{"clOrdId": str(order.id), "status": "Cancelled", "id": "EX-CO"}]
    )
    reconciler = WebSocketReconciliationService(
        repo=OrderRepository(db_session), fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.cancelled


async def test_rejected_terminal_transition(submitted_order, db_session, monkeypatch):
    """exch status Rejected → rejected 전이 + rejectReason 추출 (reconciliation.py:219-221)."""
    order, acc = submitted_order
    _silence_alert(monkeypatch)
    fetcher = _make_fetcher(
        recent_orders=[
            {
                "clientOrderId": str(order.id),
                "status": "Rejected",
                "id": "EX-REJ",
                "info": {"rejectReason": "InsufficientBalance"},
            }
        ]
    )
    reconciler = WebSocketReconciliationService(
        repo=OrderRepository(db_session), fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.rejected
    assert refreshed.error_message is not None
    assert "InsufficientBalance" in refreshed.error_message


async def test_non_terminal_status_no_transition(submitted_order, db_session, monkeypatch):
    """매칭됐지만 status 가 비종료(New) → 전이 없음, state 유지 (reconciliation.py:107 False)."""
    order, acc = submitted_order
    _silence_alert(monkeypatch)
    fetcher = _make_fetcher(
        open_orders=[{"clientOrderId": str(order.id), "status": "New", "id": "EX-NEW"}]
    )
    reconciler = WebSocketReconciliationService(
        repo=OrderRepository(db_session), fetcher=fetcher, settings=Settings()
    )
    await reconciler.run(account_id=acc.id)

    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.submitted  # 변화 없음


async def test_handle_unknown_alert_exception_swallowed(submitted_order, db_session, monkeypatch):
    """unknown order 의 alert 발송이 예외 던져도 swallow + 다음 order 계속 (reconciliation.py:188-189).

    G2 false-green 방어: state 유지만 보면 _handle_unknown/alert 호출을 지워도 통과한다.
    → (a) alert 가 실제 await 됐고 (b) 예외가 swallow 돼 *두 번째* unknown order 까지
    루프가 계속됐음(await_count==2)을 단언. Slack 다운 시 reconcile graceful 보장.
    """
    order1, acc = submitted_order
    # 같은 account 에 2번째 submitted order — 첫 alert 예외 후 loop 계속을 증명
    order2 = Order(
        strategy_id=order1.strategy_id,
        exchange_account_id=acc.id,
        symbol="ETH/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        price=None,
        state=OrderState.submitted,
    )
    db_session.add(order2)
    await db_session.flush()

    mock_alert = AsyncMock(side_effect=RuntimeError("slack down"))
    monkeypatch.setattr(
        "src.trading.services.websocket_reconciliation_service.send_critical_alert", mock_alert
    )
    fetcher = _make_fetcher()  # 빈 snapshot → 두 order 모두 unknown
    reconciler = WebSocketReconciliationService(
        repo=OrderRepository(db_session), fetcher=fetcher, settings=Settings()
    )
    # 예외 전파 없이 완료해야 함
    await reconciler.run(account_id=acc.id)

    # 두 unknown order 각각 _handle_unknown → alert raise → swallow → loop 계속
    assert mock_alert.await_count == 2
    from sqlalchemy import select

    for oid in (order1.id, order2.id):
        stmt = select(Order).where(Order.id == oid)  # type: ignore[arg-type]
        refreshed = (await db_session.execute(stmt)).scalar_one()
        assert refreshed.state == OrderState.submitted  # state 유지
