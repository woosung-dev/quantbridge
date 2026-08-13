"""Sprint 10 Phase A1/A2 — Distributed lock + rate-limit Redis client.

Celery broker(DB 1) / result(DB 2)와 격리된 별도 논리 DB(`REDIS_LOCK_URL`, 기본 DB 3)에
`redis.asyncio.Redis` 풀을 lazy-singleton 으로 노출한다.

- Lazy init: 모듈 import 시점에는 connection 없음. 첫 호출 시 생성.
- Prefork-safe: Celery worker fork 후 자식 프로세스에서 `reset_redis_lock_pool()` 로
  부모 프로세스에서 만들어진 Redis client 폐기 후 재생성 가능 (Celery prefork 모범).
- Healthcheck (Phase A2 upgrade): PING+SET+GET+DEL round-trip. PING 만으로는 OOM+noeviction
  상태 (READ OK but WRITE FAIL) 미감지. 실질 쓰기 가능성 검증.
- Bytes I/O: `decode_responses=False` 라 모든 GET/SET/Lua CAS 인자/반환은 `bytes`. Phase A2 redlock 토큰은 반드시 bytes 로 생성·비교.

Phase A2(redlock.py) / Phase B(rate_limit.py) 가 본 모듈을 import 한다.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from redis.asyncio import Redis

from src.core.config import settings

_LOGGER = logging.getLogger(__name__)
_pool: Redis | None = None


def get_redis_lock_pool() -> Redis:
    """Lazy singleton — 분산 락 + rate-limit 용 Redis client 반환."""
    global _pool
    if _pool is None:
        _pool = Redis.from_url(
            settings.redis_lock_url,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
            retry_on_timeout=True,
            health_check_interval=30,
            decode_responses=False,  # Lua CAS 등 raw bytes 사용
        )
    return _pool


def reset_redis_lock_pool() -> None:
    """Celery prefork 자식 프로세스 / 테스트 격리용 — 기존 풀 폐기.

    실제 connection close 는 호출자가 책임. 본 함수는 module-level 참조만 끊는다.

    Celery 자식 프로세스에서 호출 진입점 예시 (Phase A2 wire-up scope):

        from celery.signals import worker_process_init

        @worker_process_init.connect
        def _reset_redis_after_fork(**_kwargs: object) -> None:
            reset_redis_lock_pool()
    """
    global _pool
    _pool = None


async def healthcheck_redis_lock(app: FastAPI) -> bool:
    """lifespan startup PING+SET+GET+DEL 결합 healthcheck.

    Sprint 10 Phase A2 upgrade: PING 만으로는 OOM+noeviction 상태 (READ OK but WRITE FAIL)
    미감지. SET+GET+DEL round-trip 으로 실질 쓰기 가능성 검증.

    - `get_redis_lock_pool()` 이 ValueError raise 해도 흡수 (invalid URL 방어).
    - `asyncio.wait_for` 3s 하드캡 — hang 시나리오 (READONLY/GIL contention) 방어.
    - 어떤 backend 오류든 degraded 모드로 흡수해 lifespan startup 이 abort 되지 않음.

    probe_key 는 uuid suffix 로 격리 — 다중 instance 동시 startup 시 SET/GET/DEL
    race 로 오진단 방지 (3-way review Opus + Sonnet 2 vote 반영).

    실패 시 `app.state.redis_lock_healthy=False` + WARN 로그 + `qb_redis_lock_pool_healthy=0`.
    """
    import uuid as _uuid

    from src.common.metrics import qb_redis_lock_pool_healthy  # circular import 방지 (lazy)

    healthy = False
    try:
        pool = get_redis_lock_pool()
        # PING — 기본 연결 확인
        await asyncio.wait_for(pool.ping(), timeout=3.0)
        # 각 instance 고유 probe_key — concurrent startup race 봉쇄
        probe_key = f"__qb_healthcheck__:{_uuid.uuid4().hex}".encode()
        probe_value = b"1"
        await asyncio.wait_for(pool.set(probe_key, probe_value, px=3000), timeout=3.0)
        got = await asyncio.wait_for(pool.get(probe_key), timeout=3.0)
        if got != probe_value:
            raise RuntimeError(f"probe roundtrip mismatch: set={probe_value!r} got={got!r}")
        await asyncio.wait_for(pool.delete(probe_key), timeout=3.0)
        healthy = True
    except Exception as exc:  # BLE001
        _LOGGER.warning(
            "redis_lock_pool_ping_failed action_required=true",
            extra={"url": settings.redis_lock_url, "error": str(exc)},
        )
    app.state.redis_lock_healthy = healthy
    qb_redis_lock_pool_healthy.set(1 if healthy else 0)
    if not healthy:
        _LOGGER.warning(
            "redis_lock_pool_degraded action_required=true",
            extra={"url": settings.redis_lock_url},
        )
    return healthy
