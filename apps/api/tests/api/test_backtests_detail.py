"""GET /api/v1/backtests/:id — detail + ownership isolation."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _seed_bt(
    session: AsyncSession,
    user_id,
    status: BacktestStatus = BacktestStatus.COMPLETED,
) -> Backtest:
    """테스트용 Strategy + Backtest 시드 생성 헬퍼."""
    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()  # FK constraint: backtests.strategy_id 삽입 전 strategies 먼저
    bt = Backtest(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=status,
    )
    session.add(bt)
    return bt


@pytest.mark.asyncio
async def test_get_detail_queued(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """queued 상태 → metrics/equity_curve null."""
    authed_user: User = mock_clerk_auth

    bt = await _seed_bt(db_session, authed_user.id, status=BacktestStatus.QUEUED)
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(bt.id)
    assert body["status"] == "queued"
    assert body["metrics"] is None
    assert body["equity_curve"] is None


@pytest.mark.asyncio
async def test_get_detail_completed(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """completed 상태 + metrics/equity_curve 포함."""
    authed_user: User = mock_clerk_auth

    bt = await _seed_bt(db_session, authed_user.id, status=BacktestStatus.COMPLETED)
    bt.metrics = {
        "total_return": "0.18",
        "sharpe_ratio": "1.4",
        "max_drawdown": "-0.08",
        "win_rate": "0.56",
        "num_trades": 12,
    }
    bt.equity_curve = [["2024-01-01T00:00:00Z", "10000"]]
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["metrics"]["num_trades"] == 12
    assert body["metrics"]["total_return"] == "0.18"
    assert len(body["equity_curve"]) == 1


@pytest.mark.asyncio
async def test_get_detail_404_unknown(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """존재하지 않는 backtest_id → 404."""
    _: User = mock_clerk_auth  # 인증 활성화

    r = await client.get(f"/api/v1/backtests/{uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "backtest_not_found"


@pytest.mark.asyncio
async def test_get_detail_404_other_user(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """타 유저의 backtest → 404 (ownership isolation)."""
    _: User = mock_clerk_auth  # 인증 활성화

    other_user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    db_session.add(other_user)
    bt = await _seed_bt(db_session, other_user.id)
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}")
    assert r.status_code == 404
