"""DELETE /api/v1/backtests/:id — terminal only + CASCADE trades."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus, BacktestTrade, TradeDirection, TradeStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _seed_bt(session, user_id, status=BacktestStatus.COMPLETED, with_trades: bool = False):
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
    )
    session.add(bt)
    if with_trades:
        await session.flush()
        session.add(BacktestTrade(
            id=uuid4(), backtest_id=bt.id, trade_index=0,
            direction=TradeDirection.LONG, status=TradeStatus.CLOSED,
            entry_time=datetime(2024, 1, 1), exit_time=datetime(2024, 1, 1, 1),
            entry_price=Decimal("100"), exit_price=Decimal("102"),
            size=Decimal("10"), pnl=Decimal("20"), return_pct=Decimal("0.02"),
            fees=Decimal("0.1"),
        ))
    return bt


@pytest.mark.asyncio
async def test_delete_completed_returns_204(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    user = mock_clerk_auth
    bt = await _seed_bt(db_session, user.id, BacktestStatus.COMPLETED)
    await db_session.commit()

    r = await client.delete(f"/api/v1/backtests/{bt.id}")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_running_returns_409(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    user = mock_clerk_auth
    bt = await _seed_bt(db_session, user.id, BacktestStatus.RUNNING)
    await db_session.commit()

    r = await client.delete(f"/api/v1/backtests/{bt.id}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "backtest_state_conflict"


@pytest.mark.asyncio
async def test_delete_cascade_trades(
    client: AsyncClient, db_session: AsyncSession, mock_clerk_auth
) -> None:
    """DELETE가 backtest_trades까지 CASCADE."""
    user = mock_clerk_auth
    bt = await _seed_bt(db_session, user.id, BacktestStatus.COMPLETED, with_trades=True)
    await db_session.commit()

    before = (await db_session.execute(
        select(func.count(BacktestTrade.id)).where(BacktestTrade.backtest_id == bt.id)
    )).scalar_one()
    assert before == 1

    r = await client.delete(f"/api/v1/backtests/{bt.id}")
    assert r.status_code == 204

    after = (await db_session.execute(
        select(func.count(BacktestTrade.id)).where(BacktestTrade.backtest_id == bt.id)
    )).scalar_one()
    assert after == 0
