# Sprint 61 T-6 (BL-310) — /livez + HEALTHZ_CELERY_TIMEOUT_S env override 회귀 test
"""/livez 신규 endpoint + HEALTHZ_CELERY_TIMEOUT_S 환경변수 검증.

Multi-Agent QA 2026-05-17 (BL-310): /healthz 의 3s celery inspect timeout 이
Docker isolated mode broker round-trip 대비 너무 짧음 → false-503. /livez 분리로
K8s liveness probe restart loop 위험 차단 + env override 로 readiness probe 환경별 조정.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_livez_returns_200_always(client: AsyncClient) -> None:
    """/livez 는 dep check 없이 process up 만 확인 → 항상 200."""
    resp = await client.get("/livez")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


def test_get_celery_timeout_s_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """HEALTHZ_CELERY_TIMEOUT_S 미설정 시 default 8.0."""
    from src.health.router import _get_celery_timeout_s

    monkeypatch.delenv("HEALTHZ_CELERY_TIMEOUT_S", raising=False)
    assert _get_celery_timeout_s() == 8.0


def test_get_celery_timeout_s_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """env 설정 시 override (production 환경별 조정)."""
    from src.health.router import _get_celery_timeout_s

    monkeypatch.setenv("HEALTHZ_CELERY_TIMEOUT_S", "12.5")
    assert _get_celery_timeout_s() == 12.5


def test_get_celery_timeout_s_invalid_env_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """invalid env → fallback 8.0 (silent, raise 없음)."""
    from src.health.router import _get_celery_timeout_s

    monkeypatch.setenv("HEALTHZ_CELERY_TIMEOUT_S", "not_a_number")
    assert _get_celery_timeout_s() == 8.0
