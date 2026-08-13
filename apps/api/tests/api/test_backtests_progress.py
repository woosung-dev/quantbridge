"""GET /api/v1/backtests/:id/progress — stale flag + 404."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _seed_bt(session, user_id, status, started_at=None):
    strategy = Strategy(
        id=uuid4(), user_id=user_id, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()
    bt = Backtest(
        id=uuid4(), user_id=user_id, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("10000"), status=status,
        started_at=started_at,
    )
    session.add(bt)
    return bt


@pytest.mark.asyncio
async def test_progress_queued_not_stale(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    """queued → started_at None → stale false."""
    user = mock_clerk_auth
    bt = await _seed_bt(db_session, user.id, BacktestStatus.QUEUED)
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}/progress")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert body["started_at"] is None
    assert body["stale"] is False


@pytest.mark.asyncio
async def test_progress_stale_running(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    """running + started_at 2h ago > 30min threshold → stale true."""
    user = mock_clerk_auth
    bt = await _seed_bt(
        db_session, user.id, BacktestStatus.RUNNING,
        started_at=datetime.now(UTC) - timedelta(hours=2),
    )
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}/progress")
    body = r.json()
    assert body["status"] == "running"
    assert body["stale"] is True


@pytest.mark.asyncio
async def test_progress_unknown_backtest_404(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    r = await client.get(f"/api/v1/backtests/{uuid4()}/progress")
    assert r.status_code == 404
