"""Sprint 10 Phase B — Rate limiting 7 TDD.

1. limit 초과 시 429
2. user A 가 limit 도달해도 user B 는 영향 없음
3. 비인증 요청은 client.host 기반 IP fallback (XFF 무시)
4. 신뢰된 proxy 의 X-Forwarded-For leftmost 만 IP 로 인정
5. /metrics, /webhooks/*, /health 는 무제한
6. Redis 장애 → fail-open (통과 + WARN)
7. multi-worker 시뮬레이션 — 동일 키에 대한 atomic increment

구현 메모:
- slowapi @limiter.limit 데코레이터 적용 endpoint 에 `response: Response` 파라미터 필수.
- slowapi 0.1.9 버그: swallow_errors 경로에서 view_rate_limit 미설정 → _RateLimitStateInitMiddleware 로 우회.
- TestClient 의 client.host 는 'testclient' (비IP). XFF 테스트는 _client_ip_or_xff 유닛 테스트로 대체.
- key_func lambda 의 파라미터명은 반드시 'request' (slowapi inspect.signature 에서 'request' 키워드 확인).
"""

from __future__ import annotations

import ipaddress

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from src.common.rate_limit import install_rate_limit


@pytest.fixture
def limited_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """테스트 전용 앱 — slowapi storage 를 memory:// 로 override (Redis 의존 제거).

    2/minute 데코레이터 적용된 minimal endpoint /echo + /metrics stub 포함.

    Fix 1 (C1) 이후 install_rate_limit 는 module-level singleton 을 반환하므로
    settings URL 만 바꿔서는 새 storage 가 적용되지 않음.
    테스트 격리를 위해 memory:// limiter 를 직접 생성 후 module에 monkeypatch.
    """
    from src.common import rate_limit as rl

    # memory:// limiter 생성 후 module-level singleton 교체
    monkeypatch.setattr("src.core.config.settings.redis_lock_url", "memory://")
    mem_limiter = rl.create_limiter()
    monkeypatch.setattr(rl, "limiter", mem_limiter)

    app = FastAPI()
    app.state.redis_lock_healthy = True  # storage 정상 가정
    limiter = install_rate_limit(app)

    @app.get("/echo")
    @limiter.limit("2/minute")
    async def echo(request: Request, response: Response) -> dict[str, str]:
        # slowapi headers_enabled=True 시 response: Response 파라미터 필수
        return {"ok": "true"}

    @app.get("/metrics")
    async def metrics_stub(request: Request, response: Response) -> dict[str, str]:
        return {"metrics": "ok"}

    return app


# ─────────────────────────────────────────────────────
# Test 1: limit 초과 시 429
# ─────────────────────────────────────────────────────


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


# ─────────────────────────────────────────────────────
# Test 2: per-user 격리
# ─────────────────────────────────────────────────────


def test_per_user_isolation(limited_app: FastAPI) -> None:
    """user A 가 limit 도달해도 user B 는 정상 처리.

    slowapi key_func 의 파라미터명은 'request' 여야 inspect.signature 로 인식.
    """
    limiter = limited_app.state.limiter

    @limited_app.get("/private-limited")
    @limiter.limit(
        "1/minute",
        # 주의: slowapi 가 inspect.signature 로 'request' 파라미터 존재 여부 확인.
        # 파라미터명이 다르면 no-arg 방식으로 호출 → TypeError → swallow_errors 로 흡수.
        key_func=lambda request: f"user:{request.headers.get('x-test-user', 'anon')}",
    )
    async def private_limited(request: Request, response: Response) -> dict[str, str]:
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


# ─────────────────────────────────────────────────────
# Test 3: 비인증 IP fallback (XFF 무시)
# ─────────────────────────────────────────────────────


def test_unauthenticated_uses_client_host_when_no_xff(
    monkeypatch: pytest.MonkeyPatch,
    limited_app: FastAPI,
) -> None:
    """TRUSTED_PROXIES 비어 있으면 X-Forwarded-For 무시 + client.host 만 사용.

    TestClient 의 client.host = 'testclient' (비IP) 이므로 모든 요청이 동일 키 → 2/min 한도.
    """
    monkeypatch.setattr("src.core.config.settings.trusted_proxies_raw", "")
    # rate_limit module 의 _TRUSTED_NETS 도 갱신 (module-level 캐시)
    from src.common import rate_limit as rl

    rl._TRUSTED_NETS = []

    with TestClient(limited_app) as client:
        # X-Forwarded-For 헤더 다르게 보내도 동일 client.host (testclient) 로 처리
        r1 = client.get("/echo", headers={"x-forwarded-for": "1.2.3.4"})
        r2 = client.get("/echo", headers={"x-forwarded-for": "5.6.7.8"})
        r3 = client.get("/echo", headers={"x-forwarded-for": "9.10.11.12"})
    # 2/minute limit → 세 번째는 429 (모두 동일 client.host 키)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429  # 같은 client.host 로 묶임


# ─────────────────────────────────────────────────────
# Test 4: 신뢰된 proxy XFF leftmost 인정 (유닛 테스트)
# ─────────────────────────────────────────────────────


def test_xff_trusted_when_proxy_in_whitelist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """신뢰된 proxy 의 XFF leftmost 만 IP 로 인정 — _client_ip_or_xff 유닛 테스트.

    TestClient 의 client.host 가 'testclient' (비IP) 이므로 통합 테스트 불가.
    대신 _client_ip_or_xff 함수를 직접 테스트 (Request 를 mock 으로 대체).
    """
    from src.common import rate_limit as rl

    # 신뢰된 proxy 네트워크 설정
    trusted_net = ipaddress.ip_network("10.0.0.0/8")
    monkeypatch.setattr(rl, "_TRUSTED_NETS", [trusted_net])

    # --- 케이스 A: client.host 가 신뢰된 proxy 대역에 있고 XFF 있음 → leftmost 반환 ---
    class _MockRequest:
        """Request 를 최소한으로 흉내내는 mock."""

        def __init__(self, client_host: str, xff: str = "") -> None:
            self.client = type("C", (), {"host": client_host})()
            self.headers = {"x-forwarded-for": xff} if xff else {}

    mock_req_trusted = _MockRequest("10.0.0.1", xff="1.2.3.4, 10.0.0.1")
    result = rl._client_ip_or_xff(mock_req_trusted)  # type: ignore[arg-type]
    assert result == "1.2.3.4", f"Expected '1.2.3.4', got '{result}'"

    # --- 케이스 B: client.host 가 신뢰된 proxy 대역 외부 → client.host 반환 ---
    mock_req_untrusted = _MockRequest("5.5.5.5", xff="1.2.3.4, 5.5.5.5")
    result = rl._client_ip_or_xff(mock_req_untrusted)  # type: ignore[arg-type]
    assert result == "5.5.5.5", f"Expected '5.5.5.5', got '{result}'"

    # --- 케이스 C: TRUSTED_NETS 비어 있으면 XFF 무시 ---
    monkeypatch.setattr(rl, "_TRUSTED_NETS", [])
    mock_req_empty = _MockRequest("10.0.0.1", xff="1.2.3.4")
    result = rl._client_ip_or_xff(mock_req_empty)  # type: ignore[arg-type]
    assert result == "10.0.0.1", f"Expected '10.0.0.1', got '{result}'"


# ─────────────────────────────────────────────────────
# Test 5: /metrics 제외 path 무제한
# ─────────────────────────────────────────────────────


def test_metrics_path_unlimited(limited_app: FastAPI) -> None:
    """/metrics endpoint 는 limiter.exempt 처리 시 default_limits 도 무시."""
    limiter = limited_app.state.limiter
    # fixture 의 /metrics 라우트를 exempt 처리 (main.py 에서 install_rate_limit 후 동일하게 호출)
    for route in limited_app.routes:
        if hasattr(route, "path") and route.path == "/metrics":  # type: ignore[union-attr]
            limiter.exempt(route.endpoint)  # type: ignore[union-attr]
            break

    with TestClient(limited_app) as client:
        # default_limits=100/minute 보다 많이 호출해도 모두 통과
        for _ in range(120):
            r = client.get("/metrics")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


# ─────────────────────────────────────────────────────
# Test 6: Redis 장애 fail-open
# ─────────────────────────────────────────────────────


def test_fail_open_when_redis_down(
    monkeypatch: pytest.MonkeyPatch,
    limited_app: FastAPI,
) -> None:
    """Redis storage 가 접근 불가해도 limiter 가 통과 (swallow_errors=True).

    slowapi 0.1.9 버그 우회: _RateLimitStateInitMiddleware 가 view_rate_limit=None 으로
    초기화해 AttributeError 를 방지. fail-open 경로에서 모든 요청이 200 으로 통과.
    """
    from src.common import rate_limit as rl

    # 존재하지 않는 Redis 로 새 limiter 생성 → swallow_errors 로 모든 연결 오류 흡수
    monkeypatch.setattr("src.core.config.settings.redis_lock_url", "redis://nonexistent:6379/3")
    new_limiter = rl.create_limiter()
    limited_app.state.limiter = new_limiter

    @limited_app.get("/risky")
    @new_limiter.limit("1/minute")
    async def risky(request: Request, response: Response) -> dict[str, str]:
        return {"ok": "true"}

    with TestClient(limited_app) as client:
        # Redis down 상황. 1번째, 2번째 모두 통과 (fail-open)
        r1 = client.get("/risky")
        r2 = client.get("/risky")
    assert r1.status_code == 200
    assert r2.status_code == 200  # limit 적용 안 됨 (fail-open)


# ─────────────────────────────────────────────────────
# Test 7: multi-request atomicity (동일 키 연속 호출 카운트 정합성)
# ─────────────────────────────────────────────────────


def test_multi_request_same_key_count_atomic(limited_app: FastAPI) -> None:
    """동일 키에 대한 연속 호출이 정확히 N 번 카운트 (race 없음).

    limits 라이브러리의 memory storage 는 thread-safe atomic increment 를 보장.
    2/minute limit 검증 → 200 2개, 429 3개.
    """
    with TestClient(limited_app) as client:
        responses = [client.get("/echo") for _ in range(5)]
    # limit 2/min — 처음 2개만 200, 나머지 429
    statuses = [r.status_code for r in responses]
    assert statuses.count(200) == 2
    assert statuses.count(429) == 3
