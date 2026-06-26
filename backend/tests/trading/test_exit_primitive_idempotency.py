# Wave 1 C23 — exit-primitive 주문의 idempotency + persistence 통합 검증 (verify only).
"""신규 reduce_only/bracket/trigger 필드가 execute 전 구간을 통과해 Order 에 저장되고,
RedisLock+body_hash idempotency 가 신규 필드 포함 payload 에도 정상 동작함을 재확인.

신규 빌드 X — Task 1~5 의 cross-layer 정합만 검증.
"""
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
    OrderType,
)
from src.trading.schemas import OrderRequest


@pytest.fixture
def crypto() -> EncryptionService:
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


class _NoopKillSwitch:
    async def ensure_not_gated(self, strategy_id, account_id):
        return None


class _FakeDispatcher:
    def __init__(self) -> None:
        self.dispatched_count = 0

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        self.dispatched_count += 1


def _exit_request(exchange_account, strategy) -> OrderRequest:
    return OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        reduce_only=True,
        trigger_price=Decimal("47000"),
        trigger_by="MarkPrice",
        take_profit=Decimal("52000"),
        stop_loss=Decimal("46000"),
    )


async def test_exit_primitive_fields_persist_through_execute(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """execute 전 구간을 통과해 Order 에 exit-primitive 필드가 저장된다 (Task 1+3+4 정합)."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.order_service import OrderService

    repo = OrderRepository(db_session)
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=_FakeDispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    resp, replayed = await svc.execute(
        _exit_request(exchange_account, strategy), idempotency_key=None
    )
    assert not replayed

    stored = await repo.get_by_id(resp.id)
    assert stored is not None
    assert stored.reduce_only is True
    assert stored.trigger_price == Decimal("47000")
    assert stored.trigger_by == "MarkPrice"
    assert stored.take_profit == Decimal("52000")
    assert stored.stop_loss == Decimal("46000")
    # OrderResponse 도 신규 필드를 노출
    assert resp.reduce_only is True
    assert resp.trigger_price == Decimal("47000")


async def test_idempotency_conflict_with_exit_fields_payload(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """동일 key + 다른 body_hash(신규 필드 변경분) → IdempotencyConflict (C23 재확인)."""
    from src.trading.exceptions import IdempotencyConflict
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.order_service import OrderService

    repo = OrderRepository(db_session)
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=_FakeDispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    key = f"exit-idem-{uuid4().hex}"
    await svc.execute(
        _exit_request(exchange_account, strategy),
        idempotency_key=key,
        body_hash=b"hash-reduce-only-true",
    )
    with pytest.raises(IdempotencyConflict):
        await svc.execute(
            _exit_request(exchange_account, strategy),
            idempotency_key=key,
            body_hash=b"hash-reduce-only-false",
        )


async def test_idempotency_replay_with_exit_fields_payload(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """동일 key + 동일 body_hash → cached replay (dispatch 1회). C23 재확인."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.order_service import OrderService

    repo = OrderRepository(db_session)
    fake = _FakeDispatcher()
    svc = OrderService(
        session=db_session,
        repo=repo,
        dispatcher=fake,
        kill_switch=_NoopKillSwitch(),
    )
    key = f"exit-replay-{uuid4().hex}"
    first, first_replayed = await svc.execute(
        _exit_request(exchange_account, strategy),
        idempotency_key=key,
        body_hash=b"hash-same",
    )
    second, second_replayed = await svc.execute(
        _exit_request(exchange_account, strategy),
        idempotency_key=key,
        body_hash=b"hash-same",
    )
    assert not first_replayed
    assert second_replayed
    assert first.id == second.id
    assert fake.dispatched_count == 1
