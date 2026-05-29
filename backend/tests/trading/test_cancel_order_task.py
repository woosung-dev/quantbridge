"""CF4 — cancel_order_task: submitted 주문의 거래소 취소 (fail-closed).

DB-only 취소는 거래소에 resting 중인 주문을 orphan 으로 남긴다 (DB=cancelled, 거래소=live).
submitted 주문은 provider.cancel_order 성공 시에만 DB cancelled 로 전이한다.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService
from src.trading.exceptions import ProviderError
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
async def submitted_order(db_session: AsyncSession):
    crypto = EncryptionService(settings.trading_encryption_keys)
    user = User(id=uuid4(), clerk_user_id=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@t.local")
    db_session.add(user)
    await db_session.flush()
    strategy = Strategy(
        user_id=user.id, name="cf4", pine_source="//@version=5\nstrategy('c')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()
    account = ExchangeAccount(
        user_id=user.id, exchange=ExchangeName.bybit, mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test-k"), api_secret_encrypted=crypto.encrypt("test-s"),
        label="cf4 acc",
    )
    db_session.add(account)
    await db_session.flush()
    order = Order(
        strategy_id=strategy.id, exchange_account_id=account.id, symbol="BTCUSDT",
        side=OrderSide.buy, type=OrderType.market, quantity=Decimal("0.001"),
        state=OrderState.submitted, submitted_at=datetime.now(UTC),
        exchange_order_id="bybit-cf4-1",
    )
    db_session.add(order)
    await db_session.commit()
    return order, account


class _NoopEngine:
    async def dispose(self) -> None:
        return None


def _fake_create_worker_engine_and_sm(db_session: AsyncSession):
    @asynccontextmanager
    async def _ctx():
        yield db_session

    class _SM:
        def __call__(self):
            return _ctx()

    def _factory():
        return _NoopEngine(), _SM()

    return _factory


class _RecordingProvider:
    def __init__(self, *, raise_error: bool = False) -> None:
        self.cancel_calls: list[str] = []
        self._raise = raise_error

    async def cancel_order(self, creds, exchange_order_id: str) -> None:
        self.cancel_calls.append(exchange_order_id)
        if self._raise:
            raise ProviderError("exchange cancel failed")


@pytest.mark.asyncio
async def test_cancel_order_task_cancels_submitted_on_exchange(
    db_session: AsyncSession, submitted_order, monkeypatch: pytest.MonkeyPatch
) -> None:
    """provider.cancel_order 성공 → DB cancelled + 거래소 호출 발생."""
    import src.tasks.trading as task_mod

    order, _acc = submitted_order
    prov = _RecordingProvider()
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(task_mod, "_provider_for_account_and_leverage", lambda e, m, h: prov)
    monkeypatch.setattr(task_mod.qb_active_orders, "dec", lambda *a, **k: None)

    result = await task_mod._async_cancel_order(order.id)

    assert result["state"] == "cancelled"
    assert prov.cancel_calls == ["bybit-cf4-1"], "거래소 cancel_order 가 호출돼야 함"
    await db_session.refresh(order)
    assert order.state == OrderState.cancelled


@pytest.mark.asyncio
async def test_cancel_order_task_provider_error_keeps_submitted(
    db_session: AsyncSession, submitted_order, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ProviderError → DB flip 금지 (false cancel 방지). 주문은 submitted 유지."""
    import src.tasks.trading as task_mod

    order, _acc = submitted_order
    prov = _RecordingProvider(raise_error=True)
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(task_mod, "_provider_for_account_and_leverage", lambda e, m, h: prov)

    result = await task_mod._async_cancel_order(order.id)

    assert result.get("skipped") == "provider_error"
    await db_session.refresh(order)
    assert order.state == OrderState.submitted, (
        "거래소 취소 실패 시 DB 를 cancelled 로 바꾸면 안 됨 (orphan/false-cancel)"
    )
