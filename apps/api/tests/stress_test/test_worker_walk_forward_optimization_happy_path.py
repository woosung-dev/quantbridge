# WFO worker happy path — submit(optimizer spec) → DB → worker 재최적화 → result JSONB 저장.
"""진짜 OOS 풀 경로 통합(HTTP submit 스키마 → JSONB → worker → 실 grid 옵티마이저 →
fold별 selected_params + reoptimized_per_fold 저장). DB-backed (db_session fixture)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository
from src.stress_test.dispatcher import FakeStressTaskDispatcher
from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from src.stress_test.repository import StressTestRepository
from src.stress_test.service import StressTestService

PINE_WITH_INPUT = """//@version=5
strategy("WFO", overlay=true)
emaPeriod = input.int(10, "EMA")
fast = ta.ema(close, emaPeriod)
slow = ta.ema(close, 20)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("L")
"""


def _make_sine_csv_fixture(tmp_path: Path, n: int = 300) -> Path:
    """진동(sine) OHLCV CSV — 잦은 EMA 교차로 cell 비-degenerate 보장."""
    root = tmp_path / "ohlcv"
    root.mkdir()
    rows = ["timestamp,open,high,low,close,volume"]
    base_dt = datetime(2024, 1, 1, tzinfo=UTC)
    closes = [100.0 + 5.0 * math.sin(2 * math.pi * i / 50) for i in range(n)]
    for i in range(n):
        ts_iso = (base_dt + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        close = closes[i]
        open_ = closes[i - 1] if i > 0 else closes[0]
        high = max(open_, close) + 0.05
        low = min(open_, close) - 0.05
        rows.append(f"{ts_iso},{open_},{high},{low},{close},100")
    csv = root / "BTCUSDT_1h.csv"
    csv.write_text("\n".join(rows))
    return root


@pytest.mark.asyncio
async def test_wfo_worker_stores_reoptimized_result(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user = User(
        id=uuid4(), clerk_user_id=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@ex.com"
    )
    db_session.add(user)
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="WFO",
        pine_source=PINE_WITH_INPUT,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    backtest = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=299),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        completed_at=datetime.now(UTC),
    )
    db_session.add(backtest)
    await db_session.flush()

    fixture_root = _make_sine_csv_fixture(tmp_path, n=300)
    service = StressTestService(
        repo=StressTestRepository(db_session),
        backtest_repo=BacktestRepository(db_session),
        strategy_repo=StrategyRepository(db_session),
        ohlcv_provider=FixtureProvider(root=str(fixture_root)),
        dispatcher=FakeStressTaskDispatcher(),
    )

    # WFO 모드 — optimizer_param_space + kind 동봉 (submit 이 JSONB 저장하는 형태).
    st = StressTest(
        id=uuid4(),
        user_id=user.id,
        backtest_id=backtest.id,
        kind=StressTestKind.WALK_FORWARD,
        status=StressTestStatus.QUEUED,
        params={
            "train_bars": 100,
            "test_bars": 50,
            "step_bars": 50,
            "max_folds": 4,
            "optimizer_param_space": {
                "schema_version": 1,
                "objective_metric": "total_return",
                "direction": "maximize",
                "max_evaluations": 9,
                "parameters": {
                    "emaPeriod": {"kind": "integer", "min": 5, "max": 10, "step": 5}
                },
            },
            "optimizer_kind": "grid_search",
        },
    )
    db_session.add(st)
    await db_session.flush()

    await service.run(st.id)

    reloaded = await StressTestRepository(db_session).get_by_id(st.id)
    assert reloaded is not None
    assert reloaded.status == StressTestStatus.COMPLETED, reloaded.error
    assert reloaded.result is not None
    assert reloaded.result["reoptimized_per_fold"] is True
    folds = reloaded.result["folds"]
    assert len(folds) >= 1
    for fold in folds:
        assert fold["selected_params"] is not None
        assert "emaPeriod" in fold["selected_params"]
