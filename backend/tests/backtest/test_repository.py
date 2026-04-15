"""BacktestRepository — CRUD + 조건부 UPDATE."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus, _utcnow
from src.backtest.repository import BacktestRepository


async def _seed_bt(
    session: AsyncSession, status: BacktestStatus = BacktestStatus.QUEUED
) -> Backtest:
    """User + Strategy + Backtest seed."""
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        clerk_user_id=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    session.add(user)
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="T",
        pine_source="//@version=5\nstrategy('T')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()

    bt = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 1, 31),
        initial_capital=Decimal("10000"),
        status=status,
    )
    session.add(bt)
    await session.flush()
    return bt


class TestBacktestRepository:
    @pytest.mark.asyncio
    async def test_get_by_id_with_owner(self, db_session: AsyncSession) -> None:
        bt = await _seed_bt(db_session)
        repo = BacktestRepository(db_session)
        fetched = await repo.get_by_id(bt.id, user_id=bt.user_id)
        assert fetched is not None
        assert fetched.id == bt.id

    @pytest.mark.asyncio
    async def test_get_other_user_returns_none(self, db_session: AsyncSession) -> None:
        bt = await _seed_bt(db_session)
        repo = BacktestRepository(db_session)
        fetched = await repo.get_by_id(bt.id, user_id=uuid4())
        assert fetched is None

    @pytest.mark.asyncio
    async def test_transition_to_running_conditional(self, db_session: AsyncSession) -> None:
        bt = await _seed_bt(db_session)
        repo = BacktestRepository(db_session)
        rows = await repo.transition_to_running(bt.id, started_at=_utcnow())
        assert rows == 1

        # 재호출 — 이미 running이므로 rows=0
        rows2 = await repo.transition_to_running(bt.id, started_at=_utcnow())
        assert rows2 == 0

    @pytest.mark.asyncio
    async def test_complete_conditional(self, db_session: AsyncSession) -> None:
        bt = await _seed_bt(db_session, status=BacktestStatus.RUNNING)
        repo = BacktestRepository(db_session)
        rows = await repo.complete(
            bt.id,
            metrics={"total_return": "0.18"},
            equity_curve=[["2024-01-01T00:00:00Z", "10000"]],
        )
        assert rows == 1

    @pytest.mark.asyncio
    async def test_request_cancel_then_finalize(self, db_session: AsyncSession) -> None:
        bt = await _seed_bt(db_session)
        repo = BacktestRepository(db_session)
        rows = await repo.request_cancel(bt.id)
        assert rows == 1

        # 재호출 — 이미 cancelling
        rows2 = await repo.request_cancel(bt.id)
        assert rows2 == 0

        rows3 = await repo.finalize_cancelled(bt.id, completed_at=_utcnow())
        assert rows3 == 1

    @pytest.mark.asyncio
    async def test_exists_for_strategy(self, db_session: AsyncSession) -> None:
        bt = await _seed_bt(db_session)
        repo = BacktestRepository(db_session)
        assert await repo.exists_for_strategy(bt.strategy_id) is True
        assert await repo.exists_for_strategy(uuid4()) is False

    @pytest.mark.asyncio
    async def test_list_by_user_pagination(self, db_session: AsyncSession) -> None:
        bt = await _seed_bt(db_session)
        repo = BacktestRepository(db_session)
        items, total = await repo.list_by_user(bt.user_id, limit=10, offset=0)
        assert total >= 1
        assert any(i.id == bt.id for i in items)

    @pytest.mark.asyncio
    async def test_reclaim_stale(self, db_session: AsyncSession) -> None:
        from datetime import timedelta
        bt = await _seed_bt(db_session, status=BacktestStatus.RUNNING)
        bt.started_at = _utcnow() - timedelta(hours=2)  # 2h ago
        db_session.add(bt)
        await db_session.flush()

        repo = BacktestRepository(db_session)
        running_reclaimed, cancelling_reclaimed = await repo.reclaim_stale(
            threshold_seconds=1800,  # 30 min
            now=_utcnow(),
        )
        assert running_reclaimed == 1
        assert cancelling_reclaimed == 0

    @pytest.mark.asyncio
    async def test_reclaim_stale_cancelling_with_null_started_at(
        self, db_session: AsyncSession
    ) -> None:
        """QUEUED → CANCELLING 전이된 backtest (started_at=NULL)도 stale reclaim 대상.

        created_at 기준으로 threshold 초과 시 cancelled 전이되어야 함.
        이 없으면 worker가 pickup 못 한 queued-cancel이 영영 stuck.
        """
        from datetime import timedelta
        bt = await _seed_bt(db_session, status=BacktestStatus.QUEUED)
        # created_at을 2h 전으로 조정, started_at NULL 유지
        bt.created_at = _utcnow() - timedelta(hours=2)
        db_session.add(bt)
        await db_session.flush()

        repo = BacktestRepository(db_session)
        # QUEUED → CANCELLING 전이
        rows = await repo.request_cancel(bt.id)
        assert rows == 1
        await db_session.refresh(bt)
        assert bt.started_at is None  # QUEUED에서 cancel이라 NULL

        # reclaim 호출 — cancelling 경로가 created_at 기준으로 잡아야 함
        running_reclaimed, cancelling_reclaimed = await repo.reclaim_stale(
            threshold_seconds=1800,  # 30 min
            now=_utcnow(),
        )
        assert running_reclaimed == 0
        assert cancelling_reclaimed == 1

        await db_session.refresh(bt)
        assert bt.status == BacktestStatus.CANCELLED
        assert bt.completed_at is not None
