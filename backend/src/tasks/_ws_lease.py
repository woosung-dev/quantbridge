"""Sprint 24 BL-011 — Redis distributed WebSocket stream lease + heartbeat.

`websocket_task.py` 의 process-level `_PROCESS_ACTIVE_STREAMS` set + threading.Lock
을 Redis distributed lease 로 교체. multi-account 사용자 + prefork (BL-012) 환경에서
동일 account 의 중복 stream 차단.

codex G.0 P1 #1 (Sprint 24): `RedisLock.__aenter__()` 는 `acquired=False` (Redis
장애 / contention) 여도 body 실행 가능 — graceful degrade. 그러나 WS lease 는
correctness fallback 없음 (중복 stream 시 broker side effect 분기 위험). 미획득
시 stream 절대 시작하면 안 됨 — `acquire_ws_lease()` 가 wrap, 미획득 → None 반환.

Heartbeat 정책:
- TTL 60s + extend 20s 마다 (TTL 의 1/3) → 3 heartbeat per cycle (충분한 grace)
- extend 실패 = 다른 owner 가 가져감 / Redis 장애 → loop 종료 + Slack alert (Sprint 24+)
- task lifetime 동안 async CM `__aexit__` 가 lease release 자동 보장 (codex G.0 P1 #2 —
  worker_process_shutdown hook 에 lease 객체 두지 않음)

Reconcile path (BL-012):
- `reconcile_ws_streams` 는 Redis lease key 존재 여부로 active 판단
- `_PROCESS_ACTIVE_STREAMS` snapshot 은 prefork 후 무의미

Sprint 11 Phase E `RedisLock.extend()` API 직접 재사용 (Lua CAS PEXPIRE).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from types import TracebackType

from src.common.redis_client import get_redis_lock_pool
from src.common.redlock import RedisLock

logger = logging.getLogger(__name__)

# TTL 60s 기본. extend 20s 마다 = 3 heartbeat per cycle.
_DEFAULT_TTL_MS = 60_000
_HEARTBEAT_RATIO = 3  # extend interval = TTL / 3


def _lease_key(account_id: str) -> str:
    """단일 source — `reconcile_ws_streams` 와 동일 prefix 공유."""
    return f"ws:lease:{account_id}"


async def acquire_ws_lease(
    account_id: str,
    *,
    ttl_ms: int = _DEFAULT_TTL_MS,
    lost_event: asyncio.Event | None = None,
) -> WsLease | None:
    """Redis distributed lease 획득 시도.

    Args:
        account_id: lease key 식별자
        ttl_ms: lease TTL (default 60s)
        lost_event: heartbeat 실패 (lease lost) 시 set 될 asyncio.Event.
                    None 이면 자동 생성. caller 가 외부에서 wait 하려면 직접 주입.

    Returns:
        WsLease — 획득 성공 (caller 가 async with 로 사용)
        None — Redis 장애 또는 contention (다른 worker 보유). caller 는 stream skip.

    codex G.0 P1 #1 보호: RedisLock 의 graceful degrade (acquired=False) 를
    None 반환으로 변환 → caller 가 stream 시작 안 함 보장.

    codex G.2 P1 #1 (Sprint 24a): heartbeat 실패 시 lost_event.set() → caller 가
    감지 후 stream 종료. lease 만료 후 다른 worker 가 재획득 → 두 stream 활성
    상태를 차단 (split-brain 방지).
    """
    lock = RedisLock(_lease_key(account_id), ttl_ms=ttl_ms)
    acquired = await lock.__aenter__()
    if not acquired:
        # contention / Redis 장애 — release any held state + skip
        with contextlib.suppress(Exception):
            await lock.__aexit__(None, None, None)
        return None
    return WsLease(
        lock, account_id, ttl_ms=ttl_ms, lost_event=lost_event or asyncio.Event()
    )


class WsLease:
    """Active WS stream lease — heartbeat loop + graceful release.

    Async context manager 사용:
        lease = await acquire_ws_lease(account_id)
        if lease is None:
            return {"status": "duplicate"}
        async with lease:
            await _stream_main(...)  # heartbeat 자동 진행
        # __aexit__ 에서 heartbeat cancel + RedisLock release 자동
    """

    __slots__ = ("_account_id", "_heartbeat_task", "_lock", "_lost_event", "_ttl_ms")

    def __init__(
        self,
        lock: RedisLock,
        account_id: str,
        *,
        ttl_ms: int,
        lost_event: asyncio.Event,
    ) -> None:
        self._lock = lock
        self._account_id = account_id
        self._ttl_ms = ttl_ms
        self._lost_event = lost_event
        self._heartbeat_task: asyncio.Task[None] | None = None

    @property
    def lost_event(self) -> asyncio.Event:
        """heartbeat 실패 시 set — caller 가 wait 하여 stream 종료 신호."""
        return self._lost_event

    async def __aenter__(self) -> WsLease:
        """heartbeat task 시작 (TTL 의 1/3 마다 extend)."""
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(), name=f"ws_lease_heartbeat_{self._account_id}"
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """heartbeat cancel + RedisLock release. 모든 종료 경로 (정상/예외/CancelledError) 에서 보장."""
        # 1. heartbeat cancel + drain
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._heartbeat_task
            self._heartbeat_task = None

        # 2. RedisLock release (Lua CAS DEL — token 일치 시에만)
        with contextlib.suppress(Exception):
            await self._lock.__aexit__(exc_type, exc, tb)

    async def _heartbeat_loop(self) -> None:
        """TTL 의 1/3 마다 RedisLock.extend(ttl_ms). extend 실패 시 loop 종료.

        다른 owner 가 lease key 를 가져갔거나 Redis 장애 시 loop 종료. caller
        의 _stream_main 은 stop_event wait 중 — heartbeat 종료 시 별도 신호
        필요 없음 (caller 가 task 결과 await 하지 않으므로). 단 logger.warning
        은 운영 모니터링 신호.
        """
        interval_seconds = self._ttl_ms / _HEARTBEAT_RATIO / 1000.0
        while True:
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                # __aexit__ 에서 cancel — 정상 종료
                raise
            success = await self._lock.extend(self._ttl_ms)
            if not success:
                # token mismatch (다른 owner 가 가져감) 또는 Redis 장애.
                # codex G.2 P1 #1 (Sprint 24a): lost_event.set() → caller 가 감지하여
                # stream 종료. lease 만료 후 다른 worker 재획득 시 split-brain 차단.
                logger.warning(
                    "ws_lease_lost account=%s — lost_event set, caller stream 종료 신호",
                    self._account_id,
                )
                self._lost_event.set()
                return


async def is_lease_active(account_id: str) -> bool:
    """Reconcile path 용 — Redis lease key 존재 여부 (codex P2 #1 fix).

    `_PROCESS_ACTIVE_STREAMS` snapshot 대신 lease key 기반 active 판단.
    prefork 환경에서 process-level snapshot 은 무의미.
    """
    pool = get_redis_lock_pool()
    try:
        result = await pool.exists(_lease_key(account_id))
        return bool(result)
    except Exception as exc:
        logger.warning(
            "ws_lease_exists_check_failed account=%s err=%s — assume active (보수적)",
            account_id,
            exc,
        )
        # Redis 장애 시 보수적으로 active 가정 → reconcile 가 enqueue skip
        return True
