"""OrderService — idempotency + advisory lock pattern (T12)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.trading.encryption import EncryptionService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.schemas import OrderRequest


@pytest.fixture
def crypto():
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


@pytest.fixture
async def exchange_account(
    db_session: AsyncSession, user: User, crypto: EncryptionService
) -> ExchangeAccount:
    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


@pytest.fixture
def order_request(exchange_account: ExchangeAccount, strategy) -> OrderRequest:
    return OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )


# ---------- tests ----------


async def test_execute_without_idempotency_creates_order(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    from src.trading.repository import OrderRepository
    from src.trading.service import OrderService

    repo = OrderRepository(db_session)
    fake = _FakeDispatcher()
    svc = OrderService(session=db_session, repo=repo, dispatcher=fake)

    resp = await svc.execute(order_request, idempotency_key=None)

    assert resp.state == OrderState.pending
    assert resp.symbol == "BTC/USDT"
    assert fake.dispatched_count == 1


async def test_execute_with_idempotency_returns_cached_on_second_call(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    from src.trading.repository import OrderRepository
    from src.trading.service import OrderService

    repo = OrderRepository(db_session)
    fake = _FakeDispatcher()
    svc = OrderService(session=db_session, repo=repo, dispatcher=fake)

    key = f"idem-{uuid4().hex}"
    first = await svc.execute(order_request, idempotency_key=key)
    second = await svc.execute(order_request, idempotency_key=key)

    assert first.id == second.id
    assert fake.dispatched_count == 1  # dispatch only once


async def test_advisory_lock_prevents_concurrent_insert(
    db_session: AsyncSession,
    order_request: OrderRequest,
):
    """Advisory lock smoke test: same-session re-entry does not deadlock."""
    from src.trading.repository import OrderRepository
    from src.trading.service import OrderService

    repo = OrderRepository(db_session)
    fake = _FakeDispatcher()
    svc = OrderService(session=db_session, repo=repo, dispatcher=fake)

    key = f"lock-{uuid4().hex}"
    resp = await svc.execute(order_request, idempotency_key=key)
    assert resp.state == OrderState.pending
    assert fake.dispatched_count == 1

    # Re-entry with same key: should return cached, no deadlock
    resp2 = await svc.execute(order_request, idempotency_key=key)
    assert resp2.id == resp.id
    assert fake.dispatched_count == 1


# ---------- helpers ----------


class _FakeDispatcher:
    """Celery dispatcher mock — commit 후 dispatch 카운팅."""

    def __init__(self) -> None:
        self.dispatched_count = 0
        self.dispatched_ids: list = []

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        self.dispatched_count += 1
        self.dispatched_ids.append(order_id)
