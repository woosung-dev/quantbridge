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


# Process-local active streams. Single Celery worker (concurrency=1) 가정.
# Sprint 13 multi-worker 시 Redis lease + heartbeat 로 교체.
_PROCESS_ACTIVE_STREAMS: set[str] = set()
_PROCESS_LOCK = threading.Lock()

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

    asyncio.run() 안에서 BybitPrivateStream context manager 가 stop_event 까지 대기.
    SIGTERM 시 worker_shutdown 시그널이 stop_event set → graceful close.

    Returns:
        {"status": "completed" | "duplicate" | "auth_failed" | "error", ...}
    """
    return asyncio.run(_run_async(account_id))


async def _run_async(account_id: str) -> dict[str, Any]:
    # codex G3 #5/#6: process-level guard. 중복 진입 시 raise 대신 no-op return.
    with _PROCESS_LOCK:
        if account_id in _PROCESS_ACTIVE_STREAMS:
            qb_ws_duplicate_enqueue_total.inc()
            logger.info("ws_stream_duplicate_skip account=%s", account_id)
            return {"status": "duplicate", "account_id": account_id}
        _PROCESS_ACTIVE_STREAMS.add(account_id)

    try:
        return await _stream_main(account_id)
    finally:
        with _PROCESS_LOCK:
            _PROCESS_ACTIVE_STREAMS.discard(account_id)


async def _stream_main(account_id: str) -> dict[str, Any]:
    """실제 stream 실행 — account 조회 + decrypt + WebSocket 진입.

    Sprint 17 Phase B: per-stream engine 1개 + outer try/finally engine.dispose().
    BaseException (CancelledError / KeyboardInterrupt) 까지 dispose 보장.
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
                # stop_event 까지 무한 대기. SIGTERM 시 worker_shutdown 가 set.
                await stop_event.wait()
            return {
                "status": "completed",
                "account_id": account_id,
                "reconnect_count": stream.reconnect_count,
            }
        except BybitAuthError as exc:
            logger.error(
                "ws_stream_auth_failed account=%s err=%s", account_id, exc
            )
            # codex G3 #12: circuit breaker 미구현 — Slack alert + manual fix.
            await send_critical_alert(
                settings,
                "Bybit WS Auth Failed",
                f"WebSocket stream auth rejected for account {account_id}. "
                "Check API key validity, IP whitelist, system clock. "
                "Manual credentials update required.",
                {"account_id": account_id, "error": str(exc)[:200]},
            )
            return {"status": "auth_failed", "account_id": account_id}
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
    """
    return asyncio.run(_reconcile_async())


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

        with _PROCESS_LOCK:
            active_snapshot = set(_PROCESS_ACTIVE_STREAMS)

        for acc in accounts:
            acc_id_str = str(acc.id)
            if acc_id_str in active_snapshot:
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
