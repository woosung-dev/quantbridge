"""Alembic migration upgrade/downgrade round-trip 검증 + metadata drift 검증."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
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
from tests import _db_guard

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _resolved_test_db_url() -> str:
    """이 모듈이 파괴할 DB 의 DSN — 판정 본문은 `tests/_db_guard.py` 가 갖는다.

    ★exit-attribution — 이 모듈은 `command.downgrade(cfg, "base")` 로 **전 테이블을
    드롭**한다. `TEST_DATABASE_URL` 없이 `DATABASE_URL` 만 export 된 셸에서 이 파일을
    돌리면 종전에는 그 폴백이 개발 DB 를 향했고, 실제로 로컬 dogfood 데이터(주문 17행 ·
    거래소 계정의 암호화 API 키 · 전략 6종)가 전소했다.

    ★[BL-451] 판정을 여기서 **하지 않고** 위임한다. 종전에는 이 파일 안에만 가드가
    있어서 `tests/conftest.py` 의 세션 픽스처(`drop_all`)와 `alembic` CLI 는 맨몸이었다 —
    같은 판정이 세 곳에 흩어져 있으면 한 곳만 고쳐지는 날이 온다.
    """
    return _db_guard.resolve_test_dsn()


def _assert_disposable_database(url: str) -> None:
    """파괴적 마이그레이션 테스트가 버려도 되는 DB 를 향하는지 확인한다 (위임)."""
    _db_guard.assert_disposable(url)


def _alembic_cfg() -> Config:
    """Sprint 19 BL-083: psycopg2 sync DSN 변환은 conftest._to_psycopg2_url 사용."""
    from tests.conftest import _to_psycopg2_url

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _to_psycopg2_url(_resolved_test_db_url()))
    return cfg


def test_alembic_roundtrip(tmp_path, monkeypatch):
    """upgrade head → downgrade base → upgrade head가 모두 성공해야 함."""
    monkeypatch.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = _alembic_cfg()

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


async def test_upgrade_head_survives_the_create_all_bootstrap(monkeypatch, _test_engine):
    """`create_all` 로 만든 DB 에 `alembic upgrade head` 를 돌리면 통과해야 한다 ([BL-741]).

    ★이 단언은 2026-08-15 까지 레포에 **0건**이었다. 그래서 스키마는 모델-head 인데
    `alembic_version` 만 낡은 리비전으로 남는 상태가 아무에게도 안 걸렸고, 그 DB 에
    `upgrade head` 를 돌린 개발자만 `DuplicateTable`/`DuplicateObject` 로 죽었다.
    CI 는 fresh DB 라 영원히 초록이다.

    ★**낡은 리비전을 일부러 심는다.** 그러지 않으면 red 가 `test_alembic_roundtrip` 의
    실행 순서에 좌우된다 — 그 테스트가 먼저 돌면 `alembic_version` 이 이미 head 라
    수리 없이도 우연히 통과한다. 여기서는 head 바로 앞 리비전을 심어 **사고 상황을
    결정적으로 재현**하고, 그 위에서 conftest 의 부트스트랩 경로를 다시 태운다.
    """
    from tests.conftest import bootstrap_test_schema

    monkeypatch.chdir(_BACKEND_ROOT)
    cfg = _alembic_cfg()
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    assert head is not None, "alembic head 를 못 읽었다 — 이 테스트는 무의미하다"
    stale = script.get_revision(head).down_revision
    assert isinstance(stale, str) and stale, f"head({head}) 앞 리비전이 없다 — fixture 를 못 만든다"

    async with _test_engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
        )
        await conn.execute(text("DELETE FROM alembic_version"))
        await conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": stale}
        )
        # conftest 가 매 세션 하는 그 일 — 여기서 같은 경로를 그대로 태운다.
        await bootstrap_test_schema(conn)

    # 수리 전에는 여기서 `DuplicateObject`(이미 있는 인덱스를 또 만든다)로 죽는다.
    command.upgrade(cfg, "head")

    async with _test_engine.begin() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        assert result.scalar_one() == head


def test_stress_test_enum_labels_match_member_names(monkeypatch):
    """alembic 제공 DB 의 enum 라벨 = SAEnum 이 저장하는 member NAME 전체 (drift sentinel).

    functional-parity 2026-07-23 실측 — 최초 migration 의 소문자 라벨('monte_carlo',
    'walk_forward')이 잔존해 실 DB 에서 Monte Carlo / Walk-Forward 생성이 500
    (`invalid input value for enum stress_test_kind: "MONTE_CARLO"`). 테스트 DB 는
    metadata 생성이라 이 클래스의 드리프트를 못 잡았다 — 본 테스트가 alembic 경로의
    enum 라벨을 Python member NAME 과 직접 대조한다 (migration 20260723_0001 검증).
    """
    from sqlalchemy import text

    from src.stress_test.models import StressTestKind, StressTestStatus
    from tests.conftest import _to_psycopg2_url

    monkeypatch.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = _alembic_cfg()
    command.upgrade(cfg, "head")

    engine = create_engine(_to_psycopg2_url(_resolved_test_db_url()), poolclass=NullPool)
    try:
        with engine.connect() as conn:
            for enum_name, member_cls in (
                ("stress_test_kind", StressTestKind),
                ("stress_test_status", StressTestStatus),
            ):
                labels = {
                    row[0]
                    for row in conn.execute(
                        text(
                            "SELECT e.enumlabel FROM pg_enum e "
                            "JOIN pg_type t ON t.oid = e.enumtypid "
                            "WHERE t.typname = :name"
                        ),
                        {"name": enum_name},
                    )
                }
                member_names = {member.name for member in member_cls}
                missing = member_names - labels
                assert not missing, (
                    f"{enum_name} enum 에 SAEnum 저장값(member NAME) 누락: {missing} "
                    f"(라벨 실측: {sorted(labels)})"
                )
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_alembic_schema_matches_sqlmodel_metadata(monkeypatch):
    """alembic upgrade 후 실제 schema와 SQLModel.metadata가 일치하는지 검증.

    Migration drift 방지 — 모델 변경 시 Alembic migration 작성 누락 검출.
    핵심 컬럼 누락만 검사 (정확한 type 비교는 PostgreSQL ↔ Python type 차이로 어려움).
    """
    # Alembic upgrade head 선행 실행 — 테스트 단독 실행 시에도 idempotent 보장
    monkeypatch.chdir(_BACKEND_ROOT)
    command.upgrade(_alembic_cfg(), "head")

    # Sprint 19 BL-083: 격리 stack 호환 위해 conftest 우선순위 함수 사용.
    db_url = _resolved_test_db_url()
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
            f"Table '{full_name}' missing columns in DB: {missing}. Migration 누락 또는 drift 발생."
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
    """trading schema + 10 테이블이 upgrade head 후 존재하는지 검증.

    Sprint 26 Phase A 추가 — live_signal_sessions / live_signal_states /
    live_signal_events (Pine Signal Auto-Trading outbox + state).
    tier-c 추가 — alert_rules (세션별 손실한도/워치독 알림 규칙).
    exit-attribution 추가 — exchange_exits (거래소 원본 청산 원장).
    범위 축소로 exchange_exit_sync_state (과거 적재 경계) 는 도입 전에 걷어냈다.
    """
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
            # Sprint 26 Phase A — Pine Signal Auto-Trading
            "live_signal_sessions",
            "live_signal_states",
            "live_signal_events",
            # tier-c — 세션별 알림 규칙
            "alert_rules",
            # exit-attribution — 거래소 원본 청산 원장
            "exchange_exits",
        }, f"예상 10 테이블과 불일치: {trading_tables}"
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


def test_deactivation_reason_check_matches_the_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    """alembic 이 만든 CHECK 의 값 집합 = SessionDeactivationReason 전건 (drift sentinel, BL-571).

    ★이 테스트가 없으면 드리프트가 프로덕션에서만 터진다 — conftest 의 테스트 DB 는
    `metadata.create_all` 로 만들어지고 그 CHECK 표현식은 enum 에서 **생성**되므로 절대
    어긋나지 않는다. 마이그레이션에 동결된 사본만 어긋날 수 있고, 어긋나면 새 사유로
    세션을 죽이려는 순간 IntegrityError 로 **종료가 실패**한다(라벨 오염보다 나쁘다).
    stress_test enum 라벨 사고(`test_stress_test_enum_labels_match_member_names`)와 같은 형태다.
    """
    import re

    from sqlalchemy import text

    from src.trading.models import SessionDeactivationReason

    engine, _ = _upgrade_and_inspect(monkeypatch)
    try:
        with engine.connect() as conn:
            definition = conn.execute(
                text(
                    "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                    "JOIN pg_class t ON t.oid = c.conrelid "
                    "JOIN pg_namespace n ON n.oid = t.relnamespace "
                    "WHERE n.nspname = 'trading' AND t.relname = 'live_signal_sessions' "
                    "AND c.conname = :name"
                ),
                {"name": "ck_live_signal_sessions_deactivated_reason"},
            ).scalar_one_or_none()
    finally:
        engine.dispose()

    assert definition is not None, (
        "ck_live_signal_sessions_deactivated_reason 가 alembic DB 에 없다 — "
        "마이그레이션 20260801_0001 이 빠졌거나 이름이 바뀌었다."
    )
    ddl_values = set(re.findall(r"'([^']+)'", definition))
    enum_values = {str(member) for member in SessionDeactivationReason}
    assert ddl_values == enum_values, (
        f"CHECK 제약과 SessionDeactivationReason 이 어긋났다. "
        f"제약에만 있음: {sorted(ddl_values - enum_values)} / "
        f"enum 에만 있음: {sorted(enum_values - ddl_values)}. "
        "새 사유는 enum + 마이그레이션 + FE 라벨 3곳을 함께 고쳐야 한다."
    )


def test_destructive_migration_tests_refuse_a_non_disposable_database() -> None:
    """downgrade base 가 개발 DB 를 향하면 즉시 멈춰야 한다.

    exit-attribution 실사고 — TEST_DATABASE_URL 없이 DATABASE_URL 만 export 된 셸에서
    이 파일을 돌려 로컬 개발 DB 가 전소했다(주문 17행·거래소 계정 암호화 키·전략 6종).
    """
    with pytest.raises(RuntimeError, match="_test"):
        _assert_disposable_database("postgresql+asyncpg://u:p@localhost:5436/quantbridge")
    # 정상 경로는 통과한다.
    _assert_disposable_database("postgresql+asyncpg://u:p@localhost:5436/quantbridge_test")
