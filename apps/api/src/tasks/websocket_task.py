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

from src.common.alert import send_critical_alert
from src.common.metrics import qb_ws_duplicate_enqueue_total
from src.common.metrics_multiproc import _count_safely, record_metric_safely
from src.core.config import get_settings
from src.tasks.celery_app import celery_app  # noqa: F401 — Celery beat 가 모듈 import

logger = logging.getLogger(__name__)


# Sprint 18 BL-080 prefork-safe engine factory — `_worker_engine.py` 단일 SSOT.
# Long-running stream (`_stream_main`): engine 1개 stream lifetime 동안 유지 + finally dispose.
# Short beat (`_reconcile_async`): per-call.
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402

# Sprint 24 BL-011: process-local `_PROCESS_ACTIVE_STREAMS` + `_PROCESS_LOCK` 제거.
# Redis distributed lease (`apps/api/src/tasks/_ws_lease.py:acquire_ws_lease`) 로 교체.
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
            logger.warning("ws_stream_stop_signal_failed account=%s err=%s", account_id, exc)
    return count


# Bybit V5 Private WebSocket endpoint.
# Demo endpoint 는 공식 문서 기준 (https://bybit-exchange.github.io/docs/v5/ws/connect).
_BYBIT_DEMO_WS_ENDPOINT = "wss://stream-demo.bybit.com/v5/private"
_PUBLIC_TICKER_LEASE_ID = "public-ticker"
_PUBLIC_TICKER_REFRESH_S = 60.0


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
        {"status": "completed" | "duplicate" | "auth_failed" | "supervisor_failed"
                   | "first_connect_timeout" | "lease_lost" | "circuit_open" | "error", ...}
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_run_async(account_id))


@shared_task(  # type: ignore[untyped-decorator]
    name="trading.run_bybit_public_ticker_stream",
    queue="ws_stream",
    max_retries=None,
    acks_late=True,
)
def run_bybit_public_ticker_stream() -> dict[str, Any]:
    """활성 라이브 세션 심볼의 Bybit 공개 ticker 스트림을 유지한다."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_run_public_ticker_async())


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
        _count_safely(qb_ws_auth_circuit_total, outcome="skipped")
        logger.info("ws_stream_circuit_open_skip account=%s", account_id)
        return {"status": "circuit_open", "account_id": account_id}

    lease = await acquire_ws_lease(account_id)
    if lease is None:
        # Redis 장애 또는 contention (다른 worker 보유) — duplicate 처리
        record_metric_safely(qb_ws_duplicate_enqueue_total.inc)
        logger.info("ws_stream_duplicate_skip account=%s", account_id)
        return {"status": "duplicate", "account_id": account_id}

    # async CM `__aexit__` 가 heartbeat cancel + RedisLock release 자동 보장
    # (codex G.0 P1 #2 — worker_process_shutdown hook 에 lease 객체 두지 않음)
    # Sprint 24a codex G.2 P1 #1: lease.lost_event 를 _stream_main 에 전달 →
    # heartbeat 실패 시 stream 종료, split-brain 차단.
    async with lease:
        return await _stream_main(account_id, lease_lost_event=lease.lost_event)


async def _run_public_ticker_async() -> dict[str, Any]:
    """public-ticker 단일 lease로 중복 worker 연결을 차단한다."""
    from src.tasks._ws_lease import acquire_ws_lease

    lease = await acquire_ws_lease(_PUBLIC_TICKER_LEASE_ID)
    if lease is None:
        record_metric_safely(qb_ws_duplicate_enqueue_total.inc)
        logger.info("ws_public_ticker_duplicate_skip")
        return {"status": "duplicate"}

    async with lease:
        return await _public_ticker_stream_main(lease_lost_event=lease.lost_event)


async def _list_active_ticker_symbols(sm: Any) -> set[str]:
    """Repository를 통해 활성 세션의 Bybit raw ticker 심볼을 읽는다."""
    from src.market_data.constants import to_bybit_raw_symbol
    from src.trading.repositories.live_signal_session_repository import (
        LiveSignalSessionRepository,
    )

    async with sm() as session:
        symbols = await LiveSignalSessionRepository(session).list_distinct_active_symbols()
    return {to_bybit_raw_symbol(symbol) for symbol in symbols}


async def _public_ticker_stream_main(
    *, lease_lost_event: asyncio.Event | None = None
) -> dict[str, Any]:
    """공개 ticker 연결과 60초 심볼 refresh를 수행한다."""
    from src.trading.websocket.bybit_public_stream import BybitPublicTickerStream

    engine, sm = create_worker_engine_and_sm()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    try:
        symbols = await _list_active_ticker_symbols(sm)
        if not symbols:
            return {"status": "no_symbols"}

        with _STOP_EVENTS_LOCK:
            _STOP_EVENTS[_PUBLIC_TICKER_LEASE_ID] = (loop, stop_event)

        try:
            async with BybitPublicTickerStream(symbols=symbols, stop_event=stop_event) as stream:
                while not stop_event.is_set():
                    waiters = [asyncio.create_task(stop_event.wait())]
                    if lease_lost_event is not None:
                        waiters.append(asyncio.create_task(lease_lost_event.wait()))
                    try:
                        await asyncio.wait_for(
                            asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED),
                            timeout=_PUBLIC_TICKER_REFRESH_S,
                        )
                    except TimeoutError:
                        symbols = await _list_active_ticker_symbols(sm)
                        if not symbols:
                            return {"status": "no_symbols"}
                        await stream.update_symbols(symbols)
                        continue
                    finally:
                        for waiter in waiters:
                            if not waiter.done():
                                waiter.cancel()
                        await asyncio.gather(*waiters, return_exceptions=True)
                    if lease_lost_event is not None and lease_lost_event.is_set():
                        logger.warning("ws_public_ticker_lease_lost_terminating")
                        return {"status": "lease_lost"}
            return {"status": "completed"}
        except TimeoutError as exc:
            from src.tasks._ws_circuit_breaker import record_network_failure

            opened = await record_network_failure(_PUBLIC_TICKER_LEASE_ID)
            logger.warning(
                "ws_public_ticker_first_connect_timeout err=%s circuit_opened=%s",
                exc,
                opened,
            )
            return {"status": "first_connect_timeout", "circuit_opened": opened}
        finally:
            with _STOP_EVENTS_LOCK:
                _STOP_EVENTS.pop(_PUBLIC_TICKER_LEASE_ID, None)
    finally:
        await engine.dispose()


async def _stream_main(
    account_id: str, *, lease_lost_event: asyncio.Event | None = None
) -> dict[str, Any]:
    """실제 stream 실행 — account 조회 + decrypt + WebSocket 진입.

    Sprint 17 Phase B: per-stream engine 1개 + outer try/finally engine.dispose().
    BaseException (CancelledError / KeyboardInterrupt) 까지 dispose 보장.

    Sprint 24a codex G.2 P1 #1: lease_lost_event 가 set 되면 stream 종료 + lease
    release. heartbeat 실패 시 split-brain 차단.
    """
    from src.common.redis_client import get_redis_lock_pool
    from src.trading.encryption import EncryptionService
    from src.trading.product_policy import require_bybit_demo_account
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.websocket_order_event_service import WebSocketOrderEventService
    from src.trading.services.websocket_reconciliation_service import WebSocketReconciliationService
    from src.trading.websocket import (
        BybitAuthError,
        BybitPrivateStream,
        PositionFanoutHandler,
        PrivateTopicRouter,
        Reconciler,
        StateHandler,
    )
    from src.trading.websocket.position_fanout import PositionFanoutTargets

    settings = get_settings()
    # Sprint 17 Phase B P1 #3 — engine 1개를 stream lifetime 동안 유지하고 모든
    # 종료 경로 (정상 / Exception / CancelledError / KeyboardInterrupt) 에서
    # dispose 보장. try/finally 가 BaseException 류 통과 — Python 공식.
    engine, sm = create_worker_engine_and_sm()
    try:
        # 1. ExchangeAccount fetch + credentials decrypt
        async with sm() as session:
            account_uuid = UUID(account_id)
            account = await ExchangeAccountRepository(session).get_by_id(account_uuid)
            if account is None:
                logger.error("ws_stream_account_not_found account=%s", account_id)
                return {"status": "error", "reason": "account_not_found"}
            require_bybit_demo_account(account.exchange, account.mode)

            crypto = EncryptionService(settings.trading_encryption_keys)
            api_key = crypto.decrypt(account.api_key_encrypted)
            api_secret = crypto.decrypt(account.api_secret_encrypted)

        endpoint = _BYBIT_DEMO_WS_ENDPOINT

        # 2. Transport callback 조립. session은 각 callback의 composition 경계에서만 연다.
        async def handle_order_event(event_account_id: UUID, payload: dict[str, Any]) -> None:
            async with sm() as session:
                service = WebSocketOrderEventService(
                    repo=OrderRepository(session),
                    settings=settings,
                    user_id=account.user_id,
                )
                await service.handle_order_event(event_account_id, payload)

        async def load_position_targets(event_account_id: UUID) -> PositionFanoutTargets:
            async with sm() as session:
                sessions = await LiveSignalSessionRepository(session).list_active_by_account(
                    event_account_id
                )
                account_ids = [event_account_id]
                accounts = ExchangeAccountRepository(session)
                try:
                    event_account = await accounts.get_by_id(event_account_id)
                    if event_account is not None and event_account.exchange_uid is not None:
                        for sibling in await accounts.list_by_exchange_uid(
                            event_account.exchange_uid
                        ):
                            if sibling.id != event_account_id:
                                account_ids.append(sibling.id)
                except Exception as exc:
                    logger.warning(
                        "account_position_snapshot_sibling_lookup_failed account=%s err=%s",
                        event_account_id,
                        exc,
                    )
            return PositionFanoutTargets(account_ids=account_ids, sessions=sessions)

        handler = StateHandler(handle_order_event)
        position_handler = PositionFanoutHandler(
            load_position_targets,
            get_redis_lock_pool(),
            str(account.user_id),
            account_uuid,
        )
        message_handler = PrivateTopicRouter(
            account_id=account_uuid,
            state_handler=handler,
            position_handler=position_handler,
        )
        from src.trading.websocket.reconcile_fetcher import BybitReconcileFetcher

        fetcher = BybitReconcileFetcher(account=account, crypto=crypto)

        async def reconcile_stream(reconcile_account_id: UUID) -> None:
            async with sm() as session:
                service = WebSocketReconciliationService(
                    repo=OrderRepository(session),
                    fetcher=fetcher,
                    settings=settings,
                )
                await service.run(account_id=reconcile_account_id)

        reconciler: Reconciler | None = Reconciler(reconcile_stream)

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
                reconciler=reconciler,
                stop_event=stop_event,
                topics=("order", "position"),
                message_handler=message_handler,
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
                        await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
                    finally:
                        for p in waiters:
                            if not p.done():
                                p.cancel()
                    if lease_lost_event.is_set() and not stop_event.is_set():
                        logger.warning("ws_stream_lease_lost_terminating account=%s", account_id)
                        return {
                            "status": "lease_lost",
                            "account_id": account_id,
                            "reconnect_count": stream.reconnect_count,
                        }
            # ★BL-837 — supervisor 가 죽어서 깨어난 것이면 「정상 종료」로 보고하지 마라.
            #   done-callback 이 `stop_event` 를 set 해 위 대기가 풀리므로 lease 는 이미
            #   놓이지만, 여기서 구분하지 않으면 **task 결과가 조용히 거짓말**을 한다.
            #   경보는 `BybitAuthError` 선례와 같은 자리(task 층)에서 낸다 — 스트림 클래스는
            #   `Settings` 를 안 쥐고 알림 책임도 안 진다.
            supervisor_error = stream.supervisor_error
            if supervisor_error is not None:
                logger.error(
                    "ws_stream_supervisor_failed account=%s err=%r",
                    account_id,
                    supervisor_error,
                )
                await send_critical_alert(
                    settings,
                    "Bybit WS Supervisor Crashed",
                    f"Private order stream supervisor died for account {account_id}. "
                    "The lease was released so another worker can take over, and "
                    "`trading.reconcile_ws_streams` (Beat, 5m) re-enqueues the stream. "
                    "Investigate the error below — until it is fixed the stream will "
                    "keep dying on the same path.",
                    {"account_id": account_id, "error": repr(supervisor_error)[:200]},
                )
                return {
                    "status": "supervisor_failed",
                    "account_id": account_id,
                    "reconnect_count": stream.reconnect_count,
                }
            return {
                "status": "completed",
                "account_id": account_id,
                "reconnect_count": stream.reconnect_count,
            }
        except BybitAuthError as exc:
            logger.error("ws_stream_auth_failed account=%s err=%s", account_id, exc)
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
    from src.trading.models import ExchangeName
    from src.trading.product_policy import is_bybit_demo_account
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository

    enqueued: list[str] = []
    skipped: list[str] = []

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            # 현재 제품 범위는 Bybit Demo뿐이다. legacy live 행은 보존하되 stream을 재등록하지 않는다.
            accounts = [
                account
                for account in await ExchangeAccountRepository(session).list_by_exchange(
                    ExchangeName.bybit
                )
                if is_bybit_demo_account(account.exchange, account.mode)
            ]
            active_symbols = await LiveSignalSessionRepository(
                session
            ).list_distinct_active_symbols()

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

        public_ticker = "not_needed"
        if active_symbols:
            if await is_lease_active(_PUBLIC_TICKER_LEASE_ID):
                public_ticker = "skipped_active"
            else:
                run_bybit_public_ticker_stream.delay()
                public_ticker = "enqueued"
                logger.info("ws_public_ticker_reenqueued")

        return {
            "enqueued": enqueued,
            "skipped_active": skipped,
            "total": len(accounts),
            "public_ticker": public_ticker,
        }
    finally:
        await engine.dispose()
