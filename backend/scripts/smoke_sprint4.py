"""Sprint 4 §10.1 L4 smoke — 3 scenarios.

실행 방법:
    # Terminal 1 — Celery worker 기동
    cd backend
    uv run celery -A src.tasks worker --pool=prefork --concurrency=1 --loglevel=info

    # Terminal 2 — Smoke 스크립트 실행
    cd backend
    uv run python scripts/smoke_sprint4.py [s1|s2|s3]

HTTP/Clerk 우회 (로컬 smoke 목적):
- BacktestService 직접 호출 (dependency injection 대신)
- Celery broker 경로는 실제로 검증
- HTTP 레이어는 이미 368 pytest로 커버됨
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# repo root import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.auth.models import User  # noqa: E402
from src.backtest.dispatcher import CeleryTaskDispatcher  # noqa: E402
from src.backtest.exceptions import TaskDispatchError  # noqa: E402
from src.backtest.models import Backtest, BacktestStatus, _utcnow  # noqa: E402
from src.backtest.repository import BacktestRepository  # noqa: E402
from src.backtest.schemas import CreateBacktestRequest  # noqa: E402
from src.backtest.service import BacktestService  # noqa: E402
from src.core.config import settings  # noqa: E402
from src.market_data.providers.fixture import FixtureProvider  # noqa: E402
from src.strategy.models import ParseStatus, PineVersion, Strategy  # noqa: E402
from src.strategy.repository import StrategyRepository  # noqa: E402


engine = create_async_engine(settings.database_url, echo=False)
SM = async_sessionmaker(engine, expire_on_commit=False)


async def _seed(session) -> tuple[User, Strategy]:
    user = User(
        id=uuid4(),
        clerk_user_id=f"smoke_{uuid4().hex[:8]}",
        email=f"smoke_{uuid4().hex[:8]}@ex.com",
    )
    session.add(user)
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="smoke_ema",
        pine_source=(
            "//@version=5\n"
            'strategy("smoke", overlay=true)\n'
            "fast = ta.ema(close, 10)\n"
            "slow = ta.ema(close, 30)\n"
            "if ta.crossover(fast, slow)\n"
            '    strategy.entry("L", strategy.long)\n'
            "if ta.crossunder(fast, slow)\n"
            '    strategy.close("L")\n'
        ),
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.commit()
    return user, strategy


async def _poll_status(
    backtest_id: UUID, timeout_s: int = 60, target_statuses: set[BacktestStatus] | None = None
) -> BacktestStatus | None:
    terminal = target_statuses or {
        BacktestStatus.COMPLETED,
        BacktestStatus.FAILED,
        BacktestStatus.CANCELLED,
    }
    deadline = time.time() + timeout_s
    last_status: BacktestStatus | None = None
    while time.time() < deadline:
        async with SM() as session:
            repo = BacktestRepository(session)
            bt = await repo.get_by_id(backtest_id)
            if bt is None:
                return None
            last_status = bt.status
            if bt.status in terminal:
                return bt.status
        await asyncio.sleep(0.5)
    return last_status


async def s1_happy() -> bool:
    """S1: Celery worker 기동 상태에서 submit → running → completed/failed."""
    print("[S1] Happy path — submit + worker pickup + terminal")
    async with SM() as session:
        user, strategy = await _seed(session)
        print(f"  seeded user={user.id} strategy={strategy.id}")

        repo = BacktestRepository(session)
        strategy_repo = StrategyRepository(session)
        service = BacktestService(
            repo=repo,
            strategy_repo=strategy_repo,
            ohlcv_provider=FixtureProvider(),
            dispatcher=CeleryTaskDispatcher(),
        )

        request = CreateBacktestRequest(
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 3, 31),
            initial_capital=Decimal("10000"),
        )
        created = await service.submit(request, user_id=user.id)
        print(f"  submit -> 202 backtest_id={created.backtest_id} status={created.status.value}")

    # Poll from a new session to observe worker updates
    final = await _poll_status(created.backtest_id, timeout_s=60)
    ok = final in {BacktestStatus.COMPLETED, BacktestStatus.FAILED}
    marker = "✅" if ok else "❌"
    print(f"  {marker} final status={final}")
    return ok


async def s2_broker_down() -> bool:
    """S2: Redis 중단 상태에서 submit → 503 TaskDispatchError."""
    print("[S2] Broker down — submit -> TaskDispatchError")
    print("  전제: docker stop quantbridge-redis 후 실행할 것")

    async with SM() as session:
        user, strategy = await _seed(session)
        repo = BacktestRepository(session)
        strategy_repo = StrategyRepository(session)
        service = BacktestService(
            repo=repo,
            strategy_repo=strategy_repo,
            ohlcv_provider=FixtureProvider(),
            dispatcher=CeleryTaskDispatcher(),
        )
        request = CreateBacktestRequest(
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 2),
            initial_capital=Decimal("10000"),
        )
        try:
            created = await service.submit(request, user_id=user.id)
            print(f"  ❌ 예상 실패 없이 성공: {created.backtest_id}")
            return False
        except TaskDispatchError as exc:
            print(f"  ✅ TaskDispatchError raised: {exc}")
        except Exception as exc:
            print(f"  ⚠️  다른 예외: {type(exc).__name__}: {exc}")
            return False

    # DB row 미생성 확인 (submit rollback)
    async with SM() as session:
        repo = BacktestRepository(session)
        items, total = await repo.list_by_user(user.id, limit=10, offset=0)
        if total == 0:
            print(f"  ✅ DB row 미생성 (total={total})")
            return True
        else:
            print(f"  ❌ DB row 존재: {total}")
            return False


async def s3_running_cancel() -> bool:
    """S3: submit → worker가 pick up 전후로 cancel → terminal 수렴."""
    print("[S3] Running cancel — submit + cancel + terminal")
    async with SM() as session:
        user, strategy = await _seed(session)
        repo = BacktestRepository(session)
        strategy_repo = StrategyRepository(session)
        service = BacktestService(
            repo=repo,
            strategy_repo=strategy_repo,
            ohlcv_provider=FixtureProvider(),
            dispatcher=CeleryTaskDispatcher(),
        )
        request = CreateBacktestRequest(
            strategy_id=strategy.id,
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 3, 31),
            initial_capital=Decimal("10000"),
        )
        created = await service.submit(request, user_id=user.id)
        print(f"  submit -> {created.backtest_id}")

        # Cancel immediately
        cancel_resp = await service.cancel(created.backtest_id, user_id=user.id)
        print(f"  cancel -> {cancel_resp.status.value}: {cancel_resp.message}")

    # Poll terminal
    final = await _poll_status(
        created.backtest_id,
        timeout_s=30,
        target_statuses={
            BacktestStatus.CANCELLED,
            BacktestStatus.COMPLETED,
            BacktestStatus.FAILED,
        },
    )
    ok = final in {BacktestStatus.CANCELLED, BacktestStatus.COMPLETED}
    marker = "✅" if ok else "❌"
    print(f"  {marker} final status={final} (cancelled 또는 race-loser completed 허용)")
    return ok


async def main() -> int:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"
    results: dict[str, bool] = {}
    if scenario in ("s1", "all"):
        results["s1"] = await s1_happy()
    if scenario in ("s2", "all"):
        results["s2"] = await s2_broker_down()
    if scenario in ("s3", "all"):
        results["s3"] = await s3_running_cancel()

    print("\n=== Summary ===")
    for name, ok in results.items():
        print(f"  {name}: {'✅ PASS' if ok else '❌ FAIL'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
