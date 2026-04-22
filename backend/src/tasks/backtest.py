"""run_backtest_task + _execute + reclaim_stale_running."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backtest.repository import BacktestRepository
from src.core.config import settings
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# Celery prefork 워커는 매 task마다 asyncio.run()으로 새 event loop를 만든다.
# asyncpg connection pool은 생성 당시 loop에 bind되므로, 전역 engine을 캐시해 두면
# 두 번째 task부터 "got Future attached to a different loop" → 이후 pool이 깨져
# "another operation is in progress"가 연쇄된다. 따라서 engine/sessionmaker는
# _execute/reclaim 내부에서 매 호출마다 새로 만들고 dispose한다.
def async_sessionmaker_factory() -> async_sessionmaker[AsyncSession]:
    """매 호출마다 새 engine + async_sessionmaker 반환.

    반환된 sessionmaker의 engine은 호출자가 dispose해야 한다 (아래 헬퍼 사용 권장).
    테스트에서는 이 함수를 monkeypatch로 대체 가능.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, name="backtest.run", max_retries=0)  # type: ignore[untyped-decorator]
def run_backtest_task(self: object, backtest_id: str) -> None:
    """Sync Celery task — asyncio.run() 진입점.

    Worker pool 제약: prefork only (§2.4). gevent/eventlet 비호환.
    """
    asyncio.run(_execute(UUID(backtest_id)))


async def _execute(backtest_id: UUID) -> None:
    """Worker entry — BacktestService.run() 호출. Engine lifecycle을 task에 고정."""
    from src.backtest.dependencies import build_backtest_service_for_worker

    engine = create_async_engine(settings.database_url, echo=False)
    try:
        sm = async_sessionmaker(engine, expire_on_commit=False)
        async with sm() as session:
            service = build_backtest_service_for_worker(session)
            await service.run(backtest_id)
    finally:
        await engine.dispose()


@celery_app.task(name="backtest.reclaim_stale", max_retries=0)  # type: ignore[untyped-decorator]
def reclaim_stale_running_task() -> int:
    """Celery Beat 주기 호출용 sync wrapper."""
    return asyncio.run(reclaim_stale_running())


async def reclaim_stale_running() -> int:
    """stale running/cancelling → failed/cancelled (§8.3). Engine lifecycle을 task에 고정."""
    threshold = settings.backtest_stale_threshold_seconds
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        sm = async_sessionmaker(engine, expire_on_commit=False)
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
