"""OrderService reject paths — qb_order_rejected_total counter 검증 (Sprint 9 Phase D).

각 reject reason 마다 service.execute 가 카운터를 +1 하는지 before/after delta 로 확인.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.common.metrics import qb_order_rejected_total
from src.trading.encryption import EncryptionService
from src.trading.exceptions import (
    IdempotencyConflict,
    KillSwitchActive,
    LeverageCapExceeded,
    NotionalExceeded,
    TradingSessionClosed,
)
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
    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        return None


class _ActiveKillSwitch:
    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        raise KillSwitchActive("Active kill switch: cumulative_loss")


class _CapturingDispatcher:
    def __init__(self) -> None:
        self.last_id: UUID | None = None

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        self.last_id = order_id


class _ClosedSessionsPort:
    """현재 UTC hour 와 겹치지 않는 세션만 반환 → TradingSessionClosed 유도."""

    async def get_sessions(self, strategy_id: UUID) -> list[str]:
        # "00:00-00:01" — 어떤 실제 hour 에도 매칭되지 않도록 짧은 창 1분
        # is_allowed 는 hour 단위 비교이므로 실제 00시 외 모든 시각에 닫힘
        from datetime import UTC, datetime

        now_hour = datetime.now(UTC).hour
        blocked_hour = (now_hour + 12) % 24  # 반대편 시간대
        return [f"{blocked_hour:02d}:00-{blocked_hour:02d}:01"]


async def test_leverage_cap_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="leverage_cap")
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=50,  # cap=20 (default) 초과
        margin_mode="cross",
    )
    with pytest.raises(LeverageCapExceeded):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_notional_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="notional")
    before = counter._value.get()

    exchange_stub = MagicMock()
    exchange_stub.fetch_balance_usdt = AsyncMock(return_value=Decimal("100"))
    # Sprint 23 BL-102: OrderService._execute_inner 가 dispatch snapshot 채움 위해
    # account fetch. notional reject 검증만 하므로 None 반환 OK (snapshot=None → legacy fallback).
    exchange_stub._repo = MagicMock()
    exchange_stub._repo.get_by_id = AsyncMock(return_value=None)

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.1"),
        price=Decimal("50000"),  # notional=100000 > 100*20*0.95=1900
        leverage=20,
        margin_mode="cross",
    )
    with pytest.raises(NotionalExceeded):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_session_closed_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="session_closed")
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        sessions_port=_ClosedSessionsPort(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    with pytest.raises(TradingSessionClosed):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_kill_switch_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="kill_switch")
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_ActiveKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    with pytest.raises(KillSwitchActive):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_idempotency_conflict_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    """동일 idempotency_key + 다른 body_hash → IdempotencyConflict + metric +1."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    # 기존 order 를 직접 INSERT 해 둔다 (idempotency row 선점).
    idem_key = f"test-idem-{uuid4()}"
    existing = Order(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
        idempotency_key=idem_key,
        idempotency_payload_hash=b"original-hash",
    )
    db_session.add(existing)
    await db_session.commit()

    counter = qb_order_rejected_total.labels(
        exchange="unknown", reason="idempotency_conflict"
    )
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    with pytest.raises(IdempotencyConflict):
        await svc.execute(req, idempotency_key=idem_key, body_hash=b"different-hash")

    after = counter._value.get()
    assert after == before + 1
