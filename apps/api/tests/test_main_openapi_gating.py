# Sprint 61 T-4 (BL-312) — production env 시 OpenAPI 익명 노출 차단 회귀 test
"""docs_url / redoc_url / openapi_url production gating.

Curious + QA Sentinel 페르소나 발견 (Multi-Agent QA 2026-05-17, integrated-report.html §3):
production 환경에서 /openapi.json (97870 bytes 전체 스키마) + /docs + /redoc 익명 200 응답 =
공격자 reconnaissance phase 즉시 완료. settings.is_production 가 True 일 때만 None 으로
비활성 → 404. dev / staging 은 노출 유지 (DX 보존).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _build_app_with_env(monkeypatch: pytest.MonkeyPatch, env: str):
    """app_env 를 강제 monkeypatch 후 create_app() 재실행.

    settings 는 module-level singleton 이라 monkeypatch 후 create_app() 의
    `_hide_docs = settings.is_production` 분기가 즉시 반영된다.
    """
    from src.core.config import settings
    from src.main import create_app

    monkeypatch.setattr(settings, "app_env", env)
    return create_app()


@pytest.mark.parametrize(
    "path",
    ["/openapi.json", "/docs", "/redoc"],
)
def test_openapi_endpoints_exposed_in_development(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """development env → OpenAPI / Swagger UI / Redoc 모두 200 (DX 보존)."""
    app = _build_app_with_env(monkeypatch, "development")
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 200, (
        f"development env 에서 {path} 가 200 이어야 한다 (실제 {response.status_code})"
    )


@pytest.mark.parametrize(
    "path",
    ["/openapi.json", "/docs", "/redoc"],
)
def test_openapi_endpoints_exposed_in_staging(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """staging env → OpenAPI / Swagger UI / Redoc 모두 200 (내부 QA 보존)."""
    app = _build_app_with_env(monkeypatch, "staging")
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 200, (
        f"staging env 에서 {path} 가 200 이어야 한다 (실제 {response.status_code})"
    )


@pytest.mark.parametrize(
    "path",
    ["/openapi.json", "/docs", "/redoc"],
)
def test_openapi_endpoints_blocked_in_production(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """production env → OpenAPI / Swagger UI / Redoc 모두 404 (attack surface 차단)."""
    app = _build_app_with_env(monkeypatch, "production")
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 404, (
        f"production env 에서 {path} 가 404 이어야 한다 (BL-312 회귀, 실제 {response.status_code})"
    )
