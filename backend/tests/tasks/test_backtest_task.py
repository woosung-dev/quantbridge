"""tasks/backtest.py — reclaim_stale_running + _execute skeleton."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus, _utcnow


@pytest.mark.asyncio
async def test_reclaim_stale_running_marks_failed(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """running + started_at < threshold → failed."""
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    db_session.add(user)
    await db_session.flush()  # FK 제약: strategy → user

    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()  # FK 제약: backtest → strategy

    stale_bt = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=_utcnow() - timedelta(days=30),
        period_end=_utcnow() - timedelta(days=1),
        initial_capital=Decimal("1000"),
        status=BacktestStatus.RUNNING,
        started_at=_utcnow() - timedelta(hours=2),  # 2h old (> 30min threshold)
    )
    db_session.add(stale_bt)
    await db_session.commit()

    # Patch the async_sessionmaker factory inside tasks.backtest to reuse test session
    from contextlib import asynccontextmanager

    import src.tasks.backtest as task_mod

    @asynccontextmanager
    async def _mock_sessionmaker_context():
        yield db_session

    # Replace the `async_sessionmaker` callable with one that returns our test session context
    class _MockSM:
        def __call__(self):
            return _mock_sessionmaker_context()

    monkeypatch.setattr(task_mod, "async_sessionmaker_factory", _MockSM())

    from src.tasks.backtest import reclaim_stale_running

    reclaimed = await reclaim_stale_running()
    assert reclaimed >= 1

    await db_session.refresh(stale_bt)
    assert stale_bt.status == BacktestStatus.FAILED
