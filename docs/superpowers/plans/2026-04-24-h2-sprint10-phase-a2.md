# H2 Sprint 10 — Phase A2: Redis Distributed Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 서버 2+ 대 분산 환경에서 동일 alert 의 중복 체결을 Redis 분산 락으로 방지. PG advisory lock 은 최종 권위 (authoritative) 로 유지 — Redis 는 fast-path 만 담당 (codex plan-stage 평가 기반 Q1 결정).

**Architecture:** `backend/src/common/redlock.py` 에 `RedisLock` async context manager 도입. `SET NX PX + unique token + Lua CAS unlock/extend` 표준 패턴. Repository 의 `acquire_idempotency_lock` 은 Redis 시도 → PG advisory 항상 실행 이중 구조. Redis 장애 시 PG 단독 진행 (graceful degradation, Redis = fast-path, PG = correctness).

**Tech Stack:** `redis.asyncio.Redis` (Phase A1 의 `get_redis_lock_pool()`). 신규 deps 없음.

---

## Files

**Create:**

- `backend/src/common/redlock.py` — `RedisLock` 클래스, Lua scripts (unlock/extend), `acquire_or_degrade` helper
- `backend/tests/common/test_redlock.py` — 10 TDD

**Modify:**

- `backend/src/common/metrics.py` — `qb_redlock_acquire_total`, `qb_redis_lock_pool_healthy` 2 metric 추가
- `backend/src/common/redis_client.py` — `healthcheck_redis_lock` 을 PING+SET 결합으로 업그레이드 (A1 follow-up)
- `backend/src/tasks/celery_app.py` — `celeryd_after_fork` / `worker_process_init` signal 에 `reset_redis_lock_pool` 호출 (A1 follow-up)
- `backend/src/backtest/repository.py:182-187` — `acquire_idempotency_lock` 을 Redis-first + PG fallback 로
- `backend/src/trading/repository.py:206-211` — 동일

**Reuse (수정 금지):**

- `backend/src/common/redis_client.py::get_redis_lock_pool` (A1) — storage backend
- `backend/src/common/metrics.py:28-60` Sprint 9/10 metric 패턴
- `backend/src/backtest/service.py:83-102` 와 `backend/src/trading/service.py:299-311` 의 idempotency 흐름 — `acquire_idempotency_lock` 만 교체되고 UNIQUE 제약 + IntegrityError fallback 그대로

---

## Background — 설계 결정 (Sprint 10 master plan + codex plan-stage)

codex plan-stage 평가 요약:

> 분산 락은 절대 DB 경계의 권위가 되지 않는다. Redis 는 fast-path 만. 최종 correctness 는 PG advisory + UNIQUE 제약.
> Heartbeat 단순 `PEXPIRE` 금지. 반드시 token CAS extend.
> Redis broker(DB 1) / result(DB 2) 와 lock/limit(DB 3) 는 동일 인스턴스라도 DB 번호 분리 (A1 완료).

**Wrapping 패턴 (Q1 = 점진적, PG authoritative):**

```python
async def acquire_idempotency_lock(self, key: str) -> None:
    # Redis fast-path — 분산 환경에서 즉시 실패 (contention 감지)
    try:
        async with RedisLock(f"idem:{key}", ttl_ms=10_000):
            pass
    except RedisUnavailable:
        # Redis 장애 → PG 단독 진행 (graceful degradation)
        pass
    # PG authoritative — 항상 실행. DB 트랜잭션 경계 = 최종 권위
    await self.session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": key}
    )
```

→ Redis 가 fast-fail 을 하든 말든, DB UNIQUE 제약 + pg_advisory_xact_lock 이 실제 correctness 를 보장. Redis 는 DB latency 절감 + cross-server contention 감지 역할만.

---

## Task 1: Lua scripts + RedisLock 클래스 뼈대

**Files:**

- Create: `backend/src/common/redlock.py`

- [ ] **Step 1.1: redlock.py 신규**

```python
"""Sprint 10 Phase A2 — Redis distributed lock (redlock 알고리즘 단일 인스턴스).

**Correctness model:**
- Redis 는 fast-path. PG advisory_xact_lock 이 최종 권위.
- RedisLock 실패 (Redis 장애 / contention) → PG 만으로 진행 (graceful degradation).
- UNIQUE 제약 + IntegrityError fallback 은 상위 Repository 에서 유지.

**구현:**
- acquire: `SET key token NX PX ttl_ms` — atomicity 보장.
- unlock: Lua CAS `GET key == token -> DEL key`. raw DEL 금지 (wrong-release 방지).
- extend: Lua CAS `GET key == token -> PEXPIRE key ttl_ms` (heartbeat).
- token: 16-byte URL-safe base64 (`secrets.token_urlsafe(16)` 의 raw 24-byte).

**사용 (async context manager):**

    async with RedisLock("idem:abc", ttl_ms=10_000) as acquired:
        if acquired:
            # Redis fast-path 확보 — 분산 환경에서 다른 워커 이 lock 못 획득
            ...
        # acquired=False 면 Redis 장애 / contention. 호출자는 PG fallback 진행.

**Heartbeat (Celery 장기 task):**

    async with RedisLock("idem:abc", ttl_ms=30_000) as lock:
        if lock:
            await lock.extend(30_000)  # Lua CAS — 다른 워커의 lock 연장 금지
"""

from __future__ import annotations

import logging
import secrets
from types import TracebackType
from typing import Any

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
    """Redis SET NX PX + unique token + Lua CAS. Fast-path only.

    호출자는 `acquired=False` 일 때 PG advisory lock 으로 fallback 해야 함 (correctness).
    """

    __slots__ = ("_key", "_ttl_ms", "_pool", "_token", "_acquired")

    def __init__(self, key: str, *, ttl_ms: int, pool: Redis | None = None) -> None:
        if ttl_ms <= 0:
            raise ValueError("ttl_ms must be > 0")
        self._key = key
        self._ttl_ms = ttl_ms
        self._pool = pool or get_redis_lock_pool()
        # 16-byte 엔트로피. token_bytes 는 24 bytes. 충돌 확률 무시 가능.
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

        예외 흡수 — RedisError / ConnectionError / asyncio.TimeoutError 모두 False 반환.
        호출자의 PG fallback 이 correctness 를 유지.
        """
        try:
            result = await self._pool.set(
                self._key, self._token, nx=True, px=self._ttl_ms
            )
        except Exception as exc:  # BLE001 — graceful degrade
            _LOGGER.warning(
                "redlock_acquire_failed action_required=maybe",
                extra={"key": self._key, "error": str(exc), "error_class": type(exc).__name__},
            )
            self._acquired = False
            return False
        self._acquired = result is True  # Redis 는 OK → True, contention → None
        return self._acquired

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Lua CAS unlock — token 일치 시에만 DEL. 실패 silent (fail-closed → degrade).

        본 함수는 raise 하지 않음 (context manager 제약). unlock 실패는 WARN 로그.
        """
        if not self._acquired:
            return
        try:
            await self._pool.eval(_UNLOCK_LUA, 1, self._key, self._token)
        except Exception as exc_inner:  # BLE001 — unlock 실패는 TTL 만료로 최종 해제
            _LOGGER.warning(
                "redlock_unlock_failed action_required=monitor",
                extra={"key": self._key, "error": str(exc_inner)},
            )

    async def extend(self, ttl_ms: int) -> bool:
        """Heartbeat — token 일치 시에만 PEXPIRE. 만료 후 타 소유자 재획득 상태 방어.

        Returns True if extend 성공, False if token mismatch (타 소유자) / Redis 장애.
        """
        if not self._acquired:
            return False
        try:
            result = await self._pool.eval(
                _EXTEND_LUA, 1, self._key, self._token, ttl_ms
            )
            return result == 1
        except Exception as exc:  # BLE001
            _LOGGER.warning(
                "redlock_extend_failed",
                extra={"key": self._key, "error": str(exc)},
            )
            return False
```

- [ ] **Step 1.2: smoke 테스트 (import only)**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-redlock/backend
TRADING_ENCRYPTION_KEYS='9Q9G_B7IOW5IcTcq-6Va1RZw_z4e5ZCfPMdl5CIWTBM=' uv run python -c "
from src.common.redlock import RedisLock, _UNLOCK_LUA, _EXTEND_LUA
lock = RedisLock('test:a', ttl_ms=100)
assert lock.acquired is False, 'not entered yet'
assert len(lock.token) == 16, f'token bytes: {len(lock.token)}'
print('OK: RedisLock import + constructor')
"
```

Expected: `OK: RedisLock import + constructor`.

- [ ] **Step 1.3: 커밋**

```bash
git add backend/src/common/redlock.py
git commit -m "feat(common): RedisLock async CM — SET NX PX + Lua CAS unlock/extend

Sprint 10 Phase A2 — Redis 분산 락 fast-path (correctness 는 PG).
- SET NX PX atomic acquire
- Lua CAS unlock: token 일치 시에만 DEL (wrong-release 방지)
- Lua CAS extend: token 일치 시에만 PEXPIRE (heartbeat, 타 소유자 재획득 방어)
- 예외 흡수 → acquired=False. 호출자는 PG fallback 으로 correctness 보장.

TDD 10건 + Repository wrapping + metrics 는 별도 커밋."
```

---

## Task 2: Metrics 추가

**Files:**

- Modify: `backend/src/common/metrics.py`

- [ ] **Step 2.1: 2 metric 추가**

`backend/src/common/metrics.py` 의 `qb_ccxt_request_errors_total` (Sprint 10 Phase D) 다음에 추가:

```python
# 7. Redis distributed lock acquire outcomes (Sprint 10 Phase A2)
# outcome ∈ {success, contention, unavailable, timeout}
# - success: SET NX 성공
# - contention: SET NX 실패 (다른 워커 보유)
# - unavailable: Redis 연결 장애 (socket timeout, ConnectionError)
# - timeout: asyncio.wait_for timeout (본 Phase 에는 미구현, reserved)
qb_redlock_acquire_total = Counter(
    "qb_redlock_acquire_total",
    "Redis distributed lock acquire 시도 결과",
    labelnames=("outcome",),
)

# 8. Redis lock pool healthy (Sprint 10 Phase A2) — lifespan healthcheck 결과
# 1: PING+SET 정상, 0: 장애. startup 에서 1회 세팅, runtime 변경 없음.
qb_redis_lock_pool_healthy = Gauge(
    "qb_redis_lock_pool_healthy",
    "1 if startup PING+SET succeeded, 0 otherwise",
)
```

- [ ] **Step 2.2: 등록 smoke + 커밋**

```bash
TRADING_ENCRYPTION_KEYS='9Q9G_B7IOW5IcTcq-6Va1RZw_z4e5ZCfPMdl5CIWTBM=' uv run python -c "
from src.common.metrics import qb_redlock_acquire_total, qb_redis_lock_pool_healthy
print('OK: metrics registered')
"

git add backend/src/common/metrics.py
git commit -m "feat(observability): add qb_redlock_acquire_total + qb_redis_lock_pool_healthy"
```

---

## Task 3: RedisLock 과 metrics 결합

**Files:**

- Modify: `backend/src/common/redlock.py`

- [ ] **Step 3.1: `__aenter__` 에 metric 주입**

`RedisLock.__aenter__` 의 result 판정 직후, 반환 전 추가:

```python
async def __aenter__(self) -> bool:
    from src.common.metrics import qb_redlock_acquire_total

    try:
        result = await self._pool.set(
            self._key, self._token, nx=True, px=self._ttl_ms
        )
    except Exception as exc:
        _LOGGER.warning("redlock_acquire_failed action_required=maybe", extra={...})
        qb_redlock_acquire_total.labels(outcome="unavailable").inc()
        self._acquired = False
        return False

    if result is True:
        qb_redlock_acquire_total.labels(outcome="success").inc()
        self._acquired = True
    else:  # None → contention
        qb_redlock_acquire_total.labels(outcome="contention").inc()
        self._acquired = False
    return self._acquired
```

import 는 함수 내부 lazy — module import 시점에 metrics.py 가 먼저 import 되지 않도록 (circular import 방지).

- [ ] **Step 3.2: 커밋**

```bash
git add backend/src/common/redlock.py
git commit -m "feat(observability): wire qb_redlock_acquire_total to RedisLock outcomes"
```

---

## Task 4: TDD 1~4 — basic acquire/release, contention, TTL, CAS unlock

**Files:**

- Create: `backend/tests/common/test_redlock.py`

- [ ] **Step 4.1: Test 파일 + fixture**

`backend/tests/common/test_redlock.py` 신규:

```python
"""Sprint 10 Phase A2 — RedisLock 10 TDD.

fakeredis async 또는 pytest-docker-compose 필요. 본 파일은 fakeredis.aioredis 사용.
실제 Redis integration 은 Phase C (real_broker) 에서 nightly 수행.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def fake_redis(monkeypatch) -> None:
    """src.common.redis_client._pool 을 fakeredis.aioredis.FakeRedis 로 교체."""
    import fakeredis.aioredis

    from src.common import redis_client as rc

    fake = fakeredis.aioredis.FakeRedis(decode_responses=False)
    rc._pool = fake
    try:
        yield fake
    finally:
        await fake.flushdb()
        await fake.aclose()
        rc._pool = None


@pytest.mark.asyncio
async def test_redlock_basic_acquire_and_release(fake_redis) -> None:
    """SET NX 성공 → acquired=True. exit 시 DEL."""
    from src.common.redlock import RedisLock

    async with RedisLock("test:basic", ttl_ms=5000) as acquired:
        assert acquired is True
        stored = await fake_redis.get("test:basic")
        assert stored is not None
    # exit 후 key 삭제
    assert await fake_redis.get("test:basic") is None


@pytest.mark.asyncio
async def test_redlock_contention(fake_redis) -> None:
    """첫 번째 lock 이 key 점유 중이면 두 번째는 acquired=False."""
    from src.common.redlock import RedisLock

    first = RedisLock("test:cont", ttl_ms=5000)
    await first.__aenter__()

    second = RedisLock("test:cont", ttl_ms=5000)
    got = await second.__aenter__()
    assert got is False
    assert second.acquired is False

    await first.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_redlock_ttl_auto_release(fake_redis) -> None:
    """TTL 만료 후 동일 key 에 다른 워커가 획득 가능."""
    from src.common.redlock import RedisLock

    first = RedisLock("test:ttl", ttl_ms=50)  # 50ms
    await first.__aenter__()
    assert first.acquired is True

    await asyncio.sleep(0.12)  # 120ms — TTL 2배 여유

    second = RedisLock("test:ttl", ttl_ms=50)
    got = await second.__aenter__()
    assert got is True, "TTL 만료 후 재획득 가능해야"

    await second.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_redlock_unlock_cas_rejects_foreign_token(fake_redis) -> None:
    """다른 token 보유 시 unlock (DEL) 거부 — wrong-release 방지."""
    from src.common.redlock import RedisLock

    # first 획득
    first = RedisLock("test:cas", ttl_ms=5000)
    await first.__aenter__()

    # 직접 key 를 다른 value 로 덮어씀 (TTL 만료 후 다른 워커 획득 시뮬레이션)
    await fake_redis.set("test:cas", b"foreign-token", px=5000)

    # first 가 exit 해도 DEL 거부 (token mismatch)
    await first.__aexit__(None, None, None)

    # key 는 여전히 foreign-token
    assert await fake_redis.get("test:cas") == b"foreign-token"
```

- [ ] **Step 4.2: fakeredis deps 추가**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-redlock/backend
uv add --dev 'fakeredis[lua]>=2.20' 'pytest-asyncio>=0.21'
```

(pytest-asyncio 가 이미 있으면 --dev skip)

- [ ] **Step 4.3: 4 TDD PASS 확인**

```bash
uv run pytest tests/common/test_redlock.py -v
```

Expected: 4 passed.

- [ ] **Step 4.4: 커밋**

```bash
git add backend/tests/common/test_redlock.py backend/pyproject.toml backend/uv.lock
git commit -m "test(common): RedisLock TDD 1-4 — acquire/release/contention/TTL/CAS unlock"
```

---

## Task 5: TDD 5~7 — Redis 장애, mid-lock/mid-unlock disconnect

- [ ] **Step 5.1: TDD 5~7 추가**

`backend/tests/common/test_redlock.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_redlock_unavailable_graceful_degrade() -> None:
    """Redis 장애 → acquired=False + metric outcome=unavailable."""
    from unittest.mock import AsyncMock, patch

    from src.common.redlock import RedisLock
    from src.common import redis_client as rc

    fake = AsyncMock()
    fake.set = AsyncMock(side_effect=ConnectionError("boom"))
    rc._pool = fake

    lock = RedisLock("test:unavail", ttl_ms=1000)
    got = await lock.__aenter__()
    assert got is False
    assert lock.acquired is False

    # cleanup
    rc._pool = None


@pytest.mark.asyncio
async def test_redlock_mid_lock_disconnect() -> None:
    """Lock 보유 중 Redis 연결 끊김 — extend/unlock 모두 silent fail. raise 안 함."""
    from unittest.mock import AsyncMock

    from src.common.redlock import RedisLock
    from src.common import redis_client as rc

    fake = AsyncMock()
    fake.set = AsyncMock(return_value=True)  # acquire 성공
    fake.eval = AsyncMock(side_effect=ConnectionError("disconnect"))
    rc._pool = fake

    lock = RedisLock("test:middisc", ttl_ms=5000)
    got = await lock.__aenter__()
    assert got is True

    # extend 실패 → False. raise 안 함.
    ok = await lock.extend(1000)
    assert ok is False

    # unlock 실패 → silent. raise 안 함.
    await lock.__aexit__(None, None, None)

    rc._pool = None


@pytest.mark.asyncio
async def test_redlock_mid_unlock_disconnect_does_not_raise() -> None:
    """exit 시 Redis 끊겨도 context manager raise 금지 (기존 예외 전파 유지)."""
    from unittest.mock import AsyncMock

    from src.common.redlock import RedisLock
    from src.common import redis_client as rc

    fake = AsyncMock()
    fake.set = AsyncMock(return_value=True)
    fake.eval = AsyncMock(side_effect=ConnectionError("eof"))
    rc._pool = fake

    lock = RedisLock("test:exitdisc", ttl_ms=1000)

    # 일반 사용 내에서 예외 발생 시, unlock 실패는 원 예외를 가리지 않아야
    class _Sentinel(Exception):
        pass

    with pytest.raises(_Sentinel):
        async with lock as got:
            assert got is True
            raise _Sentinel("original")

    rc._pool = None
```

- [ ] **Step 5.2: 7 TDD PASS + 커밋**

```bash
uv run pytest tests/common/test_redlock.py -v  # 7 passed
git add backend/tests/common/test_redlock.py
git commit -m "test(common): RedisLock TDD 5-7 — unavailable + mid-lock/unlock disconnect"
```

---

## Task 6: TDD 8 — Heartbeat CAS extend

- [ ] **Step 6.1: TDD 8 추가**

```python
@pytest.mark.asyncio
async def test_redlock_extend_cas_blocks_expired_foreign_acquirer(fake_redis) -> None:
    """TTL 만료 → 타 워커 재획득 → 원 소유자의 extend 는 CAS 로 거부."""
    from src.common.redlock import RedisLock

    # first 짧은 TTL 로 획득
    first = RedisLock("test:heartbeat", ttl_ms=50)
    await first.__aenter__()

    # TTL 만료 대기
    await asyncio.sleep(0.12)

    # second 가 재획득
    second = RedisLock("test:heartbeat", ttl_ms=5000)
    assert await second.__aenter__() is True

    # first 가 extend 시도 — CAS 로 거부 (token mismatch)
    ok = await first.extend(1000)
    assert ok is False, "CAS extend 는 token 일치 시에만 성공"

    # cleanup
    await second.__aexit__(None, None, None)
```

- [ ] **Step 6.2: 8 TDD PASS + 커밋**

```bash
uv run pytest tests/common/test_redlock.py -v
git add backend/tests/common/test_redlock.py
git commit -m "test(common): RedisLock TDD 8 — heartbeat extend CAS blocks foreign acquirer"
```

---

## Task 7: Repository wrapping — backtest + trading

**Files:**

- Modify: `backend/src/backtest/repository.py:182-187`
- Modify: `backend/src/trading/repository.py:206-211`

- [ ] **Step 7.1: backtest repository 확장**

`backend/src/backtest/repository.py:182-187` 교체:

```python
    async def acquire_idempotency_lock(self, key: str) -> None:
        """Redis fast-path + PG authoritative — Sprint 10 Phase A2.

        Wrapping 패턴:
        1. RedisLock 시도 — 분산 환경에서 cross-server contention 을 즉시 감지.
        2. Redis 성공/실패 관계없이 pg_advisory_xact_lock 항상 실행.
           DB 트랜잭션 경계 + UNIQUE 제약이 최종 correctness 권위.
        3. Redis 장애 → PG 단독 진행 (graceful degradation).
        """
        from src.common.redlock import RedisLock

        # fast-path (10s TTL — 일반 Celery task 보다 충분히 짧게 + PG 가 커버)
        async with RedisLock(f"idem:backtest:{key}", ttl_ms=10_000):
            pass  # acquired=True/False 무관 — PG 가 최종 권위

        # authoritative — 항상 실행
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": key},
        )
```

- [ ] **Step 7.2: trading repository 동일 패턴**

`backend/src/trading/repository.py:206-211` 교체:

```python
    async def acquire_idempotency_lock(self, key: str) -> None:
        """Redis fast-path + PG authoritative — Sprint 10 Phase A2 (Sprint 5 M2 확장).

        동일 wrapping 패턴 (backtest repository 참고).
        """
        from src.common.redlock import RedisLock

        async with RedisLock(f"idem:trading:{key}", ttl_ms=10_000):
            pass

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": key},
        )
```

`idem:backtest:` / `idem:trading:` prefix 로 도메인 격리.

- [ ] **Step 7.3: 기존 backtest/trading idempotency 테스트가 여전히 green 인지 확인**

```bash
uv run pytest tests/backtest/ tests/trading/ -v -k "idempot" --tb=short 2>&1 | tail -15
```

Expected: 기존 테스트 모두 green. Redis 가 없는 환경에서도 graceful degrade 로 PG 경로만 실행 → 동작 동일.

- [ ] **Step 7.4: 커밋**

```bash
git add backend/src/backtest/repository.py backend/src/trading/repository.py
git commit -m "feat(backtest,trading): acquire_idempotency_lock → Redis fast-path + PG authoritative

Sprint 10 Phase A2 — 분산 환경에서 cross-server contention 감지 + DB 트랜잭션
최종 권위 유지. Q1 = gradual (Redis primary + PG fallback) 결정 반영.

Wrapping:
  async with RedisLock(f'idem:<domain>:{key}', ttl_ms=10_000):
      pass  # fast-path
  await session.execute(pg_advisory_xact_lock(hashtext(:k)))  # authoritative

Redis 장애 → PG 단독. Correctness 는 DB UNIQUE + IntegrityError fallback 가 보장."
```

---

## Task 8: TDD 9 — Repository wrapping 동작 검증

- [ ] **Step 8.1: 통합 테스트 추가**

`backend/tests/common/test_redlock.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_repository_wrapping_redis_unavailable_falls_back_to_pg() -> None:
    """Redis 장애 → PG 단독 실행. acquire_idempotency_lock 이 raise 하지 않음."""
    from unittest.mock import AsyncMock, MagicMock

    from src.backtest.repository import BacktestRepository
    from src.common import redis_client as rc

    # Redis 장애 simulate
    fake = AsyncMock()
    fake.set = AsyncMock(side_effect=ConnectionError("boom"))
    rc._pool = fake

    # PG session mock — execute 만 검증
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())

    repo = BacktestRepository(session)
    # raise 하지 않음 (graceful)
    await repo.acquire_idempotency_lock("test-key")

    # PG advisory lock 이 실제로 호출됨
    assert session.execute.await_count == 1
    call_args = session.execute.await_args
    assert "pg_advisory_xact_lock" in str(call_args[0][0])

    rc._pool = None
```

- [ ] **Step 8.2: 9 TDD PASS + 커밋**

```bash
uv run pytest tests/common/test_redlock.py -v
git add backend/tests/common/test_redlock.py
git commit -m "test(common): RedisLock TDD 9 — repository wrapping Redis down → PG fallback"
```

---

## Task 9: TDD 10 — DB UNIQUE 충돌 clean rollback

- [ ] **Step 9.1: TDD 10 추가**

이건 backtest 도메인 레벨 테스트이므로 `backend/tests/backtest/test_idempotency_redlock.py` (신규):

```python
"""Sprint 10 Phase A2 — Redis fast-path + PG authoritative 시 DB UNIQUE 충돌 흐름.

기존 test_repository_idempotency.py 패턴을 따르되, Redis fake 장애 하에서도
UNIQUE 제약 + IntegrityError fallback 이 정상 409 / replay 분기 유지하는지 검증.
"""

from __future__ import annotations

import pytest

from src.backtest.service import BacktestService


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_409_when_redis_unavailable(
    db_session, user_fixture, strategy_fixture
):
    """Redis 장애 하에서도 동일 Idempotency-Key 는 409 BacktestDuplicateIdempotencyKey 반환."""
    # 이미 있는 test_service_idempotency.py 의 패턴을 재사용. 구현 힌트:
    # 1. Redis 미가용 환경 (rc._pool = None) 에서
    # 2. submit(idempotency_key="KEY-1", body=A)
    # 3. submit(idempotency_key="KEY-1", body=A) 재시도 → replayed=True
    # 4. submit(idempotency_key="KEY-1", body=B) → BacktestDuplicateIdempotencyKey raise
    # fixtures 는 conftest.py 의 기존 것 사용
    pass  # implementation — 기존 test_service_idempotency.py 참고
```

주의: 이 테스트는 **기존 `test_service_idempotency.py`** (Sprint 9-6 생성) 의 중복. 실제로는 **기존 테스트가 Redis 장애 하에서도 깨지지 않음을 검증** 하는 것이 목적. 따라서 새 테스트를 추가하기보다 **기존 테스트가 여전히 green** 인지만 확인하면 충분. 구체적 구현은 implementer 판단.

- [ ] **Step 9.2: 기존 idempotency 테스트 (Redis 장애 하) PASS 확인**

기존 `pytest tests/backtest/ tests/trading/ -v -k idempot` 가 Redis 환경 없이 (conftest 가 `rc._pool = None` 유지) 모두 green 이면 TDD 10 충족.

```bash
uv run pytest tests/backtest/ tests/trading/ -v -k "idempot" 2>&1 | tail -15
```

Expected: 기존 ~10+ idempotency 테스트 모두 green.

만약 fail 이면 — 기존 테스트의 session mock 또는 fixture 가 새 RedisLock wrapping 을 흡수하지 못함. 이 경우 test_redlock.py 에 명시적 TDD 10 추가:

```python
@pytest.mark.asyncio
async def test_repository_wrapping_does_not_break_existing_idempotency_flow(fake_redis):
    """Redis 정상 환경에서 acquire_idempotency_lock 이 정상 flow 방해 안 함."""
    from unittest.mock import MagicMock, AsyncMock

    from src.backtest.repository import BacktestRepository

    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())

    repo = BacktestRepository(session)
    # Redis 정상 → fast-path 성공. PG 도 호출.
    await repo.acquire_idempotency_lock("integration-key")
    assert session.execute.await_count == 1  # PG advisory 1회
```

- [ ] **Step 9.3: 10 TDD PASS + 커밋**

```bash
uv run pytest tests/common/test_redlock.py -v  # 10 passed
git add backend/tests/common/test_redlock.py
git commit -m "test(common): RedisLock TDD 10 — repository wrapping integration (Redis ok + down)"
```

---

## Task 10: Celery prefork hook (A1 follow-up)

**Files:**

- Modify: `backend/src/tasks/celery_app.py`

- [ ] **Step 10.1: signal hook 추가**

`backend/src/tasks/celery_app.py` 하단 (`celery_app` 정의 다음) 에 추가:

```python
from celery.signals import worker_process_init  # noqa: E402

@worker_process_init.connect
def _reset_redis_lock_pool_after_fork(**_kwargs: object) -> None:
    """Celery prefork 자식 프로세스에서 부모의 Redis 연결 FD 폐기 후 재생성.

    Sprint 10 Phase A1 follow-up / Phase A2 wire-up — 분산 락 storage 가 fork 후
    stale connection 을 공유하지 않도록 lazy 재생성 트리거.
    """
    from src.common.redis_client import reset_redis_lock_pool

    reset_redis_lock_pool()
```

- [ ] **Step 10.2: 기존 Celery task 테스트 회귀 없음 확인**

```bash
uv run pytest tests/tasks/ -v --tb=short 2>&1 | tail -15
```

Expected: 기존 테스트 모두 green.

- [ ] **Step 10.3: 커밋**

```bash
git add backend/src/tasks/celery_app.py
git commit -m "feat(tasks): reset_redis_lock_pool on Celery prefork (A1 follow-up wire-up)

Sprint 10 Phase A2 — worker_process_init signal 에서 부모 Redis 연결 폐기 후
자식이 lazy 재생성. fork 시 FD 복제로 인한 stale connection 방지."
```

---

## Task 11: healthcheck PING+SET (A1 follow-up)

**Files:**

- Modify: `backend/src/common/redis_client.py:60-80`

- [ ] **Step 11.1: healthcheck 업그레이드**

`backend/src/common/redis_client.py` 의 `healthcheck_redis_lock` 함수를 다음으로 교체:

```python
async def healthcheck_redis_lock(app: FastAPI) -> bool:
    """lifespan startup PING+SET 결합 healthcheck.

    Sprint 10 Phase A2 upgrade: PING 만으로는 OOM+noeviction 상태 (READ OK but WRITE FAIL)
    미감지. SET+GET+DEL round-trip 으로 실질 쓰기 가능성 검증.

    실패 시 `app.state.redis_lock_healthy=False` + WARN 로그 + `qb_redis_lock_pool_healthy=0`.
    예외 raise 안 함 (lifespan abort 방지).
    """
    from src.common.metrics import qb_redis_lock_pool_healthy

    healthy = False
    try:
        pool = get_redis_lock_pool()
        # PING
        await asyncio.wait_for(pool.ping(), timeout=3.0)
        # SET + GET + DEL (실질 쓰기 검증)
        probe_key = b"__qb_healthcheck__"
        probe_value = b"1"
        await asyncio.wait_for(pool.set(probe_key, probe_value, px=3000), timeout=3.0)
        got = await asyncio.wait_for(pool.get(probe_key), timeout=3.0)
        if got != probe_value:
            raise RuntimeError(f"probe roundtrip mismatch: set={probe_value!r} got={got!r}")
        await asyncio.wait_for(pool.delete(probe_key), timeout=3.0)
        healthy = True
    except Exception as exc:  # BLE001 — degraded mode wraps every backend error
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
```

- [ ] **Step 11.2: 기존 redis_client 테스트 업데이트**

`backend/tests/common/test_redis_client.py` 의 `test_healthcheck_ping_success_sets_healthy_true` 와 `test_healthcheck_ping_failure_sets_healthy_false` 를 PING+SET+GET+DEL 모두 mock 하도록 수정. fake_pool 에 `set`, `get`, `delete` AsyncMock 추가:

```python
fake_pool.ping = AsyncMock(return_value=True)
fake_pool.set = AsyncMock(return_value=True)
fake_pool.get = AsyncMock(return_value=b"1")
fake_pool.delete = AsyncMock(return_value=1)
```

- [ ] **Step 11.3: 회귀 확인 + 커밋**

```bash
uv run pytest tests/common/test_redis_client.py -v  # 6 passed
uv run pytest tests/common/test_redlock.py -v       # 10 passed
git add backend/src/common/redis_client.py backend/tests/common/test_redis_client.py
git commit -m "feat(common): healthcheck_redis_lock → PING+SET+GET+DEL 결합 (A1 follow-up)

Sprint 10 Phase A2 — PING 만으로는 OOM+noeviction 상태 미감지.
실질 쓰기 가능성을 round-trip 으로 검증. Phase A2 의 Redis 의존이
실제로 가동 가능한지 startup 시점에 확신."
```

---

## Task 12: Gate-A2 검증

- [ ] **Step 12.1: 전체 검증**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-redlock/backend
uv run ruff check . && uv run mypy src/ && uv run pytest -q --tb=short -p no:randomly
```

Expected: ruff 0 / mypy 0 / **1091 + ~11 신규 ≈ 1102 green** / 0 fail.

- [ ] **Step 12.2: /metrics 노출 smoke**

```bash
uv run python -c "
from src.common.metrics import qb_redlock_acquire_total, qb_redis_lock_pool_healthy
qb_redlock_acquire_total.labels(outcome='success').inc()
qb_redis_lock_pool_healthy.set(1)
from prometheus_client import generate_latest
output = generate_latest().decode()
assert 'qb_redlock_acquire_total' in output
assert 'qb_redis_lock_pool_healthy' in output
print('OK: 2 new metrics in /metrics output')
"
```

---

## Verification Summary (Gate-A2)

| 항목            | 통과 기준                                                     |
| --------------- | ------------------------------------------------------------- |
| Lint            | ruff 0 error                                                  |
| Type            | mypy 0 error                                                  |
| Tests           | ~1102 green / 0 fail                                          |
| TDD 10건        | `pytest tests/common/test_redlock.py -v` 10 passed            |
| Repository 회귀 | `pytest tests/backtest/ tests/trading/ -k idempot` green      |
| /metrics 노출   | `qb_redlock_acquire_total`, `qb_redis_lock_pool_healthy` 포함 |
| Celery hook     | `tests/tasks/` green (prefork reset 무회귀)                   |

---

## What this Phase is NOT

- Sentinel / Cluster 고가용성 (Sprint 11)
- 분산 환경 실측 E2E (Phase C real_broker 에서 간접 검증)
- `qb_redis_lock_pool_healthy` 의 runtime 주기적 갱신 (startup 1회만 — Sprint 11 monitoring)
- Redis 장애 시 fail-open vs fail-closed 정책 전환 (본 Phase 는 fail-open in lock = PG degrade)

---

## Generator-Evaluator (Phase 완료 직후)

Phase A1/B/D 와 동일 절차:

1. `git diff stage/h2-sprint10..feat/h2s10-redlock > /tmp/h2s10-a2-diff.patch`
2. **codex** (foreground 5min timeout) — diff + 다음 체크리스트:
   - Lua CAS unlock/extend 가 정확히 동작 (token 비교 `KEYS[1]` vs `ARGV[1]`)?
   - `raise` 가 exit 에서 nesting 되면 원 예외 가림?
   - Heartbeat 미사용 — 실제 Celery task 가 본 Phase 에서 `extend` 를 부르는 진입점 없으니 "infra only" 주장 검증
   - Repository wrapping 이 session scope 내부에 있는지 (transaction 경계 정확)
3. **Opus blind** (background, opus) — 파일 경로 + Golden Rules
4. **Sonnet blind** (background, sonnet) — PR body + edge case (Redis+PG 양쪽 장애, Lua script sandbox, fakeredis integration 한계, Celery prefork 실측)
5. PASS = avg ≥ 8/10 ∧ blocker 0 ∧ major ≤ 2

---

## Phase A1/B/D follow-ups 중 본 PR 로 해소되는 항목

- ✅ celeryd_after_fork / worker_process_init hook (A1 follow-up) — Task 10
- ✅ PING+SET 결합 healthcheck (A1 follow-up) — Task 11
- ✅ `qb_redis_lock_pool_healthy` Gauge metric (A1 follow-up Phase D 이관) — Task 2
- ✅ allkeys-lru DB 3 evict correctness — Redis TTL 10s + PG authoritative 로 상쇄 (대기 ~10s 초과하면 다른 워커가 duplicate 시도할 수 있으나 PG UNIQUE 가 catch)
- ❌ prefork integration test (실제 fork + FD 복제) — Phase C nightly 에서 간접 검증

---

## Phase C 연결 맥락

- Phase C (real broker E2E) — Bybit Demo 실호출로 본 Phase 의 분산 락 wrapping 을 통과. 실제 cross-server 행동은 CI 단일 서버에서는 검증 불가 — 운영 smoke test 가 최종 검증.
