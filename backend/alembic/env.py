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
