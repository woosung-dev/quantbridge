# 비활성 세션의 조건부 진입 스윕 태스크를 검증한다.

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401
from src.auth.models import User
from src.common.metrics import qb_live_conditional_reconcile_errors_total
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)

celery_module = sys.modules["src.tasks.celery_app"]
live_signal_module = sys.modules["src.tasks.live_signal"]


class _NoopEngine:
    async def dispose(self) -> None:
        return None


def _fake_create_worker_engine_and_sm(db_session: AsyncSession):
    @asynccontextmanager
    async def _context():
        yield db_session

    class _SessionMaker:
        def __call__(self):
            return _context()

    return lambda: (_NoopEngine(), _SessionMaker())


@pytest.fixture
async def conditional_entry_factory(db_session: AsyncSession):
    crypto = EncryptionService(settings.trading_encryption_keys)
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@s.local",
    )
    strategy = Strategy(
        user_id=user.id,
        name="conditional-sweeper",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("key"),
        api_secret_encrypted=crypto.encrypt("secret"),
        label="conditional-sweeper",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(strategy)
    await db_session.flush()
    db_session.add(account)
    await db_session.flush()

    async def _make(*, active: bool, valid_key: bool = True) -> Order:
        session = LiveSignalSession(
            user_id=user.id,
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            interval=LiveSignalInterval.m1,
            is_active=active,
            deactivated_at=None if active else datetime.now(UTC),
        )
        db_session.add(session)
        await db_session.flush()
        key = (
            f"live:{session.id}:cond:1:100:0.001:entry"
            if valid_key
            else "external-conditional-order"
        )
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            state=OrderState.submitted,
            trigger_price=Decimal("100"),
            exchange_order_id=f"exchange-{uuid4()}",
            idempotency_key=key,
            submitted_at=datetime.now(UTC),
        )
        db_session.add(order)
        await db_session.flush()
        return order

    return _make


@pytest.mark.asyncio
async def test_sweeper_cancels_only_inactive_owned_conditional_entries(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inactive = await conditional_entry_factory(active=False)
    active = await conditional_entry_factory(active=True)
    foreign = await conditional_entry_factory(active=False, valid_key=False)
    await db_session.commit()

    cancelled_exchange_ids: list[str] = []

    class _Provider:
        async def cancel_order(self, _creds: Any, exchange_order_id: str, _symbol: str) -> None:
            cancelled_exchange_ids.append(exchange_order_id)

    monkeypatch.setattr(live_signal_module, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr("src.trading.providers.BybitFuturesProvider", _Provider)

    result = await live_signal_module._async_sweep_conditional_entries()
    await db_session.refresh(inactive)
    await db_session.refresh(active)
    await db_session.refresh(foreign)

    assert result == {"cancelled": 1}
    assert cancelled_exchange_ids == [inactive.exchange_order_id]
    assert inactive.state == OrderState.cancelled
    assert active.state == OrderState.submitted
    assert foreign.state == OrderState.submitted


@pytest.mark.asyncio
async def test_sweeper_logs_and_metrics_provider_cancel_failure(
    db_session: AsyncSession,
    conditional_entry_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orphan = await conditional_entry_factory(active=False)
    await db_session.commit()

    class _FailingProvider:
        async def cancel_order(self, _creds: Any, _exchange_order_id: str, _symbol: str) -> None:
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(live_signal_module, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr("src.trading.providers.BybitFuturesProvider", _FailingProvider)
    metric = qb_live_conditional_reconcile_errors_total.labels(stage="sweep_cancel")
    before = metric._value.get()

    result = await live_signal_module._async_sweep_conditional_entries()
    await db_session.refresh(orphan)

    assert result == {"cancelled": 0}
    assert metric._value.get() == before + 1
    assert orphan.state == OrderState.submitted


def test_conditional_entry_sweeper_beat_schedule() -> None:
    schedule = celery_module.celery_app.conf.beat_schedule
    entry = schedule["sweep-orphan-conditional-entries"]

    assert entry["task"] == "live_signal.sweep_conditional_entries"
    assert entry["schedule"] == 300.0
    assert entry["options"]["expires"] == 240
    assert "live_signal.sweep_conditional_entries" in celery_module.celery_app.tasks


def test_every_deactivation_site_enqueues_conditional_sweep() -> None:
    """★세션이 죽는 모든 경로가 조건부 진입 청소를 요청해야 한다.

    이걸 놓치면 "엔진을 못 믿겠다" 고 판단한 바로 그 순간에 거래소 주문을 남긴다 -
    fail-closed 의 정반대다. 비활성화 경로는 앞으로도 늘어날 수 있으므로 호출처를
    소스에서 세어 래칫으로 고정한다(경로별 무거운 하네스 4벌보다 이쪽이 정직하다).
    """
    from pathlib import Path

    source = Path(live_signal_module.__file__).read_text(encoding="utf-8")
    lines = source.splitlines()
    deactivate_lines = [i for i, line in enumerate(lines) if "sess_repo.deactivate(" in line]

    assert deactivate_lines, "deactivate 호출처를 못 찾았다 - 이 테스트가 stale 이다"
    for index in deactivate_lines:
        window = "\n".join(lines[index : index + 8])
        assert "_enqueue_conditional_entry_sweep()" in window, (
            f"{index + 1} 행의 deactivate 뒤에 조건부 진입 청소 요청이 없다"
        )
