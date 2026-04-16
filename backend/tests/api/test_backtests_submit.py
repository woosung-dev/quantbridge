"""POST /api/v1/backtests — HTTP integration."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dependencies import get_backtest_service
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.repository import BacktestRepository
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


def _fixture_root(tmp_path: Path) -> Path:
    """미니 OHLCV fixture (submit 테스트에서는 미사용이지만 FixtureProvider 초기화 필요)."""
    root = tmp_path / "ohlcv"
    root.mkdir()
    csv = root / "BTCUSDT_1h.csv"
    csv.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01T00:00:00Z,100,101,99,100.5,10\n"
    )
    return root


@pytest.fixture
def override_service(app: FastAPI, db_session: AsyncSession, tmp_path: Path):
    """FakeTaskDispatcher + 격리된 FixtureProvider 주입."""
    dispatcher = FakeTaskDispatcher()

    async def _override():
        return BacktestService(
            repo=BacktestRepository(db_session),
            strategy_repo=StrategyRepository(db_session),
            ohlcv_provider=FixtureProvider(root=_fixture_root(tmp_path)),
            dispatcher=dispatcher,
        )

    app.dependency_overrides[get_backtest_service] = _override
    yield dispatcher
    app.dependency_overrides.pop(get_backtest_service, None)


def _body(strategy_id) -> dict:
    return {
        "strategy_id": str(strategy_id),
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "period_start": "2024-01-01T00:00:00+00:00",
        "period_end": "2024-01-02T00:00:00+00:00",
        "initial_capital": "10000",
    }


@pytest.mark.asyncio
async def test_submit_202_with_backtest_id(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
    override_service: FakeTaskDispatcher,
) -> None:
    """Happy path — 202 + backtest_id + queued status."""
    authed_user: User = mock_clerk_auth

    strategy = Strategy(
        id=uuid4(),
        user_id=authed_user.id,
        name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()

    r = await client.post("/api/v1/backtests", json=_body(strategy.id))
    assert r.status_code == 202
    body = r.json()
    assert "backtest_id" in body
    assert body["status"] == "queued"
    assert "created_at" in body
    # Dispatcher가 1회 호출됐는지 확인
    assert len(override_service.dispatched) == 1


@pytest.mark.asyncio
async def test_submit_422_invalid_period(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
    override_service: FakeTaskDispatcher,
) -> None:
    """period_end <= period_start → 422."""
    authed_user: User = mock_clerk_auth

    strategy = Strategy(
        id=uuid4(),
        user_id=authed_user.id,
        name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()

    body = _body(strategy.id)
    body["period_end"] = "2023-01-01T00:00:00+00:00"  # period_start보다 이전
    r = await client.post("/api/v1/backtests", json=body)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_404_strategy_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
    override_service: FakeTaskDispatcher,
) -> None:
    """존재하지 않는 strategy → 404."""
    _: User = mock_clerk_auth  # 인증 활성화

    r = await client.post("/api/v1/backtests", json=_body(uuid4()))
    assert r.status_code == 404
    body = r.json()
    assert body["detail"]["code"] == "strategy_not_found"


@pytest.mark.asyncio
async def test_submit_404_other_user_strategy(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth,
    override_service: FakeTaskDispatcher,
) -> None:
    """타 유저의 strategy → 404 (ownership isolation)."""
    _: User = mock_clerk_auth  # 인증 활성화

    other_user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    db_session.add(other_user)
    strategy = Strategy(
        id=uuid4(),
        user_id=other_user.id,
        name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()

    r = await client.post("/api/v1/backtests", json=_body(strategy.id))
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "strategy_not_found"
