"""Alembic 환경 설정.

URL 스킴에 따라 async (asyncpg) 또는 sync (psycopg2) 엔진을 자동 선택:
- +asyncpg → async_engine_from_config (운영/개발 기본)
- 그 외      → engine_from_config      (테스트 round-trip 등 sync 필요 시)
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context

# 도메인 models 를 import 하여 SQLModel.metadata 에 테이블이 등록되도록 함.
# 새 도메인 models 추가 시 여기에 import 라인을 추가한다.
from src.auth import models as _auth_models  # noqa: F401
from src.backtest import models as _backtest_models  # noqa: F401
from src.core.config import settings
from src.market_data import models as _market_data_models  # noqa: F401
from src.strategy import models as _strategy_models  # noqa: F401
from src.stress_test import models as _stress_test_models  # noqa: F401
from src.trading import models as _trading_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# .env 기반 DB URL 주입.
# cfg.set_main_option() 으로 외부 주입된 경우 (테스트 등) 덮어쓰지 않는다.
_injected_url = config.get_main_option("sqlalchemy.url")
if not _injected_url or _injected_url == "driver://user:pass@localhost/dbname":
    # alembic.ini 기본값이거나 미설정이면 settings 에서 주입
    config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = SQLModel.metadata


# ---------------------------------------------------------------------------
# ★[BL-451] 파괴적 CLI 가드 — `alembic downgrade` 가 개발 DB 를 향하는 것을 막는다.
# ---------------------------------------------------------------------------
#
# 왜 여기인가: 위 40행이 `settings.database_url`(= 개발 DB)을 주입한다. `pytest` 경로는
# `tests/_db_guard.py` 가 막지만 **수동 CLI 는 이 파일 말고 지날 곳이 없다**. 전수 확인 결과
# entrypoint · `make migrate` · `make migrate-isolated` · `scripts/final-gates.sh` ·
# `scripts/worktree-bootstrap.sh` 가 전부 이 파일을 지나며, 그 다섯은 모두 `upgrade` 다.
#
# ★**`upgrade` 는 의도적으로 통과시킨다.** 방향을 안 보고 막으면 파괴를 막는 가드가 아니라
#   alembic 을 막는 가드가 되어 위 다섯 경로가 전부 죽는다.
#
# ★**이 가드가 못 보는 표면이 하나 있다** — `command.downgrade(cfg, "base")` 처럼 파이썬에서
#   직접 부르면 `config.cmd_opts` 가 `None` 이라 방향을 알 수 없다. 그 표면은
#   `tests/_db_guard.py` + 루트 `tests/conftest.py::pytest_configure` 가 덮는다.
#   초록은 「통과했다」가 아니라 「내가 본 것 중에는 없었다」만 말한다(`backend/AGENTS.md` §10).
#
# 탈출구: `alembic -x allow_destructive=1 downgrade -1`. env 변수가 아니라 CLI 인자다 —
# `.env.example` 에 없는 환경 변수를 코드에서 참조하지 않는다(AGENTS.md Golden Rule).

_DESTRUCTIVE_GUARD_MARKER = "QB-GUARD-DESTRUCTIVE-ALEMBIC"


def _is_destructive_invocation() -> bool:
    """이번 호출이 `alembic downgrade` 인가.

    `alembic.config.CommandLine.main` 이 `cfg.cmd_opts = options` 를 심고, 그
    `options.cmd` 는 `(함수, positional, kwarg)` 다(alembic 1.18.4 실측). 파이썬에서
    `command.*` 를 직접 부른 경우에는 `cmd_opts` 가 없다 — 위 주석의 「못 보는 표면」.
    """
    cmd_opts = getattr(config, "cmd_opts", None)
    cmd = getattr(cmd_opts, "cmd", None)
    if not cmd:
        return False
    return getattr(cmd[0], "__name__", "") == "downgrade"


def _destructive_is_explicitly_allowed() -> bool:
    """`-x allow_destructive=…` 로 사용자가 명시적으로 허용했는가."""
    return bool(context.get_x_argument(as_dictionary=True).get("allow_destructive"))


def _guard_destructive_migrations() -> None:
    """파괴적 호출이 버려도 되지 않는 DB 를 향하면 **연결 전에** 멈춘다."""
    if not _is_destructive_invocation() or _destructive_is_explicitly_allowed():
        return

    from sqlalchemy.engine import make_url

    url = config.get_main_option("sqlalchemy.url") or ""
    database = make_url(url).database
    if database and database.endswith("_test"):
        return

    raise SystemExit(
        f"[{_DESTRUCTIVE_GUARD_MARKER}] 중단 — `alembic downgrade` 가 "
        f"database='{database}' 를 향한다. 버려도 되는 DB(_test 접미사)가 아니다.\n"
        "  downgrade 는 테이블을 드롭한다. 2026-07-25 에 이 경로로 로컬 개발 DB 가 "
        "전소했다(주문 17행 · 암호화된 API 키 · 전략 6종, API 키는 복구 불가).\n"
        "  먼저 백업해라: `make db-snapshot`\n"
        "  그래도 진행하려면: `alembic -x allow_destructive=1 downgrade <rev>`"
    )


_guard_destructive_migrations()


def _is_async_url() -> bool:
    """현재 설정된 URL 이 asyncpg 드라이버를 사용하는지 판별."""
    url = config.get_main_option("sqlalchemy.url") or ""
    return "+asyncpg" in url


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async() -> None:
    """asyncpg 드라이버 사용 시 async 경로."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online_sync() -> None:
    """psycopg2 등 sync 드라이버 사용 시 (테스트 round-trip 용)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    if _is_async_url():
        asyncio.run(run_migrations_online_async())
    else:
        run_migrations_online_sync()
