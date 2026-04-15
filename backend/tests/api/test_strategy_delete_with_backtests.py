"""Sprint 3 회귀 방지 — Strategy delete with backtests.

§4.8 StrategyHasBacktests 409 경로:
1. happy path — 백테스트 없음 → 204
2. has-backtest — 선조회에서 409 응답
3. TOCTOU race — exists_for_strategy mock false 후 DB FK RESTRICT → 동일 409
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy

_PINE_OK = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""


async def _seed_strategy(session: AsyncSession, user_id) -> Strategy:
    strat = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="s",
        pine_source=_PINE_OK,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strat)
    await session.flush()
    return strat


async def _seed_backtest(
    session: AsyncSession, user_id, strategy_id
) -> Backtest:
    bt = Backtest(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("1000"),
        status=BacktestStatus.COMPLETED,
        completed_at=datetime(2024, 1, 2, 1, 0, 0),
    )
    session.add(bt)
    await session.flush()
    return bt


@pytest.mark.asyncio
async def test_delete_strategy_without_backtest_still_works(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """회귀 없음 — 백테스트 없는 전략 삭제는 204 정상 응답."""
    authed_user = mock_clerk_auth
    strategy = await _seed_strategy(db_session, authed_user.id)
    await db_session.commit()

    response = await client.delete(f"/api/v1/strategies/{strategy.id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_strategy_with_backtest_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
) -> None:
    """백테스트가 있는 전략 삭제 시 409 반환."""
    authed_user = mock_clerk_auth
    strategy = await _seed_strategy(db_session, authed_user.id)
    await _seed_backtest(db_session, authed_user.id, strategy.id)
    await db_session.commit()

    response = await client.delete(f"/api/v1/strategies/{strategy.id}")
    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["code"] == "strategy_has_backtests"


@pytest.mark.asyncio
async def test_delete_strategy_integrity_error_toctou(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
    monkeypatch,
) -> None:
    """TOCTOU: exists_for_strategy False 후에도 DB-level FK RESTRICT가 catch → 409 반환."""
    authed_user = mock_clerk_auth
    strategy = await _seed_strategy(db_session, authed_user.id)
    await _seed_backtest(db_session, authed_user.id, strategy.id)
    await db_session.commit()

    # exists_for_strategy를 False 리턴하도록 monkeypatch → race loser 경로 유도
    from src.backtest.repository import BacktestRepository

    async def _fake_exists(self, strategy_id) -> bool:
        return False

    monkeypatch.setattr(BacktestRepository, "exists_for_strategy", _fake_exists)

    response = await client.delete(f"/api/v1/strategies/{strategy.id}")
    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["code"] == "strategy_has_backtests"
