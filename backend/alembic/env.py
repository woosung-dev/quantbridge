"""Alembic 환경 설정 (async). SQLModel 메타데이터 기반 autogenerate."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context
from src.core.config import settings

# 도메인 models 를 import 하여 SQLModel.metadata 에 테이블이 등록되도록 함.
# Stage 3에서 각 도메인의 실제 models 가 정의되면 여기에 추가.
# (현재는 스캐폴드 단계이므로 빈 상태)
# from src.strategy import models as _strategy_models
# from src.backtest import models as _backtest_models
# ... (나머지 도메인)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# .env 기반 DB URL 주입
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = SQLModel.metadata


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


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
