# 2026-09-06 데이터 경로 조사 3-C — CORS 명시화 회귀.
"""단일 origin(`FRONTEND_URL`) · 메서드/요청 헤더 명시 목록 · preflight 600s · expose_headers.

종전 `allow_methods=["*"]`·`allow_headers=["*"]` 는 아무 헤더나 통과시켰고 `expose_headers` 가
없어 브라우저가 `X-RateLimit-*` 를 읽지 못했다. 이 파일은 **명시 목록의 판별력**(모르는 헤더·
다른 origin 은 400)과 노출 목록을 함께 잰다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

FRONTEND = "https://qb.example.test"
PREFLIGHT_PATH = "/api/v1/strategies"


def _build_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """`frontend_url` 을 고정한 뒤 create_app() — ambient `.env.local` 값에 기대지 않는다."""
    from src.core.config import settings
    from src.main import create_app

    monkeypatch.setattr(settings, "frontend_url", FRONTEND)
    monkeypatch.setattr(settings, "debug", True)
    return TestClient(create_app())


def _csv_set(value: str, *, lower: bool = False) -> set[str]:
    parts = (p.strip() for p in value.split(","))
    return {p.lower() if lower else p for p in parts if p}


def test_preflight_allows_frontend_origin_with_explicit_lists_and_600s_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)
    response = client.options(
        PREFLIGHT_PATH,
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type, idempotency-key",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-max-age"] == "600"
    assert _csv_set(response.headers["access-control-allow-methods"]) == {
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    }
    assert {"authorization", "content-type", "idempotency-key"} <= _csv_set(
        response.headers["access-control-allow-headers"], lower=True
    )


def test_preflight_rejects_request_header_outside_the_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`["*"]` 시절엔 어떤 헤더든 통과했다 — 명시 목록의 판별력은 여기서만 보인다."""
    client = _build_client(monkeypatch)
    response = client.options(
        PREFLIGHT_PATH,
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-not-allowed",
        },
    )
    assert response.status_code == 400


def test_preflight_rejects_other_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client(monkeypatch)
    response = client.options(
        PREFLIGHT_PATH,
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_simple_response_exposes_rate_limit_and_idempotency_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """서버가 내는 헤더를 브라우저가 **읽을 수 있게** 노출한다(종전엔 expose 목록이 없었다)."""
    client = _build_client(monkeypatch)
    response = client.get("/health", headers={"Origin": FRONTEND})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert {
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
        "X-Idempotency-Replayed",
        "Idempotency-Replayed",
    } <= _csv_set(response.headers["access-control-expose-headers"])
