"""Celery 인스턴스 + @worker_ready stale reclaim hook."""
from __future__ import annotations

import asyncio
import logging

from celery import Celery
from celery.signals import worker_ready

from src.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "quantbridge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks.backtest"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@worker_ready.connect  # type: ignore[untyped-decorator]
def _on_worker_ready(sender: object = None, **_kwargs: object) -> None:
    """Worker 기동 시 stale reclaim 1회 자동 실행 (§8.3).

    @worker_ready는 Celery master 프로세스에서 1회 실행 — prefork 자식마다 아님.
    """
    from src.tasks.backtest import reclaim_stale_running  # 지연 import

    try:
        reclaimed = asyncio.run(reclaim_stale_running())
        if reclaimed:
            logger.info(
                "stale_reclaim_on_startup", extra={"reclaimed_count": reclaimed}
            )
    except Exception:
        logger.exception("stale_reclaim_failed_on_startup")
