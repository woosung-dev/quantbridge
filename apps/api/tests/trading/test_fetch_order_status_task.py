"""Sprint 15 Phase A.2 — fetch_order_status_task Celery + watchdog alert throttle.

BL-001 submitted 영구 고착 watchdog. CCXT fetch_order 결과 → terminal 전이.
codex G.0 P1 #1+#2 fix: rowcount guard + Redis alert throttle.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
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
async def submitted_order(db_session: AsyncSession):
    """state=submitted + exchange_order_id 가 채워진 order. watchdog target."""
    crypto = EncryptionService(settings.trading_encryption_keys)
    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="watchdog",
        pine_source="//@version=5\nstrategy('w')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test-k"),
        api_secret_encrypted=crypto.encrypt("test-s"),
        label="watchdog acc",
    )
    db_session.add(account)
    await db_session.flush()

    order = Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.submitted,
        submitted_at=datetime.now(UTC),
        exchange_order_id="bybit-watchdog-1",
    )
    db_session.add(order)
    await db_session.commit()
    return order, account


class _NoopEngine:
    """Sprint 17 Phase C — async dispose no-op for tests."""

    async def dispose(self) -> None:
        return None


def _fake_create_worker_engine_and_sm(db_session: AsyncSession):
    """Sprint 17 Phase C — (engine, sm) tuple mock matching backtest.py:31."""

    @asynccontextmanager
    async def _ctx():
        yield db_session

    class _SM:
        def __call__(self):
            return _ctx()

    def _factory():
        return _NoopEngine(), _SM()

    return _factory


class _MockRedisPool:
    """Redis SET NX EX 의 minimum mock — set(key, value, nx=True, ex=N)."""

    def __init__(self) -> None:
        self.keys: set[bytes] = set()

    async def set(self, key, value, *, nx: bool = False, ex: int | None = None, **kw):  # type: ignore[no-untyped-def]
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


# -------------------------------------------------------------------------
# Phase A.2 — fetch_order_status_task — terminal transitions
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_order_status_filled_transitions_and_decs_gauge(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G.0 P1 #1 — provider.fetch_order returns filled → transition + dec gauge."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, account = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="filled"
        ),
    )

    # qb_active_orders 호출 spy
    dec_calls = {"n": 0}
    monkeypatch.setattr(
        task_mod.qb_active_orders,
        "dec",
        lambda *a, **kw: dec_calls.__setitem__("n", dec_calls["n"] + 1),
    )
    publisher = AsyncMock()
    monkeypatch.setattr(task_mod, "publish_realtime", publisher)

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert result["state"] == "filled"
    assert result["order_id"] == str(order.id)
    assert dec_calls["n"] == 1, "rowcount=1 일 때만 dec — race winner 만"

    await db_session.refresh(order)
    assert order.state == OrderState.filled
    assert order.filled_at is not None
    publisher.assert_awaited_once_with(
        str(account.user_id),
        "order_update",
        {
            "order_id": str(order.id),
            "state": "filled",
            "symbol": order.symbol,
            "side": order.side.value,
            "source": "watchdog",
        },
    )


@pytest.mark.asyncio
async def test_fetch_order_status_partial_fill_increments_watchdog_metric(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod
    from src.common.metrics import qb_partial_fill_total
    from src.trading.providers import OrderStatusFetch

    class _PartialStatusProvider:
        async def fetch_order(self, creds, exchange_order_id, symbol):  # type: ignore[no-untyped-def]
            return OrderStatusFetch(
                exchange_order_id=exchange_order_id,
                status="filled",
                filled_price=Decimal("50000"),
                filled_quantity=Decimal("0.0005"),
            )

    order, _ = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: _PartialStatusProvider(),
    )
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())
    counter = qb_partial_fill_total.labels(source="watchdog", kind="entry")
    before = counter._value.get()

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert result["state"] == "filled"
    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_fetch_order_status_cancelled_transitions(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _acc = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="cancelled"
        ),
    )
    dec_calls = {"n": 0}
    monkeypatch.setattr(
        task_mod.qb_active_orders,
        "dec",
        lambda *a, **kw: dec_calls.__setitem__("n", dec_calls["n"] + 1),
    )

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert result["state"] == "cancelled"
    assert dec_calls["n"] == 1
    await db_session.refresh(order)
    assert order.state == OrderState.cancelled


@pytest.mark.asyncio
async def test_fetch_order_status_rejected_transitions(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _acc = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="rejected"
        ),
    )
    dec_calls = {"n": 0}
    monkeypatch.setattr(
        task_mod.qb_active_orders,
        "dec",
        lambda *a, **kw: dec_calls.__setitem__("n", dec_calls["n"] + 1),
    )

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert result["state"] == "rejected"
    assert dec_calls["n"] == 1
    await db_session.refresh(order)
    assert order.state == OrderState.rejected


# -------------------------------------------------------------------------
# Phase A.2 — submitted retry + max-attempts alert (G.0 P1 #2)
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_order_status_still_submitted_returns_retry_signal(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """status='submitted' 응답 + attempt < 3 → result['watchdog_retry']=True."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _acc = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="submitted"
        ),
    )
    monkeypatch.setattr(task_mod, "_get_redis_lock_pool_for_alert", lambda: _MockRedisPool())

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert result["state"] == "submitted"
    assert result["watchdog_retry"] is True
    assert result["next_attempt"] == 2
    assert result["countdown"] >= 15

    await db_session.refresh(order)
    assert order.state == OrderState.submitted  # 변경 없음


@pytest.mark.asyncio
async def test_fetch_order_status_max_attempts_alerts_and_giveup(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """attempt=3 에서 status='submitted' → alert 1회 fire + result['watchdog_giveup']=True.

    G.0 P1 #2 — alert flood 회피: Redis throttle 안에서 send_critical_alert 가 호출됨.
    """
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _acc = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="submitted"
        ),
    )

    pool = _MockRedisPool()
    monkeypatch.setattr(task_mod, "_get_redis_lock_pool_for_alert", lambda: pool)

    alert_calls: list[dict] = []

    async def _fake_alert(_settings, title, message, context=None, **_kw):  # type: ignore[no-untyped-def]
        alert_calls.append({"title": title, "message": message, "context": context})
        return True

    monkeypatch.setattr(task_mod, "send_critical_alert", _fake_alert)
    rule_fanout_calls: list[str] = []

    async def _fake_rule_fanout(_session, _order, reason):  # type: ignore[no-untyped-def]
        rule_fanout_calls.append(reason)

    monkeypatch.setattr(task_mod, "_try_rule_fanout_watchdog", _fake_rule_fanout)

    result = await task_mod._async_fetch_order_status(order.id, attempt=3)

    assert result["state"] == "submitted"
    assert result["watchdog_giveup"] is True
    assert len(alert_calls) == 1
    assert rule_fanout_calls == ["still_submitted_after_max_attempts"]
    assert (
        "stuck" in alert_calls[0]["message"].lower()
        or "submit" in alert_calls[0]["message"].lower()
    )


@pytest.mark.asyncio
async def test_fetch_order_status_alert_throttled_on_second_giveup(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G.0 P1 #2 — 동일 order 의 두 번째 giveup 은 Redis throttle 로 silent."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _acc = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="submitted"
        ),
    )

    pool = _MockRedisPool()
    monkeypatch.setattr(task_mod, "_get_redis_lock_pool_for_alert", lambda: pool)

    alert_calls: list[dict] = []

    async def _fake_alert(_settings, title, message, context=None, **_kw):  # type: ignore[no-untyped-def]
        alert_calls.append({"title": title, "message": message})
        return True

    monkeypatch.setattr(task_mod, "send_critical_alert", _fake_alert)

    # 첫 giveup — alert fire
    await task_mod._async_fetch_order_status(order.id, attempt=3)
    # 둘째 giveup (5분 후 beat 가 또 enqueue 가정) — Redis 키 존재 → silent
    await task_mod._async_fetch_order_status(order.id, attempt=3)

    assert len(alert_calls) == 1, "throttle 후 두 번째 alert 안 발화"


@pytest.mark.asyncio
async def test_rule_watchdog_fanout_is_noop_without_event_attribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 세션 필드 조합의 수동 주문도 이벤트 귀속 없이는 발화하지 않는다."""
    import src.tasks.trading as task_mod

    strategy_id = uuid4()
    account_id = uuid4()
    live_session = SimpleNamespace(
        id=uuid4(), strategy_id=strategy_id, exchange_account_id=account_id, symbol="BTCUSDT"
    )
    lookup_order_ids: list = []

    class _Sessions:
        def __init__(self, _session) -> None:
            pass

        async def find_active_by_order_id(self, order_id):
            lookup_order_ids.append(order_id)
            return None

    rule_repo_calls = 0

    class _Rules:
        def __init__(self, _session) -> None:
            nonlocal rule_repo_calls
            rule_repo_calls += 1

    monkeypatch.setattr(task_mod, "LiveSignalSessionRepository", _Sessions)
    monkeypatch.setattr(task_mod, "AlertRuleRepository", _Rules)
    order = type(
        "OrderStub",
        (),
        {
            "id": uuid4(),
            "strategy_id": live_session.strategy_id,
            "exchange_account_id": live_session.exchange_account_id,
            "symbol": live_session.symbol,
        },
    )()
    await task_mod._try_rule_fanout_watchdog(object(), order, "test")
    assert lookup_order_ids == [order.id]
    assert rule_repo_calls == 0


@pytest.mark.asyncio
async def test_rule_watchdog_fanout_sends_only_for_event_attributed_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod

    live_session = SimpleNamespace(id=uuid4())
    rule = SimpleNamespace(id=uuid4(), channel="slack")

    class _Sessions:
        def __init__(self, _session) -> None:
            pass

        async def find_active_by_order_id(self, _order_id):
            return live_session

    class _Rules:
        def __init__(self, _session) -> None:
            pass

        async def find_active_watchdog_rules_for(self, session_id):
            assert session_id == live_session.id
            return [rule]

    class _Redis:
        async def set(self, *_args, **_kwargs):
            return True

    sent: list[dict] = []

    async def _send(_settings, **kwargs):
        sent.append(kwargs)
        return {"slack": True}

    monkeypatch.setattr(task_mod, "LiveSignalSessionRepository", _Sessions)
    monkeypatch.setattr(task_mod, "AlertRuleRepository", _Rules)
    monkeypatch.setattr(task_mod, "_get_redis_lock_pool_for_rule_alert", _Redis)
    monkeypatch.setattr(task_mod, "send_rule_alert", _send)
    order = SimpleNamespace(id=uuid4())

    await task_mod._try_rule_fanout_watchdog(object(), order, "test")

    assert sent[0]["context"]["session_id"] == str(live_session.id)[:8]


# -------------------------------------------------------------------------
# Phase A.2 — terminal-skip + race guard + null exchange_order_id
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_order_status_already_terminal_skip(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """이미 filled / rejected 인 order 는 skip — 거짓 dec 회피."""
    import src.tasks.trading as task_mod

    order, _acc = submitted_order
    # 이미 filled 로 직접 transition (race winner 시나리오)
    order.state = OrderState.filled
    await db_session.commit()
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )

    dec_calls = {"n": 0}
    monkeypatch.setattr(
        task_mod.qb_active_orders,
        "dec",
        lambda *a, **kw: dec_calls.__setitem__("n", dec_calls["n"] + 1),
    )

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert "skipped" in result
    assert dec_calls["n"] == 0


@pytest.mark.asyncio
async def test_fetch_provider_error_returns_retry_signal_when_under_max(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """codex G.2 P1 #2 — ProviderError + attempt < 3 → retry signal (silent skip 회피)."""
    import src.tasks.trading as task_mod
    from src.trading.exceptions import ProviderError

    order, _acc = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )

    class _FailingProvider:
        async def create_order(self, creds, o):  # type: ignore[no-untyped-def]
            return None

        async def cancel_order(self, creds, eid):  # type: ignore[no-untyped-def]
            return None

        async def fetch_order(self, creds, eid, sym):  # type: ignore[no-untyped-def]
            raise ProviderError("rate limit exceeded")

    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: _FailingProvider(),
    )
    monkeypatch.setattr(task_mod, "_get_redis_lock_pool_for_alert", lambda: _MockRedisPool())

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert result.get("watchdog_retry") is True, "P1 #2 — provider error 도 retry"
    assert result.get("next_attempt") == 2
    assert result.get("countdown") == 15


@pytest.mark.asyncio
async def test_fetch_provider_error_alerts_at_max_attempts(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """codex G.2 P1 #2 — ProviderError + attempt >= 3 → throttled alert + giveup."""
    import src.tasks.trading as task_mod
    from src.trading.exceptions import ProviderError

    order, _acc = submitted_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )

    class _FailingProvider:
        async def create_order(self, creds, o):  # type: ignore[no-untyped-def]
            return None

        async def cancel_order(self, creds, eid):  # type: ignore[no-untyped-def]
            return None

        async def fetch_order(self, creds, eid, sym):  # type: ignore[no-untyped-def]
            raise ProviderError("auth failed")

    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: _FailingProvider(),
    )
    monkeypatch.setattr(task_mod, "_get_redis_lock_pool_for_alert", lambda: _MockRedisPool())

    alert_calls: list[dict] = []

    async def _fake_alert(_settings, title, message, context=None, **_kw):  # type: ignore[no-untyped-def]
        alert_calls.append({"title": title, "message": message})
        return True

    monkeypatch.setattr(task_mod, "send_critical_alert", _fake_alert)

    result = await task_mod._async_fetch_order_status(order.id, attempt=3)

    assert result.get("watchdog_giveup") is True
    assert len(alert_calls) == 1
    assert (
        "ProviderError" in alert_calls[0]["message"]
        or "provider_error" in alert_calls[0]["message"]
    )


def test_build_watchdog_retry_kwargs_explicit_args_kwargs() -> None:
    """codex G.2 P1 #1 — _build_watchdog_retry_kwargs 가 args=[order_id] +
    kwargs={attempt:N} 만 반환. order_id 가 kwargs 에 들어가면 positional 충돌."""
    from src.tasks.trading import _build_watchdog_retry_kwargs

    target_id = str(uuid4())
    result = {
        "order_id": target_id,
        "watchdog_retry": True,
        "next_attempt": 2,
        "countdown": 30,
    }

    retry_kwargs = _build_watchdog_retry_kwargs(target_id, result)

    assert retry_kwargs is not None
    assert retry_kwargs["args"] == [target_id]
    assert retry_kwargs["kwargs"] == {"attempt": 2}
    assert "order_id" not in retry_kwargs["kwargs"], (
        "order_id 는 kwargs 에 포함 X — positional 충돌 회피"
    )
    assert retry_kwargs["countdown"] == 30


def test_build_watchdog_retry_kwargs_returns_none_when_no_retry() -> None:
    """watchdog_retry signal 없으면 None — task 가 result 그대로 반환."""
    from src.tasks.trading import _build_watchdog_retry_kwargs

    result = {"state": "filled", "order_id": "x"}
    assert _build_watchdog_retry_kwargs("x", result) is None


@pytest.mark.asyncio
async def test_fetch_order_status_null_exchange_order_id_skipped(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G.0 P1 #3 — exchange_order_id IS NULL 시 fetch 호출 불가, skip with reason."""
    import src.tasks.trading as task_mod

    order, _acc = submitted_order
    order.exchange_order_id = None
    await db_session.commit()
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )

    result = await task_mod._async_fetch_order_status(order.id, attempt=1)

    assert result.get("skipped") == "no_exchange_order_id"


# -------------------------------------------------------------------------
# Phase A.2 — _async_execute submitted 분기에서 fetch_order_status_task enqueue
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_execute_submitted_enqueues_fetch_order_status_task(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_async_execute 가 receipt.status='submitted' 시 fetch_order_status_task enqueue."""
    from decimal import Decimal as _D

    import src.tasks.trading as task_mod
    from src.auth.models import User as _U
    from src.strategy.models import ParseStatus as _PS
    from src.strategy.models import PineVersion as _PV
    from src.strategy.models import Strategy as _S
    from src.trading.encryption import EncryptionService as _Enc
    from src.trading.models import (
        ExchangeAccount as _EA,
    )
    from src.trading.models import (
        ExchangeMode as _EM,
    )
    from src.trading.models import (
        ExchangeName as _EN,
    )
    from src.trading.models import (
        Order as _O,
    )
    from src.trading.models import (
        OrderSide as _OS,
    )
    from src.trading.models import (
        OrderState as _OST,
    )
    from src.trading.models import (
        OrderType as _OT,
    )

    crypto = _Enc(settings.trading_encryption_keys)
    u = _U(id=uuid4(), auth_subject=f"u_{uuid4().hex[:6]}", email=f"{uuid4().hex[:6]}@t.l")
    db_session.add(u)
    await db_session.flush()
    s = _S(
        user_id=u.id,
        name="enq",
        pine_source="//@version=5\nstrategy('e')",
        pine_version=_PV.v5,
        parse_status=_PS.ok,
    )
    db_session.add(s)
    await db_session.flush()
    a = _EA(
        user_id=u.id,
        exchange=_EN.bybit,
        mode=_EM.demo,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
        label="enq",
    )
    db_session.add(a)
    await db_session.flush()
    o = _O(
        strategy_id=s.id,
        exchange_account_id=a.id,
        symbol="BTCUSDT",
        side=_OS.buy,
        type=_OT.market,
        quantity=_D("0.001"),
        state=_OST.pending,
    )
    db_session.add(o)
    await db_session.commit()
    order_id = o.id

    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )

    class _Submitted:
        async def create_order(self, creds, order):  # type: ignore[no-untyped-def]
            from src.trading.providers import OrderReceipt

            return OrderReceipt(
                exchange_order_id="bybit-enq-1",
                filled_price=None,
                status="submitted",
                raw={},
            )

        async def cancel_order(self, creds, eid):  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: _Submitted(),
    )

    enqueued: list[tuple] = []

    def _fake_apply_async(*, args=None, kwargs=None, countdown=None, **kw):  # type: ignore[no-untyped-def]
        enqueued.append((args, kwargs, countdown))

    monkeypatch.setattr(task_mod.fetch_order_status_task, "apply_async", _fake_apply_async)

    result = await task_mod._async_execute(order_id)

    assert result["state"] == "submitted"
    assert len(enqueued) == 1, "submitted 분기에서 fetch_order_status_task.apply_async 1회 호출"
    args, _kwargs, countdown = enqueued[0]
    assert args == [str(order_id)]
    assert countdown == 15


@pytest.mark.asyncio
async def test_watchdog_reduce_only_fill_clears_account_position_cache(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★BL-498 — watchdog 도 체결을 확정하는 경로다.

    접수 응답이 `submitted` 이고 position WS 를 놓치면 체결을 확정하는 것은 watchdog
    뿐이다. 즉시 `filled` 경로에만 캐시 무효화를 걸면 그 조합에서 계정 표가 **이미
    닫힌 포지션**을 최대 15초 더 보여준다.
    """
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider
    from src.trading.services.position_service import account_position_snapshot_cache_key

    order, account = submitted_order
    order.reduce_only = True
    account.exchange_uid = "same-uid"
    await db_session.commit()
    sibling_id = uuid4()

    redis = SimpleNamespace(delete=AsyncMock())
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="filled"
        ),
    )
    monkeypatch.setattr(task_mod, "get_redis_lock_pool", lambda: redis)
    monkeypatch.setattr(
        task_mod.ExchangeAccountRepository,
        "list_by_exchange_uid",
        AsyncMock(return_value=[SimpleNamespace(id=account.id), SimpleNamespace(id=sibling_id)]),
    )
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())

    result = await task_mod._async_fetch_order_status(order.id, 1)

    assert result["state"] == "filled"
    assert [call.args for call in redis.delete.await_args_list] == [
        (account_position_snapshot_cache_key(account.id),),
        (account_position_snapshot_cache_key(sibling_id),),
    ]


@pytest.mark.asyncio
async def test_watchdog_entry_fill_does_not_clear_account_position_cache(
    db_session: AsyncSession,
    submitted_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — 진입(reduce_only=False) 체결은 캐시를 버릴 이유가 없다."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _ = submitted_order
    assert order.reduce_only is False

    redis = SimpleNamespace(delete=AsyncMock())
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(
            fetch_status_override="filled"
        ),
    )
    monkeypatch.setattr(task_mod, "get_redis_lock_pool", lambda: redis)
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())

    await task_mod._async_fetch_order_status(order.id, 1)

    redis.delete.assert_not_awaited()
