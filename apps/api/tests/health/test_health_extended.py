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


@pytest.mark.asyncio
async def test_healthz_concurrent_requests_share_one_celery_inspect(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """동시 `/healthz` N 건은 inspect 를 **한 번만** 띄운다 (보안 감사 2026-11-19).

    inspect 1회가 공유 스레드풀 1칸 + broker 커넥션 1개를 수집 창 내내 쥐므로,
    익명 동시 요청마다 새로 띄우면 풀이 묶인다.
    """
    import asyncio

    calls = 0
    release = asyncio.Event()

    async def _ok_pg() -> tuple[str, str | None]:
        return ("ok", None)

    async def _slow_celery() -> tuple[int, str | None]:
        nonlocal calls
        calls += 1
        await release.wait()
        return (1, None)

    monkeypatch.setattr("src.health.router._check_postgres", _ok_pg)
    monkeypatch.setattr("src.health.router._check_redis", _ok_pg)
    monkeypatch.setattr("src.health.router._check_celery_workers", _slow_celery)

    pending = [asyncio.create_task(client.get("/healthz")) for _ in range(5)]
    await asyncio.sleep(0.05)
    release.set()
    responses = await asyncio.gather(*pending)

    assert [r.status_code for r in responses] == [200] * 5
    assert calls == 1


@pytest.mark.asyncio
async def test_healthz_concurrent_requests_share_one_db_and_redis_probe(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """동시 `/healthz` N 건은 Postgres·Redis 점검도 **한 번만** 돈다 (보안 감사 run-2).

    `SELECT 1` 은 앱 공용 DB 풀 1칸을 최대 5초 쥐고, Redis PING 은 상한 없는 풀에
    연결을 늘린다. 익명·rate limit 면제 경로라 요청마다 돌리면 동시 요청 수만큼 쌓인다.
    """
    import asyncio

    calls = {"pg": 0, "redis": 0}
    release = asyncio.Event()

    async def _slow_pg() -> tuple[str, str | None]:
        calls["pg"] += 1
        await release.wait()
        return ("ok", None)

    async def _ok_redis() -> tuple[str, str | None]:
        calls["redis"] += 1
        return ("ok", None)

    async def _ok_celery() -> tuple[int, str | None]:
        return (1, None)

    monkeypatch.setattr("src.health.router._check_postgres", _slow_pg)
    monkeypatch.setattr("src.health.router._check_redis", _ok_redis)
    monkeypatch.setattr("src.health.router._check_celery_workers", _ok_celery)

    pending = [asyncio.create_task(client.get("/healthz")) for _ in range(5)]
    await asyncio.sleep(0.05)
    release.set()
    responses = await asyncio.gather(*pending)

    assert [r.status_code for r in responses] == [200] * 5
    assert calls == {"pg": 1, "redis": 1}


@pytest.mark.asyncio
async def test_check_postgres_error_hides_connection_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """익명 응답의 오류 문구에 host:port · DB 이름이 실리지 않는다 — 클래스 이름만."""
    import src.common.database as database
    from src.health.router import _check_postgres

    class _BrokenEngine:
        def connect(self) -> None:
            raise OSError("connect to 10.0.0.5:5432 failed for role qb_secret db prod_db")

    monkeypatch.setattr(database, "engine", _BrokenEngine())

    status, err = await _check_postgres()
    assert status == "fail"
    assert err == "OSError"
