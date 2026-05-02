"""Celery 인스턴스 + @worker_ready stale reclaim hook + CCXTProvider singleton."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init, worker_ready, worker_shutdown

from src.core.config import settings

if TYPE_CHECKING:
    from src.market_data.providers.ccxt import CCXTProvider

logger = logging.getLogger(__name__)

celery_app = Celery(
    "quantbridge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.tasks.backtest",
        "src.tasks.trading",
        "src.tasks.funding",
        "src.tasks.dogfood_report",
        "src.tasks.stress_test_tasks",
        "src.tasks.websocket_task",
        "src.tasks.orphan_scanner",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Sprint 12 Phase C — long-running ws_stream task 운영 모델 (codex G3 #3).
# - acks_late=True: worker crash 시 ack 안 된 task 가 broker 로 복귀 → re-enqueue 보장.
# - reject_on_worker_lost=True: worker_lost SIGKILL 시 동일.
# - prefetch_multiplier=1: ws_stream worker 가 1 task 만 prefetch (concurrency=1 + 1 task).
#
# Sprint 17 Phase C+ (architectural fix for codex G.0 P1 #2): Celery prefork worker
# 의 같은 child 가 여러 task 처리 시 SQLAlchemy/asyncpg dialect cache 가 stale loop
# 의 Future 보유 → 두 번째 task 부터 RuntimeError("attached to a different loop")
# 또는 InterfaceError. per-call create_worker_engine_and_sm + dispose 만으로 부족.
# worker_max_tasks_per_child=1 로 매 task 마다 child rotate (memory bloat 방어 +
# stale state 완전 정리). 5분 cycle task 빈도라 fork overhead acceptable.
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1,
)

# Sprint 12 Phase C — ws_stream queue routing
celery_app.conf.task_routes = {
    "trading.run_bybit_private_stream": {"queue": "ws_stream"},
}

# Beat schedule — worker 상주 시 주기 task 실행.
celery_app.conf.beat_schedule = {
    "reclaim-stale-backtests": {
        "task": "backtest.reclaim_stale",
        "schedule": 300.0,  # 5분 주기 — startup @worker_ready hook 보완
        "options": {
            # 4분 내 처리 안 되면 폐기 (다음 schedule까지 bursts 방지)
            "expires": 240,
        },
    },
    # Sprint 12 Phase C — ws_stream worker crash 시 자동 re-enqueue (codex G3 #3).
    # 5분 주기로 active ExchangeAccount 중 stream 미동작인 것 enqueue.
    "reconcile-ws-streams": {
        "task": "trading.reconcile_ws_streams",
        "schedule": 300.0,
        "options": {"expires": 240},
    },
    "fetch-funding-rates-btc": {
        "task": "trading.fetch_funding_rates",
        "schedule": 3600.0,  # 매 1시간 (Bybit funding 정산 주기 8h, 여유있게 1h)
        "args": ["bybit", "BTC/USDT:USDT", 2],
        "options": {"expires": 3000},
    },
    "fetch-funding-rates-eth": {
        "task": "trading.fetch_funding_rates",
        "schedule": 3600.0,
        "args": ["bybit", "ETH/USDT:USDT", 2],
        "options": {"expires": 3000},
    },
    "dogfood-daily-report": {
        "task": "reporting.dogfood_daily",
        "schedule": crontab(hour=22, minute=0),  # 매일 22:00 UTC
        "options": {"expires": 3600},
    },
    # Sprint 15 Phase A.3 — stuck order watchdog (BL-001 + BL-002).
    # 30분 이상 pending/submitted 자동 reconcile + throttled alert.
    "scan-stuck-orders": {
        "task": "trading.scan_stuck_orders",
        "schedule": 300.0,  # 5분
        "options": {"expires": 240},
    },
}


@worker_process_init.connect  # type: ignore[untyped-decorator]
def _reset_redis_lock_pool_after_fork(**_kwargs: object) -> None:
    """Celery prefork 자식 프로세스에서 부모의 Redis 연결 FD 폐기 후 재생성.

    Sprint 10 Phase A1 follow-up / Phase A2 wire-up — 분산 락 storage 가 fork 후
    stale connection 을 공유하지 않도록 lazy 재생성 트리거.
    import 시점에 등록되므로 테스트 환경에서 실제 fork 없어도 no-op.
    """
    from src.common.redis_client import reset_redis_lock_pool

    reset_redis_lock_pool()


@worker_ready.connect  # type: ignore[untyped-decorator]
def _on_worker_ready(sender: object = None, **_kwargs: object) -> None:
    """Worker 기동 시 stale reclaim 1회 자동 실행 (§8.3).

    @worker_ready는 Celery master 프로세스에서 1회 실행 — prefork 자식마다 아님.
    """
    from src.tasks.backtest import reclaim_stale_running  # 지연 import

    try:
        reclaimed = asyncio.run(reclaim_stale_running())
        if reclaimed:
            logger.info("stale_reclaim_on_startup", extra={"reclaimed_count": reclaimed})
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
    """Worker 종료 시 CCXTProvider 리소스 해제 + WebSocket stream graceful close."""
    # Sprint 12 Phase C — G4 fix #4: 모든 active ws_stream 의 stop_event set.
    # _stream_main 의 await stop_event.wait() 가 즉시 깨어나 supervisor → ws.close.
    try:
        from src.tasks.websocket_task import signal_all_stop_events

        count = signal_all_stop_events()
        if count > 0:
            logger.info("ws_streams_signaled_on_shutdown count=%d", count)
    except Exception:
        logger.exception("ws_stream_shutdown_signal_failed")

    global _ccxt_provider
    if _ccxt_provider is not None:
        try:
            asyncio.run(_ccxt_provider.close())
        except Exception:
            logger.exception("ccxt_close_failed_on_shutdown")
        finally:
            _ccxt_provider = None
