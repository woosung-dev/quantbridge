"""Sprint 30 ε B-tests health-only fixtures — DB 의존 회피.

상위 ``tests/conftest.py`` 의 ``client`` fixture 는 ``app`` → ``db_session``
→ ``_test_engine`` chain 으로 실제 Postgres ``quantbridge_test`` DB 연결을
시도. ``/healthz`` endpoint 는 ``_check_postgres`` / ``_check_redis`` /
``_check_celery_workers`` 를 monkeypatch 하므로 DB 가 필요 없음.

본 conftest 는 health-test 전용 lightweight ``client`` fixture 를 override —
``health.router`` 만 mount 한 minimal FastAPI app 으로 ASGITransport 연결.

Fixture override 우선순위: ``tests/health/conftest.py`` > ``tests/conftest.py``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Health-only client — DB / Redis / Celery 의존 없는 minimal app.

    상위 conftest 의 ``client`` 를 fixture name shadowing 으로 대체.
    """
    from src.health.router import router as health_router

    app = FastAPI()
    app.include_router(health_router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
