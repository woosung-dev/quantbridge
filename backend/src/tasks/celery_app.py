"""Celery 인스턴스 + @worker_ready stale reclaim hook + CCXTProvider singleton."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from src.core.config import settings

if TYPE_CHECKING:
    from src.market_data.providers.ccxt import CCXTProvider

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


# -----------------------------------------------------------------------------
# CCXTProvider worker singleton (prefork-safe: lazy init per child process)
# -----------------------------------------------------------------------------
_ccxt_provider: CCXTProvider | None = None


def get_ccxt_provider_for_worker() -> CCXTProvider:
    """Worker 자식 프로세스 lazy singleton.

    prefork-safe: 모듈 import 시점이 아닌 task 실행 시점에 생성되어
    fork() 이후 새 프로세스 컨텍스트에서 초기화됨 (D3 교훈).
    """
    global _ccxt_provider
    if _ccxt_provider is None:
        from src.market_data.providers.ccxt import CCXTProvider

        _ccxt_provider = CCXTProvider(exchange_name=settings.default_exchange)
    return _ccxt_provider


@worker_shutdown.connect  # type: ignore[untyped-decorator]
def _on_worker_shutdown(sender: object = None, **_kwargs: object) -> None:
    """Worker 종료 시 CCXTProvider 리소스 해제."""
    global _ccxt_provider
    if _ccxt_provider is not None:
        try:
            asyncio.run(_ccxt_provider.close())
        except Exception:
            logger.exception("ccxt_close_failed_on_shutdown")
        finally:
            _ccxt_provider = None
