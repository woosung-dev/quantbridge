"""Sprint 3 공용 테스트 fixtures.

전략:
- 세션 스코프 엔진: quantbridge_test DB. 시작 시 SQLModel.metadata.drop_all + create_all.
  (빠른 경로 — Alembic round-trip은 tests/test_migrations.py 에서만 검증)
- 함수 스코프 db_session: connection + outer tx + savepoint 격리. 테스트 종료 시 전체 rollback.
- FastAPI app fixture는 get_async_session을 db_session으로 override.
- authed_user: 테스트용 User 레코드 생성.
- mock_authed_user: get_current_user dependency를 authed_user로 bypass (Task 7+에서 활성화).
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

from src.auth import better_auth_tables  # noqa: F401 — metadata 등록 (auth_* 5테이블)
from src.auth.models import User
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401 — metadata 등록
from src.common.database import get_async_session
from src.main import create_app
from src.market_data.models import OHLCV  # noqa: F401 — metadata 등록 (ts.ohlcv)

# ★[BL-788] 이 줄은 「없어도 초록이던」 것을 명시로 되돌린 것이다. 2026-08-17 실측 —
#   `optimization_runs` 는 위 `from src.main import create_app` 이 `src/main.py:447` 의
#   `app = create_app()` 을 태우고, 그것이 stress_test router → dependencies → service 를
#   지나며 **우연히** 등록해 주고 있었다. 그 배선 중 한 칸이 지연 import 로 바뀌면 조용히
#   사라진다. 범위는 우연이 아니라 이 목록이어야 한다(`test_metadata_table_coverage.py` ⑴).
from src.optimizer.models import OptimizationRun  # noqa: F401 — metadata 등록
from src.strategy.models import Strategy  # noqa: F401 — metadata 등록
from src.stress_test.models import StressTest  # noqa: F401 — metadata 등록
from src.trading.models import (  # noqa: F401 — metadata 등록 (trading.*)
    ExchangeAccount,
    KillSwitchEvent,
    Order,
    WebhookSecret,
)
from src.waitlist.models import WaitlistApplication  # noqa: F401 — metadata 등록
from tests import _db_guard

# -------------------------------------------------------------------------
# Path β Stage 2c C-1 — Mutation Oracle marker 기반 실행 제어 (Gate-3 codex
# W-2c1 / opus W-1 해소). 기본 pytest 실행에서는 `mutation` marker test 를
# 자동 skip (CI 시간 예산 ≤3분 보호). `--run-mutations` 명시 시 실행.
# ADR-020 §10.1 Q2 "nightly only" 결정의 실 구현.
# -------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """[BL-451] ★파괴적 DB 경로의 **최상단** 가드 — 다른 어떤 것보다 먼저 판정한다.

    red 면 고장난 것: `DATABASE_URL` 만 export 된 셸에서 스위트가 그대로 돌고,
    `_test_engine` 의 `SQLModel.metadata.drop_all` 이 개발 DB 를 겨냥한다.

    ★**왜 루트 conftest 인가.** 같은 판정이 `tests/real_broker/conftest.py` 에 있었지만
    그 파일은 **그 디렉터리를 수집할 때만** 로드된다. 착수 시점 실측 —
    `DATABASE_URL=<개발 DB>` 하나만 있는 셸에서

        pytest tests/real_broker/       → rc=3  (막혔다)
        pytest tests/trading/           → rc=0  ← 1088건 수집. 실행하면 drop_all 이 돈다
        pytest tests/test_migrations.py → rc=0

    루트 conftest 는 어느 하위 경로를 돌리든 로드되므로, 가드가 붙을 자리는 여기다.

    ★`pytest.fail` 이 아니라 `pytest.exit` 이다 — 하나의 테스트가 실패하는 것이 아니라
    **세션이 계속되면 안 되는 상황**이다(`tests/real_broker/conftest.py:71` 의 판단 승계).
    """
    reason = _db_guard.refusal_reason()
    if reason is not None:
        pytest.exit(f"[db-guard] {reason}", returncode=_db_guard.GUARD_EXIT_CODE)


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
# env 를 export 후 실행.
#
# ★[BL-451] 우선순위가 바뀌었다 — 종전 `TEST_DATABASE_URL > DATABASE_URL > default` 에서
#   **`DATABASE_URL` 폴백이 빠졌다.** 아래 `_test_engine` 이 이 DSN 에
#   `SQLModel.metadata.drop_all` 을 돌기 때문이다. 폴백이 개발 DB 를 겨냥해 실제로 전소시킨
#   전례가 있다. 판정 본문과 이유는 `tests/_db_guard.py`.
DB_URL = _db_guard.effective_dsn()


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
    sanitized_query = {k: v for k, v in url.query.items() if k not in asyncpg_only_keys}
    sync_url = url.set(drivername="postgresql+psycopg2", query=sanitized_query)
    return sync_url.render_as_string(hide_password=False)


def alembic_head_revision() -> str:
    """`alembic/versions/` 의 head 리비전. ★하드코딩 금지 — 다음 migration 이 들어오는 순간
    조용히 거짓이 된다. `alembic.ini` 의 `script_location` 이 상대경로(`alembic`)라 cwd 에
    의존하므로 여기서 절대경로로 덮어쓴다(conftest 는 chdir 할 수 없다)."""
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    if head is None:
        raise RuntimeError("alembic head 리비전을 못 읽었다 — 테스트 DB 를 stamp 할 수 없다")
    return head


async def bootstrap_test_schema(conn) -> None:
    """테스트 DB 스키마를 `metadata` 로 재생성한다 — `_test_engine` 의 본문.

    ★함수로 뽑아 둔 이유는 재사용이 아니라 **검증 가능성**이다([BL-741]).
    이 경로가 남기는 `alembic_version` 상태는 세션 픽스처 안에서만 만들어지므로,
    테스트가 같은 경로를 다시 태울 수 없으면 회귀를 **픽스처 실행 순서에 맡기게** 된다
    (그러면 CI 에서는 영원히 초록이다 — 그게 [BL-741] 이 숨어 있던 방식이다).
    """
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
    # ★`create_all` 이 만드는 것은 **이 순간 metadata 에 등록된** 테이블뿐이다. 그래서 이 파일
    #   머리의 모델 import 목록이 곧 스키마 범위다 — 하나라도 빠지면 그 테이블은 안 만들어진다.
    #   2026-08-17 실측: `src/auth/better_auth_tables.py` 를 **`alembic/env.py` 만** import 하고
    #   있어서 `auth_*` 5테이블이 여기서 안 만들어졌다. 그런데 아래 stamp 는 head 를 적으므로
    #   `test_migrations.py` 의 `downgrade base` 가 `DROP TABLE auth_jwks` 에서 죽는다
    #   (**fresh DB 에서만** — 이전에 migration 이 돈 DB 에는 그 테이블이 남아 있어 통과한다).
    await conn.run_sync(SQLModel.metadata.drop_all)
    await conn.run_sync(SQLModel.metadata.create_all)

    # ★`alembic_version` 은 `SQLModel.metadata` 밖이라 `drop_all` 이 안 지운다([BL-741]).
    #   그대로 두면 스키마는 방금 만든 **모델-head** 인데 버전만 낡은 리비전으로 남고,
    #   그 DB 에 `alembic upgrade head` 를 돌린 개발자가 이미 있는 객체를 또 만들어 죽는다
    #   (실측: `DuplicateTable: relation "ix_exchange_exits_account_order" already exists`).
    #   CI 는 fresh DB 라 이 상태에 도달하지 않아 영원히 초록이다.
    # ★지우기만 하면 안 된다 — 버전이 없으면 `upgrade head` 가 base 부터 돌아 **여전히 죽는다.**
    #   방금 metadata 로 head 스키마를 만들었으므로 head 로 stamp 하는 것이 **사실 진술**이고,
    # ★★**이 stamp 의 사실성은 부분적으로만 보증된다 — 그 한계를 여기 적어 둔다**(2026-08-15 codex P1).
    #   `test_alembic_schema_matches_sqlmodel_metadata` 는 **컬럼 이름 집합만**, 그것도
    #   `metadata_cols - alembic_cols` **한 방향**으로만 본다(그 함수 docstring 이 스스로
    #   「정확한 type 비교는 어렵다」고 적었다). ⇒ **타입·제약·인덱스가 갈린 경우는 못 잡는다.**
    #   즉 「create_all 스키마 ≡ migration 스키마」는 이름 층에서만 참이고, 그 아래층에서
    #   갈리면 이 stamp 는 조용히 거짓이 된다. 그 검사 확장은 [BL-749].
    #   ★단 그 위험은 이 변경이 **새로 만든 것이 아니다** — conftest 는 원래부터 `create_all` 로
    #     스키마를 만들었고 테스트는 늘 그 물리 스키마 위에서 돌았다. 이 stamp 가 바꾼 것은
    #     「alembic 이 그 DB 를 head 로 인식한다」 하나뿐이다.
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
    )
    await conn.execute(text("DELETE FROM alembic_version"))
    await conn.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
        {"v": alembic_head_revision()},
    )


@pytest_asyncio.fixture(scope="session")
async def _test_engine():
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await bootstrap_test_schema(conn)
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
        auth_subject=f"user_test_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        username="tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def mock_authed_user(app, authed_user):
    """get_current_user dependency를 authed_user로 bypass.

    Task 7~14 E2E 테스트에서 인증 경로를 우회할 때 사용.
    실제 JWT/JWKS 검증 테스트는 별도 (test_jwt_auth.py).
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


@pytest.fixture(autouse=True)
def _disable_pine_ast_disk_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """AST 디스크 캐시(BL-832)를 기본 비활성 — 테스트는 hermetic해야 한다.

    켜 두면 캐시가 **테스트 프로세스 사이에서도 살아남아** 파스 계수를 바꾼다.
    실제로 그렇게 됐다: 이 캐시를 넣자 n13의 `test_parse_call_census.py`가
    `assert 0 == 1`로 3건 red였고, 원인은 앞선 실행이 채운 `apps/api/.ast-cache`였다.
    계수를 세는 테스트가 어제 무엇을 돌렸는지에 의존하면 그것은 테스트가 아니다.

    캐시 자체를 검증하는 `test_parse_ast_disk_cache.py`는 자기 fixture로 tmp_path를
    덮어써서 이 기본값을 무력화한다.
    """
    monkeypatch.setattr("src.core.config.settings.pine_ast_cache_dir", "")


@pytest.fixture
def celery_eager(monkeypatch: pytest.MonkeyPatch):
    """Celery eager mode — task.apply() executes synchronously in-process."""
    from src.tasks.celery_app import celery_app

    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    return celery_app
