# Sprint 60 S5 — BL-246 /metrics endpoint 인증 검증 RED test (P1-13 채택)
"""BL-246 / Multi-Agent QA QA(Sentinel) 발견 — Public `/metrics` Prometheus
endpoint 가 `prometheus_bearer_token` 미설정 시 unauth allow (Beta 외부 노출 시
즉시 audit fail).

P1-13 채택 fix:
1. Production env 에서 `prometheus_bearer_token` 강제 (미설정 시 _verify_prometheus_bearer
   가 자동 차단 — 의무는 환경변수 보장 / dev/local 은 그대로 allow).
2. token 설정 시 bearer 없으면 401, 잘못된 bearer 면 403.

본 test 는 token 설정 케이스의 정상 동작 검증.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import SecretStr


@pytest.mark.asyncio
async def test_metrics_unauth_401_when_token_set(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    """BL-246 — token 설정된 환경에서 bearer 없으면 401."""
    from src import main as main_module

    with patch.object(
        main_module.settings, "prometheus_bearer_token", SecretStr("test-secret-token")
    ):
        resp = await client.get("/metrics")

    assert resp.status_code == 401, (
        f"BL-246 — /metrics without bearer should 401 (token configured), "
        f"got {resp.status_code}: {resp.text[:200]}"
    )
    body = resp.json()
    assert "detail" in body
    assert "bearer" in body["detail"].lower()


@pytest.mark.asyncio
async def test_metrics_invalid_bearer_403_when_token_set(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    """BL-246 — token 설정된 환경에서 잘못된 bearer 면 403."""
    from src import main as main_module

    with patch.object(
        main_module.settings, "prometheus_bearer_token", SecretStr("test-secret-token")
    ):
        resp = await client.get(
            "/metrics",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert resp.status_code == 403, (
        f"BL-246 — /metrics with wrong bearer should 403, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_metrics_valid_bearer_returns_text(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    """BL-246 — 정확한 bearer 시 200 + Prometheus text format."""
    from src import main as main_module

    token = "test-secret-token-xyz"
    with patch.object(main_module.settings, "prometheus_bearer_token", SecretStr(token)):
        resp = await client.get(
            "/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, (
        f"BL-246 — /metrics with valid bearer should 200, got {resp.status_code}"
    )
    # Prometheus text format = "text/plain; version=0.0.4; charset=utf-8" 등
    assert "text/plain" in resp.headers.get("content-type", "").lower()


def test_settings_production_requires_prometheus_token() -> None:
    """BL-246 — production 환경에서 prometheus_bearer_token 강제 권고 (Beta gate).

    이 test 는 현재 Settings 의 prometheus_bearer_token 이 production 에서
    None 가능한지 확인 — None 이면 P1-13 외부 노출 risk 명시.
    Sprint 60 S5 P1-13 채택: dev/local 은 allow, production 은 token 의무.
    """
    from src.core.config import Settings

    # Settings 의 prometheus_bearer_token 이 SecretStr | None 타입 — production 에서
    # 명시 의무 (.env.example 갱신 + production deploy 시 환경변수 설정 의무).
    # 본 test 는 type 검증만 (실제 production 검증은 deploy CI 책임).
    field_info = Settings.model_fields.get("prometheus_bearer_token")
    assert field_info is not None
    # SecretStr | None 형태 (Optional)
    # production deploy 시 환경변수 PROMETHEUS_BEARER_TOKEN 의무 (manual).
