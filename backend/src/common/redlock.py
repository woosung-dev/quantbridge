"""Sprint 10 Phase A2 — Redis distributed lock (redlock 알고리즘 단일 인스턴스).

**Correctness model:**
- Redis 는 fast-path. PG advisory_xact_lock 이 최종 권위.
- RedisLock 실패 (Redis 장애 / contention) → PG 만으로 진행 (graceful degradation).
- UNIQUE 제약 + IntegrityError fallback 은 상위 Repository 에서 유지.

**구현:**
- acquire: `SET key token NX PX ttl_ms` — atomicity 보장.
- unlock: Lua CAS `GET key == token -> DEL key`. raw DEL 금지 (wrong-release 방지).
- extend: Lua CAS `GET key == token -> PEXPIRE key ttl_ms` (heartbeat).
- token: 16-byte secrets.token_bytes(16) — raw bytes, decode_responses=False 환경.

**사용 (async context manager):**

    async with RedisLock("idem:abc", ttl_ms=10_000) as acquired:
        if acquired:
            # Redis fast-path 확보 — 분산 환경에서 다른 워커가 이 lock 못 획득
            ...
        # acquired=False 면 Redis 장애 / contention. 호출자는 PG fallback 진행.

**Heartbeat (Celery 장기 task):**

    lock = RedisLock("idem:abc", ttl_ms=30_000)
    async with lock as acquired:
        if acquired:
            ok = await lock.extend(30_000)  # Lua CAS — 다른 워커의 lock 연장 금지
"""

from __future__ import annotations

import logging
import secrets
from types import TracebackType

from redis.asyncio import Redis

from src.common.redis_client import get_redis_lock_pool

_LOGGER = logging.getLogger(__name__)

# Lua CAS unlock — token 일치 시에만 DEL. raw DEL 시 다른 워커 lock 삭제 위험.
_UNLOCK_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""

# Lua CAS extend — token 일치 시에만 PEXPIRE. 만료 후 타 소유자 재획득 상태에서 extend 거부.
_EXTEND_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("PEXPIRE", KEYS[1], ARGV[2])
else
    return 0
end
"""


class RedisLock:
    """Redis SET NX PX + unique token + Lua CAS. **Fast-path only, NOT a full mutex.**

    **현재 wrapping 패턴 (Phase A2):**

        async with RedisLock(key, ttl_ms=10_000):
            pass  # body 비어 있음
        await session.execute(pg_advisory_xact_lock(...))

    → Redis SET NX 직후 `__aexit__` 가 Lua CAS DEL. Lock hold 시간 ≈ 1 RTT.
       두 워커가 RTT 이상 간격으로 진입하면 둘 다 `acquired=True` 반환.
       **즉 현재 구현은 mutual exclusion 이 아니라 "contention 감지 신호 + metrics 관찰" 역할.**
       실제 correctness 는 이어지는 PG advisory_xact_lock 이 보장.

    **Observability 효과:**
    - `qb_redlock_acquire_total{outcome=contention}` 증가가 multi-server 동시 요청 감지.
    - `qb_redis_lock_pool_healthy` + degraded 로그로 infra 건강 관측.

    **실질 분산 mutex 로 확장하려면 (Follow-up):**
    - Option A: Service-level lock hold — `async with RedisLock(...): await service.submit(...)`
      로 PG tx + INSERT 전체를 Redis lock 안에 둠. Redis 가 1차 mutex, PG 가 2차 권위.
    - Option B: `__aexit__` 을 PG tx commit 이후 on_commit hook 으로 지연.

    **호출자 계약:** `acquired=False` 일 때도 PG fallback 경로로 진행 가능해야 함.
    correctness 는 절대 Redis 단독 의존 금지.

    구현:
    - acquire: `SET key token NX PX ttl_ms` — atomicity 보장
    - unlock: Lua CAS `GET key == token -> DEL key`. raw DEL 금지 (wrong-release)
    - extend: Lua CAS `GET key == token -> PEXPIRE key ttl_ms` (heartbeat 용, 미사용)
    - token: 16-byte `secrets.token_bytes(16)`
    """

    __slots__ = ("_acquired", "_key", "_pool", "_token", "_ttl_ms")

    def __init__(self, key: str, *, ttl_ms: int, pool: Redis | None = None) -> None:
        if ttl_ms <= 0:
            raise ValueError("ttl_ms must be > 0")
        self._key = key
        self._ttl_ms = ttl_ms
        self._pool = pool  # ← lazy: None 이면 __aenter__ 에서 get_redis_lock_pool() 호출
        # 16-byte 엔트로피 — 충돌 확률 무시 가능. decode_responses=False 환경이므로 raw bytes.
        self._token = secrets.token_bytes(16)
        self._acquired = False

    @property
    def acquired(self) -> bool:
        return self._acquired

    @property
    def token(self) -> bytes:
        return self._token

    async def __aenter__(self) -> bool:
        """Redis SET NX PX 시도. 성공 시 True, 장애/contention 시 False.

        pool 획득을 try block 안에 넣어 `Redis.from_url()` 의 ValueError 도
        graceful degrade 로 흡수. REDIS_LOCK_URL malformed 시에도 500 아닌
        PG fallback 경로 유지 (codex Critical 반영).
        """
        from src.common.metrics import qb_redlock_acquire_total  # circular import 방지 (lazy)

        try:
            if self._pool is None:
                self._pool = get_redis_lock_pool()
            result = await self._pool.set(self._key, self._token, nx=True, px=self._ttl_ms)
        except Exception as exc:  # BLE001 — graceful degrade (URL malformed 포함)
            _LOGGER.warning(
                "redlock_acquire_failed action_required=maybe",
                extra={
                    "key": self._key,
                    "error": str(exc),
                    "error_class": type(exc).__name__,
                },
            )
            qb_redlock_acquire_total.labels(outcome="unavailable").inc()
            self._acquired = False
            return False

        if result is True:
            # SET NX 성공 — 분산 lock 획득
            qb_redlock_acquire_total.labels(outcome="success").inc()
            self._acquired = True
        else:
            # result is None → contention (다른 워커가 이미 보유)
            qb_redlock_acquire_total.labels(outcome="contention").inc()
            self._acquired = False
        return self._acquired

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Lua CAS unlock — token 일치 시에만 DEL. 실패 silent (fail-closed → TTL 만료로 최종 해제).

        본 함수는 raise 하지 않음 (context manager 제약). unlock 실패는 WARN 로그.
        None 반환 → 원 예외 전파 결정을 호출자에게 위임.
        """
        if not self._acquired or self._pool is None:
            return
        try:
            # redis-py eval 스텁은 str args 만 선언하지만 bytes 도 동작함 (decode_responses=False)
            await self._pool.eval(_UNLOCK_LUA, 1, self._key, self._token)  # type: ignore[misc,arg-type]
        except Exception as exc_inner:
            _LOGGER.warning(
                "redlock_unlock_failed action_required=monitor",
                extra={"key": self._key, "error": str(exc_inner)},
            )

    async def extend(self, ttl_ms: int) -> bool:
        """Heartbeat — token 일치 시에만 PEXPIRE. 만료 후 타 소유자 재획득 상태 방어.

        Returns True if extend 성공, False if token mismatch (타 소유자) / Redis 장애.
        """
        if not self._acquired or self._pool is None:
            return False
        try:
            # redis-py eval 스텁은 str args 만 선언하지만 bytes/int 도 동작 (decode_responses=False)
            # key/token 은 bytes, ttl_ms 는 int — mypy 스텁 불일치로 ignore
            args: list[str] = [self._key, self._token, ttl_ms]  # type: ignore[list-item]
            result = await self._pool.eval(_EXTEND_LUA, 1, *args)  # type: ignore[misc]
            return bool(result == 1)
        except Exception as exc:
            _LOGGER.warning(
                "redlock_extend_failed",
                extra={"key": self._key, "error": str(exc)},
            )
            return False
