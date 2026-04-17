"""execute_order_task + bybit_futures provider 분기 — Sprint 7a (T3).

Pending futures Order → `_async_execute` → BybitFuturesProvider 호출 시
OrderSubmit에 leverage/margin_mode가 주입되는지 검증.

Monkeypatch 패턴은 test_celery_task.py (Sprint 4 세션 팩토리 교체 + provider 직접 주입)를 따른다.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService
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
async def pending_futures_order(db_session: AsyncSession):
    """User → Strategy → ExchangeAccount → Order(pending, leverage=5, margin_mode='cross').

    Credentials는 settings.trading_encryption_keys로 암호화 (task 복호화와 동일 key).
    """
    crypto = EncryptionService(settings.trading_encryption_keys)

    user = User(
        id=uuid4(),
        clerk_user_id=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="T3 Futures Strategy",
        pine_source="//@version=5\nstrategy('t3 futures')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test-api-key-futures"),
        api_secret_encrypted=crypto.encrypt("test-api-secret-futures"),
        label="T3 futures test account",
    )
    db_session.add(account)
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
        leverage=5,
        margin_mode="cross",
    )
    db_session.add(order)
    await db_session.commit()

    return order, account


def _make_fake_session_factory(db_session: AsyncSession):
    """test_celery_task.py와 동일 패턴 — task가 보는 session을 테스트 session으로 대체."""

    @asynccontextmanager
    async def _session_ctx():
        yield db_session

    class _FakeSM:
        def __call__(self):
            return _session_ctx()

    return lambda: _FakeSM()


class _CapturingFuturesProvider:
    """OrderSubmit 필드를 캡처만 하고 filled receipt 반환하는 fake."""

    def __init__(self) -> None:
        self.captured: dict[str, Any] = {}

    async def create_order(self, creds, submit):
        from src.trading.providers import OrderReceipt

        self.captured["symbol"] = submit.symbol
        self.captured["leverage"] = submit.leverage
        self.captured["margin_mode"] = submit.margin_mode
        self.captured["quantity"] = submit.quantity
        return OrderReceipt(
            exchange_order_id="fx-futures-1",
            filled_price=Decimal("50000"),
            status="filled",
            raw={},
        )

    async def cancel_order(self, creds, exchange_order_id: str) -> None:
        return None


@pytest.mark.asyncio
async def test_async_execute_uses_bybit_futures_provider_with_leverage(
    db_session: AsyncSession,
    pending_futures_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pending futures 주문 → Celery async path → BybitFuturesProvider 호출 시
    OrderSubmit.leverage/margin_mode가 Order row로부터 올바르게 주입된다.
    """
    import src.tasks.trading as task_mod

    order, _account = pending_futures_order

    monkeypatch.setattr(
        task_mod, "async_session_factory", _make_fake_session_factory(db_session)
    )

    fake_provider = _CapturingFuturesProvider()
    monkeypatch.setattr(task_mod, "_exchange_provider", fake_provider)

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "filled"
    assert result["exchange_order_id"] == "fx-futures-1"
    assert fake_provider.captured["symbol"] == "BTC/USDT:USDT"
    assert fake_provider.captured["leverage"] == 5
    assert fake_provider.captured["margin_mode"] == "cross"
    assert fake_provider.captured["quantity"] == Decimal("0.001")


def test_build_exchange_provider_dispatches_bybit_futures(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings.exchange_provider='bybit_futures' → BybitFuturesProvider 인스턴스 반환."""
    import src.tasks.trading as task_mod
    from src.trading.providers import BybitFuturesProvider

    # lru_cache된 settings 객체에 직접 속성 교체 (monkeypatch가 자동 복구)
    monkeypatch.setattr(task_mod.settings, "exchange_provider", "bybit_futures")
    # lazy singleton 초기화 우회
    monkeypatch.setattr(task_mod, "_exchange_provider", None)

    provider = task_mod._build_exchange_provider()
    assert isinstance(provider, BybitFuturesProvider)
