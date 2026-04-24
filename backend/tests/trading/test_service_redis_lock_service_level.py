"""Sprint 11 Phase E — OrderService.execute 의 Service-level RedisLock guard.

Phase A2 Repository wrapping (1 RTT contention signal only) 제거 후 Service layer 에서
`async with RedisLock(...): await self._execute_inner(...)` 로 real distributed mutex.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from src.auth.models import User
from src.trading.encryption import EncryptionService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderType,
)
from src.trading.repository import OrderRepository
from src.trading.schemas import OrderRequest
from src.trading.service import OrderService


class _NoopKillSwitch:
    async def ensure_not_gated(self, strategy_id, account_id):
        return


class _FakeDispatcher:
    def __init__(self) -> None:
        self.dispatched_count = 0

    async def dispatch_order_execution(self, order_id) -> None:
        self.dispatched_count += 1


@pytest.fixture
def _crypto() -> EncryptionService:
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


@pytest.fixture
async def _order_service_fixture(
    db_session: AsyncSession, user: User, strategy, _crypto: EncryptionService
) -> tuple[OrderService, OrderRequest]:
    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=_crypto.encrypt("k"),
        api_secret_encrypted=_crypto.encrypt("s"),
    )
    db_session.add(acct)
    await db_session.flush()

    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=acct.id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_FakeDispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    return svc, req


@pytest.mark.asyncio
async def test_execute_wraps_redis_lock_when_idempotency_key_present(
    _order_service_fixture,
) -> None:
    """idempotency_key 있을 때 RedisLock(key, ttl_ms=30_000) context 로 감싸기."""
    svc, req = _order_service_fixture
    acquired_calls: list[tuple[str, int]] = []

    class _SpyLock:
        def __init__(self, key: str, *, ttl_ms: int, pool: object | None = None) -> None:
            acquired_calls.append((key, ttl_ms))

        async def __aenter__(self) -> bool:
            return True

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("src.common.redlock.RedisLock", _SpyLock):
        await svc.execute(req, idempotency_key="phase-e-trade-key", body_hash=None)

    assert len(acquired_calls) == 1
    assert acquired_calls[0][0] == "idem:trading:phase-e-trade-key"
    assert acquired_calls[0][1] == 30_000


@pytest.mark.asyncio
async def test_execute_skips_redis_lock_when_no_idempotency_key(
    _order_service_fixture,
) -> None:
    """idempotency_key=None → RedisLock 생성 스킵."""
    svc, req = _order_service_fixture
    acquired_calls: list[tuple[str, int]] = []

    class _SpyLock:
        def __init__(self, key: str, *, ttl_ms: int, pool: object | None = None) -> None:
            acquired_calls.append((key, ttl_ms))

        async def __aenter__(self) -> bool:
            return True

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("src.common.redlock.RedisLock", _SpyLock):
        await svc.execute(req, idempotency_key=None)

    assert len(acquired_calls) == 0


@pytest.mark.asyncio
async def test_execute_redis_unavailable_graceful_degrade_to_pg(
    _order_service_fixture,
) -> None:
    """RedisLock 획득 실패 (False) 해도 execute 정상 완료 — PG advisory 권위."""
    svc, req = _order_service_fixture

    class _UnavailableLock:
        def __init__(self, key: str, *, ttl_ms: int, pool: object | None = None) -> None:
            pass

        async def __aenter__(self) -> bool:
            return False

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("src.common.redlock.RedisLock", _UnavailableLock):
        resp, is_replayed = await svc.execute(
            req, idempotency_key="unavailable-trade-key", body_hash=None
        )

    assert resp is not None
    assert is_replayed is False
