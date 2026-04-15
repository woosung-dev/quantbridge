"""run_backtest_task + _execute + reclaim_stale_running.

Task 17 범위: Celery task skeleton + reclaim_stale_running.
Task 18에서 _execute()를 실제 BacktestService.run() 호출로 채움.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.backtest.models import _utcnow
from src.backtest.repository import BacktestRepository
from src.core.config import settings
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# Worker-local async session factory (prefork pool 전제).
# 테스트에서는 monkeypatch로 async_sessionmaker_factory를 대체 가능.
_worker_engine = create_async_engine(settings.database_url, echo=False)
async_sessionmaker_factory = async_sessionmaker(_worker_engine, expire_on_commit=False)


@celery_app.task(bind=True, name="backtest.run", max_retries=0)  # type: ignore[untyped-decorator]
def run_backtest_task(self: object, backtest_id: str) -> None:
    """Sync Celery task — asyncio.run() 진입점.

    Worker pool 제약: prefork only (§2.4). gevent/eventlet 비호환.
    """
    asyncio.run(_execute(UUID(backtest_id)))


async def _execute(backtest_id: UUID) -> None:
    """async 실행 본체 — Task 18에서 BacktestService.run() 호출로 채움.

    현재 Task 17: skeleton only. worker 진입 경로 검증용 placeholder.

    Task 18 구현 시 아래 TODO 블록으로 교체:
        from src.backtest.dependencies import build_backtest_service_for_worker
        async with async_sessionmaker_factory() as session:
            service = build_backtest_service_for_worker(session)
            await service.run(backtest_id)
    """
    logger.info(
        "backtest_task_execute_placeholder",
        extra={"backtest_id": str(backtest_id)},
    )
    # TODO Task 18: replace stub with BacktestService.run() call.


async def reclaim_stale_running() -> int:
    """Worker 기동 시 호출. stale running/cancelling → failed/cancelled (§8.3).

    Returns: reclaimed row 총수 (running + cancelling).
    """
    threshold = settings.backtest_stale_threshold_seconds
    async with async_sessionmaker_factory() as session:
        repo = BacktestRepository(session)
        running, cancelling = await repo.reclaim_stale(
            threshold_seconds=threshold,
            now=_utcnow(),
        )
        await repo.commit()
        return running + cancelling
