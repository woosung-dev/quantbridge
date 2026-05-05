"""Sprint 30 ε B-tests — ``GET /healthz`` (Postgres / Redis / Celery 3-dep).

기존 ``GET /health`` (단순 status) 와 분리. ``/healthz`` 는 readiness probe 로
모든 dep 가 OK + worker ≥ 1 일 때만 200, 1+ fail 시 503.

Mock 패턴:
- ``_check_postgres`` / ``_check_redis`` / ``_check_celery_workers`` 를 monkeypatch.
- DB / Redis 실제 round-trip 회피 — pytest-asyncio + AsyncClient 충분.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_all_ok_returns_200(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """모든 dep OK + celery worker ≥ 1 → 200 + body."""

    async def _ok_pg() -> tuple[str, str | None]:
        return ("ok", None)

    async def _ok_redis() -> tuple[str, str | None]:
        return ("ok", None)

    async def _ok_celery() -> tuple[int, str | None]:
        return (2, None)

    monkeypatch.setattr("src.health.router._check_postgres", _ok_pg)
    monkeypatch.setattr("src.health.router._check_redis", _ok_redis)
    monkeypatch.setattr("src.health.router._check_celery_workers", _ok_celery)

    resp = await client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"db": "ok", "redis": "ok", "celery_workers": 2}


@pytest.mark.asyncio
async def test_healthz_postgres_fail_returns_503(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Postgres fail → 503 + body 안 db: 'fail' + errors.db."""

    async def _fail_pg() -> tuple[str, str | None]:
        return ("fail", "connection refused")

    async def _ok_redis() -> tuple[str, str | None]:
        return ("ok", None)

    async def _ok_celery() -> tuple[int, str | None]:
        return (1, None)

    monkeypatch.setattr("src.health.router._check_postgres", _fail_pg)
    monkeypatch.setattr("src.health.router._check_redis", _ok_redis)
    monkeypatch.setattr("src.health.router._check_celery_workers", _ok_celery)

    resp = await client.get("/healthz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["db"] == "fail"
    assert body["redis"] == "ok"
    assert body["celery_workers"] == 1
    assert "errors" in body
    assert "db" in body["errors"]
    assert "connection refused" in body["errors"]["db"]


@pytest.mark.asyncio
async def test_healthz_redis_fail_returns_503(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redis fail → 503 + body 안 redis: 'fail' + errors.redis."""

    async def _ok_pg() -> tuple[str, str | None]:
        return ("ok", None)

    async def _fail_redis() -> tuple[str, str | None]:
        return ("fail", "PING returned False")

    async def _ok_celery() -> tuple[int, str | None]:
        return (1, None)

    monkeypatch.setattr("src.health.router._check_postgres", _ok_pg)
    monkeypatch.setattr("src.health.router._check_redis", _fail_redis)
    monkeypatch.setattr("src.health.router._check_celery_workers", _ok_celery)

    resp = await client.get("/healthz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["db"] == "ok"
    assert body["redis"] == "fail"
    assert "errors" in body
    assert body["errors"]["redis"] == "PING returned False"


@pytest.mark.asyncio
async def test_healthz_zero_celery_workers_returns_503(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Celery 0 worker → 503 (정책: api 단독 부팅 시 503).

    DB/Redis 가 ok 여도 celery_workers == 0 이면 unhealthy.
    """

    async def _ok_pg() -> tuple[str, str | None]:
        return ("ok", None)

    async def _ok_redis() -> tuple[str, str | None]:
        return ("ok", None)

    async def _zero_celery() -> tuple[int, str | None]:
        return (0, "no workers responded")

    monkeypatch.setattr("src.health.router._check_postgres", _ok_pg)
    monkeypatch.setattr("src.health.router._check_redis", _ok_redis)
    monkeypatch.setattr("src.health.router._check_celery_workers", _zero_celery)

    resp = await client.get("/healthz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["db"] == "ok"
    assert body["redis"] == "ok"
    assert body["celery_workers"] == 0
    assert body["errors"]["celery"] == "no workers responded"


@pytest.mark.asyncio
async def test_healthz_all_fail_aggregates_errors(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """모든 dep fail → 503 + errors 안 3 항목 모두 포함 (단일 round-trip 묶음)."""

    async def _fail_pg() -> tuple[str, str | None]:
        return ("fail", "timeout after 5.0s")

    async def _fail_redis() -> tuple[str, str | None]:
        return ("fail", "Connection reset by peer")

    async def _fail_celery() -> tuple[int, str | None]:
        return (0, "broker unreachable")

    monkeypatch.setattr("src.health.router._check_postgres", _fail_pg)
    monkeypatch.setattr("src.health.router._check_redis", _fail_redis)
    monkeypatch.setattr("src.health.router._check_celery_workers", _fail_celery)

    resp = await client.get("/healthz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["db"] == "fail"
    assert body["redis"] == "fail"
    assert body["celery_workers"] == 0
    assert set(body["errors"].keys()) == {"db", "redis", "celery"}
