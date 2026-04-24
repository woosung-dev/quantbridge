"""Sprint 10 Phase A1 — Distributed lock + rate-limit Redis client.

Celery broker(DB 1) / result(DB 2)와 격리된 별도 논리 DB(`REDIS_LOCK_URL`, 기본 DB 3)에
`redis.asyncio.Redis` 풀을 lazy-singleton 으로 노출한다.

- Lazy init: 모듈 import 시점에는 connection 없음. 첫 호출 시 생성.
- Prefork-safe: Celery worker fork 후 자식 프로세스에서 `reset_redis_lock_pool()` 로
  부모 프로세스에서 만들어진 Redis client 폐기 후 재생성 가능 (Celery prefork 모범).
- Healthcheck: lifespan startup 에서 1회 PING. 실패 시 degraded 플래그 세팅.
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
    """lifespan startup 1회 PING. 결과를 `app.state.redis_lock_healthy` 에 기록.

    `Redis.from_url()` 자체가 invalid URL 로 ValueError 를 raise 할 수 있어
    pool 생성도 try 안에 포함. PING 자체도 `asyncio.wait_for` 로 3s timeout
    하드캡 적용 — TCP 핸드셰이크는 끝났는데 Redis 가 응답 hang 하는 시나리오
    (READONLY 모드 / GIL contention 등) 에서 lifespan startup 이 무한 대기되지
    않도록. 어떤 backend 오류든 degraded 모드로 흡수해 lifespan startup 이
    abort 되지 않도록 한다 (Beta trust-first 원칙).

    실패 시 WARN 로그 + degraded 모드(False) 진입. 이후 락/limiter 호출자가
    `app.state.redis_lock_healthy` 를 보고 fallback 경로(PG advisory / fail-open)
    선택. 본 healthcheck 자체는 예외를 raise 하지 않는다.
    """
    healthy = False
    try:
        pool = get_redis_lock_pool()
        result = await asyncio.wait_for(pool.ping(), timeout=3.0)
        healthy = bool(result)
    except Exception as exc:  # BLE001 — degraded mode wraps every backend error
        _LOGGER.warning(
            "redis_lock_pool_ping_failed action_required=true",
            extra={"url": settings.redis_lock_url, "error": str(exc)},
        )
    app.state.redis_lock_healthy = healthy
    if not healthy:
        _LOGGER.warning(
            "redis_lock_pool_degraded action_required=true",
            extra={"url": settings.redis_lock_url},
        )
    return healthy
