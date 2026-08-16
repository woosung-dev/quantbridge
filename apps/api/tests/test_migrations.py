"""Alembic migration upgrade/downgrade round-trip 검증 + metadata drift 검증."""

from __future__ import annotations

import os
import re
from hashlib import sha256
from pathlib import Path
from typing import Any, TypeAlias
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    JSON,
    DateTime,
    Numeric,
    String,
    Uuid,
    create_engine,
    inspect,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.sql.type_api import TypeEngine
from sqlmodel import SQLModel

from alembic import command

# 모델 import (metadata 등록) — 누락 방지용 explicit import
from src.auth.models import User  # noqa: F401
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401
from src.market_data.models import OHLCV  # noqa: F401
from src.strategy.models import Strategy  # noqa: F401
from src.trading.models import (  # noqa: F401
    ExchangeAccount,
    ExchangeExit,
    FundingRate,
    KillSwitchEvent,
    Order,
    WebhookSecret,
)
from tests import _db_guard

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

TypeDrift: TypeAlias = tuple[str, str, str, str, str]

# BL-749: 실제 alembic schema와 metadata가 이미 다른 타입은 여기 동결한다. 항목은
# (schema, table, column, db_type, metadata_type) 순서이며, 새 drift만 test failure로 만든다.
_TYPE_DRIFT_BASELINE: frozenset[TypeDrift] = frozenset()


def _normalize_postgresql_type(type_: TypeEngine[Any]) -> str:
    """PostgreSQL Inspector/SQLAlchemy metadata 타입을 비교용 표기로 통일한다."""
    # ★JSON 과 JSONB 를 한 낱말로 뭉치지 않는다 (2026-08-15 codex 적대 리뷰 P2). 둘은
    #   PostgreSQL 의 **서로 다른 물리 타입**이고, 뭉치면 모델은 `JSON` 인데 DB 는 `JSONB` 인
    #   drift 가 조용히 통과한다. 아래 compile 경로가 이미 그 둘을 다른 문자열로 낸다.
    #   ★실측(2026-08-15): 이 축을 켜도 현재 스키마의 drift 는 **0건**이라 게이트가 안 깨진다.
    if isinstance(type_, SAEnum) and type_.native_enum:
        # Reflection enum은 schema를, metadata enum은 보통 table schema를 상속한다.
        # ★**라벨 집합까지** 본다 (codex 적대 리뷰 P1). 이름만 보면 「같은 `backtest_status` 인데
        #   모델에만 `ARCHIVED` 가 추가된」 drift 가 통과하고, 그 값은 실행 시 PostgreSQL 이
        #   거부한다 — migration 누락의 전형이다. 순서는 무시한다(라벨 순서는 DDL 순서일 뿐).
        #   ★실측(2026-08-15): 이 축을 켜도 라벨 drift 는 **0건**이다.
        # ★이름 없는 native enum(`name=None`)이 `"ENUM:"` 으로 뭉치는 것은 **위음성이 아니다** —
        #   PostgreSQL 방언은 그것을 아예 컴파일하지 못하므로(`CompileError: PostgreSQL Enum type
        #   requires a name`, 2026-08-15 실측) 그런 컬럼은 DB 에도 metadata-DDL 에도 존재할 수 없다.
        #   ★이 분기를 `and type_.name` 으로 좁히면 남은 것이 아래 compile 경로로 떨어져
        #   **그 CompileError 로 검사기 자신이 죽는다.**
        labels = ",".join(sorted(type_.enums or []))
        return f"ENUM:{(type_.name or '').upper()}({labels})"

    compiled = type_.compile(dialect=postgresql.dialect())
    normalized = re.sub(r"\s+", " ", compiled).strip().upper()
    normalized = normalized.replace("CHARACTER VARYING", "VARCHAR")
    return re.sub(r",\s+", ",", normalized)


def _type_drifts_for_table(
    schema: str,
    table_name: str,
    db_columns: dict[str, TypeEngine[Any]],
    metadata_columns: dict[str, TypeEngine[Any]],
) -> set[TypeDrift]:
    """한 테이블의 공통 컬럼에서 type drift 5-튜플을 수집한다."""
    drifts: set[TypeDrift] = set()
    for column_name, metadata_type in metadata_columns.items():
        if column_name not in db_columns:
            continue
        db_type = _normalize_postgresql_type(db_columns[column_name])
        normalized_metadata_type = _normalize_postgresql_type(metadata_type)
        if db_type != normalized_metadata_type:
            drifts.add((schema, table_name, column_name, db_type, normalized_metadata_type))
    return drifts


def _assert_no_new_type_drifts(
    observed_type_drifts: set[TypeDrift], baseline: frozenset[TypeDrift] = _TYPE_DRIFT_BASELINE
) -> None:
    """동결 baseline 밖의 type drift는 검사 실패로 만든다."""
    new_type_drifts = observed_type_drifts - baseline
    assert not new_type_drifts, (
        "새 column type drift 발견 (schema, table, column, db_type, metadata_type): "
        f"{sorted(new_type_drifts)}. 기존 drift만 허용하려면 "
        "_TYPE_DRIFT_BASELINE에 정확한 5-튜플을 동결하라."
    )


@pytest.mark.parametrize(
    ("db_type", "metadata_type"),
    [
        pytest.param(postgresql.VARCHAR(32), String(32), id="varchar-length"),
        pytest.param(
            postgresql.TIMESTAMP(timezone=True), DateTime(timezone=True), id="timestamptz"
        ),
        pytest.param(postgresql.NUMERIC(20, 8), Numeric(20, 8), id="numeric-precision-scale"),
        pytest.param(postgresql.JSONB(), postgresql.JSONB(), id="jsonb-jsonb"),
        pytest.param(
            postgresql.ENUM("PENDING", "FILLED", name="order_status"),
            SAEnum("PENDING", "FILLED", name="order_status"),
            id="named-enum",
        ),
        pytest.param(postgresql.UUID(as_uuid=True), Uuid(as_uuid=True), id="uuid"),
    ],
)
def test_normalize_postgresql_type_accepts_equivalent_types(
    db_type: TypeEngine[Any], metadata_type: TypeEngine[Any]
) -> None:
    """동등한 PostgreSQL/SQLAlchemy 표현을 type drift로 오인하지 않는다."""
    assert _normalize_postgresql_type(db_type) == _normalize_postgresql_type(metadata_type)


def test_jsonb_and_json_are_not_the_same_type() -> None:
    """★JSON ↔ JSONB 를 한 낱말로 뭉치면 실제 drift 가 통과한다 (codex 적대 리뷰 P2).

    둘은 PostgreSQL 의 서로 다른 물리 타입이다. 실측(2026-08-15)으로 현재 스키마에는
    이 축의 drift 가 0건이라 켜도 게이트가 안 깨진다.
    """
    assert _normalize_postgresql_type(postgresql.JSONB()) != _normalize_postgresql_type(JSON())
    # ★양성 대조 — 같은 것끼리는 여전히 같다(과다 포획 방어)
    assert _normalize_postgresql_type(postgresql.JSONB()) == _normalize_postgresql_type(
        postgresql.JSONB()
    )


def test_same_enum_name_with_a_new_label_is_a_drift() -> None:
    """★이름이 같아도 **라벨 집합이 다르면 drift** 다 (codex 적대 리뷰 P1).

    모델에만 `ARCHIVED` 를 추가하고 migration 을 빠뜨리면, 이름 축만 보는 검사는 통과하지만
    그 값을 저장하는 순간 PostgreSQL 이 거부한다 — migration 누락의 전형이다.
    """
    db = postgresql.ENUM("QUEUED", "DONE", name="backtest_status")
    model = SAEnum("QUEUED", "DONE", "ARCHIVED", name="backtest_status")

    assert _normalize_postgresql_type(db) != _normalize_postgresql_type(model)
    # ★양성 대조 — 라벨 **순서**만 다른 것은 drift 가 아니다(DDL 순서일 뿐)
    assert _normalize_postgresql_type(
        postgresql.ENUM("DONE", "QUEUED", name="backtest_status")
    ) == _normalize_postgresql_type(db)


def test_an_unnamed_native_enum_cannot_exist_in_a_postgres_schema() -> None:
    """이름 없는 native enum 둘이 `"ENUM:"` 으로 뭉치는 것이 **왜 위음성이 아닌지**를 못박는다.

    2026-08-15 agy 교차 검토가 「값 집합이 다른 두 무명 enum 이 같다고 판정된다」를 P2 로 냈다.
    지적 자체는 정규화 함수만 보면 참이지만, **그런 컬럼은 PostgreSQL 스키마에 존재할 수 없다** —
    방언이 컴파일을 거부하므로 DDL 이 만들어지지 않는다. ★그래서 그 분기를 `and type_.name` 으로
    좁히는 「수리」는 오히려 **검사기를 CompileError 로 죽인다**(실제로 그렇게 고쳤다가 되돌렸다).
    이 테스트가 없으면 다음 사람이 같은 지적을 받고 같은 개악을 한다.
    """
    from sqlalchemy.exc import CompileError

    unnamed = SAEnum("PENDING", "FILLED")
    assert unnamed.name is None
    with pytest.raises(CompileError, match="requires a name"):
        unnamed.compile(dialect=postgresql.dialect())

    # 이름이 있으면 정상 — 그리고 이름이 다르면 타입도 다르다(양성/음성 한 쌍)
    named = SAEnum("PENDING", "FILLED", name="order_status")
    other = SAEnum("ADMIN", "USER", name="user_role")
    assert _normalize_postgresql_type(named) != _normalize_postgresql_type(other)


def test_empty_type_drift_baseline_rejects_a_string_length_mutation() -> None:
    """실제 모델의 String(32) → String(64) 변이는 빈 baseline에서 새 drift로 남는다."""
    symbol_column = ExchangeExit.__table__.c.symbol
    original_type = symbol_column.type
    symbol_column.type = String(64)
    try:
        observed = _type_drifts_for_table(
            "trading",
            "exchange_exits",
            {"symbol": postgresql.VARCHAR(32)},
            {"symbol": symbol_column.type},
        )
    finally:
        symbol_column.type = original_type

    assert observed == {("trading", "exchange_exits", "symbol", "VARCHAR(32)", "VARCHAR(64)")}
    with pytest.raises(AssertionError, match="새 column type drift"):
        _assert_no_new_type_drifts(observed, frozenset())


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


def test_strategy_version_migration_backfills_existing_backtests(monkeypatch) -> None:
    """BL-773: 기존 Backtest도 StrategyVersion 하나에 반드시 고정한다."""
    monkeypatch.chdir(_BACKEND_ROOT)
    cfg = _alembic_cfg()
    user_id = uuid4()
    strategy_id = uuid4()
    backtest_id = uuid4()
    pine_source = "//@version=5\nstrategy('migration A')\n"

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "20260817_0001")

    engine = create_engine(cfg.get_main_option("sqlalchemy.url"), poolclass=NullPool)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, auth_subject, is_active) "
                    "VALUES (:id, :auth_subject, true)"
                ),
                {"id": user_id, "auth_subject": "bl-773-migration"},
            )
            conn.execute(
                text(
                    "INSERT INTO strategies "
                    "(id, user_id, name, pine_source, pine_version, parse_status, is_archived, "
                    "created_at, updated_at) "
                    "VALUES (:id, :user_id, 'migration', :pine_source, 'v5', 'ok', false, "
                    "NOW(), NOW())"
                ),
                {"id": strategy_id, "user_id": user_id, "pine_source": pine_source},
            )
            conn.execute(
                text(
                    "INSERT INTO backtests "
                    "(id, user_id, strategy_id, symbol, timeframe, period_start, period_end, "
                    "initial_capital, status, created_at) "
                    "VALUES (:id, :user_id, :strategy_id, 'BTC/USDT', '1h', NOW(), NOW(), "
                    "10000, 'COMPLETED', NOW())"
                ),
                {"id": backtest_id, "user_id": user_id, "strategy_id": strategy_id},
            )
    finally:
        engine.dispose()

    try:
        command.upgrade(cfg, "head")
        engine = create_engine(cfg.get_main_option("sqlalchemy.url"), poolclass=NullPool)
        try:
            with engine.connect() as conn:
                version = (
                    conn.execute(
                        text(
                            "SELECT id, pine_source, source_hash, parser_version "
                            "FROM strategy_versions WHERE strategy_id = :strategy_id"
                        ),
                        {"strategy_id": strategy_id},
                    )
                    .mappings()
                    .one()
                )
                pinned_version_id = conn.execute(
                    text("SELECT strategy_version_id FROM backtests WHERE id = :id"),
                    {"id": backtest_id},
                ).scalar_one()
                missing = conn.execute(
                    text("SELECT count(*) FROM backtests WHERE strategy_version_id IS NULL")
                ).scalar_one()
        finally:
            engine.dispose()

        assert pinned_version_id == version["id"]
        assert version["pine_source"] == pine_source
        assert version["source_hash"] == sha256(pine_source.encode()).hexdigest()
        assert version["parser_version"] == "pine_v2"
        assert missing == 0
    finally:
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
    컬럼 누락 + PostgreSQL/SQLAlchemy 표현차를 정규화한 타입을 검사한다.
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
                        c["name"]: c["type"]
                        for c in inspect(sync_conn).get_columns(t, schema=schema)
                    }
                    for schema in schemas
                    for t in inspect(sync_conn).get_table_names(schema=schema)
                }
            )
    finally:
        await engine.dispose()

    # SQLModel metadata 등록된 모델 테이블 — (schema, name) 키로 매핑
    metadata_tables = {
        (t.schema or "public", t.name): {c.name: c.type for c in t.columns}
        for t in SQLModel.metadata.tables.values()
    }

    # alembic_version 테이블 제외 (Alembic 전용 메타, public schema)
    alembic_tables.pop(("public", "alembic_version"), None)

    # metadata의 모든 table + column이 DB schema에 존재해야 함.
    # 역방향 DB-only column, nullable/default/제약/인덱스는 BL-749 범위 밖이다.
    observed_type_drifts: set[TypeDrift] = set()
    for (schema, table_name), metadata_cols in metadata_tables.items():
        full_name = f"{schema}.{table_name}"
        assert (schema, table_name) in alembic_tables, (
            f"Table '{full_name}' defined in SQLModel metadata but missing from alembic schema. "
            f"Migration 작성 누락?"
        )
        alembic_cols = alembic_tables[(schema, table_name)]
        # ★두 매핑은 이제 `{컬럼: 타입}` 이다 — 이름 축은 **키 집합**으로 비교한다.
        #   타입 축을 켜며 값이 set → dict 로 바뀌었는데 이 줄이 집합 차 그대로 남아
        #   `TypeError: unsupported operand -` 로 죽었다(2026-08-15, [BL-749]).
        missing = set(metadata_cols) - set(alembic_cols)
        assert not missing, (
            f"Table '{full_name}' missing columns in DB: {missing}. Migration 누락 또는 drift 발생."
        )
        observed_type_drifts.update(
            _type_drifts_for_table(schema, table_name, alembic_cols, metadata_cols)
        )

    _assert_no_new_type_drifts(observed_type_drifts)


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


def test_trading_orders_list_sort_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ix_orders_account_created` 존재 + 컬럼 순서 검증 (2026-08-15 surface-truth · S5).

    ★**순서가 계약이다.** `OrderRepository.list_by_user` 는 계정으로 좁힌 뒤
    `created_at DESC` 로 정렬하므로 선두 컬럼이 `exchange_account_id` 여야 한다.
    뒤집으면 조인 축을 못 밀어 인덱스가 있으나 마나가 된다.

    ★★**`_upgrade_and_inspect` 만으로는 이 테스트가 무증거다** — 2026-08-15 실측으로
    확인했다. conftest 부트스트랩이 `create_all` + `alembic_version` **head stamp**([BL-741])
    를 하므로 `upgrade head` 는 **아무 마이그레이션도 실행하지 않고**, 인덱스는
    `models.py` metadata 에서 온다. 그 상태에서 **마이그레이션 파일의 컬럼 순서를 뒤집는
    변이를 심어도 19 passed 로 초록**이었다. 이것이 [BL-749] 가 적은 한계의 실사례다.
    ⇒ 여기서는 `downgrade base` → `upgrade head` 로 **마이그레이션 경로를 강제로 태운다**
    (`test_alembic_roundtrip` 이 세운 선례). 그러고 나서야 이 단언이 마이그레이션을 잰다.
    """
    monkeypatch.chdir(_BACKEND_ROOT)
    cfg = _alembic_cfg()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    engine, inspector = _upgrade_and_inspect(monkeypatch)
    try:
        indexes = inspector.get_indexes("orders", schema="trading")
        found = [i for i in indexes if i["name"] == "ix_orders_account_created"]
        assert len(found) == 1, (
            "ix_orders_account_created 가 alembic DB 에 없다 — 마이그레이션 "
            f"20260815_0002 를 확인해라 (실제 인덱스: {[i['name'] for i in indexes]})"
        )
        assert found[0]["column_names"] == ["exchange_account_id", "created_at"], (
            f"컬럼 순서가 계약과 다르다: {found[0]['column_names']}"
        )
        assert found[0]["unique"] is False, "한 계정이 같은 순간에 여러 주문을 가질 수 있다"
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
