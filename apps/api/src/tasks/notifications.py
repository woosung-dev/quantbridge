"""send_push_task — 사용자 구독 전부에 웹 푸시 1건 (pwa.md §3.4)."""

from __future__ import annotations

from uuid import UUID

from src.notifications.webpush_client import load_vapid_config
from src.tasks._worker_engine import create_worker_engine_and_sm
from src.tasks.celery_app import celery_app


@celery_app.task(name="notifications.send_push", max_retries=0)  # type: ignore[untyped-decorator]
def send_push_task(user_id: str, payload: dict[str, str]) -> dict[str, int]:
    """재시도 없음 — 실패는 서비스가 로그로만 남긴다(§3.4)."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(send_push(UUID(user_id), payload))


async def send_push(user_id: UUID, payload: dict[str, str]) -> dict[str, int]:
    """Worker entry. VAPID 가 없으면 DB 도 열지 않고 0 을 돌려준다."""
    if load_vapid_config() is None:
        return {"sent": 0, "removed": 0}

    from src.notifications.dependencies import build_push_service_for_worker

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            service = build_push_service_for_worker(session)
            result = await service.send_push(user_id, payload)
            return {"sent": result.sent, "removed": result.removed}
    finally:
        await engine.dispose()
