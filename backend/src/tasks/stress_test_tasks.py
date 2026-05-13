"""run_stress_test_task — Celery prefork-safe Stress Test 실행기.

src.tasks.backtest 패턴을 그대로 따른다:
- 모듈 top-level 에서는 무거운 import (vectorbt, engine, async_session_factory) 금지.
- Sprint 18 BL-080 Option C: run_in_worker_loop 안에서 engine/sessionmaker 매 호출 생성 후 dispose.
"""
from __future__ import annotations

import logging
from uuid import UUID

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# Sprint 18 BL-080 prefork-safe engine factory — `_worker_engine.py` 단일 SSOT.
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402


@celery_app.task(bind=True, name="stress_test.run", max_retries=0)  # type: ignore[untyped-decorator]
def run_stress_test_task(self: object, stress_test_id: str) -> None:
    """Sync Celery task — Sprint 18 BL-080 Option C run_in_worker_loop.

    Worker pool: prefork only (D3 교훈).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    run_in_worker_loop(_execute(UUID(stress_test_id)))


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
