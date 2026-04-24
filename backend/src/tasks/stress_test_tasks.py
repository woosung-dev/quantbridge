"""run_stress_test_task — Celery prefork-safe Stress Test 실행기.

src.tasks.backtest 패턴을 그대로 따른다:
- 모듈 top-level 에서는 무거운 import (vectorbt, engine, async_session_factory) 금지.
- asyncio.run 내부에서 engine/sessionmaker 매 호출 생성 후 dispose.
"""
from __future__ import annotations

import asyncio
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

    asyncpg connection pool은 생성 당시 loop에 bind되므로 전역 캐시 금지.
    테스트에서 monkeypatch 로 공유 세션을 주입할 수 있도록 함수 형태 유지.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm


@celery_app.task(bind=True, name="stress_test.run", max_retries=0)  # type: ignore[untyped-decorator]
def run_stress_test_task(self: object, stress_test_id: str) -> None:
    """Sync Celery task — asyncio.run() 진입점.

    Worker pool: prefork only (D3 교훈).
    """
    asyncio.run(_execute(UUID(stress_test_id)))


async def _execute(stress_test_id: UUID) -> None:
    """Worker entrypoint — StressTestService.run() 호출."""
    # 지연 import (순환 + celery fork 안전)
    from src.stress_test.dependencies import build_stress_test_service_for_worker

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            service = build_stress_test_service_for_worker(session)
            await service.run(stress_test_id)
    finally:
        await engine.dispose()
