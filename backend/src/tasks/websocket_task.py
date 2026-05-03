"""Sprint 12 Phase C — Bybit WebSocket stream Celery task + Beat reconcile.

설계 (codex G3 결정):
- ``run_bybit_private_stream(account_id)`` — long-running task. ws_stream queue
  (concurrency=1). asyncio.run() + stop_event 패턴으로 graceful shutdown 가능.
- process-level ``_PROCESS_ACTIVE_STREAMS`` set + threading.Lock — Sprint 12 dogfood
  1-user 가정 (codex G3 #5/#7). Sprint 13+ multi-worker 시 Redis lease 로 교체.
- ``reconcile_ws_streams`` beat task — 5분 주기로 active ExchangeAccount 조회 후
  stream 미동작인 것 자동 re-enqueue (worker crash recovery).
- auth circuit breaker 미구현 (codex G3 #12) — Sprint 13+. BybitAuthError raise →
  Slack alert + Celery task fail. Beat 가 다시 enqueue 시 재시도, 사용자 수동 fix 필요.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.common.alert import send_critical_alert
from src.common.metrics import qb_ws_duplicate_enqueue_total
from src.core.config import get_settings
from src.core.config import settings as _module_settings
from src.tasks.celery_app import celery_app  # noqa: F401 — Celery beat 가 모듈 import

logger = logging.getLogger(__name__)


# Sprint 17 Phase B — Celery prefork worker 의 매 task 마다 asyncio.run() 으로
# 새 event loop 가 생기는데, asyncpg connection pool 은 생성 당시 loop 에 bind
# 되므로 module-level (또는 다른 module 의 uvicorn-only) 캐시된 engine 은 두 번째
# task 부터 RuntimeError("Future attached to a different loop") 또는 InterfaceError
# 로 silent fail. 따라서 backtest.py / funding.py 와 동일하게 매 호출마다 fresh
# engine + finally dispose.
def create_worker_engine_and_sm() -> (
    tuple[AsyncEngine, async_sessionmaker[AsyncSession]]
):
    """매 호출마다 새 engine + async_sessionmaker 튜플 반환.

    호출자는 engine 을 finally 에서 dispose 해야 한다. 테스트는 monkeypatch 로
    공유 세션 + no-op engine 주입 가능.

    Long-running stream (`_stream_main`): engine 1개를 stream lifetime 동안 유지
    + finally dispose. Short beat (`_reconcile_async`): per-call.
    """
    engine = create_async_engine(_module_settings.database_url, echo=False)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sm


# Sprint 24 BL-011: process-local `_PROCESS_ACTIVE_STREAMS` + `_PROCESS_LOCK` 제거.
# Redis distributed lease (`backend/src/tasks/_ws_lease.py:acquire_ws_lease`) 로 교체.
# multi-account / prefork (BL-012) 환경 지원.

# G4 fix #4: stop_event 글로벌 dict — worker_shutdown signal 이 모든 active stream
# 의 stop_event 를 set 하여 graceful shutdown 보장. account_id → (loop, event).
# loop 참조 보관: signal handler 가 다른 thread 에서 실행되므로 set 호출 시
# call_soon_threadsafe 로 task asyncio loop 에 전달.
_STOP_EVENTS: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Event]] = {}
_STOP_EVENTS_LOCK = threading.Lock()


def signal_all_stop_events() -> int:
    """worker_shutdown signal 핸들러에서 호출. 모든 active stream 의 stop_event set.

    return: 신호 보낸 stream 수.
    """
    count = 0
    with _STOP_EVENTS_LOCK:
        snapshot = list(_STOP_EVENTS.items())
    for account_id, (loop, evt) in snapshot:
        try:
            # 다른 thread (Celery shutdown) 에서 asyncio.Event.set 안전 호출.
            loop.call_soon_threadsafe(evt.set)
            count += 1
            logger.info("ws_stream_stop_signaled account=%s", account_id)
        except Exception as exc:
            logger.warning(
                "ws_stream_stop_signal_failed account=%s err=%s", account_id, exc
            )
    return count


# Bybit V5 Private WebSocket endpoint.
# Demo endpoint 는 공식 문서 기준 (https://bybit-exchange.github.io/docs/v5/ws/connect).
_BYBIT_WS_ENDPOINTS: dict[str, str] = {
    "demo": "wss://stream-demo.bybit.com/v5/private",
    "live": "wss://stream.bybit.com/v5/private",
}


@shared_task(  # type: ignore[untyped-decorator]
    name="trading.run_bybit_private_stream",
    queue="ws_stream",
    max_retries=None,
    acks_late=True,
)
def run_bybit_private_stream(account_id: str) -> dict[str, Any]:
    """Bybit Private WebSocket order stream — long-running.

    Sprint 18 BL-080 Option C: run_in_worker_loop 으로 영속 `_WORKER_LOOP` 안에서
    BybitPrivateStream context manager 가 stop_event 까지 대기. SIGTERM 시
    worker_shutdown 시그널이 stop_event set → graceful close.

    Returns:
        {"status": "completed" | "duplicate" | "auth_failed" | "error", ...}
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_run_async(account_id))


async def _run_async(account_id: str) -> dict[str, Any]:
    """Sprint 24 BL-011: Redis distributed lease 기반 중복 진입 차단.

    이전 (Sprint 12): process-local `_PROCESS_ACTIVE_STREAMS` set + threading.Lock.
    `--pool=solo --concurrency=1` dogfood 1-user 가정.
    이후 (Sprint 24): Redis lease (`ws:lease:{account_id}` SET NX PX 60s) +
    heartbeat (20s extend). multi-account / prefork (BL-012) 환경 지원.

    codex G.0 P1 #1: `acquire_ws_lease()` 가 미획득 시 None 반환 — stream
    절대 시작 안 함 (RedisLock 의 graceful degrade 와 격리).
    """
    from src.common.metrics import qb_ws_auth_circuit_total
    from src.tasks._ws_circuit_breaker import is_circuit_open
    from src.tasks._ws_lease import acquire_ws_lease

    # Sprint 24 BL-013: circuit breaker open 시 stream 시작 안 함 (Slack alert 0).
    # `BybitAuthError` 또는 network 3회 누적으로 set 됐을 가능성. TTL 3600s 만료
    # 또는 수동 해제 (`redis-cli DEL`) 후 재개.
    if await is_circuit_open(account_id):
        qb_ws_auth_circuit_total.labels(outcome="skipped").inc()
        logger.info("ws_stream_circuit_open_skip account=%s", account_id)
        return {"status": "circuit_open", "account_id": account_id}

    lease = await acquire_ws_lease(account_id)
    if lease is None:
        # Redis 장애 또는 contention (다른 worker 보유) — duplicate 처리
        qb_ws_duplicate_enqueue_total.inc()
        logger.info("ws_stream_duplicate_skip account=%s", account_id)
        return {"status": "duplicate", "account_id": account_id}

    # async CM `__aexit__` 가 heartbeat cancel + RedisLock release 자동 보장
    # (codex G.0 P1 #2 — worker_process_shutdown hook 에 lease 객체 두지 않음)
    # Sprint 24a codex G.2 P1 #1: lease.lost_event 를 _stream_main 에 전달 →
    # heartbeat 실패 시 stream 종료, split-brain 차단.
    async with lease:
        return await _stream_main(account_id, lease_lost_event=lease.lost_event)


async def _stream_main(
    account_id: str, *, lease_lost_event: asyncio.Event | None = None
) -> dict[str, Any]:
    """실제 stream 실행 — account 조회 + decrypt + WebSocket 진입.

    Sprint 17 Phase B: per-stream engine 1개 + outer try/finally engine.dispose().
    BaseException (CancelledError / KeyboardInterrupt) 까지 dispose 보장.

    Sprint 24a codex G.2 P1 #1: lease_lost_event 가 set 되면 stream 종료 + lease
    release. heartbeat 실패 시 split-brain 차단.
    """
    from src.trading.encryption import EncryptionService
    from src.trading.models import ExchangeAccount, ExchangeName
    from src.trading.websocket import (
        BybitAuthError,
        BybitPrivateStream,
        Reconciler,
        StateHandler,
    )

    settings = get_settings()
    # Sprint 17 Phase B P1 #3 — engine 1개를 stream lifetime 동안 유지하고 모든
    # 종료 경로 (정상 / Exception / CancelledError / KeyboardInterrupt) 에서
    # dispose 보장. try/finally 가 BaseException 류 통과 — Python 공식.
    engine, sm = create_worker_engine_and_sm()
    try:
        # 1. ExchangeAccount fetch + credentials decrypt
        async with sm() as session:
            account_uuid = UUID(account_id)
            account = await session.get(ExchangeAccount, account_uuid)
            if account is None:
                logger.error("ws_stream_account_not_found account=%s", account_id)
                return {"status": "error", "reason": "account_not_found"}
            if account.exchange != ExchangeName.bybit:
                # OKX 는 Sprint 13 (다른 endpoint + signing 방식)
                logger.warning(
                    "ws_stream_unsupported_exchange account=%s exchange=%s",
                    account_id,
                    account.exchange,
                )
                return {"status": "error", "reason": "unsupported_exchange"}

            crypto = EncryptionService(settings.trading_encryption_keys)
            api_key = crypto.decrypt(account.api_key_encrypted)
            api_secret = crypto.decrypt(account.api_secret_encrypted)
            env = account.mode.value  # "demo" | "live"

        endpoint = _BYBIT_WS_ENDPOINTS.get(env, _BYBIT_WS_ENDPOINTS["demo"])

        # 2. Handler / Reconciler 조립 — sm() 가 stream lifetime 동안 새 session 발급.
        handler = StateHandler(session_factory=sm, settings=settings)
        from src.trading.websocket.reconcile_fetcher import BybitReconcileFetcher

        fetcher = BybitReconcileFetcher(account=account, crypto=crypto)
        reconciler: Reconciler | None = Reconciler(
            session_factory=sm, fetcher=fetcher, settings=settings
        )

        stop_event = asyncio.Event()

        # G4 fix #4: 글로벌 dict 등록 → worker_shutdown signal 이 set 가능.
        loop = asyncio.get_running_loop()
        with _STOP_EVENTS_LOCK:
            _STOP_EVENTS[account_id] = (loop, stop_event)

        # 3. WebSocket 진입 + stop_event wait
        try:
            async with BybitPrivateStream(
                endpoint=endpoint,
                api_key=api_key,
                api_secret=api_secret,
                account_id=account_uuid,
                handler=handler,
                reconciler=reconciler,
                stop_event=stop_event,
            ) as stream:
                logger.info(
                    "ws_stream_connected account=%s endpoint=%s reconnect_count=%d",
                    account_id,
                    endpoint,
                    stream.reconnect_count,
                )
                # stop_event (SIGTERM) 또는 lease_lost_event (heartbeat 실패) 중
                # 먼저 set 되는 것까지 대기. Sprint 24a codex G.2 P1 #1 — lease 만료
                # 시 다른 worker 가 acquire 가능 → split-brain 방지 위해 stream 종료.
                if lease_lost_event is None:
                    await stop_event.wait()
                else:
                    waiters = [
                        asyncio.create_task(stop_event.wait()),
                        asyncio.create_task(lease_lost_event.wait()),
                    ]
                    try:
                        await asyncio.wait(
                            waiters, return_when=asyncio.FIRST_COMPLETED
                        )
                    finally:
                        for p in waiters:
                            if not p.done():
                                p.cancel()
                    if lease_lost_event.is_set() and not stop_event.is_set():
                        logger.warning(
                            "ws_stream_lease_lost_terminating account=%s", account_id
                        )
                        return {
                            "status": "lease_lost",
                            "account_id": account_id,
                            "reconnect_count": stream.reconnect_count,
                        }
            return {
                "status": "completed",
                "account_id": account_id,
                "reconnect_count": stream.reconnect_count,
            }
        except BybitAuthError as exc:
            logger.error(
                "ws_stream_auth_failed account=%s err=%s", account_id, exc
            )
            # Sprint 24 BL-013 (codex G.0 P1 #3): BybitAuthError 즉시 circuit breaker.
            # `ws:auth:blocked:{account_id}` SET PX 3_600_000 — 1h Beat 재시도 noise 차단.
            # 운영자 manual fix (API key 회전 / IP whitelist / clock) + `redis-cli DEL` 수동 해제.
            from src.tasks._ws_circuit_breaker import record_auth_failure

            await record_auth_failure(account_id)
            await send_critical_alert(
                settings,
                "Bybit WS Auth Failed",
                f"WebSocket stream auth rejected for account {account_id}. "
                "Check API key validity, IP whitelist, system clock. "
                "Manual credentials update required. "
                "Circuit breaker: 1h block — redis-cli DEL ws:auth:blocked:{account_id} 수동 해제.",
                {"account_id": account_id, "error": str(exc)[:200]},
            )
            return {"status": "auth_failed", "account_id": account_id}
        except TimeoutError as exc:
            # Sprint 24 BL-016 (codex G.0 P1 #4): first-connect timeout (60s) 발생 횟수
            # 만 task layer 에서 카운트 — supervisor 내부 reconnect (1→30s) 손대지 않음.
            # 3회 누적 시 BL-013 circuit breaker 자동 trigger (record_network_failure 가
            # threshold 도달 시 ws:auth:blocked SET).
            from src.tasks._ws_circuit_breaker import record_network_failure

            opened = await record_network_failure(account_id)
            logger.warning(
                "ws_stream_first_connect_timeout account=%s err=%s circuit_opened=%s",
                account_id,
                exc,
                opened,
            )
            return {
                "status": "first_connect_timeout",
                "account_id": account_id,
                "circuit_opened": opened,
            }
        finally:
            # G4 fix #4: 글로벌 dict 에서 제거 — worker_shutdown signal 이후 stale 방지.
            with _STOP_EVENTS_LOCK:
                _STOP_EVENTS.pop(account_id, None)
    finally:
        await engine.dispose()


@shared_task(name="trading.reconcile_ws_streams")  # type: ignore[untyped-decorator]
def reconcile_ws_streams() -> dict[str, Any]:
    """Beat 5분 주기 — active ExchangeAccount 중 stream 미동작인 것 re-enqueue.

    codex G3 #3: long-running task auto-respawn 메커니즘. worker crash/restart
    후 broker 가 task 를 재배달해도 process state 가 휘발됐으니 명시적 enqueue 필요.

    Sprint 18 BL-080: asyncio.run → run_in_worker_loop (Option C).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_reconcile_async())


async def _reconcile_async() -> dict[str, Any]:
    """Sprint 17 Phase B: per-call engine + finally dispose."""
    from sqlalchemy import select

    from src.trading.models import ExchangeAccount, ExchangeName

    enqueued: list[str] = []
    skipped: list[str] = []

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            # Sprint 13+ scope: TradingSession.is_active 또는 별도 ws_enabled 컬럼 검토.
            # 현재는 모든 Bybit demo/live 계정이 stream 대상.
            stmt = select(ExchangeAccount).where(
                ExchangeAccount.exchange == ExchangeName.bybit,  # type: ignore[arg-type]
            )
            accounts = (await session.execute(stmt)).scalars().all()

        # Sprint 24 BL-012 (codex G.0 P2 #1): _PROCESS_ACTIVE_STREAMS snapshot 대신
        # Redis lease key 존재 여부로 active 판단. prefork 환경에서 process-level
        # snapshot 은 무의미 (각 child process 가 별도 set 보유).
        from src.tasks._ws_lease import is_lease_active

        for acc in accounts:
            acc_id_str = str(acc.id)
            if await is_lease_active(acc_id_str):
                skipped.append(acc_id_str)
                continue
            run_bybit_private_stream.delay(acc_id_str)
            enqueued.append(acc_id_str)
            logger.info("ws_stream_reenqueued account=%s", acc_id_str)

        return {
            "enqueued": enqueued,
            "skipped_active": skipped,
            "total": len(accounts),
        }
    finally:
        await engine.dispose()
