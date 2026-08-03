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
import sys
import uuid
from collections.abc import AsyncGenerator, Generator, Iterable
from typing import Any
from unittest.mock import NonCallableMock

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
#
# Sprint 18 BL-080 (codex G.0 P1 #7): 격리 docker stack 은 redis 를 host port
# 6380 에 publish (docker-compose.isolated.yml `redis: 6380:6379`). 격리 stack
# 안에서 pytest 실행 시 `TEST_REDIS_LOCK_URL=redis://localhost:6380/3` 환경변수
# 를 export 후 실행 권장. 그래도 미설정 시 비격리 stack 의 6379 가 default.
if not os.environ.get("REDIS_LOCK_URL"):
    os.environ["REDIS_LOCK_URL"] = (
        os.environ.get("TEST_REDIS_LOCK_URL") or "redis://localhost:6379/3"
    )

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
# ADR-020 §10.1 Q2 "nightly only" 결정의 실 구현.
# -------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-mutations",
        action="store_true",
        default=False,
        help="Path β Mutation Oracle 실행. 기본은 skip — nightly workflow 또는 수동 실행.",
    )
    # Sprint 19 BL-085 (codex G.0 P1 #3): integration marker 별도 flag.
    # mutation 과 분리 처리 — `--run-mutations` 가 integration 도 활성화하지 않도록 보장.
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Real-DB prefork integration test 실행. 기본은 skip — 격리 docker stack 필요 + nightly.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """기본 실행에서 marker 별 자동 skip.

    Sprint 19 BL-085 (codex G.0 P1 #3): 기존 early return 패턴은 `--run-mutations`
    1개 flag 만으로 모든 marker skip 해제 — integration test 가 의도와 다르게 활성화될 risk.
    각 marker 를 독립적으로 처리하도록 분리.
    """
    skip_mutation = pytest.mark.skip(
        reason="Mutation Oracle — `pytest --run-mutations` 또는 nightly workflow 에서 실행"
    )
    skip_integration = pytest.mark.skip(
        reason="Real-DB integration — `pytest --run-integration` 필요 (격리 docker stack)"
    )
    run_mutations = config.getoption("--run-mutations")
    run_integration = config.getoption("--run-integration")
    for item in items:
        if "mutation" in item.keywords and not run_mutations:
            item.add_marker(skip_mutation)
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)


# -------------------------------------------------------------------------
# BL-583 — 테스트 대역이 프로덕션 모듈 전역으로 **영구 복사**되는 것을 잡는다.
#
# 왜. 테스트가 **클래스 정의 모듈**의 속성을 monkeypatch 한 상태에서 소비 모듈이 **처음**
# 적재되면, 그 소비 모듈 최상단의 `from … import X` 가 가짜를 자기 전역으로 복사한다.
# monkeypatch teardown 은 정의 모듈만 되돌리므로 **복사본은 세션 끝까지 남는다.**
# 2026-08-03 실측: 오염원 테스트 **4개**가 모듈 **3개**의 전역 **8개**를 그렇게 오염시켰다 —
# `src.tasks.trading` 6개(`OrderRepository`·`ExchangeAccountRepository`·
# `LiveSignalSessionRepository`·`ExchangeAccountService`·`BybitFuturesProvider`·
# `_dispatch_provider`) · `src.tasks.orphan_scanner.OrderRepository` ·
# `src.market_data.providers.timescale.CCXTProvider`. 관측된 피해는 무관한 테스트 **5건**
# (`tests/trading/test_cancel_order_task.py` 2 + `tests/trading/test_orphan_scanner.py` 3)이고,
# **어떤 파일이 함께 수집됐는지에 따라** red/green 이 바뀌었다. 그러면 「전부 통과」가 증거가
# 아니다.
#
# 창(window) = 한 항목의 setup~teardown 사이에 **처음** 적재된 `src.*` 모듈. 수집 시점 import
# 는 패치가 없어 안전하고, 이 창 밖에서는 복사가 일어날 수 없다.
#
# ★검사 지점은 teardown wrapper 의 post-yield 다 — 그때가 monkeypatch 되돌림 **뒤**다
#   (실측: 같은 배치의 프로브에서 `teardown-post` 가 원본 값으로 복귀). 그전에 보면 정당한
#   패치를 오염으로 오검출한다.
# ★이 가드가 **못 잡는 것**을 적어 둔다 (codex G1/G6 — 「가드 발화 0」을 「전역 오염이 없다」로
#   인용하지 마라):
#     1. 이미 적재된 모듈의 직접 변조 (창은 「처음 적재」만 본다)
#     2. 클로저나 객체 내부에 숨은 대역 (전역만 훑는다)
#     3. `sys.modules` 키의 모듈 객체 교체 (`patch.dict(sys.modules, …)`)
#     4. **창 안의 `importlib.reload` / `del sys.modules[name]` 후 재import** — 이름이 차집합에
#        없으므로 재복사를 못 본다 (현재 레포에서 그 관용구 사용 **0건**, 잠재 갭)
#     5. **비-Mock 대역** — `SimpleNamespace()`·`object()` 는 `__module__` 이 없고
#        `functools.partial` 은 `functools` 라 술어 2 에 안 걸린다 (실측)
# -------------------------------------------------------------------------

_MODULES_BEFORE_ITEM = pytest.StashKey[frozenset[str]]()


def leaked_test_doubles(module_names: Iterable[str]) -> list[str]:
    """`src.*` 모듈 전역에 남은 테스트 대역을 `"module.attr"` 로 열거한다.

    술어가 둘인 이유 — 하네스가 심는 것이 Mock 만이 아니다:
      1. `unittest.mock` 객체. `Mock`/`MagicMock`/`AsyncMock` 은 전부 `NonCallableMock` 하위다.
      2. **테스트 모듈에서 정의된** 객체(lambda·헬퍼·가짜 클래스). `monkeypatch.setattr` 에
         lambda 를 넘기는 곳이 `tests/` 에 126곳 있어, 1번만 보면 그 종류를 통째로 놓친다.
    프로덕션 모듈 전역에 둘 중 어느 것이든 있으면 그것은 정의상 누수다.
    """
    leaked: list[str] = []
    for module_name in sorted(module_names):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        for attr, value in list(vars(module).items()):
            if isinstance(value, NonCallableMock):
                leaked.append(f"{module_name}.{attr}")
                continue
            origin = getattr(value, "__module__", None)
            if isinstance(origin, str) and (origin == "tests" or origin.startswith("tests.")):
                leaked.append(f"{module_name}.{attr}")
    return leaked


def leaked_test_doubles_since(modules_before: frozenset[str]) -> list[str]:
    """스냅샷 **이후** 처음 적재된 `src.*` 모듈만 검사한다.

    ★창 계산을 술어와 **따로** 떼어 둔 이유는 판별력이다(codex G1 BLOCKING). 술어만
    함수로 두면 「스캔 범위를 없애는」 변이가 어떤 테스트도 red 로 만들지 못한다.
    """
    first_imported_here = {
        name for name in sys.modules.keys() - modules_before if name.startswith("src.")
    }
    return leaked_test_doubles(first_imported_here)


def _leak_report(leaked: list[str]) -> str:
    return (
        "★BL-583 — 이 테스트가 끝난 뒤에도 테스트 대역이 프로덕션 모듈 전역에 남아 있다:\n"
        + "\n".join(f"  - {entry}" for entry in leaked)
        + "\n\n이 테스트가 **클래스 정의 모듈**을 패치한 상태에서 위 모듈이 **처음** 적재됐다는"
        " 뜻이다 (소비 모듈 최상단의 `from … import X` 가 가짜를 자기 전역으로 복사하고,"
        " monkeypatch 는 정의 모듈만 되돌린다).\n"
        "고치는 법: 패치를 걸기 **전에** 그 모듈을 적재해라 (예: 하네스 진입부에"
        " `from src.tasks import trading as _preload_trading  # noqa: F401`"
        " — 별칭을 붙이면 두 줄 이상이어도 ruff RUF100 이 안 난다)."
    )


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> Generator[None, object, object]:
    """항목 시작 시점의 적재 목록을 남긴다 — fixture setup 보다 앞이어야 창이 안 좁아진다.

    ★`wrapper=True, tryfirst=True` 인 이유(codex G6 MAJOR) — 평범한 `tryfirst` 훅은 **다른
    플러그인의 setup wrapper 의 pre-yield 보다 뒤**다(실측 순서: `other-wrapper-pre` →
    `my-plain-tryfirst`). 그 플러그인이 pre-yield 에서 패치를 걸고 소비 모듈을 적재하면 창이
    그만큼 좁아진다. wrapper + tryfirst 면 내 pre-yield 가 가장 먼저 온다(실측으로 확인).
    """
    item.stash[_MODULES_BEFORE_ITEM] = frozenset(sys.modules)
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(
    item: pytest.Item, nextitem: pytest.Item | None
) -> Generator[None, object, object]:
    try:
        result = yield
    except BaseException as exc:
        # ★teardown 이 이미 터졌다. pluggy 는 그 예외를 이 `yield` 지점에 재발화하므로
        #   post-yield 검사는 통째로 건너뛰어진다(codex G1 MAJOR). 그렇다고 여기서 `fail` 을
        #   던지면 **원인 예외를 가린다.**
        #   `add_note` 를 쓰는 이유 — 예외를 만들지 않으므로 원본을 절대 가리지 않고,
        #   `filterwarnings = error` 가 켜져도 안전하며(경고는 그때 또 다른 예외가 된다),
        #   pytest 9 가 원인 예외 **바로 아래**에 그대로 출력한다(실측).
        leaked = _leaked_since_snapshot(item)
        if leaked:
            exc.add_note(_leak_report(leaked))
        raise
    leaked = _leaked_since_snapshot(item)
    if leaked:
        pytest.fail(_leak_report(leaked), pytrace=False)
    return result


def _leaked_since_snapshot(item: pytest.Item) -> list[str]:
    """스냅샷이 **없으면 검사하지 않는다.**

    ★기본값을 빈 집합으로 두면 창이 「지금까지 적재된 전부」로 벌어져, 선재 누수를 엉뚱한
    테스트에 귀속시킨다. 거짓 지목은 미검출보다 나쁘다 — 창을 모르면 조용히 넘긴다.
    """
    if _MODULES_BEFORE_ITEM not in item.stash:
        return []
    return leaked_test_doubles_since(item.stash[_MODULES_BEFORE_ITEM])


# Sprint 18 BL-080 (codex G.0 P1 #7): 격리 docker stack 은 db host port 5433
# (docker-compose.isolated.yml `db: 5433:5432`). 격리 stack 안에서 pytest 실행 시
# `TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge_test`
# env 를 export 후 실행. 우선순위: TEST_DATABASE_URL > DATABASE_URL > default.
DB_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test"
)


def _to_psycopg2_url(asyncpg_url: str) -> str:
    """Sprint 19 BL-083 — asyncpg DSN → psycopg2 sync DSN 변환.

    Alembic / SQLAlchemy sync engine 은 psycopg2 (또는 다른 sync driver) 필요.
    `sqlalchemy.engine.make_url()` 로 안전하게 파싱 + drivername 변경. 단순
    `.replace("+asyncpg", "")` 는 query string 의 asyncpg-specific 옵션 보존
    문제 회피 위해 사용 안 함.

    asyncpg-specific query params (e.g., `server_settings`, `command_timeout`)
    가 있으면 psycopg2 가 unknown param 으로 reject 가능 → 제거.

    codex G.0 P2 권장: `URL.set(drivername="postgresql+psycopg2")`.
    """
    from sqlalchemy.engine import make_url

    url = make_url(asyncpg_url)
    # asyncpg-only 옵션 제거 (psycopg2 가 reject 하는 키)
    asyncpg_only_keys = {"server_settings", "command_timeout", "ssl_negotiation"}
    sanitized_query = {
        k: v for k, v in url.query.items() if k not in asyncpg_only_keys
    }
    sync_url = url.set(drivername="postgresql+psycopg2", query=sanitized_query)
    return sync_url.render_as_string(hide_password=False)


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
