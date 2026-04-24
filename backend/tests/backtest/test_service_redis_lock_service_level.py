"""Sprint 11 Phase E — BacktestService.submit 의 Service-level RedisLock guard.

Phase A2 의 Repository wrapping (1 RTT contention signal only) 을 제거하고
Service layer 에서 `async with RedisLock(...): await self._submit_inner(...)`
로 감싸 real distributed mutex 를 달성했음을 검증.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


@pytest.fixture
async def _backtest_service_fixture(
    db_session: AsyncSession, authed_user: User
) -> tuple[BacktestService, CreateBacktestRequest, User]:
    """Strategy + OHLCV provider stub 주입된 BacktestService."""
    strategy = Strategy(
        user_id=authed_user.id,
        name="phase-e-strategy",
        pine_source="//@version=5\nstrategy('noop')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)

    dispatcher = MagicMock()
    dispatcher.dispatch_backtest = MagicMock(return_value="task-123")
    provider = MagicMock()
    service = BacktestService(
        repo=BacktestRepository(db_session),
        strategy_repo=StrategyRepository(db_session),
        ohlcv_provider=provider,
        dispatcher=dispatcher,
    )
    req = CreateBacktestRequest(
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start="2024-01-01T00:00:00Z",
        period_end="2024-01-07T00:00:00Z",
        initial_capital=Decimal("1000"),
    )
    return service, req, authed_user


@pytest.mark.asyncio
async def test_submit_wraps_redis_lock_when_idempotency_key_present(
    _backtest_service_fixture,
) -> None:
    """idempotency_key 있을 때 RedisLock(key, ttl_ms=30_000) context 에서 실행."""
    service, req, user = _backtest_service_fixture

    acquired_calls: list[tuple[str, int]] = []

    class _SpyLock:
        def __init__(self, key: str, *, ttl_ms: int, pool: object | None = None) -> None:
            acquired_calls.append((key, ttl_ms))

        async def __aenter__(self) -> bool:
            return True

        async def __aexit__(self, *args: object) -> None:
            return None

    # submit 내부 `from src.common.redlock import RedisLock` 는 `sys.modules` 에서 동일
    # 심볼을 꺼내므로 `src.common.redlock` 모듈을 직접 patch.
    with patch("src.common.redlock.RedisLock", _SpyLock):
        await service.submit(req, user_id=user.id, idempotency_key="phase-e-key")

    assert len(acquired_calls) == 1
    assert acquired_calls[0][0] == "idem:backtest:phase-e-key"
    assert acquired_calls[0][1] == 30_000


@pytest.mark.asyncio
async def test_submit_skips_redis_lock_when_no_idempotency_key(
    _backtest_service_fixture,
) -> None:
    """idempotency_key 가 None 이면 RedisLock 감싸지 않음 (optimization)."""
    service, req, user = _backtest_service_fixture

    acquired_calls: list[tuple[str, int]] = []

    class _SpyLock:
        def __init__(self, key: str, *, ttl_ms: int, pool: object | None = None) -> None:
            acquired_calls.append((key, ttl_ms))

        async def __aenter__(self) -> bool:
            return True

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("src.common.redlock.RedisLock", _SpyLock):
        await service.submit(req, user_id=user.id, idempotency_key=None)

    # idempotency_key 없으면 RedisLock 생성 자체를 skip.
    assert len(acquired_calls) == 0


@pytest.mark.asyncio
async def test_submit_redis_unavailable_graceful_degrade_to_pg(
    _backtest_service_fixture,
) -> None:
    """RedisLock.__aenter__ 가 False 반환 (Redis 장애) 해도 submit 정상 완료.
    PG advisory lock 이 최종 권위로 수렴.
    """
    service, req, user = _backtest_service_fixture

    class _UnavailableLock:
        def __init__(self, key: str, *, ttl_ms: int, pool: object | None = None) -> None:
            pass

        async def __aenter__(self) -> bool:
            return False  # Redis 장애 시뮬레이션

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("src.common.redlock.RedisLock", _UnavailableLock):
        resp = await service.submit(req, user_id=user.id, idempotency_key="unavailable-key")

    assert resp.backtest_id is not None
