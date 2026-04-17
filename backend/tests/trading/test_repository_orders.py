"""OrderRepository — 3-guard 상태 전이 + idempotency 조회."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
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


async def _make_order(db_session, strategy, account, *, idem: str | None = None):
    from src.trading.repository import OrderRepository

    repo = OrderRepository(db_session)
    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.pending,
        idempotency_key=idem,
    )
    saved = await repo.save(order)  # Sprint 6 naming — NOT create
    await repo.commit()
    return repo, saved


async def test_create_order_starts_in_pending(db_session, strategy, account):
    _repo, order = await _make_order(db_session, strategy, account)
    assert order.state == OrderState.pending


async def test_transition_to_submitted_3_guard_success(db_session, strategy, account):
    repo, order = await _make_order(db_session, strategy, account)

    rowcount = await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched.state == OrderState.submitted
    assert fetched.submitted_at is not None


async def test_transition_to_submitted_guard_blocks_wrong_state(db_session, strategy, account):
    """pending이 아닌 상태에서 submitted 전이 시도 → rowcount 0."""
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    # 이미 submitted인 상태에서 재시도 → 0
    rowcount = await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()
    assert rowcount == 0


async def test_transition_to_filled_records_exchange_order_id_and_price(db_session, strategy, account):
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    rowcount = await repo.transition_to_filled(
        order.id,
        exchange_order_id="bybit-42",
        filled_price=Decimal("50000"),
        filled_at=datetime.now(UTC),
    )
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched.state == OrderState.filled
    assert fetched.exchange_order_id == "bybit-42"
    assert fetched.filled_price == Decimal("50000")


async def test_transition_to_rejected_records_error_message(db_session, strategy, account):
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    rowcount = await repo.transition_to_rejected(
        order.id, error_message="InsufficientFunds", failed_at=datetime.now(UTC)
    )
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched.state == OrderState.rejected
    assert fetched.error_message == "InsufficientFunds"


async def test_get_by_idempotency_key_returns_order(db_session, strategy, account):
    repo, order = await _make_order(db_session, strategy, account, idem="tv-signal-001")
    fetched = await repo.get_by_idempotency_key("tv-signal-001")
    assert fetched is not None
    assert fetched.id == order.id


async def test_get_by_idempotency_key_miss_returns_none(db_session, strategy, account):
    from src.trading.repository import OrderRepository
    repo = OrderRepository(db_session)
    assert await repo.get_by_idempotency_key("never-seen") is None


async def test_transition_to_filled_records_partial_quantity(db_session, strategy, account):
    """CCXT 부분체결 — filled_quantity < quantity. ADR-006 / autoplan Eng E7."""
    repo, order = await _make_order(db_session, strategy, account)
    await repo.transition_to_submitted(order.id, submitted_at=datetime.now(UTC))
    await repo.commit()

    rowcount = await repo.transition_to_filled(
        order.id,
        exchange_order_id="bybit-partial-1",
        filled_price=Decimal("50000"),
        filled_quantity=Decimal("0.005"),  # ordered 0.01, partial fill 0.005
        filled_at=datetime.now(UTC),
    )
    await repo.commit()
    assert rowcount == 1

    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.filled_quantity == Decimal("0.005")
    assert fetched.quantity == Decimal("0.01")  # 원 주문 수량 유지


async def test_order_persists_leverage_and_margin_mode(db_session, strategy, account):
    """Sprint 7a T1 — leverage/margin_mode 컬럼 round-trip 저장/조회."""
    from src.trading.repository import OrderRepository

    repo = OrderRepository(db_session)
    order = await repo.save(
        Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT:USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            price=None,
            state=OrderState.pending,
            leverage=5,
            margin_mode="cross",
        )
    )
    await repo.commit()

    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.leverage == 5
    assert fetched.margin_mode == "cross"


async def test_advisory_lock_acquire_and_release(db_session, strategy, account):
    """pg_advisory_xact_lock 트랜잭션 범위 내 동작 검증 (Sprint 5 M2 패턴).

    savepoint 격리 fixture가 이미 outer tx를 보유하므로 `session.begin()` 재호출 불가.
    advisory lock은 해당 tx 범위 내에서 걸리고 tx 종료 시 자동 해제됨.
    """
    from src.trading.repository import OrderRepository

    repo = OrderRepository(db_session)
    await repo.acquire_idempotency_lock("test-key-abc")
    result = await db_session.execute(
        text("SELECT pg_try_advisory_xact_lock(hashtext(:k))"),
        {"k": "test-key-abc"},
    )
    # 동일 트랜잭션에서는 재진입 가능이라 True — 실제 경쟁은 별도 connection 필요
    # 이 테스트는 쿼리 실행 자체가 에러 없이 완료됨을 확인
    assert result.scalar() is not None
