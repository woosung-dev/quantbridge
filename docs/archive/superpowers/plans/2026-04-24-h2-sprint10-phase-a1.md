# H2 Sprint 10 — Phase A1: Redis Client + Topology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase B(rate limit) / Phase A2(Redis distributed lock)가 공유할 `redis.asyncio.Redis` 락 전용 클라이언트(별도 논리 DB 3) + 시작 시 healthcheck를 도입한다.

**Architecture:** Celery broker(`DB 1`) / result backend(`DB 2`)와 분리된 신규 논리 DB(`DB 3`)에 락·rate-limit 전용 풀을 두고, `redis.asyncio.Redis`를 lazy-singleton으로 노출한다. FastAPI lifespan 시작 시 1회 PING으로 healthcheck를 수행하고 실패 시 `app.state.redis_lock_healthy = False`로 degraded 모드 플래그를 세운다. 실제 락/limiter 구현(A2/B)은 본 Phase의 모듈을 단순 import 한다.

**Tech Stack:** `redis>=5.0` (asyncio interface) — `backend/pyproject.toml` 이미 포함. 추가 dependency 없음. pydantic-settings 기존 `Settings` 확장.

---

## Files

**Create:**

- `backend/src/common/redis_client.py` — singleton Redis lock pool + healthcheck helper
- `backend/tests/common/test_redis_client.py` — 4 TDD case

**Modify:**

- `backend/.env.example` — `REDIS_LOCK_URL=redis://localhost:6379/3` 라인 추가
- `backend/src/core/config.py:30-34` — `Settings.redis_lock_url` 필드 추가 (기본값 `redis://redis:6379/3`)
- `backend/src/main.py:44-60` — lifespan에 `healthcheck_redis_lock(app)` 호출 추가

**Reuse (read-only reference):**

- `backend/src/main.py:44-60` lifespan 패턴 (`app.state.ccxt_provider` 동일 컨벤션)
- `backend/src/core/config.py:30-34` Redis URL 선언 패턴

---

## Background — 왜 별도 DB인가

H2 Sprint 10 codex plan-stage 평가:

> Celery broker Redis를 lock/rate-limit와 공용: 트리거는 broker burst, eviction, restart, failover. **최소 별도 DB/connection pool/timeout/circuit-breaker 필요**.

→ broker(DB 1) / result(DB 2)와 격리된 DB 3에 신규 풀. eviction policy / max-memory도 운영에서 별도로 튜닝 가능.

`.env.example` 현 상태 (lines 41-43):

```
REDIS_URL=redis://localhost:6379/0       # 캐시
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

→ DB 3 은 비어 있음. 신규 슬롯 사용.

---

## Task 1: env 추가 + Settings 필드

**Files:**

- Modify: `backend/.env.example` (Redis 섹션 마지막에 1줄 추가)
- Modify: `backend/src/core/config.py:30-34`

- [ ] **Step 1.1: `.env.example` 라인 추가**

`backend/.env.example` 의 Redis 섹션(`# Redis / Celery (Sprint 4+)` 블록) 마지막(라인 43 다음)에 다음 라인 추가:

```bash
REDIS_LOCK_URL=redis://localhost:6379/3                                # [기본값 OK] 분산 락 + rate limit (Sprint 10 A1)
```

- [ ] **Step 1.2: `Settings.redis_lock_url` 필드 추가**

`backend/src/core/config.py:30-34` 의 Redis/Celery 섹션을 다음으로 교체:

```python
    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    redis_lock_url: str = Field(
        default="redis://redis:6379/3",
        description=(
            "분산 락 + slowapi rate-limit storage 전용 Redis URL. "
            "Celery broker(DB 1) / result(DB 2)와 격리된 DB 3 사용. "
            "Sprint 10 Phase A1."
        ),
    )
```

- [ ] **Step 1.3: 기존 테스트 회귀 확인**

```bash
cd backend && uv run pytest tests/common/ tests/core/ -v --no-header 2>&1 | tail -20
```

Expected: 기존 테스트 모두 PASS, `redis_lock_url` 필드 추가만으로 깨지는 테스트 없음.

- [ ] **Step 1.4: lint + mypy**

```bash
cd backend && uv run ruff check src/core/config.py && uv run mypy src/core/config.py
```

Expected: 0 error.

- [ ] **Step 1.5: 커밋 (사용자 승인 후)**

```bash
git add backend/.env.example backend/src/core/config.py
git commit -m "feat(common): add REDIS_LOCK_URL setting for distributed lock pool

H2 Sprint 10 Phase A1 — Redis 분산 락 + slowapi rate-limit 가 공유할 별도 논리 DB(3) 분리.
Celery broker(DB 1)/result(DB 2)와 격리해 broker burst·eviction 으로 lock 유실 방지.
codex plan-stage evaluator 보강 권고 반영."
```

---

## Task 2: Test 1 — singleton 재사용 (RED)

**Files:**

- Create: `backend/tests/common/test_redis_client.py`

- [ ] **Step 2.1: 실패하는 테스트 작성**

`backend/tests/common/test_redis_client.py` 신규:

```python
"""Sprint 10 Phase A1 — Redis lock pool client.

src/common/redis_client.py 의 4 가지 계약:
1. get_redis_lock_pool() singleton 재사용
2. prefork-safe (asyncio.run 다회 호출 안전)
3. healthcheck PING 정상 → True
4. healthcheck PING 실패 → False (timeout/connection error 모두)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_redis_lock_pool_returns_same_singleton() -> None:
    """동일 이벤트 루프에서 두 번 호출 시 동일 인스턴스 반환."""
    from src.common.redis_client import get_redis_lock_pool, reset_redis_lock_pool

    reset_redis_lock_pool()  # 다른 테스트의 singleton 격리
    a = get_redis_lock_pool()
    b = get_redis_lock_pool()
    assert a is b
```

- [ ] **Step 2.2: 실패 확인**

```bash
cd backend && uv run pytest tests/common/test_redis_client.py::test_get_redis_lock_pool_returns_same_singleton -v
```

Expected: `ModuleNotFoundError: No module named 'src.common.redis_client'`.

---

## Task 3: 구현 — singleton (GREEN)

**Files:**

- Create: `backend/src/common/redis_client.py`

- [ ] **Step 3.1: 최소 구현**

`backend/src/common/redis_client.py` 신규:

```python
"""Sprint 10 Phase A1 — Distributed lock + rate-limit Redis client.

Celery broker(DB 1) / result(DB 2)와 격리된 별도 논리 DB(`REDIS_LOCK_URL`, 기본 DB 3)에
`redis.asyncio.Redis` 풀을 lazy-singleton 으로 노출한다.

- Lazy init: 모듈 import 시점에는 connection 없음. 첫 호출 시 생성.
- Prefork-safe: Celery worker fork 후 자식 프로세스에서 `reset_redis_lock_pool()` 로
  부모 프로세스에서 만들어진 Redis client 폐기 후 재생성 가능 (Celery prefork 모범).
- Healthcheck: lifespan startup 에서 1회 PING. 실패 시 degraded 플래그 세팅.

Phase A2(redlock.py) / Phase B(rate_limit.py) 가 본 모듈을 import 한다.
"""

from __future__ import annotations

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
    """
    global _pool
    _pool = None


async def healthcheck_redis_lock(app: FastAPI) -> bool:
    """lifespan startup 1회 PING. 결과를 `app.state.redis_lock_healthy` 에 기록.

    실패 시 WARN 로그 + degraded 모드(False) 진입. 이후 락/limiter 호출자가
    `app.state.redis_lock_healthy` 를 보고 fallback 경로(PG advisory / fail-open)
    선택. 본 healthcheck 자체는 예외를 raise 하지 않는다.
    """
    pool = get_redis_lock_pool()
    try:
        result = await pool.ping()
        healthy = bool(result)
    except Exception as exc:  # noqa: BLE001 — 모든 connection error 흡수
        _LOGGER.warning(
            "redis_lock_pool_ping_failed",
            extra={"url": settings.redis_lock_url, "error": str(exc)},
        )
        healthy = False
    app.state.redis_lock_healthy = healthy
    if not healthy:
        _LOGGER.warning(
            "redis_lock_pool_degraded",
            extra={"url": settings.redis_lock_url},
        )
    return healthy
```

- [ ] **Step 3.2: PASS 확인**

```bash
cd backend && uv run pytest tests/common/test_redis_client.py::test_get_redis_lock_pool_returns_same_singleton -v
```

Expected: 1 passed.

---

## Task 4: Test 2 — prefork 안전 (RED → GREEN)

**Files:**

- Modify: `backend/tests/common/test_redis_client.py`

- [ ] **Step 4.1: 테스트 추가**

`backend/tests/common/test_redis_client.py` 끝에 추가:

```python
def test_reset_pool_clears_singleton() -> None:
    """Celery prefork worker 재진입 시 singleton 초기화 가능."""
    from src.common.redis_client import (
        get_redis_lock_pool,
        reset_redis_lock_pool,
    )

    reset_redis_lock_pool()
    a = get_redis_lock_pool()
    reset_redis_lock_pool()
    b = get_redis_lock_pool()
    assert a is not b, "reset 후 신규 인스턴스가 생성되어야 한다"


def test_get_pool_safe_across_event_loops() -> None:
    """asyncio.run 두 번 호출이 첫 번째 루프 종료 후에도 안전.

    Celery prefork worker (`asyncio.run(_execute(...))`) 가 task 마다
    새 이벤트 루프를 만드는 상황을 시뮬레이션.
    """
    from src.common.redis_client import (
        get_redis_lock_pool,
        reset_redis_lock_pool,
    )

    async def _touch() -> int:
        pool = get_redis_lock_pool()
        return id(pool)

    reset_redis_lock_pool()
    first = asyncio.run(_touch())

    # 새 task 시작 시 자식 프로세스라면 reset 후 진입.
    reset_redis_lock_pool()
    second = asyncio.run(_touch())

    assert first != second  # 다른 instance — close timing 무관 무문제
```

- [ ] **Step 4.2: 실행 → 모두 PASS 확인**

```bash
cd backend && uv run pytest tests/common/test_redis_client.py -v
```

Expected: 3 passed (Task 2 + Task 4 두 케이스 누적).

---

## Task 5: Test 3+4 — healthcheck PING (RED)

**Files:**

- Modify: `backend/tests/common/test_redis_client.py`

- [ ] **Step 5.1: PING 정상 / 실패 케이스 추가**

`backend/tests/common/test_redis_client.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_healthcheck_ping_success_sets_healthy_true() -> None:
    """PING 정상 응답 → app.state.redis_lock_healthy = True."""
    from src.common.redis_client import (
        healthcheck_redis_lock,
        reset_redis_lock_pool,
    )

    reset_redis_lock_pool()

    fake_pool = AsyncMock()
    fake_pool.ping = AsyncMock(return_value=True)

    fake_app = type("FakeApp", (), {"state": type("State", (), {})()})()

    with patch(
        "src.common.redis_client.get_redis_lock_pool",
        return_value=fake_pool,
    ):
        result = await healthcheck_redis_lock(fake_app)

    assert result is True
    assert fake_app.state.redis_lock_healthy is True
    fake_pool.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_healthcheck_ping_failure_sets_healthy_false() -> None:
    """connection error → degraded 플래그 + 예외 raise 안 함."""
    from src.common.redis_client import (
        healthcheck_redis_lock,
        reset_redis_lock_pool,
    )

    reset_redis_lock_pool()

    fake_pool = AsyncMock()
    fake_pool.ping = AsyncMock(side_effect=ConnectionError("boom"))

    fake_app = type("FakeApp", (), {"state": type("State", (), {})()})()

    with patch(
        "src.common.redis_client.get_redis_lock_pool",
        return_value=fake_pool,
    ):
        result = await healthcheck_redis_lock(fake_app)

    assert result is False
    assert fake_app.state.redis_lock_healthy is False
```

- [ ] **Step 5.2: 실행 → 4 case 모두 PASS 확인**

```bash
cd backend && uv run pytest tests/common/test_redis_client.py -v
```

Expected: 5 passed (singleton 1 + reset 1 + cross-loop 1 + ping success 1 + ping failure 1).

> 구현은 Task 3 의 `healthcheck_redis_lock` 으로 이미 커버됨. 별도 코드 변경 없음.

---

## Task 6: lifespan 통합

**Files:**

- Modify: `backend/src/main.py:44-60`

- [ ] **Step 6.1: lifespan 수정**

`backend/src/main.py:44-60` 의 `lifespan` 함수를 다음으로 교체:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown 자원 라이프사이클.

    - CCXTProvider singleton (ohlcv_provider=timescale 일 때만)
    - Redis lock pool healthcheck (Sprint 10 A1) — 실패 시 degraded 모드
    """
    if settings.ohlcv_provider == "timescale":
        from src.market_data.providers.ccxt import CCXTProvider

        app.state.ccxt_provider = CCXTProvider(
            exchange_name=settings.default_exchange
        )
    else:
        app.state.ccxt_provider = None

    from src.common.redis_client import healthcheck_redis_lock

    await healthcheck_redis_lock(app)

    yield

    if getattr(app.state, "ccxt_provider", None) is not None:
        await app.state.ccxt_provider.close()
```

- [ ] **Step 6.2: 통합 smoke**

```bash
cd backend && uv run pytest tests/ -v -x --tb=short 2>&1 | tail -30
```

Expected:

- BE 1074 + 신규 5 = 1079 passed (혹은 그 이상; 0 fail)
- redis_lock_pool ping 실패해도 lifespan 이 yield 까지 도달 (테스트 환경에서 Redis container 없으면 WARN 로그 + degraded 진입, 그러나 startup 자체 성공)

- [ ] **Step 6.3: 수동 smoke (선택)**

`docker compose up -d redis` 한 상태에서:

```bash
cd backend && uv run uvicorn src.main:app --reload --port 8000 &
sleep 3
curl -s http://localhost:8000/health
# 종료
kill %1
```

Expected: `{"status":"ok","env":"development"}` + 백그라운드 로그에서 `redis_lock_pool_ping_failed` 가 **없어야** 함 (Redis 가 떠 있으면).

Redis 가 꺼진 환경에서는 `redis_lock_pool_ping_failed` WARN 로그가 1회 떠야 함 (정상 degraded 동작).

---

## Task 7: Gate-A1 검증 + 커밋

- [ ] **Step 7.1: 전체 verification**

```bash
cd backend && uv run ruff check . && uv run mypy src/ && uv run pytest -q --tb=short
```

Expected (Gate-A1 통과 기준):

- `ruff check .` → 0 error
- `mypy src/` → 0 error
- `pytest -q` → BE 1074 + 신규 5 모두 PASS, 0 fail

- [ ] **Step 7.2: 변경 파일 검토**

```bash
git status -s
```

Expected:

```
 M backend/.env.example
 M backend/src/core/config.py        (Task 1 에서 이미 commit 했다면 빠짐)
 A backend/src/common/redis_client.py
 A backend/tests/common/test_redis_client.py
 M backend/src/main.py
 A docs/superpowers/plans/2026-04-24-h2-sprint10-phase-a1.md
```

- [ ] **Step 7.3: 커밋 (사용자 승인 후)**

```bash
git add backend/src/common/redis_client.py \
        backend/tests/common/test_redis_client.py \
        backend/src/main.py \
        docs/superpowers/plans/2026-04-24-h2-sprint10-phase-a1.md
git commit -m "feat(common): add Redis lock pool client + lifespan healthcheck

H2 Sprint 10 Phase A1 — 분산 락 + rate-limit 공유 Redis client.

- get_redis_lock_pool() lazy singleton (DB 3)
- reset_redis_lock_pool() Celery prefork worker 안전
- healthcheck_redis_lock() lifespan startup 1회 PING
- 실패 시 app.state.redis_lock_healthy=False degraded 모드 (예외 raise 안 함)

Phase B(rate limit) / Phase A2(redlock) 가 본 모듈을 단순 import 한다.
codex plan-stage 평가의 'broker Redis 공용' 리스크 보강 — DB 1/2 와 격리.

Tests: 5 case (singleton, reset, cross-loop, ping success, ping failure).
Gate-A1: ruff 0 / mypy 0 / pytest BE 1074 + 5 신규 = 1079 green."
```

- [ ] **Step 7.4: 푸시 (사용자 승인 후)**

worktree 가 `feat/h2s10-redis-client` 브랜치라면:

```bash
git push -u origin feat/h2s10-redis-client
```

`stage/h2-sprint10` 으로 squash merge 는 별도 단계 (Phase A1 3-way Evaluator PASS 후).

---

## Verification Summary (Gate-A1)

| 항목              | 명령                                                              | 통과 기준                                             |
| ----------------- | ----------------------------------------------------------------- | ----------------------------------------------------- |
| Lint              | `cd backend && uv run ruff check .`                               | 0 error                                               |
| Type              | `cd backend && uv run mypy src/`                                  | 0 error                                               |
| Tests             | `cd backend && uv run pytest -q`                                  | BE 1074 + 5 신규 = 1079 green, 0 fail                 |
| Settings          | `grep REDIS_LOCK_URL backend/.env.example`                        | 1 line hit                                            |
| Lifespan          | `docker compose up -d redis && uv run uvicorn src.main:app` smoke | startup 성공 + WARN 없음                              |
| Lifespan degraded | (redis 종료 후) 동일 smoke                                        | startup 성공 + `redis_lock_pool_ping_failed` WARN 1회 |

---

## What this Phase is NOT

- **락 자체 구현 X** — `RedisLock` async CM 은 Phase A2 (`backend/src/common/redlock.py`)
- **rate-limit middleware X** — slowapi 는 Phase B (`backend/src/common/rate_limit.py`). 본 Phase 는 storage backend 가 사용할 client 만 노출
- **Heartbeat / extend logic X** — Phase A2
- **`acquire_idempotency_lock` 마이그레이션 X** — Phase A2

본 Phase 는 **공유 인프라 1 파일 + 4 테스트 + lifespan 1 줄** 만. Critical-path 의 가장 짧은 첫 단계.

---

## Generator-Evaluator (Phase 완료 직후)

본 SDD 의 Task 7 까지 완료 후, sprint10 master plan §검증 의 3-way blind review 절차 수행:

1. `git diff origin/stage/h2-sprint10..origin/feat/h2s10-redis-client > /tmp/h2s10-a1-diff.patch`
2. **codex** (foreground, 5 min timeout) — diff + 다음 체크리스트 평가:
   - DB 3 사용이 broker(DB 1)/result(DB 2)와 충돌 없는가?
   - `reset_redis_lock_pool()` 가 Celery prefork 자식 프로세스에서 실제로 호출되는 진입점이 있는가? (현 단계는 Phase A2 완료 시점에 보강 — 본 Phase 에서는 helper 만 노출)
   - `decode_responses=False` 가 향후 Lua script raw bytes 와 호환되는가?
   - `socket_*_timeout=2s` 가 startup 지연으로 lifespan 차단 위험 없는가?
3. **Opus blind** Agent (background, model=opus) — 파일 경로 4 개만 + Golden Rules 요약
4. **Sonnet blind** Agent (background, model=sonnet) — PR body 초안 + edge case 탐색
5. PASS = 평균 confidence ≥ 8/10 ∧ blocker 0 ∧ major ≤ 2 → squash merge to `stage/h2-sprint10`
6. GWF 시 2 vote 이상 major 만 fix 커밋
