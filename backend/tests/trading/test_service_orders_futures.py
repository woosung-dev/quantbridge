"""OrderService — Sprint 7a Futures 필드 전파 (T3).

leverage/margin_mode가 OrderRequest → Order 레코드 → dispatcher까지 흐르는지 검증.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

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


class _CapturingDispatcher:
    def __init__(self) -> None:
        self.last_id: UUID | None = None

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        self.last_id = order_id


async def test_order_service_persists_and_dispatches_futures_fields(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """Sprint 7a: leverage/margin_mode가 Order 레코드에 persist + OrderResponse에 노출."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    disp = _CapturingDispatcher()
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=disp,
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
        leverage=5,
        margin_mode="cross",
    )
    resp, replayed = await svc.execute(req, idempotency_key=None)

    assert replayed is False
    assert resp.leverage == 5
    assert resp.margin_mode == "cross"
    assert disp.last_id is not None

    fetched = await OrderRepository(db_session).get_by_id(disp.last_id)
    assert fetched is not None
    assert fetched.leverage == 5
    assert fetched.margin_mode == "cross"


async def test_order_service_persists_futures_fields_with_idempotency_key(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
):
    """Sprint 7a: idempotent branch에서도 leverage/margin_mode 전파."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService

    disp = _CapturingDispatcher()
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=disp,
        kill_switch=_NoopKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="ETH/USDT:USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        price=None,
        leverage=10,
        margin_mode="isolated",
    )
    resp, replayed = await svc.execute(req, idempotency_key="futures-idem-1", body_hash=b"h")

    assert replayed is False
    assert resp.leverage == 10
    assert resp.margin_mode == "isolated"

    assert disp.last_id is not None
    fetched = await OrderRepository(db_session).get_by_id(disp.last_id)
    assert fetched is not None
    assert fetched.leverage == 10
    assert fetched.margin_mode == "isolated"


async def test_order_service_rejects_leverage_above_cap(
    db_session: AsyncSession,
    strategy,
    exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
):
    """Sprint 7a 리뷰 합의: `bybit_futures_max_leverage` config가 서비스 계층에서 enforce.

    OrderRequest.leverage Field(le=125)는 Bybit 이론 상한. 운영 리스크 cap(기본 20)은
    settings 기반 동적 체크. Pydantic에서 통과한 값이 service에서 거부되어야 함.
    """
    from src.trading.exceptions import LeverageCapExceeded
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService
    from src.trading.services import order_service as service_module

    # 운영 cap을 20으로 강제 (default와 동일하지만 명시)
    monkeypatch.setattr(service_module.settings, "bybit_futures_max_leverage", 20)

    disp = _CapturingDispatcher()
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=disp,
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
        leverage=50,  # cap(20) 초과 — Bybit le=125는 통과
        margin_mode="cross",
    )
    with pytest.raises(LeverageCapExceeded) as exc_info:
        await svc.execute(req, idempotency_key=None)
    assert exc_info.value.requested == 50
    assert exc_info.value.cap == 20

    # DB에 Order 생성 안 됨 + dispatcher 호출 안 됨 (guard가 begin_nested 이전)
    assert disp.last_id is None


async def test_order_service_accepts_leverage_at_cap_boundary(
    db_session: AsyncSession,
    strategy,
    exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
):
    """경계 조건: leverage == cap은 통과 (>만 차단)."""
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderService
    from src.trading.services import order_service as service_module

    monkeypatch.setattr(service_module.settings, "bybit_futures_max_leverage", 20)

    disp = _CapturingDispatcher()
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=disp,
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
        leverage=20,  # == cap → 통과
        margin_mode="cross",
    )
    resp, _ = await svc.execute(req, idempotency_key=None)
    assert resp.leverage == 20
