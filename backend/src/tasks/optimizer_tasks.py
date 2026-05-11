"""run_optimization_task — Celery prefork-safe Optimizer 실행기 (Sprint 54 Phase 3).

src.tasks.stress_test_tasks 패턴을 그대로 따른다:
- 모듈 top-level 에서는 무거운 import 금지 (engine / async_session_factory).
- Sprint 18 BL-080 Option C: run_in_worker_loop 안에서 engine/sessionmaker 매 호출 생성 후 dispose.
- backend.md §11.1 — asyncio.run() 금지 (run_in_worker_loop 강제).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def create_worker_engine_and_sm() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """매 호출마다 새 engine + async_sessionmaker 반환.

    asyncpg connection pool 은 생성 당시 loop 에 bind 되므로 전역 캐시 금지.
    테스트에서 monkeypatch 로 공유 세션 주입 가능하도록 함수 형태 유지.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="optimizer.run",
    max_retries=0,
    soft_time_limit=600,  # BL-237: 10분 소프트 상한 (SoftTimeLimitExceeded raise)
    time_limit=660,  # BL-237: 11분 하드 상한 (SIGKILL)
)
def run_optimization_task(self: object, run_id: str) -> None:
    """Sync Celery task — Sprint 18 BL-080 Option C run_in_worker_loop.

    Worker pool: prefork only (D3 교훈).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    run_in_worker_loop(_execute(UUID(run_id)))


async def _execute(run_id: UUID) -> None:
    """Worker entrypoint — OptimizerService.run() 호출."""
    # 지연 import (순환 + celery fork 안전).
    from src.optimizer.dependencies import build_optimizer_service_for_worker

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            service = build_optimizer_service_for_worker(session)
            await service.run(run_id)
    finally:
        await engine.dispose()
