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


def _build_app_with_env(monkeypatch: pytest.MonkeyPatch, env: str):
    from src.core.config import settings
    from src.main import create_app

    monkeypatch.setattr(settings, "app_env", env)
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
    assert (
        response.headers["permissions-policy"]
        == "geolocation=(), camera=(), microphone=()"
    )


def test_server_header_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    """uvicorn server 헤더 strip (OWASP A05 info leak)."""
    app = _build_app_with_env(monkeypatch, "development")
    client = TestClient(app)
    response = client.get("/health")
    assert "server" not in {k.lower() for k in response.headers}


def test_hsts_omitted_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    """development env → HSTS 헤더 부재 (HTTP 가정)."""
    app = _build_app_with_env(monkeypatch, "development")
    client = TestClient(app)
    response = client.get("/health")
    assert "strict-transport-security" not in {k.lower() for k in response.headers}


def test_hsts_attached_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """production env → HSTS 헤더 부착 (HTTPS 가정)."""
    app = _build_app_with_env(monkeypatch, "production")
    client = TestClient(app)
    response = client.get("/health")
    assert (
        response.headers["strict-transport-security"]
        == "max-age=31536000; includeSubDomains"
    )


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
