"""GET /api/v1/backtests — pagination + ownership isolation."""
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


async def _seed_backtest(session: AsyncSession, user_id, symbol: str = "BTCUSDT") -> Backtest:
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
        symbol=symbol,
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("1000"),
        status=BacktestStatus.COMPLETED,
    )
    session.add(bt)
    return bt


@pytest.mark.asyncio
async def test_list_empty(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """백테스트 없음 → 빈 목록 + 기본 페이지네이션 값."""
    _: User = mock_clerk_auth

    r = await client.get("/api/v1/backtests")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["limit"] == 20
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_list_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """3건 시드, limit=2 → items=2 반환, total=3."""
    authed_user: User = mock_clerk_auth

    for _ in range(3):
        await _seed_backtest(db_session, authed_user.id)
    await db_session.commit()

    r = await client.get("/api/v1/backtests?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_list_ownership_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """타 유저 backtest는 목록에 노출되지 않음."""
    authed_user: User = mock_clerk_auth

    other_user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    db_session.add(other_user)
    await _seed_backtest(db_session, other_user.id, symbol="OTHER")
    await _seed_backtest(db_session, authed_user.id, symbol="MINE")
    await db_session.commit()

    r = await client.get("/api/v1/backtests")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "MINE"
