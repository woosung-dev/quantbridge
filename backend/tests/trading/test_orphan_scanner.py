"""Sprint 15 Phase A.3 — orphan_scanner Celery beat (BL-001 + BL-002).

scan_stuck_orders_task: 30분 이상 pending/submitted 인 order 자동 reconcile + alert.
- pending + created_at < cutoff → execute_order_task.apply_async (dispatch 누락 복구)
- submitted + submitted_at < cutoff + exchange_order_id NOT NULL → fetch_order_status_task
- submitted + submitted_at < cutoff + exchange_order_id IS NULL → throttled alert (manual cleanup)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
async def stuck_orders_factory(db_session: AsyncSession):
    """user/strategy/account + on-demand stuck order 생성 helper."""
    crypto = EncryptionService(settings.trading_encryption_keys)
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@s.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="scan",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
        label="scan",
    )
    db_session.add(account)
    await db_session.flush()

    async def _make(
        *,
        state: OrderState,
        created_at: datetime | None = None,
        submitted_at: datetime | None = None,
        exchange_order_id: str | None = None,
    ) -> Order:
        order = Order(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            state=state,
            submitted_at=submitted_at,
            exchange_order_id=exchange_order_id,
        )
        db_session.add(order)
        await db_session.flush()
        if created_at is not None:
            # PG-side server_default 후 manual update (created_at 강제)
            order.created_at = created_at
            await db_session.flush()
        return order

    yield _make
    await db_session.commit()


def _fake_session_factory(db_session: AsyncSession):
    @asynccontextmanager
    async def _ctx():
        yield db_session

    class _SM:
        def __call__(self):
            return _ctx()

    return lambda: _SM()


# -------------------------------------------------------------------------
# Repository — list_stuck_* 메서드
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_stuck_pending_excludes_recent(
    db_session: AsyncSession, stuck_orders_factory
) -> None:
    """list_stuck_pending — pending + created_at < cutoff 만."""
    from src.trading.repository import OrderRepository

    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=30)

    stuck = await stuck_orders_factory(
        state=OrderState.pending, created_at=now - timedelta(hours=2)
    )
    recent = await stuck_orders_factory(
        state=OrderState.pending, created_at=now - timedelta(minutes=5)
    )
    await db_session.commit()

    repo = OrderRepository(db_session)
    result = await repo.list_stuck_pending(cutoff)

    ids = {o.id for o in result}
    assert stuck.id in ids
    assert recent.id not in ids


@pytest.mark.asyncio
async def test_list_stuck_submitted_requires_exchange_order_id(
    db_session: AsyncSession, stuck_orders_factory
) -> None:
    """G.0 P1 #3 — submitted + null exchange_order_id 는 list_stuck_submitted 에 포함 X."""
    from src.trading.repository import OrderRepository

    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=30)
    stale = now - timedelta(hours=1)

    with_id = await stuck_orders_factory(
        state=OrderState.submitted,
        submitted_at=stale,
        exchange_order_id="ex-1",
    )
    null_id = await stuck_orders_factory(
        state=OrderState.submitted, submitted_at=stale, exchange_order_id=None
    )
    await db_session.commit()

    repo = OrderRepository(db_session)
    result = await repo.list_stuck_submitted(cutoff)

    ids = {o.id for o in result}
    assert with_id.id in ids
    assert null_id.id not in ids


@pytest.mark.asyncio
async def test_list_stuck_submission_interrupted_only_null_exchange_order_id(
    db_session: AsyncSession, stuck_orders_factory
) -> None:
    """G.0 P1 #3 — submitted + null exchange_order_id 만 별도 list."""
    from src.trading.repository import OrderRepository

    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=30)
    stale = now - timedelta(hours=1)

    interrupted = await stuck_orders_factory(
        state=OrderState.submitted, submitted_at=stale, exchange_order_id=None
    )
    normal = await stuck_orders_factory(
        state=OrderState.submitted,
        submitted_at=stale,
        exchange_order_id="ex-2",
    )
    await db_session.commit()

    repo = OrderRepository(db_session)
    result = await repo.list_stuck_submission_interrupted(cutoff)

    ids = {o.id for o in result}
    assert interrupted.id in ids
    assert normal.id not in ids


# -------------------------------------------------------------------------
# scan_stuck_orders_task
# -------------------------------------------------------------------------


class _MockRedisPool:
    def __init__(self) -> None:
        self.keys: set[bytes] = set()

    async def set(self, key, value, *, nx: bool = False, ex: int | None = None, **kw):  # type: ignore[no-untyped-def]
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


@pytest.mark.asyncio
async def test_scan_stuck_orders_enqueues_pending_via_execute_order_task(
    db_session: AsyncSession, stuck_orders_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.tasks.orphan_scanner as scanner_mod
    import src.tasks.trading as trading_mod

    now = datetime.now(UTC)
    stuck_pending = await stuck_orders_factory(
        state=OrderState.pending, created_at=now - timedelta(hours=2)
    )
    await db_session.commit()

    monkeypatch.setattr(
        scanner_mod, "async_session_factory", _fake_session_factory(db_session)
    )

    enqueued: list[tuple] = []

    def _fake_apply_async(*, args=None, **kw):  # type: ignore[no-untyped-def]
        enqueued.append((args, kw))

    monkeypatch.setattr(trading_mod.execute_order_task, "apply_async", _fake_apply_async)
    monkeypatch.setattr(scanner_mod, "_get_redis_lock_pool_for_alert", lambda: _MockRedisPool())

    async def _noop_alert(*a, **kw):  # type: ignore[no-untyped-def]
        return True

    monkeypatch.setattr(scanner_mod, "send_critical_alert", _noop_alert)

    result = await scanner_mod._async_scan_stuck_orders()

    assert result["pending"] >= 1
    assert any(args == [str(stuck_pending.id)] for args, _ in enqueued)


@pytest.mark.asyncio
async def test_scan_stuck_orders_enqueues_submitted_via_fetch_order_status_task(
    db_session: AsyncSession, stuck_orders_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.tasks.orphan_scanner as scanner_mod
    import src.tasks.trading as trading_mod

    now = datetime.now(UTC)
    stuck_submitted = await stuck_orders_factory(
        state=OrderState.submitted,
        submitted_at=now - timedelta(hours=1),
        exchange_order_id="bybit-stuck-2",
    )
    await db_session.commit()

    monkeypatch.setattr(
        scanner_mod, "async_session_factory", _fake_session_factory(db_session)
    )

    enqueued: list[tuple] = []

    def _fake_apply_async(*, args=None, **kw):  # type: ignore[no-untyped-def]
        enqueued.append((args, kw))

    monkeypatch.setattr(
        trading_mod.fetch_order_status_task, "apply_async", _fake_apply_async
    )
    monkeypatch.setattr(scanner_mod, "_get_redis_lock_pool_for_alert", lambda: _MockRedisPool())

    async def _noop_alert(*a, **kw):  # type: ignore[no-untyped-def]
        return True

    monkeypatch.setattr(scanner_mod, "send_critical_alert", _noop_alert)

    result = await scanner_mod._async_scan_stuck_orders()

    assert result["submitted"] >= 1
    assert any(args == [str(stuck_submitted.id)] for args, _ in enqueued)


@pytest.mark.asyncio
async def test_scan_stuck_orders_alerts_throttled_per_order(
    db_session: AsyncSession, stuck_orders_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G.0 P1 #2 — 동일 stuck pending 의 두 번째 scan cycle 은 alert 안 발화.

    Note: submitted+ex_id 는 alert 안 발화 (fetch_order task 가 attempt>=max 후 발화).
    pending stuck 만 scan 시점 alert. 이걸로 throttle 검증.
    """
    import src.tasks.orphan_scanner as scanner_mod
    import src.tasks.trading as trading_mod

    now = datetime.now(UTC)
    await stuck_orders_factory(
        state=OrderState.pending, created_at=now - timedelta(hours=1)
    )
    await db_session.commit()

    monkeypatch.setattr(
        scanner_mod, "async_session_factory", _fake_session_factory(db_session)
    )
    monkeypatch.setattr(
        trading_mod.execute_order_task,
        "apply_async",
        lambda **kw: None,  # no-op
    )

    pool = _MockRedisPool()
    monkeypatch.setattr(scanner_mod, "_get_redis_lock_pool_for_alert", lambda: pool)

    alert_count = {"n": 0}

    async def _spy_alert(*a, **kw):  # type: ignore[no-untyped-def]
        alert_count["n"] += 1
        return True

    monkeypatch.setattr(scanner_mod, "send_critical_alert", _spy_alert)

    await scanner_mod._async_scan_stuck_orders()
    await scanner_mod._async_scan_stuck_orders()

    assert alert_count["n"] == 1, "throttle 후 동일 cycle 의 두 번째 alert 안 발화"


@pytest.mark.asyncio
async def test_scan_stuck_orders_no_op_returns_zero(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """stuck order 0건 → no-op + alert 0회."""
    import src.tasks.orphan_scanner as scanner_mod

    monkeypatch.setattr(
        scanner_mod, "async_session_factory", _fake_session_factory(db_session)
    )
    pool = _MockRedisPool()
    monkeypatch.setattr(scanner_mod, "_get_redis_lock_pool_for_alert", lambda: pool)

    alert_count = {"n": 0}

    async def _spy_alert(*a, **kw):  # type: ignore[no-untyped-def]
        alert_count["n"] += 1
        return True

    monkeypatch.setattr(scanner_mod, "send_critical_alert", _spy_alert)

    result = await scanner_mod._async_scan_stuck_orders()

    assert result["pending"] == 0
    assert result["submitted"] == 0
    assert result["interrupted"] == 0
    assert alert_count["n"] == 0
