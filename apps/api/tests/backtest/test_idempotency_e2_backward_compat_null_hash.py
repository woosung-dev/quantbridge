"""Sprint 9-6 E2 backward compat: 기존 row(idempotency_payload_hash=NULL) 는
어떤 body hash 와도 match 되지 않음 — 항상 conflict (409).

이유: NULL 은 E1 시대에 저장된 row 로 hash 정보가 없으므로, 같은 body 여부를
검증 불가. 안전성 우선 — replay 로 잘못 매칭되어 "이전 backtest 결과가
현재 요청에 해당한다" 는 오해를 주지 않도록.
"""

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
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


async def _seed_user_strat(session: AsyncSession) -> tuple[User, Strategy]:
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


def _req(strategy_id: object) -> CreateBacktestRequest:
    return CreateBacktestRequest(
        strategy_id=strategy_id,  # type: ignore[arg-type]
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2023, 1, 1, tzinfo=UTC),
        period_end=datetime(2023, 1, 3, tzinfo=UTC),
        initial_capital=Decimal("10000"),
    )


def _service(session: AsyncSession, root: Path) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root=str(root)),
        dispatcher=FakeTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_null_hash_existing_row_always_conflicts_on_replay_attempt(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, strat = await _seed_user_strat(db_session)

    key = f"legacy-{uuid4().hex}"
    # E1 시대 row 모의: idempotency_payload_hash=NULL (explicit).
    legacy = Backtest(
        user_id=user.id,
        strategy_id=strat.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2023, 1, 1, tzinfo=UTC),
        period_end=datetime(2023, 1, 3, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        idempotency_key=key,
        idempotency_payload_hash=None,  # backward-compat 시나리오
    )
    db_session.add(legacy)
    await db_session.flush()

    service = _service(db_session, _fixture_root(tmp_path))

    # 동일 body 로 재요청 → replay 가 아니라 409 (NULL hash 는 match 안 함)
    with pytest.raises(BacktestDuplicateIdempotencyKey):
        await service.submit(_req(strat.id), user_id=user.id, idempotency_key=key)
