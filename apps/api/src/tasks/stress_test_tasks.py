"""run_stress_test_task — Celery prefork-safe Stress Test 실행기.

src.tasks.backtest 패턴을 그대로 따른다:
- 모듈 top-level 에서는 무거운 import (engine, async_session_factory) 금지.
- Sprint 18 BL-080 Option C: run_in_worker_loop 안에서 engine/sessionmaker 매 호출 생성 후 dispose.
"""

from __future__ import annotations

import logging
from uuid import UUID

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# Sprint 18 BL-080 prefork-safe engine factory — `_worker_engine.py` 단일 SSOT.
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="stress_test.run",
    max_retries=0,
    # ★상한의 근거는 임의 값이 아니라 **이미 레포가 선언한 계약**이다 —
    #   `settings.stress_test_stale_threshold_seconds` 가 1800(30분)이고 그 뜻은
    #   「RUNNING stress test 가 30분을 넘으면 stale → FAILED」다. 그런데 그 watchdog 은
    #   **DB 행만 FAILED 로 바꾸고 돌고 있는 태스크는 멈추지 않는다.** 상한이 없으면
    #   원장은 FAILED 인데 워커는 계속 도는 상태가 남는다.
    #   형제 = `optimizer_tasks.py` 의 600/660(+60초) — 같은 간격을 쓴다.
    #   ★stress_test 는 `task_routes` 에 없어 **백테스트와 같은 기본 큐**(backend-worker,
    #   concurrency 2)로 간다. 상한이 없으면 첫 스트레스 테스트가 자기 백테스트 큐를 막는다.
    soft_time_limit=1800,
    time_limit=1860,
)
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


@celery_app.task(name="stress_test.reclaim_stale", max_retries=0)  # type: ignore[untyped-decorator]
def reclaim_stale_running_task() -> int:
    """CF3 (Phase C-1) — Celery Beat 주기 호출용 sync wrapper. backtest.reclaim_stale mirror."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(reclaim_stale_running())


async def reclaim_stale_running() -> int:
    """CF3 — stale RUNNING stress test → FAILED. Engine lifecycle 을 task 에 고정."""
    from datetime import UTC, datetime

    from src.core.config import settings
    from src.stress_test.repository import StressTestRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = StressTestRepository(session)
            reclaimed = await repo.reclaim_stale(
                threshold_seconds=settings.stress_test_stale_threshold_seconds,
                now=datetime.now(UTC),
            )
            await repo.commit()
            return reclaimed
    finally:
        await engine.dispose()
