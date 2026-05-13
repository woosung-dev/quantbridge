"""run_backtest_task + _execute + reclaim_stale_running."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from src.backtest.repository import BacktestRepository
from src.common.metrics import qb_backtest_duration_seconds
from src.core.config import settings
from src.tasks._worker_engine import create_worker_engine_and_sm
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="backtest.run", max_retries=0)  # type: ignore[untyped-decorator]
def run_backtest_task(self: object, backtest_id: str) -> None:
    """Sync Celery task — Sprint 18 BL-080 Option C run_in_worker_loop.

    Worker pool 제약: prefork only (§2.4). gevent/eventlet 비호환.

    Sprint 9 Phase D: 실행 시간을 qb_backtest_duration_seconds histogram 에 기록.
    성공/실패 무관하게 finally 에서 1회 observe.
    """
    from src.tasks._worker_loop import run_in_worker_loop

    started = time.monotonic()
    try:
        run_in_worker_loop(_execute(UUID(backtest_id)))
    finally:
        qb_backtest_duration_seconds.observe(time.monotonic() - started)


async def _execute(backtest_id: UUID) -> None:
    """Worker entry — BacktestService.run() 호출. Engine lifecycle을 task에 고정."""
    from src.backtest.dependencies import build_backtest_service_for_worker

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            service = build_backtest_service_for_worker(session)
            await service.run(backtest_id)
    finally:
        await engine.dispose()


@celery_app.task(name="backtest.reclaim_stale", max_retries=0)  # type: ignore[untyped-decorator]
def reclaim_stale_running_task() -> int:
    """Celery Beat 주기 호출용 sync wrapper.

    Sprint 18 BL-080 Option C: run_in_worker_loop. control task 라 Sprint 17
    까지는 정상 동작했지만 일관성 + 향후 회귀 방어 위해 동일 helper 사용.
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(reclaim_stale_running())


async def reclaim_stale_running() -> int:
    """stale running/cancelling → failed/cancelled (§8.3). Engine lifecycle을 task에 고정."""
    threshold = settings.backtest_stale_threshold_seconds
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = BacktestRepository(session)
            running, cancelling = await repo.reclaim_stale(
                threshold_seconds=threshold,
                now=datetime.now(UTC),
            )
            await repo.commit()
            return running + cancelling
    finally:
        await engine.dispose()
