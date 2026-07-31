"""BL-560 — 확인된 terminal 을 **실제 DB 행에** 기록하는지 검증한다 (mock 아님).

리컨사일러 쪽 테스트는 `OrderRepository` 를 mock 으로 갈아끼우므로 "호출했다" 까지만
증명한다. 이 파일은 그 아래를 real DB 로 받는다 — 조건부 UPDATE 가 정말 행을 뒤집는지,
그리고 **단일행 승자 규약**이 중복 처리를 정말 막는지.

두 파일을 합치면 mock 만 검사하는 구간이 없다:
  리컨사일러(프로덕션 함수) → 헬퍼 호출  [tests/tasks/test_live_signal_conditional_reconcile.py]
  헬퍼 → 실제 행 전이 + 승자 규약        [이 파일]
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.tasks.live_signal import _write_back_confirmed_terminal
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


@pytest.fixture
async def account(db_session: AsyncSession, user) -> ExchangeAccount:
    acc = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
    )
    db_session.add(acc)
    await db_session.flush()
    return acc


async def _submitted_order(
    db_session: AsyncSession, strategy, account
) -> tuple[OrderRepository, Order]:
    """`submitted` 상태의 조건부 진입 1건. 전이 가드가 보는 출발 상태다."""
    repo = OrderRepository(db_session)
    saved = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.029"),
            state=OrderState.pending,
        )
    )
    await repo.transition_to_submitted(saved.id, submitted_at=datetime.now(UTC))
    await repo.commit()
    return repo, saved


def _probe(status: str) -> SimpleNamespace:
    return SimpleNamespace(
        exchange_order_id="9c7aef0b",
        status=status,
        filled_price=Decimal("64000"),
        filled_quantity=Decimal("0.029"),
        raw={},
    )


def _hook_order(order: Order) -> SimpleNamespace:
    """후속 훅이 no-op 이 되는 형태 — 이 테스트의 관심사는 행 전이뿐이다."""
    return SimpleNamespace(id=order.id, trailing_stop=None, reduce_only=False)


async def test_confirmed_fill_actually_flips_the_row(db_session, strategy, account) -> None:
    """★거래소가 체결이라고 답한 순간 우리 행도 `filled` 가 된다.

    이게 되기 전에는 `filled_at` 이 스윕까지 비어 있었고, `list_fills_since` 가 읽지
    못해 엔진 원장이 낡은 채로 돌았다 — 그게 `110017 same side` 의 뿌리였다.
    """
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "filled"
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.state == OrderState.filled
    assert fetched.exchange_order_id == "9c7aef0b"
    assert fetched.filled_price == Decimal("64000")
    assert fetched.filled_at is not None  # ← 13분 공백을 만들던 바로 그 컬럼


async def test_second_write_back_loses_and_changes_nothing(
    db_session, strategy, account
) -> None:
    """★중복 처리 금지 — 승자 규약을 real SQL 로 확인한다.

    watchdog · WS · 스윕 · 리컨사일러가 같은 주문을 동시에 본다. 두 번째 호출이
    rowcount 0 을 받아 None 을 돌려주지 않으면 gauge 가 두 번 내려가고
    trailing/closed-pnl 훅이 두 번 걸린다.
    """
    repo, order = await _submitted_order(db_session, strategy, account)
    first = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )
    assert first == "filled"
    before = await repo.get_by_id(order.id)
    assert before is not None
    filled_at_before = before.filled_at

    second = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("filled"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert second is None  # 패자
    after = await repo.get_by_id(order.id)
    assert after is not None
    assert after.filled_at == filled_at_before  # 덮어쓰지도 않았다


async def test_confirmed_reject_flips_the_row_too(db_session, strategy, account) -> None:
    """거절도 기록한다 — 안 하면 그 행이 `submitted` 로 남아 trade_id 가 영구 no-op 이 된다."""
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("rejected"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won == "rejected"
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.state == OrderState.rejected


async def test_unknown_probe_status_writes_nothing(db_session, strategy, account) -> None:
    """★음성 대조군 — terminal 이 아닌 상태는 손대지 않는다."""
    repo, order = await _submitted_order(db_session, strategy, account)

    won = await _write_back_confirmed_terminal(
        repo,
        order_id=order.id,
        probe=_probe("submitted"),
        hook_order=_hook_order(order),
        now=datetime.now(UTC),
    )

    assert won is None
    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.state == OrderState.submitted
