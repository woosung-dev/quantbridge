"""Sprint 3 공용 테스트 fixtures.

전략:
- 세션 스코프 엔진: quantbridge_test DB. 시작 시 SQLModel.metadata.drop_all + create_all.
  (빠른 경로 — Alembic round-trip은 tests/test_migrations.py 에서만 검증)
- 함수 스코프 db_session: connection + outer tx + savepoint 격리. 테스트 종료 시 전체 rollback.
- FastAPI app fixture는 get_async_session을 db_session으로 override.
- authed_user: 테스트용 User 레코드 생성.
- mock_clerk_auth: get_current_user dependency를 authed_user로 bypass (Task 7+에서 활성화).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

# Sprint 6 T3 — src.core.config.Settings.trading_encryption_keys is a required
# field (no default). src.core.config module evaluates `settings = get_settings()`
# at import time, so we MUST set TRADING_ENCRYPTION_KEYS before any import that
# transitively imports src.core.config. Generate a valid Fernet key on demand.
if not os.environ.get("TRADING_ENCRYPTION_KEYS"):
    from cryptography.fernet import Fernet as _Fernet

    os.environ["TRADING_ENCRYPTION_KEYS"] = _Fernet.generate_key().decode()

# Sprint 11 Phase C — Waitlist. `WAITLIST_TOKEN_SECRET` 은 InviteTokenService
# 가 생성자에서 길이 검증. 테스트에서 설정되지 않았다면 dummy secret 주입.
if not os.environ.get("WAITLIST_TOKEN_SECRET"):
    os.environ["WAITLIST_TOKEN_SECRET"] = "test-waitlist-token-secret-min-32-bytes-xxxx"
if not os.environ.get("RESEND_API_KEY"):
    os.environ["RESEND_API_KEY"] = "test-resend-api-key"
if not os.environ.get("WAITLIST_ADMIN_EMAILS"):
    # 테스트 fixture 의 authed_user 를 admin 으로 인정하려면 conftest authed_user fixture
    # 가 만드는 email 과 매칭 불가 (random) — 따라서 테스트는 override 로 admin 검증 우회.
    os.environ["WAITLIST_ADMIN_EMAILS"] = "admin@example.com"

# Sprint 11 Phase C — slowapi rate-limit storage. `.env.example` 의 기본값
# `redis://redis:6379/3` 은 Docker 내부 호스트명이라 로컬 pytest 에서 해석 불가.
# `@limiter.limit` 가 붙은 endpoint (예: POST /waitlist) 를 호출하는 테스트는
# Redis 연결을 실제로 시도 → ConnectionError 발생. swallow_errors=True 가 있어도
# evalsha 단계에서 Exception 으로 fall-through. localhost 로 override 하여
# docker compose up 중인 Redis (포트 6379) 를 사용하도록 강제.
if not os.environ.get("REDIS_LOCK_URL"):
    os.environ["REDIS_LOCK_URL"] = "redis://localhost:6379/3"

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from src.auth.models import User
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401 — metadata 등록
from src.common.database import get_async_session
from src.main import create_app
from src.market_data.models import OHLCV  # noqa: F401 — metadata 등록 (ts.ohlcv)
from src.strategy.models import Strategy  # noqa: F401 — metadata 등록
from src.stress_test.models import StressTest  # noqa: F401 — metadata 등록
from src.trading.models import (  # noqa: F401 — metadata 등록 (trading.*)
    ExchangeAccount,
    KillSwitchEvent,
    Order,
    WebhookSecret,
)
from src.waitlist.models import WaitlistApplication  # noqa: F401 — metadata 등록

# -------------------------------------------------------------------------
# Path β Stage 2c C-1 — Mutation Oracle marker 기반 실행 제어 (Gate-3 codex
# W-2c1 / opus W-1 해소). 기본 pytest 실행에서는 `mutation` marker test 를
# 자동 skip (CI 시간 예산 ≤3분 보호). `--run-mutations` 명시 시 실행.
# ADR-013 §10.1 Q2 "nightly only" 결정의 실 구현.
# -------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-mutations",
        action="store_true",
        default=False,
        help="Path β Mutation Oracle 실행. 기본은 skip — nightly workflow 또는 수동 실행.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """기본 실행에서 @pytest.mark.mutation 테스트를 자동 skip (ADR-013 §10.1 Q2)."""
    if config.getoption("--run-mutations"):
        return
    skip_mutation = pytest.mark.skip(
        reason="Mutation Oracle — `pytest --run-mutations` 또는 nightly workflow 에서 실행"
    )
    for item in items:
        if "mutation" in item.keywords:
            item.add_marker(skip_mutation)


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test",
)


@pytest_asyncio.fixture(scope="session")
async def _test_engine():
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        # ts schema는 SQLModel.metadata.create_all이 자동 생성하지 않으므로 명시.
        # timescaledb extension은 advisory_lock에는 불필요하지만 hypertable
        # 회귀 테스트(test_migrations.py)와 동일 환경 보장 위해 함께 보장.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ts;"))
        # trading schema는 SQLModel.metadata.create_all이 자동 생성하지 않으므로 명시적으로 bootstrap.
        # 이 라인은 영구적 — conftest 엔진은 Alembic이 아니라 metadata.create_all로 테이블을
        # 만들기 때문에, T2 migration(faa9ad7b4585)이 머지된 뒤에도 필요하다.
        # (Alembic 경로는 마이그레이션이 자체적으로 CREATE SCHEMA 한다.)
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS trading;"))
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Savepoint 격리 fixture — 매 테스트마다 깨끗한 상태."""
    connection = await _test_engine.connect()
    trans = await connection.begin()
    session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = session_maker()
    nested = await connection.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sess: Any, transaction: Any) -> None:
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        if trans.is_active:
            await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def app(db_session: AsyncSession) -> AsyncGenerator[FastAPI, None]:
    """FastAPI app + get_async_session override."""
    application = create_app()

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    application.dependency_overrides[get_async_session] = _override_session
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def authed_user(db_session: AsyncSession) -> User:
    """테스트용 User 생성."""
    user = User(
        clerk_user_id=f"user_test_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        username="tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def mock_clerk_auth(app, authed_user):
    """get_current_user dependency를 authed_user로 bypass.

    Task 7~14 E2E 테스트에서 인증 경로를 우회할 때 사용.
    실제 Clerk SDK 호출 테스트는 별도 (test_clerk_auth.py).
    """
    from src.auth.dependencies import get_current_user
    from src.auth.schemas import CurrentUser

    async def _fake_current_user() -> CurrentUser:
        return CurrentUser.model_validate(authed_user)

    app.dependency_overrides[get_current_user] = _fake_current_user
    yield authed_user
    # 명시적 cleanup — app fixture의 dependency_overrides.clear()에 의존하지 않음.
    # 혹시 teardown 순서/로직이 바뀌어도 override leak 방지.
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _force_fixture_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 테스트는 기본적으로 fixture provider 강제 — 외부 CCXT 호출 차단.

    Timescale/CCXT 경로를 명시적으로 테스트하는 곳(test_timescale_provider,
    test_ccxt_provider)은 provider를 직접 instantiate하므로 이 flag 영향 없음.
    """
    monkeypatch.setattr("src.core.config.settings.ohlcv_provider", "fixture")


@pytest.fixture
def celery_eager(monkeypatch: pytest.MonkeyPatch):
    """Celery eager mode — task.apply() executes synchronously in-process."""
    from src.tasks.celery_app import celery_app

    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    return celery_app
