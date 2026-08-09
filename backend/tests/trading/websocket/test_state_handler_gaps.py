# StateHandler 의 미커버 머니패스 분기(고아 폐기 계상 / 비종료 status skip) 보강
"""StateHandler 잔여 분기 TDD (BL-308, W3 → BL-448 재작성, 2026-08-09).

기존 test_state_handler.py 가 orderLinkId/exchange_order_id lookup, rejected alert,
filled/trailing 을 덮는다. 본 파일은 baseline coverage 의 term-missing 이 가리킨 잔여
분기만 추가(중복 금지):

- 고아 이벤트 폐기 계상 (`_discard_orphan`) — 로컬 행이 없는 WS 이벤트가 폐기될 때 **폐기
  축** 카운터가 오르는가. 유실 시 = 놓친 체결이 원장 어디에도 안 남고 관측조차 안 된다.
- 비종료 status(New/PartiallyFilled) skip — fill-progress blind spot.

★**BL-448 로 사라진 것** — `replay_orphan` found/missing 과 orphan TTL eviction 을 재던 세
케이스는 지웠다. 그 셋이 재던 5초 재생 버퍼를 **프로덕션이 한 번도 부르지 않았기 때문**이다
(`replay_orphan` 호출자 0). 즉 그 테스트들은 테스트만이 도달하는 경로를 지키고 있었고,
「REST 응답 직후 재처리」라는 시나리오는 프로덕션에 존재한 적이 없다. 회수 책임은
reconciler 하나이며 그쪽은 `tests/trading/websocket/test_reconciliation*.py` 가 잰다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import uuid4

import pytest

import src.trading.websocket.state_handler as state_handler_mod
from src.common.metrics import qb_ws_orphan_discarded_total, qb_ws_orphan_event_total
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


def _discarded(account_id, reason: str) -> float:
    return qb_ws_orphan_discarded_total.labels(
        account_id=str(account_id), reason=reason
    )._value.get()  # type: ignore[attr-defined]


def _arrived(account_id) -> float:
    return qb_ws_orphan_event_total.labels(
        account_id=str(account_id)
    )._value.get()  # type: ignore[attr-defined]


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


async def test_orphan_terminal_event_is_counted_as_discarded(
    session_factory, monkeypatch: pytest.MonkeyPatch
):
    """로컬 행이 없는 **종결** 이벤트 → 폐기 축 카운터 +1 + WARNING 로그.

    이것이 BL-448 의 red→green 이다. 종전에는 이 이벤트가 5초 버퍼에 들어갔다가 아무도
    읽지 않은 채 TTL/FIFO 로 조용히 사라졌고, 폐기 시점의 로그·메트릭이 전무해 **유실을
    도착 수와 구분할 수 없었다.**

    ★`caplog` 를 안 쓴다 — 실측으로 이 시험이 **격리에서 green, 전체 스위트에서 red** 였다.
    `caplog` 는 root 전파에 의존하는데 `logging_config.dictConfig` 는 root 핸들러를 **제거**
    하므로, 그것을 밟는 시험이 먼저 돌면 레코드가 사라진다. 같은 함정을
    `test_position_fanout.py:216` 이 이미 기록해 뒀고 거기 쓰인 관용구를 그대로 따른다.
    """
    handler = StateHandler(session_factory=session_factory, settings=_make_settings())
    account_id = uuid4()
    before_lost = _discarded(account_id, "terminal_event_lost")
    before_ignored = _discarded(account_id, "non_terminal_ignored")
    before_arrived = _arrived(account_id)

    warnings: list[str] = []
    monkeypatch.setattr(
        state_handler_mod.logger,
        "warning",
        lambda msg, *a, **k: warnings.append(str(msg)),
    )

    await handler.handle_order_event(
        account_id, {"orderLinkId": str(uuid4()), "orderStatus": "Filled"}
    )

    assert _discarded(account_id, "terminal_event_lost") == before_lost + 1
    # 두 reason 이 서로를 오염시키지 않는다 — 그래야 경보 문턱을 걸 수 있다.
    assert _discarded(account_id, "non_terminal_ignored") == before_ignored
    # 도착 축은 그대로 살아 있다 (기존 대시보드 계약 불변).
    assert _arrived(account_id) == before_arrived + 1
    # 종결 폐기는 debug 가 아니라 warning 이어야 한다 — 종전엔 프로덕션 레벨에서 무음이었다.
    assert [w for w in warnings if "ws_orphan_discarded" in w]


async def test_orphan_non_terminal_event_uses_a_distinct_reason(session_factory):
    """로컬 행이 없는 **비종결** 이벤트 → 다른 reason 으로 계상 (머니-패스 손실 아님).

    로컬 행이 있었어도 `New` 는 어차피 skip 이므로 이 폐기는 무해하다. 종결 유실과 한
    카운터로 뭉치면 경보가 상시 발화해 쓸모가 없어진다 — 축을 나눈 이유가 이것이다.
    """
    handler = StateHandler(session_factory=session_factory, settings=_make_settings())
    account_id = uuid4()
    before_lost = _discarded(account_id, "terminal_event_lost")
    before_ignored = _discarded(account_id, "non_terminal_ignored")

    await handler.handle_order_event(
        account_id, {"orderLinkId": str(uuid4()), "orderStatus": "New"}
    )

    assert _discarded(account_id, "non_terminal_ignored") == before_ignored + 1
    assert _discarded(account_id, "terminal_event_lost") == before_lost


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
