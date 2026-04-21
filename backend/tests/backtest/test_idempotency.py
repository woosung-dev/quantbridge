"""BacktestService — Idempotency-Key 중복 제출 방어 (Sprint 9-6)."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.exceptions import BacktestDuplicateIdempotencyKey
from src.backtest.models import BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed(session: AsyncSession) -> tuple[User, Strategy]:
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
fast = ta.ema(close, 10)
slow = ta.ema(close, 30)
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
    return user, strat


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


def _make_request(strategy_id: object) -> CreateBacktestRequest:
    return CreateBacktestRequest(
        strategy_id=strategy_id,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2023, 1, 1, tzinfo=UTC),
        period_end=datetime(2023, 1, 3, tzinfo=UTC),
        initial_capital=Decimal("10000"),
    )


def _make_service(session: AsyncSession, fixture_root: Path) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root=str(fixture_root)),
        dispatcher=FakeTaskDispatcher(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_submit_with_idempotency_key_succeeds(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, strat = await _seed(db_session)
    service = _make_service(db_session, _mini_fixture_root(tmp_path))

    key = f"idem-{uuid4().hex}"
    resp = await service.submit(_make_request(strat.id), user_id=user.id, idempotency_key=key)
    assert resp.status == BacktestStatus.QUEUED


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_raises_409(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, strat = await _seed(db_session)
    service = _make_service(db_session, _mini_fixture_root(tmp_path))

    key = f"idem-{uuid4().hex}"
    first = await service.submit(_make_request(strat.id), user_id=user.id, idempotency_key=key)
    assert first.status == BacktestStatus.QUEUED

    with pytest.raises(BacktestDuplicateIdempotencyKey) as exc_info:
        await service.submit(_make_request(strat.id), user_id=user.id, idempotency_key=key)

    assert str(first.backtest_id) in exc_info.value.detail


@pytest.mark.asyncio
async def test_submit_without_idempotency_key_allows_duplicates(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, strat = await _seed(db_session)
    service = _make_service(db_session, _mini_fixture_root(tmp_path))

    req = _make_request(strat.id)
    r1 = await service.submit(req, user_id=user.id)
    r2 = await service.submit(req, user_id=user.id)
    assert r1.backtest_id != r2.backtest_id


@pytest.mark.asyncio
async def test_different_idempotency_keys_create_separate_backtests(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, strat = await _seed(db_session)
    service = _make_service(db_session, _mini_fixture_root(tmp_path))

    r1 = await service.submit(
        _make_request(strat.id), user_id=user.id, idempotency_key="key-1"
    )
    r2 = await service.submit(
        _make_request(strat.id), user_id=user.id, idempotency_key="key-2"
    )
    assert r1.backtest_id != r2.backtest_id


@pytest.mark.asyncio
async def test_idempotency_key_stored_on_backtest(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, strat = await _seed(db_session)
    service = _make_service(db_session, _mini_fixture_root(tmp_path))

    key = f"stored-{uuid4().hex}"
    resp = await service.submit(_make_request(strat.id), user_id=user.id, idempotency_key=key)

    repo = BacktestRepository(db_session)
    bt = await repo.get_by_idempotency_key(key)
    assert bt is not None
    assert bt.id == resp.backtest_id
    assert bt.idempotency_key == key
