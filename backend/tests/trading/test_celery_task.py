"""T16 — execute_order_task Celery task tests.

Tests call `_async_execute` directly (not through Celery's sync wrapper) to
avoid `asyncio.run() cannot be called from a running loop` in pytest-asyncio.
The Celery sync wrapping (asyncio.run) is infrastructure tested separately.

Session monkeypatch pattern from Sprint 4 (test_backtest_task.py:61-78):
Replace task module's `async_session_factory` with a fake that yields
the test's `db_session`, so the task sees savepoint-committed test data.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
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
async def pending_order(db_session: AsyncSession):
    """Create User → Strategy → ExchangeAccount → Order(pending).

    Credentials encrypted with settings.trading_encryption_keys — same key
    the task uses for decryption (Correction #4).
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
        name="T16 Strategy",
        pine_source="//@version=5\nstrategy('t16')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test-api-key-1234"),
        api_secret_encrypted=crypto.encrypt("test-api-secret-5678"),
        label="T16 test account",
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
        state=OrderState.pending,
    )
    db_session.add(order)
    await db_session.commit()

    return order, account


class _NoopEngine:
    """Sprint 17 Phase C — async dispose no-op for tests."""

    async def dispose(self) -> None:
        return None


def _make_fake_create_worker_engine_and_sm(db_session: AsyncSession):
    """Build a fake create_worker_engine_and_sm replacement (Sprint 17 Phase C).

    New contract (backtest.py:31 mirror):
    - Task calls: engine, sm = create_worker_engine_and_sm()
    - Then: async with sm() as session  → yields test db_session
    - finally: await engine.dispose()

    So the factory must return a (engine, sm_callable) tuple.
    """

    @asynccontextmanager
    async def _session_ctx():
        yield db_session

    class _FakeSM:
        """sm() call returns context manager yielding test session."""

        def __call__(self):
            return _session_ctx()

    def _factory():
        return _NoopEngine(), _FakeSM()

    return _factory


@pytest.mark.asyncio
async def test_execute_order_task_transitions_pending_to_filled(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: pending → submitted → filled (FixtureExchangeProvider)."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, account = pending_order

    # Session monkeypatch — Sprint 4 pattern
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    # Provider monkeypatch — FixtureExchangeProvider 강제 (EXCHANGE_PROVIDER 환경변수 독립)
    monkeypatch.setattr(task_mod, "_provider_for_account_and_leverage", lambda exchange, mode, has_leverage: FixtureExchangeProvider())
    publisher = AsyncMock()
    monkeypatch.setattr(task_mod, "publish_realtime", publisher)

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "filled"
    assert result["exchange_order_id"].startswith("fixture-")
    assert result["order_id"] == str(order.id)

    # Verify DB state
    await db_session.refresh(order)
    assert order.state == OrderState.filled
    assert order.exchange_order_id is not None
    assert order.exchange_order_id.startswith("fixture-")
    assert order.filled_price is not None
    assert order.submitted_at is not None
    assert order.filled_at is not None
    assert publisher.await_count == 2
    assert publisher.await_args_list[0].args[0:2] == (str(account.user_id), "order_update")
    assert publisher.await_args_list[0].args[2]["state"] == "submitted"
    assert publisher.await_args_list[1].args[2] == {
        "order_id": str(order.id),
        "state": "filled",
        "symbol": order.symbol,
        "side": order.side.value,
        "source": "rest",
    }


@pytest.mark.asyncio
async def test_reduce_only_filled_order_deletes_active_position_snapshot_caches(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider
    from src.trading.services.position_service import (
        account_position_snapshot_cache_key,
        position_snapshot_cache_key,
    )

    order, account = pending_order
    order.reduce_only = True
    await db_session.commit()
    active_sessions = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]
    queried_account_ids: list[object] = []

    async def list_active_by_account(_self, account_id):  # type: ignore[no-untyped-def]
        queried_account_ids.append(account_id)
        return active_sessions

    redis = SimpleNamespace(delete=AsyncMock())
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(),
    )
    monkeypatch.setattr(task_mod.LiveSignalSessionRepository, "list_active_by_account", list_active_by_account)
    monkeypatch.setattr(task_mod, "get_redis_lock_pool", lambda: redis)
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "filled"
    assert queried_account_ids == [account.id]
    # ★계정 스코프 키도 함께 버려야 한다(BL-498). 위 세션 순회는 **활성** 세션만
    #   보므로 활성 0건이면 아무것도 안 지우는데, 계정 표는 바로 그 상태를 위해 있다.
    #   안 지우면 청산 직후 최대 15초 동안 방금 닫은 포지션이 살아 있는 청산 버튼과
    #   함께 다시 렌더된다.
    assert [call.args for call in redis.delete.await_args_list] == [
        (position_snapshot_cache_key(active_sessions[0].id),),
        (position_snapshot_cache_key(active_sessions[1].id),),
        (account_position_snapshot_cache_key(account.id),),
    ]


@pytest.mark.asyncio
async def test_reduce_only_fill_clears_account_cache_even_without_active_sessions(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★활성 세션이 0건인 상태가 정확히 BL-498 이다. 그때도 계정 캐시는 버려야 한다."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider
    from src.trading.services.position_service import account_position_snapshot_cache_key

    order, account = pending_order
    order.reduce_only = True
    await db_session.commit()

    async def list_active_by_account(_self, _account_id):  # type: ignore[no-untyped-def]
        return []

    redis = SimpleNamespace(delete=AsyncMock())
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(),
    )
    monkeypatch.setattr(task_mod.LiveSignalSessionRepository, "list_active_by_account", list_active_by_account)
    monkeypatch.setattr(task_mod, "get_redis_lock_pool", lambda: redis)
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "filled"
    assert [call.args for call in redis.delete.await_args_list] == [
        (account_position_snapshot_cache_key(account.id),),
    ]


@pytest.mark.asyncio
async def test_entry_filled_order_does_not_delete_position_snapshot_caches(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _ = pending_order
    list_active_by_account = AsyncMock()
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(),
    )
    monkeypatch.setattr(task_mod.LiveSignalSessionRepository, "list_active_by_account", list_active_by_account)
    monkeypatch.setattr(task_mod, "get_redis_lock_pool", lambda: SimpleNamespace(delete=AsyncMock()))
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "filled"
    list_active_by_account.assert_not_awaited()


@pytest.mark.asyncio
async def test_reduce_only_cache_delete_failure_does_not_change_filled_result(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _ = pending_order
    order.reduce_only = True
    await db_session.commit()

    async def list_active_by_account(_self, _account_id):  # type: ignore[no-untyped-def]
        return [SimpleNamespace(id=uuid4())]

    redis = SimpleNamespace(delete=AsyncMock(side_effect=RuntimeError("redis unavailable")))
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: FixtureExchangeProvider(),
    )
    monkeypatch.setattr(task_mod.LiveSignalSessionRepository, "list_active_by_account", list_active_by_account)
    monkeypatch.setattr(task_mod, "get_redis_lock_pool", lambda: redis)
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "filled"
    redis.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_order_task_transitions_to_rejected_on_provider_error(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Error path: FixtureExchangeProvider(fail_next_n=1) → rejected."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _acc = pending_order

    # Session monkeypatch — Sprint 4 pattern
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))

    # Inject failing provider — bypass lazy singleton
    monkeypatch.setattr(task_mod, "_provider_for_account_and_leverage", lambda exchange, mode, has_leverage: FixtureExchangeProvider(fail_next_n=1))

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "rejected"
    assert "failure" in result["error_message"]
    assert result["order_id"] == str(order.id)

    # Verify DB state
    await db_session.refresh(order)
    assert order.state == OrderState.rejected
    assert order.error_message is not None
    assert "failure" in order.error_message


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 14 Phase C — codex G.0 P1 #1 fix: receipt.status 분기 회귀 방지.
# Bybit / OKX REST 주문 접수 시 status="open" 같은 미체결 응답이 _map_ccxt_status
# 로 "submitted" 매핑됨. 이전엔 transition_to_filled() 무조건 호출 → DB 거짓 filled.
# Fix 후: submitted 유지 + exchange_order_id attach. WS event / reconciler 가 terminal.
# ═══════════════════════════════════════════════════════════════════════════


class _SubmittedReceiptProvider:
    """provider.create_order 가 receipt.status='submitted' 반환하는 mock."""

    async def create_order(self, creds, order):  # type: ignore[no-untyped-def]
        from src.trading.providers import OrderReceipt

        return OrderReceipt(
            exchange_order_id="bybit-submitted-12345",
            filled_price=None,
            status="submitted",
            raw={"id": "bybit-submitted-12345", "status": "open"},
        )

    async def cancel_order(self, creds, exchange_order_id):  # type: ignore[no-untyped-def]
        return None


class _PartialReceiptProvider:
    """부분 체결 receipt를 반환하는 REST winner 메트릭 테스트용 provider."""

    async def create_order(self, creds, order):  # type: ignore[no-untyped-def]
        from src.trading.providers import OrderReceipt

        return OrderReceipt(
            exchange_order_id="bybit-partial-12345",
            filled_price=Decimal("50000"),
            filled_quantity=Decimal("0.0005"),
            status="filled",
            raw={"id": "bybit-partial-12345", "status": "closed"},
        )


@pytest.mark.asyncio
async def test_execute_order_task_partial_fill_increments_rest_metric(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as task_mod
    from src.common.metrics import qb_partial_fill_total

    order, _ = pending_order
    monkeypatch.setattr(
        task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session)
    )
    monkeypatch.setattr(
        task_mod,
        "_provider_for_account_and_leverage",
        lambda exchange, mode, has_leverage: _PartialReceiptProvider(),
    )
    monkeypatch.setattr(task_mod, "publish_realtime", AsyncMock())
    counter = qb_partial_fill_total.labels(source="rest")
    before = counter._value.get()

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "filled"
    assert counter._value.get() == before + 1


class _RejectedReceiptProvider:
    """provider.create_order 가 receipt.status='rejected' 반환하는 mock."""

    async def create_order(self, creds, order):  # type: ignore[no-untyped-def]
        from src.trading.providers import OrderReceipt

        return OrderReceipt(
            exchange_order_id="bybit-rejected-99999",
            filled_price=None,
            status="rejected",
            raw={"id": "bybit-rejected-99999", "status": "rejected"},
        )

    async def cancel_order(self, creds, exchange_order_id):  # type: ignore[no-untyped-def]
        return None


@pytest.mark.asyncio
async def test_execute_order_task_keeps_submitted_when_receipt_status_submitted(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G.0 P1 #1 fix — receipt.status='submitted' → DB submitted 유지 (forced filled 회귀 방지)."""
    import src.tasks.trading as task_mod

    order, _acc = pending_order
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr(task_mod, "_provider_for_account_and_leverage", lambda exchange, mode, has_leverage: _SubmittedReceiptProvider())
    # Sprint 16 CI fix: Sprint 15 watchdog 가 _async_execute 의 submitted 분기에 추가한
    # fetch_order_status_task.apply_async 가 CI Celery result backend (Redis) 연결 retry
    # limit 초과 → RuntimeError. test 단위에서는 watchdog enqueue 를 no-op 으로 mock.
    monkeypatch.setattr(
        task_mod.fetch_order_status_task,
        "apply_async",
        lambda *args, **kwargs: None,
    )

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "submitted"
    assert result["exchange_order_id"] == "bybit-submitted-12345"
    assert result["order_id"] == str(order.id)

    # Verify DB state — filled 가 절대 발생 안 함. exchange_order_id 만 attach.
    await db_session.refresh(order)
    assert order.state == OrderState.submitted
    assert order.exchange_order_id == "bybit-submitted-12345"
    assert order.filled_price is None
    assert order.filled_at is None
    assert order.submitted_at is not None  # 첫 번째 transition 은 발생


@pytest.mark.asyncio
async def test_execute_order_task_transitions_to_rejected_when_receipt_status_rejected(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G.0 P1 #1 fix — receipt.status='rejected' → DB rejected 전이."""
    import src.tasks.trading as task_mod

    order, _acc = pending_order
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr(task_mod, "_provider_for_account_and_leverage", lambda exchange, mode, has_leverage: _RejectedReceiptProvider())

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "rejected"
    assert result["exchange_order_id"] == "bybit-rejected-99999"
    assert "exchange_rejected" in result["error_message"]

    await db_session.refresh(order)
    assert order.state == OrderState.rejected
    assert order.error_message is not None
    assert "exchange_rejected" in order.error_message


@pytest.mark.asyncio
async def test_execute_order_task_calls_session_commit_on_submitted_path(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sprint 13 LESSON — mock spy session.commit() 호출 자체 검증.

    db_session savepoint 의 same-session read-back 으로는 broken commit 못 잡음
    (Sprint 6 webhook_secret + Sprint 13 OrderService outer commit broken bug 두 번
    모두 spy 가 결정적). receipt.status='submitted' 분기에서도 attach_exchange_order_id
    후 session.commit() 호출 자체를 spy 로 검증.
    """
    import src.tasks.trading as task_mod

    order, _acc = pending_order
    monkeypatch.setattr(task_mod, "create_worker_engine_and_sm", _make_fake_create_worker_engine_and_sm(db_session))
    monkeypatch.setattr(task_mod, "_provider_for_account_and_leverage", lambda exchange, mode, has_leverage: _SubmittedReceiptProvider())
    # Sprint 16 CI fix — submitted 분기의 fetch_order_status_task.apply_async 우회 (Redis result backend retry limit).
    monkeypatch.setattr(
        task_mod.fetch_order_status_task,
        "apply_async",
        lambda *args, **kwargs: None,
    )

    # Spy on session.commit (Sprint 13 LESSON)
    commit_spy = pytest.MonkeyPatch()
    original_commit = db_session.commit
    call_count = {"n": 0}

    async def counting_commit() -> None:
        call_count["n"] += 1
        await original_commit()

    commit_spy.setattr(db_session, "commit", counting_commit)
    try:
        await task_mod._async_execute(order.id)
    finally:
        commit_spy.undo()

    # 최소 2 commit: (1) pending → submitted transition (2) attach_exchange_order_id 후
    # broken commit 패턴이면 0 또는 1 — 회귀 시 검증 실패.
    assert call_count["n"] >= 2, f"expected ≥2 commits, got {call_count['n']}"
