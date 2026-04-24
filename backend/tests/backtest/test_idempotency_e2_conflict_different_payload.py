"""Sprint 9-6 E2: 같은 Idempotency-Key + 다른 body → 409."""

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
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


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
    return user, strat


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "ohlcv"
    root.mkdir()
    rows = ["timestamp,open,high,low,close,volume"]
    base = datetime(2023, 1, 1, tzinfo=UTC)
    for i in range(50):
        ts = int((base.timestamp() + i * 3600) * 1000)
        rows.append(f"{ts},100,110,90,105,1000")
    (root / "BTCUSDT_1h.csv").write_text("\n".join(rows))
    return root


def _req(strategy_id: object, capital: str = "10000") -> CreateBacktestRequest:
    return CreateBacktestRequest(
        strategy_id=strategy_id,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2023, 1, 1, tzinfo=UTC),
        period_end=datetime(2023, 1, 3, tzinfo=UTC),
        initial_capital=Decimal(capital),
    )


def _service(session: AsyncSession, root: Path) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root=str(root)),
        dispatcher=FakeTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_different_capital_raises_409(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, strat = await _seed(db_session)
    service = _service(db_session, _fixture_root(tmp_path))

    key = f"idem-{uuid4().hex}"
    first = await service.submit(
        _req(strat.id, "10000"), user_id=user.id, idempotency_key=key
    )

    with pytest.raises(BacktestDuplicateIdempotencyKey) as exc_info:
        await service.submit(
            _req(strat.id, "20000"),  # capital 차이 → hash 불일치
            user_id=user.id,
            idempotency_key=key,
        )

    assert str(first.backtest_id) in exc_info.value.detail
    # code 변경 없음 — API contract 유지
    assert exc_info.value.code == "backtest_idempotency_conflict"


@pytest.mark.asyncio
async def test_different_user_raises_409_cross_user_reuse(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    """cross-user key 재사용도 conflict (user_id 가 hash 에 포함됨)."""
    user_a, strat_a = await _seed(db_session)
    user_b, strat_b = await _seed(db_session)

    service = _service(db_session, _fixture_root(tmp_path))

    key = f"idem-{uuid4().hex}"
    first = await service.submit(
        _req(strat_a.id), user_id=user_a.id, idempotency_key=key
    )

    with pytest.raises(BacktestDuplicateIdempotencyKey):
        await service.submit(
            _req(strat_b.id), user_id=user_b.id, idempotency_key=key
        )
    assert first.replayed is False
