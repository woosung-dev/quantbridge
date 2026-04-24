"""StressTestService.run (WFA) happy path — ≥1 fold 생성 + result JSONB 저장."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository
from src.stress_test.dispatcher import FakeStressTaskDispatcher
from src.stress_test.models import (
    StressTest,
    StressTestKind,
    StressTestStatus,
)
from src.stress_test.repository import StressTestRepository
from src.stress_test.service import StressTestService
from tests.stress_test.helpers import SIMPLE_PINE


def _make_csv_fixture(tmp_path: Path, n: int = 200) -> Path:
    """BTCUSDT_1h.csv 생성 — 완만한 상승 추세. ISO 8601 timestamp."""
    root = tmp_path / "ohlcv"
    root.mkdir()
    rows = ["timestamp,open,high,low,close,volume"]
    base = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(n):
        ts_iso = (base + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        close = 100.0 + i * 0.1
        rows.append(
            f"{ts_iso},{close - 0.2},{close + 0.3},{close - 0.3},{close},1000"
        )
    csv = root / "BTCUSDT_1h.csv"
    csv.write_text("\n".join(rows))
    return root


@pytest.mark.asyncio
async def test_walk_forward_worker_produces_folds(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    # Seed user/strategy directly (need FixtureProvider-backed run).
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    db_session.add(user)
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="WFA",
        pine_source=SIMPLE_PINE,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    period_start = datetime(2024, 1, 1, tzinfo=UTC)
    period_end = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=199)
    backtest = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=period_start,
        period_end=period_end,
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        completed_at=datetime.now(UTC),
    )
    db_session.add(backtest)
    await db_session.flush()

    # OHLCV fixture root — 200 1h bars.
    fixture_root = _make_csv_fixture(tmp_path, n=200)

    service = StressTestService(
        repo=StressTestRepository(db_session),
        backtest_repo=BacktestRepository(db_session),
        strategy_repo=StrategyRepository(db_session),
        ohlcv_provider=FixtureProvider(root=str(fixture_root)),
        dispatcher=FakeStressTaskDispatcher(),
    )

    # QUEUED StressTest — train_bars=100, test_bars=30, max_folds=2 → 2 folds 가능 (100+30=130 ≤ 200, step=30 → 2 folds).
    st = StressTest(
        id=uuid4(),
        user_id=user.id,
        backtest_id=backtest.id,
        kind=StressTestKind.WALK_FORWARD,
        status=StressTestStatus.QUEUED,
        params={
            "train_bars": 100,
            "test_bars": 30,
            "step_bars": 30,
            "max_folds": 2,
        },
    )
    db_session.add(st)
    await db_session.flush()

    # Ensure pandas is happy before run — import guard (unused otherwise).
    _ = pd.Timestamp

    await service.run(st.id)

    repo = StressTestRepository(db_session)
    reloaded = await repo.get_by_id(st.id)
    assert reloaded is not None
    assert reloaded.status == StressTestStatus.COMPLETED, reloaded.error
    assert reloaded.result is not None
    folds = reloaded.result["folds"]
    assert len(folds) >= 1, f"expected ≥1 fold, got {folds}"
    # 필드 sanity
    f0 = folds[0]
    for key in (
        "fold_index",
        "train_start",
        "train_end",
        "test_start",
        "test_end",
        "in_sample_return",
        "out_of_sample_return",
        "num_trades_oos",
    ):
        assert key in f0
    # aggregate 필드
    for key in (
        "aggregate_oos_return",
        "degradation_ratio",
        "valid_positive_regime",
        "total_possible_folds",
        "was_truncated",
    ):
        assert key in reloaded.result
