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
from src.trading.models import (  # noqa: F401 — metadata 등록 (trading.*)
    ExchangeAccount,
    KillSwitchEvent,
    Order,
    WebhookSecret,
)

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
        # trading schema는 SQLModel.metadata.create_all이 자동 생성하지 않으므로 명시.
        # Alembic T2 migration 전에도 test DB에서 create_all이 동작하도록 bootstrap.
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
    monkeypatch.setattr(
        "src.core.config.settings.ohlcv_provider", "fixture"
    )
