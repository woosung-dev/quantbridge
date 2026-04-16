"""tasks/backtest.py — reclaim_stale_running + _execute skeleton."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus


def _utcnow() -> datetime:
    """테스트 헬퍼: tz-aware UTC now."""
    return datetime.now(UTC)


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

    # async_sessionmaker_factory()를 monkeypatch로 대체하여 테스트 세션 재사용.
    # 새 패턴: async_sessionmaker_factory() → sm, async with sm() as session.
    from contextlib import asynccontextmanager

    import src.tasks.backtest as task_mod

    @asynccontextmanager
    async def _session_ctx():
        yield db_session

    class _FakeSM:
        """sm() 호출 시 테스트 세션을 yield하는 context manager 반환."""

        def __call__(self):
            return _session_ctx()

    # async_sessionmaker_factory는 이제 함수이므로 lambda로 _FakeSM 인스턴스를 반환.
    monkeypatch.setattr(task_mod, "async_sessionmaker_factory", lambda: _FakeSM())

    from src.tasks.backtest import reclaim_stale_running

    reclaimed = await reclaim_stale_running()
    assert reclaimed >= 1

    await db_session.refresh(stale_bt)
    assert stale_bt.status == BacktestStatus.FAILED
