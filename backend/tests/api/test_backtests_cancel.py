"""POST /api/v1/backtests/:id/cancel."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _seed_bt(session: AsyncSession, user_id, status: BacktestStatus) -> Backtest:
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
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("10000"),
        status=status,
        celery_task_id="fake-celery-id",
    )
    session.add(bt)
    return bt


@pytest.mark.asyncio
async def test_cancel_queued_returns_202(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    """queued → 202 + status=cancelling + message."""
    user = mock_clerk_auth
    bt = await _seed_bt(db_session, user.id, BacktestStatus.QUEUED)
    await db_session.commit()

    r = await client.post(f"/api/v1/backtests/{bt.id}/cancel")
    assert r.status_code == 202
    body = r.json()
    assert body["backtest_id"] == str(bt.id)
    assert body["status"] == "cancelling"
    assert "Cancellation requested" in body["message"]


@pytest.mark.asyncio
async def test_cancel_running_returns_202(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    """running → 202 + cancelling."""
    user = mock_clerk_auth
    bt = await _seed_bt(db_session, user.id, BacktestStatus.RUNNING)
    await db_session.commit()

    r = await client.post(f"/api/v1/backtests/{bt.id}/cancel")
    assert r.status_code == 202
    assert r.json()["status"] == "cancelling"


@pytest.mark.asyncio
async def test_cancel_completed_returns_409(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    """completed → 409 backtest_state_conflict."""
    user = mock_clerk_auth
    bt = await _seed_bt(db_session, user.id, BacktestStatus.COMPLETED)
    await db_session.commit()

    r = await client.post(f"/api/v1/backtests/{bt.id}/cancel")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "backtest_state_conflict"


@pytest.mark.asyncio
async def test_cancel_not_found_returns_404(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    r = await client.post(f"/api/v1/backtests/{uuid4()}/cancel")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "backtest_not_found"
