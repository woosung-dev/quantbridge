"""익명 경로 IP 단위 rate limit — `/healthz` · `/api/v1/waitlist` (10초 30회).

Cloudflare Free 플랜의 rate limiting 자리(1/1)가 차서 앱으로 옮긴 규칙이다.
판별력: 미들웨어가 없으면 ① 의 31번째도 200 이다.
"""

from __future__ import annotations

import ipaddress

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from limits.storage import MemoryStorage

from src.common import anon_path_rate_limit as apl
from src.common import rate_limit as rl
from src.common.anon_path_rate_limit import ANON_PATH_LIMIT, AnonPathRateLimitMiddleware

LIMIT = ANON_PATH_LIMIT.amount


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    storage = MemoryStorage()
    monkeypatch.setattr(apl, "_storage", lambda: storage)
    # cloudflared 와 같은 배치 — peer 는 신뢰된 proxy, 실제 IP 는 CF-Connecting-IP.
    monkeypatch.setattr(rl, "_TRUSTED_NETS", [ipaddress.ip_network("127.0.0.1/32")])

    app = FastAPI()
    app.add_middleware(AnonPathRateLimitMiddleware)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"ok": "1"}

    @app.post("/api/v1/waitlist")
    async def waitlist() -> dict[str, str]:
        return {"ok": "1"}

    @app.post("/api/v1/webhooks/{token}")
    async def webhook(token: str) -> dict[str, str]:
        return {"ok": token}

    @app.get("/healthz/extra")
    async def other() -> dict[str, str]:
        return {"ok": "1"}

    return TestClient(app, client=("127.0.0.1", 50000))


def _ip(addr: str) -> dict[str, str]:
    return {"cf-connecting-ip": addr}


def test_over_limit_blocked_per_ip(client: TestClient) -> None:
    """① 같은 IP 31번째 → 429 + Retry-After 10."""
    for _ in range(LIMIT):
        assert client.get("/healthz", headers=_ip("1.1.1.1")).status_code == 200
    res = client.get("/healthz", headers=_ip("1.1.1.1"))
    assert res.status_code == 429
    assert res.headers["retry-after"] == "10"
    assert res.json()["detail"]["code"] == "rate_limit_exceeded"


def test_other_ip_not_affected(client: TestClient) -> None:
    """② 버킷은 IP 단위다."""
    for _ in range(LIMIT + 1):
        client.get("/healthz", headers=_ip("1.1.1.1"))
    assert client.get("/healthz", headers=_ip("2.2.2.2")).status_code == 200


def test_waitlist_path_limited(client: TestClient) -> None:
    for _ in range(LIMIT):
        assert client.post("/api/v1/waitlist", headers=_ip("3.3.3.3")).status_code == 200
    assert client.post("/api/v1/waitlist", headers=_ip("3.3.3.3")).status_code == 429


def test_webhook_and_other_paths_not_limited(client: TestClient) -> None:
    """③ 웹훅(TradingView 공유 IP)과 정확히 일치하지 않는 경로는 세지 않는다."""
    for _ in range(LIMIT + 5):
        assert client.post("/api/v1/webhooks/abc", headers=_ip("4.4.4.4")).status_code == 200
        assert client.get("/healthz/extra", headers=_ip("4.4.4.4")).status_code == 200


def test_storage_failure_fails_open(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """④ 저장소 장애 → 통과 (slowapi 와 같은 fail-open)."""

    def _boom(path: str, ip: str) -> bool:
        raise ConnectionError("redis down")

    monkeypatch.setattr(apl, "_hit", _boom)
    for _ in range(LIMIT + 5):
        assert client.get("/healthz", headers=_ip("5.5.5.5")).status_code == 200


def test_main_app_installs_anon_limit() -> None:
    """⑤ 실제 앱 배선."""
    from src.main import create_app

    app = create_app()
    assert any(m.cls is AnonPathRateLimitMiddleware for m in app.user_middleware)
