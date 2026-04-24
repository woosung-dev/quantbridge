"""stress_test 통합 테스트 공용 helpers.

DB-seed (User + Strategy + COMPLETED Backtest) + StressTestService 조립.
Fixture provider + FakeStressTaskDispatcher 로 외부 의존 차단.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.serializers import equity_curve_to_jsonb, metrics_to_jsonb
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository
from src.stress_test.dispatcher import FakeStressTaskDispatcher
from src.stress_test.repository import StressTestRepository
from src.stress_test.service import StressTestService

# 결정적 pine — run_backtest 경로에서 "ok" 반환.
SIMPLE_PINE = """//@version=5
strategy("EMA", overlay=true)
fast = ta.ema(close, 5)
slow = ta.ema(close, 20)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("L")
"""


async def seed_user_strategy_backtest(
    session: AsyncSession,
    *,
    backtest_status: BacktestStatus = BacktestStatus.COMPLETED,
    include_equity_curve: bool = True,
) -> tuple[User, Strategy, Backtest]:
    """User + Strategy + Backtest 시드.

    equity_curve 는 단순 선형 증가 (stress_test MC 입력용).
    """
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    session.add(user)
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="SimpleEMA",
        pine_source=SIMPLE_PINE,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()

    period_start = datetime(2024, 1, 1, tzinfo=UTC)
    period_end = datetime(2024, 1, 3, tzinfo=UTC)

    backtest = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=period_start,
        period_end=period_end,
        initial_capital=Decimal("10000"),
        status=backtest_status,
    )
    if backtest_status == BacktestStatus.COMPLETED:
        backtest.completed_at = datetime.now(UTC)
        if include_equity_curve:
            # 결정적 선형 증가 curve — MC snapshot 은 아니지만 유효.
            backtest.equity_curve = _make_equity_curve_jsonb(period_start, bars=30)
            # metrics 는 None 또는 최소값. MC 에선 쓰지 않으므로 간단히.
            backtest.metrics = None
    session.add(backtest)
    await session.flush()
    return user, strategy, backtest


def _make_equity_curve_jsonb(
    start: datetime, bars: int = 30
) -> list[list[str]]:
    """30 bar 선형 증가 curve (value 10000 → 10029). JSONB 직렬화 형식."""
    import pandas as pd

    idx = pd.date_range(start=start, periods=bars, freq="1h", tz="UTC")
    values = [Decimal("10000") + Decimal(i) for i in range(bars)]
    series = pd.Series(values, index=idx)
    return equity_curve_to_jsonb(series)


def make_service(
    session: AsyncSession,
    *,
    dispatcher: FakeStressTaskDispatcher | None = None,
) -> tuple[StressTestService, FakeStressTaskDispatcher]:
    """StressTestService + FakeStressTaskDispatcher 번들.

    FixtureProvider 는 OHLCV 가 실제 사용되는 테스트(WFA worker)에서만 의미 있음.
    Fixture file 미존재 시 exception 발생이므로 WFA worker 테스트는 별도 rig.
    """
    disp = dispatcher or FakeStressTaskDispatcher()
    service = StressTestService(
        repo=StressTestRepository(session),
        backtest_repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root="/dev/null"),  # worker 아닌 submit 경로만 쓰는 테스트
        dispatcher=disp,
    )
    return service, disp


# 간단한 metrics helper (필요 시).
def completed_backtest_metrics() -> dict[str, object]:
    from src.backtest.engine.types import BacktestMetrics

    m = BacktestMetrics(
        total_return=Decimal("0.05"),
        sharpe_ratio=Decimal("1.2"),
        max_drawdown=Decimal("0.03"),
        win_rate=Decimal("0.6"),
        num_trades=10,
    )
    return metrics_to_jsonb(m)


__all__ = [
    "SIMPLE_PINE",
    "completed_backtest_metrics",
    "make_service",
    "seed_user_strategy_backtest",
    "timedelta",
]
