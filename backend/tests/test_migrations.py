"""Alembic migration upgrade/downgrade round-trip 검증 + metadata drift 검증."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from alembic import command

# 모델 import (metadata 등록) — 누락 방지용 explicit import
from src.auth.models import User  # noqa: F401
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401
from src.market_data.models import OHLCV  # noqa: F401
from src.strategy.models import Strategy  # noqa: F401
from src.trading.models import (  # noqa: F401
    ExchangeAccount,
    FundingRate,
    KillSwitchEvent,
    Order,
    WebhookSecret,
)

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

    # metadata가 사용하는 schema 목록 (None은 default = public)
    schemas = {t.schema or "public" for t in SQLModel.metadata.tables.values()}

    try:
        async with engine.connect() as conn:
            alembic_tables = await conn.run_sync(
                lambda sync_conn: {
                    (schema, t): {
                        c["name"] for c in inspect(sync_conn).get_columns(t, schema=schema)
                    }
                    for schema in schemas
                    for t in inspect(sync_conn).get_table_names(schema=schema)
                }
            )
    finally:
        await engine.dispose()

    # SQLModel metadata 등록된 모델 테이블 — (schema, name) 키로 매핑
    metadata_tables = {
        (t.schema or "public", t.name): {c.name for c in t.columns}
        for t in SQLModel.metadata.tables.values()
    }

    # alembic_version 테이블 제외 (Alembic 전용 메타, public schema)
    alembic_tables.pop(("public", "alembic_version"), None)

    # metadata의 모든 table + column이 DB schema에 존재해야 함
    for (schema, table_name), metadata_cols in metadata_tables.items():
        full_name = f"{schema}.{table_name}"
        assert (schema, table_name) in alembic_tables, (
            f"Table '{full_name}' defined in SQLModel metadata but missing from alembic schema. "
            f"Migration 작성 누락?"
        )
        alembic_cols = alembic_tables[(schema, table_name)]
        missing = metadata_cols - alembic_cols
        assert not missing, (
            f"Table '{full_name}' missing columns in DB: {missing}. "
            f"Migration 누락 또는 drift 발생."
        )


def _upgrade_and_inspect(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    """alembic upgrade head 후 sync Inspector 반환 (engine 포함 — 호출자가 dispose)."""
    monkeypatch.chdir(_BACKEND_ROOT)
    cfg = _alembic_cfg()
    command.upgrade(cfg, "head")
    url = cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    engine = create_engine(url)
    inspector = inspect(engine)
    return engine, inspector


def test_trading_schema_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """trading schema + 4 테이블이 upgrade head 후 존재하는지 검증."""
    engine, inspector = _upgrade_and_inspect(monkeypatch)
    try:
        schemas = inspector.get_schema_names()
        assert "trading" in schemas, f"trading schema 누락. 실제: {schemas}"

        trading_tables = set(inspector.get_table_names(schema="trading"))
        assert trading_tables == {
            "exchange_accounts",
            "orders",
            "kill_switch_events",
            "webhook_secrets",
            "funding_rates",
        }, f"예상 5 테이블과 불일치: {trading_tables}"
    finally:
        engine.dispose()


def test_trading_orders_idempotency_unique(monkeypatch: pytest.MonkeyPatch) -> None:
    """orders.idempotency_key partial UNIQUE index 존재 검증."""
    engine, inspector = _upgrade_and_inspect(monkeypatch)
    try:
        indexes = inspector.get_indexes("orders", schema="trading")
        idem = [i for i in indexes if i["name"] == "uq_orders_idempotency_key"]
        assert len(idem) == 1
        assert idem[0]["unique"] is True
    finally:
        engine.dispose()
