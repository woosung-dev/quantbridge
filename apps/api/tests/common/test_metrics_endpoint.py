"""GET /metrics endpoint — Sprint 9 Phase D (2026-08-11 fail-closed 전환).

- 토큰 **미설정** 시 401. ★종전 계약은 「dev default 는 인증 스킵 200」이었다 —
  production 만 `core/config.py` validator 가 막았고 dev·local·스테이징·컨테이너
  오조립은 전부 무인증 노출이었다. 그 fail-open 을 뒤집었다.
- 토큰 설정 시: header 없음 → 401, 잘못된 토큰 → 403, 일치 → 200
- 5 metric prefix 가 출력에 모두 포함 (올바른 bearer 로만 볼 수 있다)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from src.core.config import settings


async def test_metrics_endpoint_denies_when_token_unset(client: AsyncClient) -> None:
    """★settings.prometheus_bearer_token=None → 401 (2026-08-11 fail-closed 전환).

    이 파일이 2026-08-11 이전에 못 박고 있던 계약은 정확히 그 반대(200)였다.
    `_verify_prometheus_bearer` 를 `return` 으로 되돌리면 이 한 건이 red 가 된다.
    """
    # 혹시 다른 테스트가 set 했을 가능성에 대비해 명시적으로 리셋
    settings.prometheus_bearer_token = None

    response = await client.get("/metrics")
    assert response.status_code == 401, (
        f"토큰 미설정 시 /metrics 는 401 이어야 한다, got {response.status_code}"
    )


async def test_metrics_endpoint_returns_prometheus_format(client: AsyncClient) -> None:
    """올바른 bearer → 200 + Prometheus text format + 5 metric prefix."""
    token = "secret-token-xyz"
    settings.prometheus_bearer_token = SecretStr(token)
    try:
        response = await client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
    finally:
        settings.prometheus_bearer_token = None

    assert response.status_code == 200
    ctype = response.headers["content-type"]
    # prometheus_client 는 "text/plain; version=0.0.4; charset=utf-8" 형식
    assert "text/plain" in ctype

    body = response.text
    # 5 metric prefix 가 모두 registry 에 등록되어 노출되어야 함
    assert "qb_backtest_duration_seconds" in body
    assert "qb_order_rejected_total" in body
    assert "qb_kill_switch_triggered_total" in body
    assert "qb_ccxt_request_duration_seconds" in body
    assert "qb_active_orders" in body


async def test_metrics_endpoint_rejects_missing_bearer(client: AsyncClient) -> None:
    """토큰 설정 시, Authorization 헤더 없으면 401."""
    settings.prometheus_bearer_token = SecretStr("secret-token-xyz")
    try:
        r = await client.get("/metrics")
        assert r.status_code == 401
    finally:
        settings.prometheus_bearer_token = None


async def test_metrics_endpoint_rejects_wrong_bearer(client: AsyncClient) -> None:
    """토큰 설정 시, 다른 토큰이면 403."""
    settings.prometheus_bearer_token = SecretStr("secret-token-xyz")
    try:
        r = await client.get("/metrics", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 403
    finally:
        settings.prometheus_bearer_token = None


async def test_metrics_endpoint_accepts_valid_bearer(client: AsyncClient) -> None:
    """토큰 일치 시 200."""
    token = "secret-token-xyz"
    settings.prometheus_bearer_token = SecretStr(token)
    try:
        r = await client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "qb_backtest_duration_seconds" in r.text
    finally:
        settings.prometheus_bearer_token = None


@pytest.mark.parametrize("header_value", ["", "Basic foo", "bearer lowercase-prefix"])
async def test_metrics_endpoint_rejects_malformed_authorization(
    client: AsyncClient, header_value: str
) -> None:
    """Bearer prefix 가 아니거나 공백일 때 401."""
    settings.prometheus_bearer_token = SecretStr("secret-token-xyz")
    try:
        r = await client.get("/metrics", headers={"Authorization": header_value})
        assert r.status_code == 401
    finally:
        settings.prometheus_bearer_token = None
