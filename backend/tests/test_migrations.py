"""Alembic migration upgrade/downgrade round-trip 검증 + metadata drift 검증."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from alembic import command

# 모델 import (metadata 등록) — 누락 방지용 explicit import
from src.auth.models import User  # noqa: F401
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401
from src.strategy.models import Strategy  # noqa: F401

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option(
        "sqlalchemy.url",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test",
        ).replace("+asyncpg", ""),  # alembic은 sync driver 필요
    )
    return cfg


def test_alembic_roundtrip(tmp_path, monkeypatch):
    """upgrade head → downgrade base → upgrade head가 모두 성공해야 함."""
    monkeypatch.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = _alembic_cfg()

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.mark.asyncio
async def test_alembic_schema_matches_sqlmodel_metadata(monkeypatch):
    """alembic upgrade 후 실제 schema와 SQLModel.metadata가 일치하는지 검증.

    Migration drift 방지 — 모델 변경 시 Alembic migration 작성 누락 검출.
    핵심 컬럼 누락만 검사 (정확한 type 비교는 PostgreSQL ↔ Python type 차이로 어려움).
    """
    # Alembic upgrade head 선행 실행 — 테스트 단독 실행 시에도 idempotent 보장
    monkeypatch.chdir(_BACKEND_ROOT)
    command.upgrade(_alembic_cfg(), "head")

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test",
    )
    engine = create_async_engine(db_url, poolclass=NullPool)

    try:
        async with engine.connect() as conn:
            alembic_tables = await conn.run_sync(
                lambda sync_conn: {
                    t: {c["name"] for c in inspect(sync_conn).get_columns(t)}
                    for t in inspect(sync_conn).get_table_names()
                }
            )
    finally:
        await engine.dispose()

    # SQLModel metadata 등록된 모델 테이블
    metadata_tables = {
        t.name: {c.name for c in t.columns}
        for t in SQLModel.metadata.tables.values()
    }

    # alembic_version 테이블 제외 (Alembic 전용 메타)
    alembic_tables.pop("alembic_version", None)

    # metadata의 모든 table + column이 DB schema에 존재해야 함
    for table_name, metadata_cols in metadata_tables.items():
        assert table_name in alembic_tables, (
            f"Table '{table_name}' defined in SQLModel metadata but missing from alembic schema. "
            f"Migration 작성 누락?"
        )
        alembic_cols = alembic_tables[table_name]
        missing = metadata_cols - alembic_cols
        assert not missing, (
            f"Table '{table_name}' missing columns in DB: {missing}. "
            f"Migration 누락 또는 drift 발생."
        )
