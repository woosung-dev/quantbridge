"""run_backtest_task + _execute + reclaim_stale_running.

Task 17 범위: Celery task skeleton + reclaim_stale_running.
Task 18에서 _execute()를 실제 BacktestService.run() 호출로 채움.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backtest.models import _utcnow
from src.backtest.repository import BacktestRepository
from src.core.config import settings
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# Worker-local, lazy-initialized (prefork-safe — master 프로세스에서 생성되지 않음).
_worker_engine = None
_sessionmaker_cache: async_sessionmaker[AsyncSession] | None = None


def async_sessionmaker_factory() -> async_sessionmaker[AsyncSession]:
    """Worker-local async_sessionmaker. Lazy — 첫 호출 시(worker 프로세스 내) engine 생성.

    Prefork 안전성: import 시점에 절대 호출되지 않음. asyncpg pool은 worker 전용.
    테스트에서는 이 함수를 monkeypatch로 대체 가능.
    """
    global _worker_engine, _sessionmaker_cache
    if _sessionmaker_cache is None:
        _worker_engine = create_async_engine(settings.database_url, echo=False)
        _sessionmaker_cache = async_sessionmaker(_worker_engine, expire_on_commit=False)
    return _sessionmaker_cache


@celery_app.task(bind=True, name="backtest.run", max_retries=0)  # type: ignore[untyped-decorator]
def run_backtest_task(self: object, backtest_id: str) -> None:
    """Sync Celery task — asyncio.run() 진입점.

    Worker pool 제약: prefork only (§2.4). gevent/eventlet 비호환.
    """
    asyncio.run(_execute(UUID(backtest_id)))


async def _execute(backtest_id: UUID) -> None:
    """Worker entry — BacktestService.run() 호출."""
    from src.backtest.dependencies import build_backtest_service_for_worker
    sm = async_sessionmaker_factory()
    async with sm() as session:
        service = build_backtest_service_for_worker(session)
        await service.run(backtest_id)


async def reclaim_stale_running() -> int:
    """Worker 기동 시 호출. stale running/cancelling → failed/cancelled (§8.3).

    Returns: reclaimed row 총수 (running + cancelling).
    """
    threshold = settings.backtest_stale_threshold_seconds
    sm = async_sessionmaker_factory()
    async with sm() as session:
        repo = BacktestRepository(session)
        running, cancelling = await repo.reclaim_stale(
            threshold_seconds=threshold,
            now=_utcnow(),
        )
        await repo.commit()
        return running + cancelling
