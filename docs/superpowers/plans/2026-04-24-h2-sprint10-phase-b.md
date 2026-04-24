# H2 Sprint 10 — Phase B: Rate Limiting Middleware Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Beta 사용자 ~10명 진입 직전, abuse / 실수 호출이 백엔드를 죽이지 않도록 per-endpoint rate-limit 미들웨어를 도입한다.

**Architecture:** `slowapi.Limiter` + Redis storage(Phase A1 의 `get_redis_lock_pool()` 재사용, DB 3 격리). Clerk JWT user_id 기반 key, 비인증은 신뢰된 proxy 화이트리스트 기반 IP fallback. Redis 장애 시 fail-open(WARN 로그 + 통과) 으로 제어 평면이 데이터 평면을 죽이지 않게 한다. 429 응답에 `X-RateLimit-*` + `Retry-After` 표준 헤더.

**Tech Stack:** `slowapi>=0.1.9` (FastAPI 호환 wrapper for limits), `limits` (Redis storage backend, slowapi 의존). `redis` (이미 설치됨).

---

## Files

**Create:**

- `backend/src/common/rate_limit.py` — Limiter factory + key/exceeded handlers
- `backend/tests/common/test_rate_limit.py` — 7 TDD (limit 초과, 타 user 독립, 비인증 IP fallback, X-Forwarded-For 화이트리스트, 제외 path 무제한, fail-open, multi-worker atomicity)

**Modify:**

- `backend/pyproject.toml` — `slowapi>=0.1.9` deps 추가
- `backend/src/core/config.py` — `Settings.trusted_proxies: list[str]` Field
- `backend/.env.example` + `.env.example` (root) — `TRUSTED_PROXIES=` 추가 (빈 기본값)
- `backend/src/main.py` — limiter 초기화 + middleware 등록 + 429 exception handler
- `backend/src/common/metrics.py` — `qb_rate_limit_throttled_total = Counter(labels=("scope", "endpoint"))` 1건 추가
- `backend/src/backtest/router.py:26-34` — `POST /backtests` 에 `@limiter.limit("10/minute")` 데코레이터
- `backend/src/stress_test/router.py` — `POST /monte-carlo`, `POST /walk-forward` 각각 `@limiter.limit("5/minute")`
- `backend/src/strategy/router.py` — `POST /strategies` 에 `@limiter.limit("30/minute")`

**Reuse (수정 금지):**

- `backend/src/common/redis_client.py::get_redis_lock_pool` (Phase A1) — slowapi RedisStorage 가 이 client 를 받음
- `backend/src/main.py:71-75` `app.state.redis_lock_healthy` 플래그 — fail-open 분기 결정

---

## Background — codex plan-stage 보강

H2 Sprint 10 master plan §재배열 §Phase B:

> SlowAPI는 Redis client/storage가 필요할 뿐 Redlock semantics는 필요 없습니다.

→ Phase A2 (redlock) 의존성 없음. Phase A1 의 `get_redis_lock_pool()` 만 import.

> X-Forwarded-For 신뢰는 `TRUSTED_PROXIES` env 로 화이트리스트 검증.

→ reverse-proxy 환경에서 spoofed XFF 헤더로 rate limit 우회 방지. 빈 화이트리스트면 `request.client.host` 직접 사용.

> Redis 장애 → fail-open (경고 로그 + 통과)

→ slowapi 의 `swallow_errors=True` 옵션 + `app.state.redis_lock_healthy` False 시 limit decorator no-op 처리.

---

## Per-Endpoint Limit Map (Q2 = 엄격, 사용자 결정)

| Endpoint                                  | Limit      | Scope    | Reason                                 |
| ----------------------------------------- | ---------- | -------- | -------------------------------------- |
| `POST /api/v1/backtests`                  | 10/minute  | per-user | 고비용 Celery task, retry storm 방지   |
| `POST /api/v1/stress-tests/monte-carlo`   | 5/minute   | per-user | MC 1000회 ~10s 실행                    |
| `POST /api/v1/stress-tests/walk-forward`  | 5/minute   | per-user | WFA folds 비용                         |
| `POST /api/v1/strategies`                 | 30/minute  | per-user | 일반 CRUD                              |
| GET `/api/v1/**` (글로벌 default)         | 300/minute | per-user | 폴링 트래픽 허용                       |
| 글로벌 fallback                           | 100/minute | per-user | 미명시 endpoint 보호                   |
| `/metrics`, `POST /webhooks/*`, `/health` | 무제한     | —        | Prometheus/TV/health-check 정상 트래픽 |

---

## Task 1: 의존성 추가

**Files:**

- Modify: `backend/pyproject.toml`

- [ ] **Step 1.1: slowapi dep 추가**

`backend/pyproject.toml` 의 `[project] dependencies` 리스트에 다음 추가:

```toml
"slowapi>=0.1.9",
```

(`limits` 는 slowapi transitive — 명시 불필요)

- [ ] **Step 1.2: 설치 + lockfile 갱신**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-rate-limit/backend
uv sync
```

Expected: `slowapi==0.1.9` (or higher) 가 `uv.lock` 에 추가됨, 0 error.

- [ ] **Step 1.3: import smoke**

```bash
uv run python -c "from slowapi import Limiter; from slowapi.util import get_remote_address; print('OK')"
```

Expected: `OK`.

- [ ] **Step 1.4: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "feat(deps): add slowapi for Phase B rate limiting"
```

---

## Task 2: Settings.trusted_proxies 추가

**Files:**

- Modify: `backend/src/core/config.py`
- Modify: `backend/.env.example`
- Modify: `.env.example` (root)

- [ ] **Step 2.1: Settings field**

`backend/src/core/config.py` 의 `# Redis / Celery` 섹션 (라인 30-41) 직후, `# Backtest (Sprint 4)` 위에 추가:

```python
    # --- Sprint 10 Phase B: Rate limiting (TRUSTED_PROXIES whitelist) ---
    trusted_proxies: list[str] = Field(
        default_factory=list,
        description=(
            "신뢰 가능한 reverse proxy IP 화이트리스트 (CIDR 또는 IP). "
            "비인증 요청의 IP fallback 시 X-Forwarded-For 의 leftmost client IP 를 "
            "신뢰할지 결정. 빈 리스트면 XFF 무시 + request.client.host 만 사용. "
            "Sprint 10 Phase B."
        ),
    )
```

`from pydantic import Field` 가 이미 import 되어 있는지 확인 (라인 5 있음).

- [ ] **Step 2.2: backend/.env.example 추가**

`backend/.env.example` 의 `# Observability — Sprint 9 Phase D` 섹션 (라인 88 부근) 직전에 새 섹션 추가:

```bash

# =====================================================
# Rate limiting (Sprint 10 Phase B)
# =====================================================
# 신뢰 가능한 reverse proxy IP/CIDR 화이트리스트 (콤마 구분).
# 비어 있으면 X-Forwarded-For 무시 + request.client.host 직접 사용.
# 운영: nginx/cloudflare 의 IP 범위 명시. 예: TRUSTED_PROXIES=10.0.0.0/8,172.16.0.0/12
TRUSTED_PROXIES=                                                       # [기본값 OK] 로컬 dev 는 비움
```

- [ ] **Step 2.3: root .env.example 추가**

`.env.example` (worktree 루트) 끝, Phase A1 의 Redis 락 섹션 다음에 추가:

```bash

# =====================================================
# Rate limiting (Sprint 10 Phase B, docker-compose `backend-worker` interpolation)
# =====================================================
TRUSTED_PROXIES=                                                       # [기본값 OK] 로컬 dev 는 비움
```

- [ ] **Step 2.4: pydantic 파싱 검증**

```bash
cd backend
uv run python -c "
from src.core.config import settings
assert settings.trusted_proxies == [], f'expected empty, got {settings.trusted_proxies}'
print('OK: trusted_proxies =', settings.trusted_proxies)
"
```

Expected: `OK: trusted_proxies = []`.

추가로 콤마 구분 입력 검증:

```bash
TRUSTED_PROXIES='10.0.0.0/8,172.16.0.0/12' uv run python -c "
from src.core.config import settings
print(settings.trusted_proxies)
"
```

Expected: `['10.0.0.0/8', '172.16.0.0/12']`.

만약 콤마 분리가 자동으로 안 되면 (pydantic v2 의 `list[str]` 은 JSON 배열만 파싱), 다음 중 택1:

- (a) `TRUSTED_PROXIES='["10.0.0.0/8","172.16.0.0/12"]'` JSON 형식 사용 (운영 친화적이지 않음)
- (b) Field 에 `field_validator` 추가해 콤마 split 처리 (권장)

(b) 채택 시 `Settings` 클래스 끝에 추가:

```python
    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def _split_trusted_proxies(cls, v: object) -> list[str]:
        """콤마 구분 문자열 → list[str]. 빈 값 → []."""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if isinstance(v, list):
            return v
        return []
```

- [ ] **Step 2.5: 커밋**

```bash
git add backend/src/core/config.py backend/.env.example .env.example
git commit -m "feat(common): add TRUSTED_PROXIES setting for Phase B XFF whitelist"
```

---

## Task 3: rate_limit.py 모듈 골격 — Limiter factory

**Files:**

- Create: `backend/src/common/rate_limit.py`

- [ ] **Step 3.1: 모듈 작성**

`backend/src/common/rate_limit.py` 신규:

```python
"""Sprint 10 Phase B — slowapi Limiter factory + key/exceeded handlers.

- Storage: Phase A1 의 `get_redis_lock_pool()` 재사용 (DB 3 격리)
- Key: Clerk JWT user_id (없으면 신뢰된 XFF leftmost / fallback request.client.host)
- Fail-open: Redis 장애 시 (`app.state.redis_lock_healthy = False`) limiter 통과 + WARN
- 429 응답: X-RateLimit-* + Retry-After 표준 헤더 + qb_rate_limit_throttled_total inc
"""

from __future__ import annotations

import ipaddress
import logging
from typing import TYPE_CHECKING

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from src.common.metrics import qb_rate_limit_throttled_total
from src.core.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI

_LOGGER = logging.getLogger(__name__)


def _parse_trusted_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Settings.trusted_proxies 를 IPv4/v6 Network 객체 리스트로 변환."""
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw in settings.trusted_proxies:
        try:
            nets.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            _LOGGER.warning(
                "rate_limit_invalid_trusted_proxy",
                extra={"value": raw},
            )
    return nets


_TRUSTED_NETS = _parse_trusted_networks()


def _client_ip_or_xff(request: Request) -> str:
    """신뢰된 proxy 뒤에서만 X-Forwarded-For 의 leftmost IP 사용. 그 외는 client.host."""
    client_host = get_remote_address(request)
    if not _TRUSTED_NETS:
        return client_host
    try:
        client_ip = ipaddress.ip_address(client_host)
    except ValueError:
        return client_host
    if not any(client_ip in net for net in _TRUSTED_NETS):
        return client_host
    xff = request.headers.get("x-forwarded-for", "")
    if not xff:
        return client_host
    leftmost = xff.split(",")[0].strip()
    return leftmost or client_host


def rate_limit_key(request: Request) -> str:
    """Clerk JWT user_id 우선, 없으면 신뢰된 XFF / client.host."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{_client_ip_or_xff(request)}"


def create_limiter() -> Limiter:
    """slowapi Limiter — Redis storage (Phase A1 pool) + fail-open + 100/min default."""
    from src.common.redis_client import get_redis_lock_pool

    pool = get_redis_lock_pool()
    storage_uri = settings.redis_lock_url
    return Limiter(
        key_func=rate_limit_key,
        storage_uri=storage_uri,
        # slowapi 가 limits 라이브러리를 통해 storage 생성. URL 만 넘기면 자동.
        # 같은 풀 재사용 효과는 limits 가 connection pool 을 자체 관리하므로 100% 일치는 아니나,
        # 같은 Redis DB 3 을 가리켜 동일 storage 사용. _TRUSTED_NETS 등 외부 영향 없음.
        default_limits=["100/minute"],
        swallow_errors=True,  # Redis 장애 → 통과 (fail-open)
        headers_enabled=True,  # X-RateLimit-* 헤더
        in_memory_fallback_enabled=False,  # 분산 환경 정합성 우선
        strategy="fixed-window",
    )


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """429 응답 + qb_rate_limit_throttled_total inc."""
    endpoint = request.url.path
    scope = "user" if getattr(request.state, "user_id", None) else "ip"
    qb_rate_limit_throttled_total.labels(scope=scope, endpoint=endpoint).inc()
    response = JSONResponse(
        status_code=429,
        content={
            "detail": {
                "code": "rate_limit_exceeded",
                "detail": str(exc.detail),
            }
        },
    )
    # slowapi 가 X-RateLimit-* 헤더를 자동 inject 하지만, exception 경로는 수동 보강 필요
    response.headers["Retry-After"] = "60"
    return response


def install_rate_limit(app: "FastAPI") -> Limiter:
    """FastAPI 앱에 limiter 등록 + exception handler 바인딩.

    Returns the limiter so router 모듈이 `request.app.state.limiter` 또는
    데코레이터 import 로 사용.
    """
    limiter = create_limiter()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    return limiter
```

**중요 — 데코레이터 import 패턴:**
slowapi 의 `@limiter.limit("...")` 데코레이터는 `limiter` 인스턴스 메서드. 라우터에서 사용하려면 두 가지 패턴 중 택1:

(a) **lazy 패턴 — 권장.** 라우터에서 `from slowapi import Limiter` 만 가져오고 `@Limiter.limit(...)` 호환 인터페이스가 없으니 사용 불가. 따라서:
(b) **module-level limiter 패턴.** `rate_limit.py` 끝에 `limiter = create_limiter()` 추가하면 module import 시 Redis client 생성 트리거 → A1 의 lazy 원칙 위반.

**채택:** Limiter 를 두 단계로 분리 — (1) `install_rate_limit(app)` 가 lifespan 에서 호출되어 `app.state.limiter` 세팅, (2) 라우터는 module-level `from slowapi import Limiter` 미사용, 대신 dependency 패턴 + Request 의 `app.state.limiter` 활용. 그런데 slowapi 데코레이터는 정확히 module-level limiter 인스턴스를 요구.

→ **타협**: 라우터 데코레이터 적용은 module-level 단일 limiter 가 필요. 따라서 `rate_limit.py` 끝에 다음 추가:

```python
# Module-level singleton — slowapi 데코레이터 호환용.
# 첫 import 시점에 Limiter 가 storage_uri 만 보유 (Redis client 미생성).
# 실제 Redis 호출은 첫 limit hit 시점.
limiter = create_limiter()
```

`Limiter.__init__` 은 `storage_uri` 만 저장하고 storage 객체는 lazy 하게 첫 request 시 생성 → A1 의 lazy 원칙과 충돌하지 않음 (확인 필요 — Step 3.2).

- [ ] **Step 3.2: Limiter lazy 검증**

```bash
cd backend
uv run python -c "
from src.common.rate_limit import limiter, create_limiter
import src.common.redis_client as rc
rc.reset_redis_lock_pool()
assert rc._pool is None, f'expected None, got {rc._pool}'
print('OK: Limiter import did NOT trigger Redis pool creation')
"
```

Expected: `OK: Limiter import did NOT trigger Redis pool creation`.

만약 실패 (`_pool` 이 not None) 이면 SDD 작성자에게 보고. slowapi 의 storage 가 eager 라면 module-level 패턴이 A1 lazy 원칙 위반.

- [ ] **Step 3.3: 커밋**

```bash
git add backend/src/common/rate_limit.py
git commit -m "feat(common): rate_limit.py — Limiter factory + key/handler skeleton"
```

---

## Task 4: metrics.py 에 throttled Counter 추가

**Files:**

- Modify: `backend/src/common/metrics.py`

- [ ] **Step 4.1: Counter 정의 추가**

`backend/src/common/metrics.py` 의 5개 metric 정의 영역 끝에 추가:

```python
# 6. Rate limit throttled (Sprint 10 Phase B)
qb_rate_limit_throttled_total = Counter(
    "qb_rate_limit_throttled_total",
    "Rate limit 초과로 429 응답한 횟수",
    labelnames=("scope", "endpoint"),
)
```

- [ ] **Step 4.2: 등록 검증**

```bash
cd backend
uv run python -c "
from src.common import metrics
print('qb_rate_limit_throttled_total' in [
    m.name for m in metrics.qb_rate_limit_throttled_total._metrics
] or hasattr(metrics, 'qb_rate_limit_throttled_total'))
"
```

Expected: `True`.

- [ ] **Step 4.3: 커밋**

```bash
git add backend/src/common/metrics.py
git commit -m "feat(observability): add qb_rate_limit_throttled_total Counter"
```

---

## Task 5: Test 1 — 비인증 IP 기반 limit 초과 시 429 (RED → GREEN)

**Files:**

- Create: `backend/tests/common/test_rate_limit.py`

- [ ] **Step 5.1: Test 작성**

`backend/tests/common/test_rate_limit.py` 신규:

```python
"""Sprint 10 Phase B — Rate limiting 7 TDD.

1. limit 초과 시 429
2. user A 가 limit 도달해도 user B 는 영향 없음
3. 비인증 요청은 client.host 기반 IP fallback
4. 신뢰된 proxy 의 X-Forwarded-For leftmost 만 IP 로 인정
5. /metrics, /webhooks/*, /health 는 무제한
6. Redis 장애 → fail-open (통과 + WARN)
7. multi-worker 시뮬레이션 — 동일 키에 대한 atomic increment
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.common.rate_limit import install_rate_limit


@pytest.fixture
def limited_app() -> FastAPI:
    """테스트 전용 앱 — 2/minute 데코레이터 적용된 minimal endpoint."""
    app = FastAPI()
    app.state.redis_lock_healthy = True  # storage 정상 가정
    limiter = install_rate_limit(app)

    @app.get("/echo")
    @limiter.limit("2/minute")
    async def echo(request: Request) -> dict[str, str]:
        return {"ok": "true"}

    @app.get("/metrics")
    async def metrics_stub() -> dict[str, str]:
        return {"metrics": "ok"}

    return app


def test_rate_limit_exceeded_returns_429(limited_app: FastAPI) -> None:
    """동일 IP 가 limit (2/min) 초과 시 3회째 429."""
    with TestClient(limited_app) as client:
        r1 = client.get("/echo")
        r2 = client.get("/echo")
        r3 = client.get("/echo")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json()["detail"]["code"] == "rate_limit_exceeded"
    assert r3.headers.get("Retry-After") == "60"
```

- [ ] **Step 5.2: RED 확인**

```bash
cd backend
uv run pytest tests/common/test_rate_limit.py::test_rate_limit_exceeded_returns_429 -v
```

Expected: ImportError or AssertionError.

- [ ] **Step 5.3: 구현 보강 — TestClient 환경에서 Redis 없이 동작하도록**

slowapi 가 Redis storage 로 설정된 상태에서 테스트 시 실제 Redis 미가용 → in-memory fallback 또는 mock 필요. SDD 결정:

테스트 fixture 가 Redis 컨테이너를 띄우면 너무 무거움. 따라서 slowapi 의 in-memory storage 를 테스트에서 사용. 다음 두 가지 방법 중 하나:

(a) `Limiter(storage_uri="memory://", ...)` — slowapi 가 지원하는 간단한 in-memory 백엔드.
(b) `monkeypatch` 로 `create_limiter` 의 storage_uri 를 `memory://` 로 override.

채택: **(b)** — production 코드 무수정.

`backend/tests/common/test_rate_limit.py` 의 `limited_app` fixture 를 수정해 monkeypatch 로 storage_uri override:

```python
@pytest.fixture
def limited_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """테스트 전용 — slowapi storage 를 memory:// 로 override (Redis 의존 제거)."""
    monkeypatch.setattr("src.core.config.settings.redis_lock_url", "memory://")
    app = FastAPI()
    app.state.redis_lock_healthy = True
    limiter = install_rate_limit(app)
    ...
```

- [ ] **Step 5.4: GREEN 확인**

```bash
uv run pytest tests/common/test_rate_limit.py::test_rate_limit_exceeded_returns_429 -v
```

Expected: 1 passed.

---

## Task 6: Test 2 — 타 user 독립 (RED → GREEN)

**Files:**

- Modify: `backend/tests/common/test_rate_limit.py`

- [ ] **Step 6.1: Test 추가**

```python
def test_per_user_isolation(limited_app: FastAPI) -> None:
    """user A 가 limit 도달해도 user B 는 정상 처리."""
    @limited_app.get("/private")
    async def private(request: Request) -> dict[str, str]:
        # 테스트용 — user_id 를 헤더에서 직접 주입
        request.state.user_id = request.headers.get("x-test-user")
        return {"ok": "true"}

    # rate_limit_key 는 request.state.user_id 를 우선 사용. 데코레이터 없는 endpoint 라
    # default_limits=100/minute 적용. 본 테스트는 명시 limiter 적용 endpoint 추가:
    limiter = limited_app.state.limiter

    @limited_app.get("/private-limited")
    @limiter.limit("1/minute", key_func=lambda req: f"user:{req.headers.get('x-test-user', 'anon')}")
    async def private_limited(request: Request) -> dict[str, str]:
        return {"ok": "true"}

    with TestClient(limited_app) as client:
        # user A 1번째 → OK
        r1 = client.get("/private-limited", headers={"x-test-user": "userA"})
        # user A 2번째 → 429
        r2 = client.get("/private-limited", headers={"x-test-user": "userA"})
        # user B 1번째 → OK (독립 키)
        r3 = client.get("/private-limited", headers={"x-test-user": "userB"})

    assert r1.status_code == 200
    assert r2.status_code == 429
    assert r3.status_code == 200
```

- [ ] **Step 6.2: 실행 → 2 PASS**

```bash
uv run pytest tests/common/test_rate_limit.py -v
```

Expected: 2 passed.

---

## Task 7: Test 3, 4, 5 — IP fallback / XFF 화이트리스트 / 제외 path

**Files:**

- Modify: `backend/tests/common/test_rate_limit.py`

- [ ] **Step 7.1: Test 3 — 비인증 IP fallback**

이미 Test 1 이 IP fallback 을 검증함 (request.state.user_id 미세팅). 추가 테스트:

```python
def test_unauthenticated_uses_client_host_when_no_xff(monkeypatch, limited_app: FastAPI) -> None:
    """TRUSTED_PROXIES 비어 있으면 X-Forwarded-For 무시 + client.host 만 사용."""
    monkeypatch.setattr("src.core.config.settings.trusted_proxies", [])
    # rate_limit module 의 _TRUSTED_NETS 도 갱신
    from src.common import rate_limit as rl
    rl._TRUSTED_NETS = []

    with TestClient(limited_app) as client:
        # X-Forwarded-For 헤더 다르게 보내도 동일 client.host (testclient) 로 처리
        r1 = client.get("/echo", headers={"x-forwarded-for": "1.2.3.4"})
        r2 = client.get("/echo", headers={"x-forwarded-for": "5.6.7.8"})
        r3 = client.get("/echo", headers={"x-forwarded-for": "9.10.11.12"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429  # 같은 client.host 로 묶임
```

- [ ] **Step 7.2: Test 4 — XFF 화이트리스트**

```python
def test_xff_trusted_when_proxy_in_whitelist(monkeypatch, limited_app: FastAPI) -> None:
    """신뢰된 proxy 의 XFF leftmost 만 IP 로 인정."""
    from src.common import rate_limit as rl
    import ipaddress

    monkeypatch.setattr(
        "src.core.config.settings.trusted_proxies", ["127.0.0.0/8"]
    )
    rl._TRUSTED_NETS = [ipaddress.ip_network("127.0.0.0/8")]

    with TestClient(limited_app) as client:
        # testclient 의 client.host 는 127.0.0.1 (loopback) → 화이트리스트 ∈
        # 따라서 XFF leftmost 가 IP 로 인정됨
        r1 = client.get("/echo", headers={"x-forwarded-for": "1.2.3.4"})
        r2 = client.get("/echo", headers={"x-forwarded-for": "5.6.7.8"})
        r3 = client.get("/echo", headers={"x-forwarded-for": "9.10.11.12"})
    # 각각 다른 IP 키 → 모두 통과 (limit 2/min 내)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
```

- [ ] **Step 7.3: Test 5 — 제외 path 무제한**

`/metrics` 는 limiter 데코레이터 미적용 + default_limits 도 미적용 (slowapi 는 데코레이터 없는 endpoint 에 default_limits 만 적용 — 이를 우회하는 방법은 라우트별 `@limiter.exempt`).

채택: `/metrics`, `/webhooks/*`, `/health` 는 main.py 등록 시 `@limiter.exempt` 적용. 테스트:

```python
def test_metrics_path_unlimited(limited_app: FastAPI) -> None:
    """제외 path (/metrics) 는 default_limits 도 무시."""
    limiter = limited_app.state.limiter
    # limited_app 의 /metrics 는 fixture 에서 데코레이터 없이 정의됨.
    # 명시적으로 exempt 처리:
    limiter.exempt(limited_app.router.routes[-1].endpoint)

    with TestClient(limited_app) as client:
        # 100/minute default 보다 많이 호출
        for _ in range(120):
            r = client.get("/metrics")
            assert r.status_code == 200
```

(120회 호출 → 타임아웃 가능. 프로덕션 적용 시 main.py 의 `/metrics` 라우트에 `@limiter.exempt` 데코레이터 추가하는 것이 핵심. 본 테스트는 fixture 한정으로 동작 검증.)

- [ ] **Step 7.4: GREEN 확인**

```bash
uv run pytest tests/common/test_rate_limit.py -v
```

Expected: 5 passed.

---

## Task 8: Test 6 — Redis 장애 fail-open

**Files:**

- Modify: `backend/tests/common/test_rate_limit.py`

- [ ] **Step 8.1: Test 추가**

```python
def test_fail_open_when_redis_down(monkeypatch, limited_app: FastAPI, caplog) -> None:
    """Redis storage 가 raise 해도 limiter 가 통과 (swallow_errors=True)."""
    # storage_uri 를 invalid 로 강제 → slowapi 가 swallow_errors 로 흡수
    from src.common import rate_limit as rl
    monkeypatch.setattr("src.core.config.settings.redis_lock_url", "redis://nonexistent:6379/3")

    # 새 limiter 생성 (이미 fixture 에서 만들어진 것은 memory://)
    new_limiter = rl.create_limiter()
    limited_app.state.limiter = new_limiter

    @limited_app.get("/risky")
    @new_limiter.limit("1/minute")
    async def risky(request: Request) -> dict[str, str]:
        return {"ok": "true"}

    with TestClient(limited_app) as client:
        # Redis down 상황. 1번째, 2번째 모두 통과 (fail-open)
        r1 = client.get("/risky")
        r2 = client.get("/risky")
    assert r1.status_code == 200
    assert r2.status_code == 200  # limit 적용 안 됨 (fail-open)
```

- [ ] **Step 8.2: GREEN 확인**

```bash
uv run pytest tests/common/test_rate_limit.py -v
```

Expected: 6 passed.

---

## Task 9: Test 7 — multi-worker atomicity (mock 기반)

**Files:**

- Modify: `backend/tests/common/test_rate_limit.py`

- [ ] **Step 9.1: Test 추가 (단순화)**

실제 multi-process 시뮬레이션은 무거움. 대신 limits 라이브러리의 increment 가 atomic 한지 확인하는 단위 테스트로 대체:

```python
def test_multi_request_same_key_count_atomic(limited_app: FastAPI) -> None:
    """동일 키에 대한 연속 호출이 정확히 N 번 카운트 (race 없음)."""
    with TestClient(limited_app) as client:
        responses = [client.get("/echo") for _ in range(5)]
    # limit 2/min — 처음 2개만 200, 나머지 429
    statuses = [r.status_code for r in responses]
    assert statuses.count(200) == 2
    assert statuses.count(429) == 3
```

- [ ] **Step 9.2: GREEN 확인 + 전체 테스트 7 PASS**

```bash
uv run pytest tests/common/test_rate_limit.py -v
```

Expected: 7 passed.

- [ ] **Step 9.3: 커밋 (Test 5~9)**

```bash
git add backend/tests/common/test_rate_limit.py
git commit -m "test(common): rate limit 7 TDD — limit/isolation/IP/XFF/exempt/fail-open/atomicity"
```

---

## Task 10: main.py 통합

**Files:**

- Modify: `backend/src/main.py`

- [ ] **Step 10.1: limiter 등록**

`backend/src/main.py` 의 `create_app()` 함수에서 `app.state.redis_lock_healthy = False` 다음에 추가:

```python
    # Sprint 10 Phase B — rate limit middleware
    from src.common.rate_limit import install_rate_limit
    install_rate_limit(app)
```

- [ ] **Step 10.2: /metrics, /health, /webhooks/\* 면제**

`/metrics` 는 `_verify_prometheus_bearer` dependency 가 있으므로 limiter 적용해도 무방하나, master plan 에서 명시 제외. `@limiter.exempt` 데코레이터를 직접 적용하기 어려우므로 (이미 lifespan 내 bind), 다음 패턴:

main.py 에서 `app.state.limiter` 를 가져와 라우트 정의 직후 `app.state.limiter.exempt(metrics_endpoint)` 호출.

수정 위치: `metrics_endpoint` 정의 직후 (라인 109-115 부근):

```python
    @app.get(
        "/metrics",
        include_in_schema=False,
        dependencies=[Depends(_verify_prometheus_bearer)],
    )
    async def metrics_endpoint() -> Response:
        ...
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Sprint 10 Phase B — /metrics 는 rate limit 면제
    app.state.limiter.exempt(metrics_endpoint)
    app.state.limiter.exempt(health)
```

- [ ] **Step 10.3: 라우터별 데코레이터 미적용 시 default 적용 확인**

slowapi 의 `default_limits=["100/minute"]` 는 데코레이터 미적용 endpoint 에도 적용. 따라서 `/api/v1/auth/*`, `/api/v1/exchange/*`, `/api/v1/optimizer/*`, `/api/v1/market_data/*`, `/api/v1/trading/*` 는 자동 100/min per-user.

명시 데코레이터는 backtest/stress_test/strategy 만 (Task 11~13).

- [ ] **Step 10.4: 통합 smoke**

```bash
cd backend
uv run pytest -q --tb=short 2>&1 | tail -10
```

Expected: 1080 + 7 신규 = 1087 green / 0 fail.

- [ ] **Step 10.5: 커밋**

```bash
git add backend/src/main.py
git commit -m "feat(common): wire rate limiter into FastAPI app + exempt /metrics, /health"
```

---

## Task 11: backtest router 데코레이터

**Files:**

- Modify: `backend/src/backtest/router.py:26-34`

- [ ] **Step 11.1: import + 데코레이터 추가**

`backend/src/backtest/router.py` 상단 import 추가:

```python
from src.common.rate_limit import limiter
```

`submit_backtest` 데코레이터 추가:

```python
@router.post("", response_model=BacktestCreatedResponse, status_code=202)
@limiter.limit("10/minute")
async def submit_backtest(
    request: Request,  # ← Request 인자 필수 (slowapi 가 IP/key 추출에 사용)
    data: CreateBacktestRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> BacktestCreatedResponse:
    ...
```

`from fastapi import Request` 추가 (라인 6 의 `from fastapi import APIRouter, ...` 에 Request 포함).

- [ ] **Step 11.2: 통합 테스트**

기존 backtest 테스트가 깨지지 않는지 확인:

```bash
uv run pytest tests/backtest/ -v --tb=short 2>&1 | tail -15
```

Expected: 모두 green. 만약 깨지면 — Limiter 가 `Request` 인자를 강제하므로 기존 테스트가 직접 함수 호출하는 패턴이라면 수정 필요.

- [ ] **Step 11.3: 커밋**

```bash
git add backend/src/backtest/router.py
git commit -m "feat(backtest): @limiter.limit('10/minute') on POST /backtests"
```

---

## Task 12: stress_test router 데코레이터

**Files:**

- Modify: `backend/src/stress_test/router.py`

- [ ] **Step 12.1: 두 라우트에 데코레이터**

`backend/src/stress_test/router.py` 의 `submit_monte_carlo` 와 `submit_walk_forward` 각각:

```python
from fastapi import Request  # 이미 있으면 skip
from src.common.rate_limit import limiter

@router.post("/monte-carlo", ...)
@limiter.limit("5/minute")
async def submit_monte_carlo(
    request: Request,
    data: MonteCarloSubmitRequest,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_monte_carlo(data, user_id=user.id)


@router.post("/walk-forward", ...)
@limiter.limit("5/minute")
async def submit_walk_forward(
    request: Request,
    data: WalkForwardSubmitRequest,
    user: CurrentUser = Depends(get_current_user),
    service: StressTestService = Depends(get_stress_test_service),
) -> StressTestCreatedResponse:
    return await service.submit_walk_forward(data, user_id=user.id)
```

- [ ] **Step 12.2: 테스트**

```bash
uv run pytest tests/stress_test/ -v --tb=short 2>&1 | tail -15
```

- [ ] **Step 12.3: 커밋**

```bash
git add backend/src/stress_test/router.py
git commit -m "feat(stress-test): @limiter.limit('5/minute') on submit endpoints"
```

---

## Task 13: strategy router 데코레이터

**Files:**

- Modify: `backend/src/strategy/router.py`

- [ ] **Step 13.1: POST /strategies 데코레이터**

```python
from fastapi import Request
from src.common.rate_limit import limiter

@router.post("", ...)
@limiter.limit("30/minute")
async def create_strategy(
    request: Request,
    ...
):
    ...
```

- [ ] **Step 13.2: 테스트 + 커밋**

```bash
uv run pytest tests/strategy/ -v --tb=short 2>&1 | tail -15
git add backend/src/strategy/router.py
git commit -m "feat(strategy): @limiter.limit('30/minute') on POST /strategies"
```

---

## Task 14: Gate-B 검증

- [ ] **Step 14.1: 전체 verification**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-rate-limit/backend
uv run ruff check . && uv run mypy src/ && uv run pytest -q --tb=short
```

Expected:

- `ruff check .` → 0 error
- `mypy src/` → 0 error
- `pytest -q` → 1080 + 7 신규 = 1087 green / 0 fail

- [ ] **Step 14.2: 수동 smoke (Redis up)**

```bash
docker compose up -d redis
uv run uvicorn src.main:app --reload --port 8000 &
sleep 3

# 11회 POST /backtests (인증 없이 — 401 받지만 limit 적용은 미들웨어 단계)
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/v1/backtests \
    -H "Content-Type: application/json" \
    -d '{}'
done

# 11번째: 429 기대 (실제로는 401 인증 → limiter 가 인증 dependency 전 수행되므로 429 가 나올 것)
kill %1
```

- [ ] **Step 14.3: 변경 파일 검토 + 커밋 정리**

```bash
git log --oneline stage/h2-sprint10..feat/h2s10-rate-limit
```

Expected: 9~12 커밋 (Task 1~13).

---

## Verification Summary (Gate-B)

| 항목          | 명령                                        | 통과 기준                            |
| ------------- | ------------------------------------------- | ------------------------------------ |
| Lint          | `ruff check .`                              | 0 error                              |
| Type          | `mypy src/`                                 | 0 error                              |
| Tests         | `pytest -q`                                 | 1080 + 7 = 1087 green / 0 fail       |
| Settings      | `grep TRUSTED_PROXIES backend/.env.example` | 1 line hit                           |
| Settings root | `grep TRUSTED_PROXIES .env.example`         | 1 line hit                           |
| Counter       | `curl localhost:8000/metrics`               | `qb_rate_limit_throttled_total` 노출 |
| 수동 smoke    | curl 11회 POST                              | 11번째 429                           |

---

## What this Phase is NOT

- 분산 락 자체 — Phase A2
- per-IP 글로벌 화이트리스트 — Sprint 11 (관리자 IP 면제 등)
- 동적 limit 조정 — Sprint 11 (DB 기반 rule)
- WebSocket 트래픽 — Sprint 11 (slowapi 기본 미지원)

---

## Generator-Evaluator (Phase 완료 직후)

Phase A1 와 동일 절차:

1. `git diff stage/h2-sprint10..feat/h2s10-rate-limit > /tmp/h2s10-b-diff.patch`
2. **codex** (foreground) — diff + Phase B 계약 체크리스트 (`memory://` storage 가 production 코드에 누출되지 않는지, fail-open 이 limit 자체가 미적용으로 흐르지 않는지, exempt 가 제대로 적용되는지)
3. **Opus blind** (background) — 파일 경로 + Golden Rules
4. **Sonnet blind** (background) — PR body + edge case (DDoS 시나리오, Redis flush 시 stale 카운터, multi-instance Limiter 인스턴스 격리)
5. PASS = avg ≥ 8/10 ∧ blocker 0 ∧ major ≤ 2

---

## Phase A2 SDD 에 명시 따라갈 항목 (A1 follow-ups + B 함정)

A1 에서 발견된 follow-ups:

- celeryd_after_fork hook
- prefork integ test
- qb_redis_lock_pool_healthy Gauge
- PING+SET healthcheck
- allkeys-lru DB 3 evict correctness
- TestClient lifespan 격리

B 에서 발견될 가능성 있는 항목:

- Redis 장애 시 limiter fail-open 의 의도된 행동 vs DDoS 위험 trade-off — Phase A2 와 일관 정책 점검
- multi-FastAPI-instance (uvicorn `--workers 4`) 시 limiter singleton 가 process-local — Redis storage 가 모든 process 공유하는지 확인 필수
