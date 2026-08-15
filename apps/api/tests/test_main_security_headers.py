# Sprint 61 T-5 (BL-311) — BE 보안 헤더 middleware 회귀 test
"""SecurityHeadersMiddleware 가 모든 응답에 5 헤더 baseline + server strip 부착.

Multi-Agent QA 2026-05-17 발견: BE 응답에 X-Frame-Options / HSTS /
X-Content-Type-Options / Referrer-Policy / Permissions-Policy 0건 + `server: uvicorn`
info leak. 본 test 가 미들웨어 baseline 부착 + production 환경 HSTS 분기 + server strip
3 측면 검증.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _build_app_with_env(monkeypatch: pytest.MonkeyPatch, env: str, *, debug: bool = True):
    """app_env(+debug) 를 강제 monkeypatch 후 create_app() 재실행.

    ★`debug` 기본값을 True 로 **명시**한다 (2026-08-15 surface-truth). 종전 판본은
    ambient `.env.local` 의 `DEBUG` 에 의존했고, 로컬(`DEBUG=true`)과 CI(미설정 → False)가
    **다른 것을 재고 있었다** — HSTS 술어가 `is_production or not debug` 로 넓어지자
    로컬은 초록인데 CI 만 red 였다. 같은 병을 `test_main_openapi_gating.py` 에서 먼저 고쳤다.
    """
    from src.core.config import settings
    from src.main import create_app

    monkeypatch.setattr(settings, "app_env", env)
    monkeypatch.setattr(settings, "debug", debug)
    return create_app()


def test_security_headers_attached_on_health_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """간단한 /health 응답에 4 baseline 헤더 부착 검증."""
    app = _build_app_with_env(monkeypatch, "development")
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "geolocation=(), camera=(), microphone=()"


def test_server_header_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    """uvicorn server 헤더 strip (OWASP A05 info leak)."""
    app = _build_app_with_env(monkeypatch, "development")
    client = TestClient(app)
    response = client.get("/health")
    assert "server" not in {k.lower() for k in response.headers}


def test_hsts_omitted_for_trusted_local_development(monkeypatch: pytest.MonkeyPatch) -> None:
    """★**로컬 개발**(`DEBUG=true`) → HSTS 헤더 부재.

    ★2026-08-15 surface-truth — 판정축이 `app_env` 에서 **`debug`** 로 넓어졌다.
    「development 면 안 붙인다」가 아니라 「**신뢰된 로컬**이면 안 붙인다」가 계약이다.
    그 차이가 실제로 문제였다: 배포 호스트는 `APP_ENV` 를 안 넣어 `development` 인데
    HTTPS 뒤에 있었고, 종전 술어로는 HSTS 가 **영원히 안 붙었다**.
    """
    app = _build_app_with_env(monkeypatch, "development", debug=True)
    client = TestClient(app)
    response = client.get("/health")
    assert "strict-transport-security" not in {k.lower() for k in response.headers}


def test_hsts_attached_when_debug_is_off_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★실사고 모양 — `APP_ENV` 미설정(=development) + `DEBUG=false` → HSTS **부착**.

    배포 호스트가 정확히 이 상태였다(서버 `.env.local` 실측: `APP_ENV` 줄 없음 · `DEBUG=false`).
    이 테스트가 없으면 술어를 `is_production` 으로 되돌려도 초록이다.
    """
    app = _build_app_with_env(monkeypatch, "development", debug=False)
    client = TestClient(app)
    response = client.get("/health")
    assert "strict-transport-security" in {k.lower() for k in response.headers}


def test_hsts_attached_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """production env → HSTS 헤더 부착 (HTTPS 가정)."""
    app = _build_app_with_env(monkeypatch, "production")
    client = TestClient(app)
    response = client.get("/health")
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_cors_middleware_unaffected(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORS middleware (frontend_url allowlist) 동작 회귀 — disallowed origin 400."""
    app = _build_app_with_env(monkeypatch, "development")
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORSMiddleware 가 disallowed origin 을 400 차단 (allow_origins 명시).
    # 보안 헤더 미들웨어 추가 후에도 동일 동작 유지.
    assert response.status_code in (400, 405)
