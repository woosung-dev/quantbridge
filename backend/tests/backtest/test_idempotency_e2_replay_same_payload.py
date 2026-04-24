"""Sprint 9-6 E2: 같은 Idempotency-Key + 같은 body → 202 replayed=True.

- Service 레벨: BacktestCreatedResponse.replayed == True.
- Router 레벨: 응답 헤더 `X-Idempotency-Replayed: true`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
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
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


async def _seed_strategy(
    session: AsyncSession, *, user: User | None = None
) -> Strategy:
    if user is None:
        user = User(
            id=uuid4(),
            clerk_user_id=f"u_{uuid4().hex[:8]}",
            email=f"{uuid4().hex[:8]}@ex.com",
        )
        session.add(user)
    strat = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="EMA",
        pine_source="""//@version=5
strategy("EMA", overlay=true)
fast = ta.ema(close, 5)
slow = ta.ema(close, 20)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("L")
""",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strat)
    await session.flush()
    return strat


def _mini_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "ohlcv"
    root.mkdir()
    rows = ["timestamp,open,high,low,close,volume"]
    base = datetime(2023, 1, 1, tzinfo=UTC)
    for i in range(50):
        ts = int((base.timestamp() + i * 3600) * 1000)
        rows.append(f"{ts},100,110,90,105,1000")
    (root / "BTCUSDT_1h.csv").write_text("\n".join(rows))
    return root


def _req(strategy_id: object) -> CreateBacktestRequest:
    return CreateBacktestRequest(
        strategy_id=strategy_id,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2023, 1, 1, tzinfo=UTC),
        period_end=datetime(2023, 1, 3, tzinfo=UTC),
        initial_capital=Decimal("10000"),
    )


def _make_service(session: AsyncSession, root: Path) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root=str(root)),
        dispatcher=FakeTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_replay_returns_same_backtest_with_replayed_flag(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    db_session.add(user)
    strat = await _seed_strategy(db_session, user=user)
    service = _make_service(db_session, _mini_fixture_root(tmp_path))

    key = f"idem-{uuid4().hex}"
    first = await service.submit(_req(strat.id), user_id=user.id, idempotency_key=key)
    assert first.replayed is False

    second = await service.submit(_req(strat.id), user_id=user.id, idempotency_key=key)
    # replay — 동일 row 재사용
    assert second.replayed is True
    assert second.backtest_id == first.backtest_id


@pytest.mark.asyncio
async def test_replay_http_sets_idempotency_replayed_header(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
    tmp_path: Path,
) -> None:
    strat = await _seed_strategy(db_session, user=mock_clerk_auth)
    service = _make_service(db_session, _mini_fixture_root(tmp_path))
    app.dependency_overrides[get_backtest_service] = lambda: service

    payload = {
        "strategy_id": str(strat.id),
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "period_start": "2023-01-01T00:00:00Z",
        "period_end": "2023-01-03T00:00:00Z",
        "initial_capital": "10000",
    }
    key = f"idem-http-{uuid4().hex}"
    try:
        r1 = await client.post(
            "/api/v1/backtests",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        assert r1.status_code == 202
        assert r1.headers.get("X-Idempotency-Replayed") is None
        assert r1.json()["replayed"] is False

        r2 = await client.post(
            "/api/v1/backtests",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        assert r2.status_code == 202, r2.text
        assert r2.headers.get("X-Idempotency-Replayed") == "true"
        assert r2.json()["replayed"] is True
        assert r2.json()["backtest_id"] == r1.json()["backtest_id"]
    finally:
        app.dependency_overrides.pop(get_backtest_service, None)
