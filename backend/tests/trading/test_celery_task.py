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


def _make_fake_session_factory(db_session: AsyncSession):
    """Build a fake async_session_factory replacement.

    Sprint 4 pattern (test_backtest_task.py:61-78):
    - Task calls: sm = async_session_factory()  → returns sessionmaker-like
    - Then: async with sm() as session            → yields test db_session

    So the factory (function) must return a _FakeSM instance,
    and _FakeSM().__call__() must return the async context manager.
    """

    @asynccontextmanager
    async def _session_ctx():
        yield db_session

    class _FakeSM:
        """sm() call returns context manager yielding test session."""

        def __call__(self):
            return _session_ctx()

    # Return a lambda that produces _FakeSM — matches async_session_factory() call
    return lambda: _FakeSM()


@pytest.mark.asyncio
async def test_execute_order_task_transitions_pending_to_filled(
    db_session: AsyncSession,
    pending_order,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: pending → submitted → filled (FixtureExchangeProvider)."""
    import src.tasks.trading as task_mod
    from src.trading.providers import FixtureExchangeProvider

    order, _acc = pending_order

    # Session monkeypatch — Sprint 4 pattern
    monkeypatch.setattr(task_mod, "async_session_factory", _make_fake_session_factory(db_session))
    # Provider monkeypatch — FixtureExchangeProvider 강제 (EXCHANGE_PROVIDER 환경변수 독립)
    monkeypatch.setattr(task_mod, "_exchange_provider", FixtureExchangeProvider())

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
    monkeypatch.setattr(task_mod, "async_session_factory", _make_fake_session_factory(db_session))

    # Inject failing provider — bypass lazy singleton
    monkeypatch.setattr(task_mod, "_exchange_provider", FixtureExchangeProvider(fail_next_n=1))

    result = await task_mod._async_execute(order.id)

    assert result["state"] == "rejected"
    assert "failure" in result["error_message"]
    assert result["order_id"] == str(order.id)

    # Verify DB state
    await db_session.refresh(order)
    assert order.state == OrderState.rejected
    assert order.error_message is not None
    assert "failure" in order.error_message
