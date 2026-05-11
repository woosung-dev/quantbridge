"""Celery 인스턴스 + @worker_ready stale reclaim hook + CCXTProvider singleton."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from celery import Celery
from celery.schedules import crontab
from celery.signals import (
    worker_process_init,
    worker_process_shutdown,  # Sprint 18 BL-080 (codex G.0 P1 #4)
    worker_ready,
    worker_shutdown,
)

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
        "src.tasks.optimizer_tasks",  # Sprint 54 — Phase 3 Optimizer Grid Search
        "src.tasks.websocket_task",
        "src.tasks.orphan_scanner",
        "src.tasks.live_signal",  # Sprint 26 — Pine Signal Auto-Trading
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
# Sprint 18 BL-080 — Option C persistent worker loop. Sprint 17 의
# worker_max_tasks_per_child=1 (child rotate per task) 는 broker prefetch race 로
# 같은 child 가 multi-task 처리 시 한계 있음 + 매 task 마다 fork overhead. Option C
# 가 영속 _WORKER_LOOP 로 stale loop 문제 자체를 제거하므로 child rotate 불필요.
#
# **codex G.2 P2 #1 (Sprint 18) — soak 미검증 보수**: =1000 대신 =250 으로 제한.
# 1h soak gate (RSS slope + asyncpg/Redis fd count) 미수행 상태이므로 conservative.
# Sprint 19 의 soak 결과로 1000 으로 완화 검토.
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=250,
)

# Sprint 12 Phase C — ws_stream queue routing. Sprint 57 BL-237 — optimizer_heavy.
celery_app.conf.task_routes = {
    "trading.run_bybit_private_stream": {"queue": "ws_stream"},
    "optimizer.run": {"queue": "optimizer_heavy"},  # BL-237: dedicated queue
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
    # Sprint 26 — Pine Signal Auto-Trading. 1분 fire, list_active_due 가
    # interval (1m/5m/15m/1h) 별 due session 만 평가.
    "evaluate-live-signals": {
        "task": "live_signal.evaluate_all",
        "schedule": 60.0,
        "options": {"expires": 50},
    },
    # Sprint 26 codex G.2 P1 #10 fix — outbox pending 회수 안전망 (5분 fire).
    # eval task 의 apply_async 가 broker 일시 장애로 유실됐을 때 list_pending() 재enqueue.
    "dispatch-pending-live-signal-events": {
        "task": "live_signal.dispatch_pending",
        "schedule": 300.0,
        "options": {"expires": 240},
    },
}


@worker_process_init.connect  # type: ignore[untyped-decorator]
def _init_worker_state_after_fork(**_kwargs: object) -> None:
    """Celery prefork 자식 프로세스 fork 후 1회 호출.

    Sprint 18 BL-080 (Option C): persistent `_WORKER_LOOP` 생성 — 모든 task 가
    동일 loop 재사용하여 asyncpg connection / Redis pool / CCXT client 의 internal
    transport waiter 가 stale loop 참조 안 함.

    Sprint 10 Phase A1/A2 follow-up: 분산 락 Redis pool 도 fork 후 stale FD 공유
    안 하도록 lazy 재생성 트리거.

    import 시점에 등록되므로 테스트 환경에서 실제 fork 없어도 no-op.
    """
    from src.common.redis_client import reset_redis_lock_pool
    from src.tasks._worker_loop import init_worker_loop

    init_worker_loop()
    reset_redis_lock_pool()


@worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def _shutdown_worker_state_on_child_exit(**_kwargs: object) -> None:
    """Celery prefork 자식 프로세스 shutdown 시 1회 호출 (codex G.0 P1 #4 반영).

    `worker_shutdown` 은 master process / solo pool 만 시그널 — prefork child
    cleanup 에는 부적합 (Sprint 12 의 backend-ws-stream `--pool=solo` 가 동일
    이유로 worker_shutdown 사용). prefork child 의 `_WORKER_LOOP` 정리는 본
    `worker_process_shutdown` hook 에서 처리.

    Sprint 24 BL-012 (codex G.0 P1 #2): prefork 복귀 시 child process 도
    `signal_all_stop_events()` 호출하여 active WS stream 의 stop_event set →
    graceful close. lease release 는 `_run_async()` async CM `__aexit__` 가
    자동 보장 (worker_process_shutdown 에 lease 객체 두지 않음).

    pending task cancel + drain + loop close. drain 중 unhandled exception 이
    발생해도 finally 에서 close 보장 (worker_loop 모듈 안에서 처리).
    """
    # Sprint 24 BL-012: ws_stream graceful shutdown (prefork child 도)
    try:
        from src.tasks.websocket_task import signal_all_stop_events

        signaled = signal_all_stop_events()
        if signaled:
            logger.info("ws_stream_stop_signaled_on_child_exit count=%d", signaled)
    except Exception:
        logger.exception("ws_stream_stop_signal_failed_on_child_exit")

    from src.tasks._worker_loop import shutdown_worker_loop

    shutdown_worker_loop()


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
    """Master process / solo pool worker 종료 시 호출.

    Sprint 12 Phase C — G4 fix #4: 모든 active ws_stream 의 stop_event set.
    _stream_main 의 await stop_event.wait() 가 즉시 깨어나 supervisor → ws.close.

    **Sprint 18 BL-080 (codex G.2 P1 #1 fix — race 회피)**:
    solo pool (backend-ws-stream) 의 경우, ws_stream task 가 본 hook 호출 시점에
    여전히 `_WORKER_LOOP.run_until_complete()` 안에서 실행 중일 수 있다 (`stop_event`
    set 후 graceful unwind 가 진행 중). 그 상태에서 `run_in_worker_loop()` 호출 시
    running-loop guard 가 RuntimeError raise + `shutdown_worker_loop()` 가 running
    loop 에 `run_until_complete` 시도 → fail. 따라서:

    1. signal_all_stop_events() 만 호출 (cross-thread call_soon_threadsafe — 안전).
    2. `_WORKER_LOOP` 가 running 중이면 ccxt close / loop close 모두 SKIP — process
       exit 시 OS 가 정리. stream coroutine 이 BybitPrivateStream.__aexit__ 통해
       자체 cleanup.
    3. running 중이 아니면 (master process / 이미 stream 종료) ccxt close + loop
       shutdown 진행.
    """
    try:
        from src.tasks.websocket_task import signal_all_stop_events

        count = signal_all_stop_events()
        if count > 0:
            logger.info("ws_streams_signaled_on_shutdown count=%d", count)
    except Exception:
        logger.exception("ws_stream_shutdown_signal_failed")

    # codex G.2 P1 #1: running loop 안에서는 cleanup 시도 금지 (race fail).
    from src.tasks import _worker_loop as worker_loop_mod

    worker_loop = worker_loop_mod._WORKER_LOOP
    if worker_loop is not None and worker_loop.is_running():
        logger.info(
            "worker_shutdown_skipped_loop_cleanup_loop_running "
            "(stream task in flight; OS reclaim on process exit)"
        )
        return

    global _ccxt_provider
    if _ccxt_provider is not None:
        try:
            from src.tasks._worker_loop import run_in_worker_loop

            run_in_worker_loop(_ccxt_provider.close())
        except Exception:
            logger.exception("ccxt_close_failed_on_shutdown")
        finally:
            _ccxt_provider = None

    # solo pool / master 모두 idempotent.
    try:
        from src.tasks._worker_loop import shutdown_worker_loop

        shutdown_worker_loop()
    except Exception:
        logger.exception("shutdown_worker_loop_failed_on_master")
