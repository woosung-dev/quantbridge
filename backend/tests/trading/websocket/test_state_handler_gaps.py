# StateHandler 의 미커버 머니패스 분기(replay_orphan / orphan TTL / 비종료 status skip) 보강
"""StateHandler 잔여 분기 TDD (BL-308, W3).

기존 test_state_handler.py 가 orderLinkId/exchange_order_id lookup, FIFO eviction,
rejected alert, filled/trailing 을 덮는다. 본 파일은 baseline coverage 의 term-missing
이 가리킨 잔여 분기만 추가(중복 금지):
- replay_orphan found/missing (state_handler.py:142-150) — REST 응답 직후 orphan 재처리.
  유실 시 = WS 가 REST 보다 먼저 도착한 fill 이 영구 미반영(silent fill drop).
- orphan TTL(5s) eviction (state_handler.py:164-171) — FIFO(1000)는 기존 커버, TTL 미커버.
- 비종료 status(New/PartiallyFilled) skip (state_handler.py:105) — fill-progress blind spot.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import uuid4

import pytest

import src.trading.websocket.state_handler as state_handler_mod
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
from src.trading.websocket.state_handler import StateHandler


def _make_settings() -> Settings:
    return Settings()


@pytest.fixture
def session_factory(db_session):
    @asynccontextmanager
    async def factory():
        yield db_session

    return factory


@pytest.fixture
async def sample_order(db_session, strategy, user):
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


async def test_replay_orphan_found_reprocesses_event(
    sample_order, session_factory, db_session
):
    """buffer 에 있던 orphan fill → replay_orphan 이 재처리 + True + buffer 제거.

    실제 시나리오: WS Filled 이벤트가 REST Order 생성보다 먼저 도착 → orphan buffer.
    REST 응답 직후 replay_orphan 호출 → 이제 Order 존재 → filled 전이.
    """
    order, acc = sample_order
    key = str(order.id)
    # WS 가 먼저 도착했다고 가정 — buffer 에 직접 적재
    handler = StateHandler(session_factory=session_factory, settings=_make_settings())
    handler._orphan_buffer[key] = (
        {
            "orderLinkId": key,
            "orderId": "EX-REPLAY",
            "orderStatus": "Filled",
            "avgPrice": "50000.00",
        },
        0.0,
    )

    replayed = await handler.replay_orphan(key, acc.id)

    assert replayed is True
    assert key not in handler._orphan_buffer  # 재처리 후 제거
    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.filled
    assert refreshed.filled_price == Decimal("50000.00")


async def test_replay_orphan_missing_returns_false(session_factory):
    """buffer 에 없는 key → False, no-op (handle_order_event 미호출)."""
    handler = StateHandler(session_factory=session_factory, settings=_make_settings())
    result = await handler.replay_orphan("not-in-buffer", uuid4())
    assert result is False


async def test_orphan_buffer_ttl_eviction(session_factory, monkeypatch):
    """5s TTL — stale orphan 은 다음 buffer 시 만료 제거(미처리).

    fill silent-fail 위험 분기: REST 가 5s 넘게 늦으면 WS fill 이벤트가 영구 유실.
    실제 clock 대기 대신 state_handler.time.time 을 monkeypatch 해 결정론적 검증.
    """
    clock = {"t": 1000.0}
    monkeypatch.setattr(state_handler_mod.time, "time", lambda: clock["t"])

    handler = StateHandler(session_factory=session_factory, settings=_make_settings())
    account_id = uuid4()
    key_old = str(uuid4())
    key_new = str(uuid4())

    # t=1000: 미지 order → orphan buffer 적재
    await handler.handle_order_event(
        account_id, {"orderLinkId": key_old, "orderStatus": "Filled"}
    )
    assert key_old in handler._orphan_buffer

    # t=1010 (>5s 경과): 두 번째 buffer 시 TTL 이 key_old 를 만료 제거
    clock["t"] = 1010.0
    await handler.handle_order_event(
        account_id, {"orderLinkId": key_new, "orderStatus": "Filled"}
    )

    assert key_old not in handler._orphan_buffer  # TTL eviction
    assert key_new in handler._orphan_buffer
    assert len(handler._orphan_buffer) == 1


async def test_non_terminal_status_skips_transition(
    sample_order, session_factory, db_session
):
    """order 존재 + 비종료 status(New) → early-return guard, _apply_transition 미호출.

    G2 false-green 방어: state 유지만 보면 guard(state_handler.py:103) 를 지워도
    _apply_transition(..., None, ...) 가 0 을 반환해 state 가 그대로라 통과한다.
    → guard 가 _apply_transition 호출 자체를 막았음을 spy 로 단언.
    """
    from unittest.mock import AsyncMock

    order, acc = sample_order
    handler = StateHandler(session_factory=session_factory, settings=_make_settings())
    spy = AsyncMock(return_value=0)
    handler._apply_transition = spy  # type: ignore[method-assign]

    await handler.handle_order_event(
        acc.id,
        {"orderLinkId": str(order.id), "orderId": "EX-NEW", "orderStatus": "New"},
    )

    spy.assert_not_awaited()  # 비종료 → 전이 시도 자체가 없어야 함
    from sqlalchemy import select

    stmt = select(Order).where(Order.id == order.id)  # type: ignore[arg-type]
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.state == OrderState.submitted  # 변화 없음
