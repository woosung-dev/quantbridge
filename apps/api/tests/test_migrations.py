"""Alembic migration upgrade/downgrade round-trip 검증 + metadata drift 검증."""

from __future__ import annotations

import os
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any, TypeAlias
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Numeric,
    String,
    Table,
    UniqueConstraint,
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
from sqlalchemy.schema import DefaultClause
from sqlalchemy.sql.type_api import TypeEngine
from sqlmodel import SQLModel

from alembic import command

# ★[BL-788] 여기 있던 「누락 방지용 explicit import」 목록(2026-04-16~)은 지웠다.
#   그 목록은 **범위를 정하는 세 번째 손 목록**이었는데 stress_test·waitlist·optimizer·
#   better_auth_tables 4개가 빠진 채 넉 달을 살았다 — 즉 「누락 방지」라는 이름과 반대로
#   누락을 가리는 쪽이었다. metadata 등록의 실제 범위는 `tests/conftest.py` 머리의 목록
#   하나이고(이 파일은 그 conftest 의 자식이라 늘 그 목록을 물려받는다), 그 목록이
#   빠짐없는지는 `tests/test_metadata_table_coverage.py` 가 지킨다.
#   ★아래 `ExchangeExit`·`LiveSignalEvent` 는 F401 이 아니라 **본문에서 쓰는 것**이다
#   (각각 type/default baseline 변이 테스트).
from src.trading.models import ExchangeExit, LiveSignalEvent
from tests import _db_guard

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_SQL_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")

TypeDrift: TypeAlias = tuple[str, str, str, str, str]
NullableDrift: TypeAlias = tuple[str, str, str, bool, bool]
DefaultValue: TypeAlias = str | None
DefaultDrift: TypeAlias = tuple[str, str, str, str, DefaultValue, DefaultValue]
IndexSignature: TypeAlias = tuple[tuple[str, ...], bool, str]
IndexDrift: TypeAlias = tuple[str, str, str, tuple[str, ...], bool, str, int]
CheckConstraintDrift: TypeAlias = tuple[str, str, str, str]

# BL-749: 실제 alembic schema와 metadata가 이미 다른 타입은 여기 동결한다. 항목은
# (schema, table, column, db_type, metadata_type) 순서이며, 새 drift만 test failure로 만든다.
_TYPE_DRIFT_BASELINE: frozenset[TypeDrift] = frozenset()

# BL-749: nullable 는 (schema, table, column, db_nullable, metadata_nullable) 순서다.
_NULLABLE_DRIFT_BASELINE: frozenset[NullableDrift] = frozenset()

# BL-803: server default 는 (schema, table, column, direction, model_default, db_default) 순서다.
#
# ★**[BL-806] 으로 6 → 0 이 됐다** (2026-08-18, quantbridge_w2_test 실측).
#   동결돼 있던 6건은 정규화 실패가 아니라 **마이그레이션이 `server_default` 를 넣었는데 모델은
#   python-side `default=` 만 선언한** 실재하는 비대칭이었다. `tests/conftest.py` 의 `create_all` 은
#   **모델**에서 스키마를 만들므로 그 6컬럼에서 **테스트 DB 와 프로덕션 스키마가 갈려 있었다**
#   ([BL-788] 과 같은 가족의 결함). 이제 여섯 모델 모두 `sa_column=Column(..., server_default=...)`
#   으로 마이그레이션 표기를 그대로 들고 있어 두 스키마가 이 축에서 같다.
#
#   ★값 표기는 **마이그레이션 원본을 그대로 베낀다**(`text("''")` · `text("0")` · `text("true")` ·
#     `text("1")` · `"pending"`). 표현이 갈리면 훗날 `alembic/env.py` 에 `compare_server_default`
#     를 켤 때 위양성이 난다 — 지금은 두 `context.configure()` 어디에도 없어 `alembic check` 가
#     이 축을 **안 본다**(2026-08-18 실측: 6컬럼을 다 바꿔도 `alembic check` rc=0 그대로).
#   ★**빈 baseline 은 「이 축에 drift 가 하나도 없다」는 뜻이다.** 하나라도 생기면 즉시 red 다 —
#     동결하려면 그 자리에 6-튜플과 **왜 못 고치는지**를 함께 남겨라.
#   ★★방향 라벨 주의: `model_only`(모델에만 server_default)가 생기면 마이그레이션이 모델을
#     안 따라온 것이라 `db_only` 보다 훨씬 위험하다.
_DEFAULT_DRIFT_BASELINE: frozenset[DefaultDrift] = frozenset()

# BL-749: 인덱스는 이름 대신 (컬럼 순서, unique 여부, partial predicate)와 방향·개수를 비교한다.
# 이름은 Alembic/SQLAlchemy 명명 규칙 차이로 안정적인 동등성 기준이 아니다.
# ★predicate 를 넣은 것은 2026-08-18 적대 리뷰 P1 때문이다 — 빼면 `WHERE ... IS NOT NULL` 을
#   지워도 초록이고, 그 인덱스 중 하나가 주문 멱등성 계약 자체다.
_INDEX_DRIFT_BASELINE: frozenset[IndexDrift] = frozenset()

# BL-803: CHECK는 (schema, table, direction, constraint_name) 순서다. 현존 모델 CHECK 3개는
# 전부 명명돼 있다. 이름 없는 CheckConstraint가 생기면 PG 자동 이름과의 비교가 불안정하므로,
# 그때만 정확한 양방향 drift를 이 baseline에 동결하고 이유를 이 자리 주석으로 남긴다.
_CHECK_CONSTRAINT_DRIFT_BASELINE: frozenset[CheckConstraintDrift] = frozenset()

# TimescaleDB 가 hypertable 생성 때 소유하는 시간 인덱스다. metadata 에 선언하지 않아야
# `create_all` 경로에서 중복 생성되지 않으므로, 모델 동등성 검사에서도 DB-only 로 보지 않는다.
_TIMESCALE_OWNED_INDEXES: frozenset[tuple[str, str, str]] = frozenset(
    {("ts", "ohlcv", "ohlcv_time_idx")}
)

# TimescaleDB CHECK 15개는 `_timescaledb_catalog` 소속이라 metadata schema 순회 범위 밖이다.
# 현재 metadata schema 안에 TimescaleDB 소유 CHECK는 없어서 비었다. 훗날 범위 안에서 만나면
# schema/table/name을 여기에 명시해 제외한다 — 접두사나 schema 와일드카드로 조용히 가리지 않는다.
_TIMESCALE_OWNED_CHECK_CONSTRAINTS: frozenset[tuple[str, str, str]] = frozenset()


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


def _nullable_drifts_for_table(
    schema: str,
    table_name: str,
    db_columns: dict[str, bool],
    metadata_columns: dict[str, bool],
) -> set[NullableDrift]:
    """한 테이블의 공통 컬럼에서 nullable drift 5-튜플을 수집한다."""
    drifts: set[NullableDrift] = set()
    for column_name, metadata_nullable in metadata_columns.items():
        if column_name not in db_columns:
            continue
        db_nullable = db_columns[column_name]
        if db_nullable != metadata_nullable:
            drifts.add((schema, table_name, column_name, db_nullable, metadata_nullable))
    return drifts


def _assert_no_new_nullable_drifts(
    observed_nullable_drifts: set[NullableDrift],
    baseline: frozenset[NullableDrift] = _NULLABLE_DRIFT_BASELINE,
) -> None:
    """동결 baseline 밖의 nullable drift는 검사 실패로 만든다."""
    new_nullable_drifts = observed_nullable_drifts - baseline
    assert not new_nullable_drifts, (
        "새 column nullable drift 발견 (schema, table, column, db_nullable, "
        f"metadata_nullable): {sorted(new_nullable_drifts)}. 기존 drift만 허용하려면 "
        "_NULLABLE_DRIFT_BASELINE에 정확한 5-튜플을 동결하라."
    )


def _strip_postgresql_type_casts(value: str) -> str:
    """PostgreSQL reflection이 덧붙인 `::type` 렌더링 인공물을 지운다.

    타입명을 열거하지 않는다. `jsonb`와 사용자 enum처럼 새 타입이 계속 늘어나므로
    `::<식별자>` 일반형을 지운다. `character varying`은 PostgreSQL의 두 낱말 타입 표기라
    `varying`만 같은 cast의 일부로 함께 허용한다.

    호출자는 SQL 문자열 리터럴 바깥 조각만 넘긴다.
    """
    return re.sub(
        r"::\s*[a-z_][a-z0-9_]*(?:\s+varying)?(?:\s*\[\])?",
        "",
        value,
        flags=re.IGNORECASE,
    )


def _split_sql_string_literals(value: str) -> list[tuple[bool, str]]:
    """SQL 문자열 리터럴과 그 바깥을 등장 순서대로 (is_literal, 조각) 로 나눈다.

    PostgreSQL 의 리터럴 안 작은따옴표 이스케이프(`''`)를 리터럴의 일부로 본다.
    """
    fragments: list[tuple[bool, str]] = []
    cursor = 0
    for match in _SQL_STRING_LITERAL.finditer(value):
        fragments.append((False, value[cursor : match.start()]))
        fragments.append((True, match.group()))
        cursor = match.end()
    fragments.append((False, value[cursor:]))
    return fragments


def _normalize_server_default(default: Any) -> DefaultValue:
    """`Column.server_default`와 Inspector default를 비교 가능한 표기로 낮춘다.

    이 축은 **`Column.server_default` ↔ Inspector `get_columns()[i]["default"]`** 만 본다.
    SQLModel의 python-side `default` / `default_factory`(예: `default_factory=uuid4`)는 DB에
    나타나지 않으므로 축 밖이다. 그것까지 drift로 세면 baseline 전체가 시끄러워진다.
    """
    if default is None:
        return None
    default_arg = getattr(default, "arg", default)
    raw_default = str(default_arg).strip()
    fragments = _split_sql_string_literals(raw_default)
    normalized_fragments = [
        (is_literal, fragment)
        if is_literal
        else (False, _strip_postgresql_type_casts(fragment.casefold()))
        for is_literal, fragment in fragments
    ]
    normalized = "".join(fragment for _, fragment in normalized_fragments).strip()
    literal_fragments = [fragment for is_literal, fragment in fragments if is_literal]
    if len(literal_fragments) == 1 and all(
        is_literal or not fragment.strip() for is_literal, fragment in normalized_fragments
    ):
        return literal_fragments[0][1:-1]
    return normalized


def _default_drifts_for_table(
    schema: str,
    table_name: str,
    db_defaults: dict[str, Any],
    metadata_server_defaults: dict[str, Any],
) -> set[DefaultDrift]:
    """한 테이블의 공통 컬럼에서 server default 양방향 drift를 수집한다."""
    drifts: set[DefaultDrift] = set()
    for column_name, metadata_default in metadata_server_defaults.items():
        if column_name not in db_defaults:
            continue
        normalized_metadata_default = _normalize_server_default(metadata_default)
        db_default = _normalize_server_default(db_defaults[column_name])
        if normalized_metadata_default == db_default:
            continue
        # ★**한 차이는 한 행이다.** 초판은 양쪽이 다 non-None 이면 `model_only` + `db_only`
        #   **두 행**을 냈는데, 그러면 ⑴ 라벨이 거짓말을 하고(`db_only` 인데 모델 값이 찍힌다)
        #   ⑵ **정지 규칙(`> 5`)이 행 수를 세므로 실효 문턱이 절반**이 된다 —
        #   진짜 mismatch 3건이면 6행이 되어 축이 스스로 동결된다 (2026-08-18 CONTROL).
        #   방향 라벨은 「어느 쪽에만 default 가 있나」를 뜻하고, 둘 다 있으면 `mismatch` 다.
        if normalized_metadata_default is None:
            direction = "db_only"
        elif db_default is None:
            direction = "model_only"
        else:
            direction = "mismatch"
        drifts.add(
            (
                schema,
                table_name,
                column_name,
                direction,
                normalized_metadata_default,
                db_default,
            )
        )
    return drifts


def _assert_no_new_default_drifts(
    observed_default_drifts: set[DefaultDrift],
    baseline: frozenset[DefaultDrift] = _DEFAULT_DRIFT_BASELINE,
) -> None:
    """동결 baseline 밖의 server default drift는 검사 실패로 만든다."""
    new_default_drifts = observed_default_drifts - baseline
    assert not new_default_drifts, (
        "새 server default drift 발견 (schema, table, column, direction, model_default, "
        f"db_default): {sorted(new_default_drifts)}. 기존 drift만 허용하려면 "
        "_DEFAULT_DRIFT_BASELINE에 정확한 6-튜플을 동결하라."
    )


def test_server_default_normalization_absorbs_postgres_render_artifacts() -> None:
    """같은 DB default의 모델/Inspector 표현은 한 표기로 낮아진다."""
    assert _normalize_server_default(text("NOW()")) == _normalize_server_default("now()")
    assert _normalize_server_default("[]") == _normalize_server_default("'[]'::jsonb")


def test_server_default_normalization_still_separates_different_values() -> None:
    """jsonb cast를 지워도 배열과 객체 default는 서로 달라야 한다."""
    assert _normalize_server_default("'[]'::jsonb") != _normalize_server_default("'{}'::jsonb")


def test_server_default_normalization_preserves_quoted_literals() -> None:
    """따옴표 리터럴 안의 캐스트 모양과 대소문자는 서로 다른 DEFAULT 로 남는다 (BL-808 ⑴)."""
    assert _normalize_server_default("'literal::jsonb'") != _normalize_server_default("'literal'")
    assert _normalize_server_default("'CaseSensitive'") != _normalize_server_default(
        "'casesensitive'"
    )
    # 리터럴 **바깥** 캐스트는 여전히 흡수된다 — 이 축이 죽으면 안 된다.
    assert _normalize_server_default("'{}'::jsonb") == _normalize_server_default("'{}'")
    assert _normalize_server_default(text("NOW()")) == _normalize_server_default("now()")


def test_empty_default_drift_baseline_rejects_a_server_default_mutation() -> None:
    """실제 status default를 바꾸면 빈 baseline에서 양방향 default drift로 남는다."""
    status_column = LiveSignalEvent.__table__.c.status
    original_server_default = status_column.server_default
    status_column.server_default = DefaultClause(text("'dispatched'"))
    try:
        observed = _default_drifts_for_table(
            "trading",
            "live_signal_events",
            {"status": "'pending'::character varying"},
            {"status": status_column.server_default},
        )
    finally:
        status_column.server_default = original_server_default

    # ★양쪽 다 default 가 있으므로 방향은 `mismatch` 이고 **행은 하나**다.
    #   두 행을 내면 정지 규칙(`> 5`)의 실효 문턱이 절반이 된다.
    assert observed == {
        ("trading", "live_signal_events", "status", "mismatch", "dispatched", "pending"),
    }
    with pytest.raises(AssertionError, match="새 server default drift"):
        _assert_no_new_default_drifts(observed, frozenset())


def _normalize_index_predicate(where: Any) -> str:
    """partial index 의 `WHERE` 를 모델↔DB 가 비교 가능한 문자열로 낮춘다.

    ★**서명에서 predicate 를 빼면 partial index 가 통째로 안 보인다** (2026-08-18 적대 리뷰 P1).
    `uq_orders_idempotency_key` 의 `WHERE idempotency_key IS NOT NULL` 을 migration 에서 지워도
    (컬럼, unique) 가 같아 초록이었다 — 그 인덱스는 **멱등성 계약 자체**라 조용히 넓어지면
    중복 주문이 통과한다. 레포에 `postgresql_where` 인덱스가 5개 있다.

    표현이 갈리는 것을 흡수한다 — PostgreSQL 은 reflection 에서 괄호를 씌우고(`(a IS NOT NULL)`)
    대소문자·공백도 원문과 다를 수 있다. 그래서 겉껍질 괄호·연속 공백·대소문자를 지운다.

    ★**렌더링 인공물 2종만 더 지운다** — 켜자마자 실측으로 나온 것이 정확히 이 한 쌍이다:
    모델 `status = 'pending'` ↔ DB `(status)::text = 'pending'::text`. varchar/enum 컬럼을
    리터럴과 비교하면 PostgreSQL 이 **양쪽에 `::text` 를 붙이고 식별자를 괄호로 감싼다.**
    ⑴ `::text`·`::character varying` 캐스트 접미 ⑵ 홑 식별자를 감싼 괄호 — 둘 다 의미가 없다.
    ★★**이 축은 `_strip_postgresql_type_casts`(default 축용 일반형)를 쓰지 않는다** (2026-08-18 CONTROL).
      일반형은 `::<식별자>` 를 전부 지우므로 `a::int = b` 와 `a::text = b` 가 같아진다 —
      이 축이 방금 적대 리뷰로 얻은 판별력을 새 축의 부수효과로 넓히지 않는다.
      default 축이 `::jsonb`·enum 캐스트를 필요로 하는 것은 그 축의 사정이고, 여기 옮겨 붙이지 마라.
    ★**그 이상은 하지 않는다.** 표현식을 파싱하기 시작하면 그 파서가 다음 결함의 출처가 된다.
    판별력이 남아 있다는 것은 `test_index_predicate_normalization_*` 둘이 고정한다 —
    같은 술어는 같게, **다른 술어는 다르게** 낮춘다.
    """
    if where is None:
        return ""
    text_form = str(where).strip()
    while text_form.startswith("(") and text_form.endswith(")"):
        text_form = text_form[1:-1].strip()
    text_form = text_form.lower()
    text_form = re.sub(r"::\s*(text|character varying|varchar)\b", "", text_form)
    text_form = re.sub(r"\(\s*([a-z_][a-z0-9_]*)\s*\)", r"\1", text_form)
    return " ".join(text_form.split())


def test_index_predicate_normalization_absorbs_postgres_render_artifacts() -> None:
    """모델 원문과 PostgreSQL reflection 원문이 **같은 술어면 같게** 낮아진다.

    이 한 쌍은 지어낸 것이 아니라 2026-08-18 에 축을 켜자마자 나온 **실측**이다
    (`trading.live_signal_events` 의 `ix_live_signal_events_pending`).
    """
    assert _normalize_index_predicate("status = 'pending'") == _normalize_index_predicate(
        "(status)::text = 'pending'::text"
    )
    assert _normalize_index_predicate("idempotency_key IS NOT NULL") == _normalize_index_predicate(
        "(idempotency_key IS NOT NULL)"
    )


def test_index_predicate_normalization_still_separates_different_predicates() -> None:
    """정규화가 **판별력을 버리지 않았다**는 것을 고정한다.

    ★캐스트를 지우는 규칙은 지나치면 서로 다른 술어를 한 낱말로 뭉갠다. 그러면 partial index
    를 넣은 이유(=그 조건)가 조용히 사라진다 — 이 축을 켠 목적 자체가 무효가 된다.
    """
    assert _normalize_index_predicate("status = 'pending'") != _normalize_index_predicate(
        "status = 'done'"
    )
    assert _normalize_index_predicate("resolved_at IS NULL") != _normalize_index_predicate(
        "resolved_at IS NOT NULL"
    )
    # predicate 가 아예 없는 인덱스와 있는 인덱스는 절대 같아선 안 된다.
    assert _normalize_index_predicate(None) != _normalize_index_predicate("is_active = true")


def _index_signature(
    column_names: tuple[str, ...], unique: bool, where: str = ""
) -> IndexSignature:
    """이름과 무관한 인덱스/UNIQUE 비교 단위를 만든다."""
    assert column_names, "인덱스/UNIQUE 컬럼 목록이 비었다 — 비교를 계속하면 무의미하다"
    return (column_names, unique, where)


def _metadata_index_signatures(table: Table) -> Counter[IndexSignature]:
    """SQLModel table 의 Index + UniqueConstraint 를 구조 서명으로 모은다."""
    signatures: Counter[IndexSignature] = Counter()
    for index in table.indexes:
        where = index.dialect_options.get("postgresql", {}).get("where")
        signatures[
            _index_signature(
                tuple(column.name for column in index.columns),
                bool(index.unique),
                _normalize_index_predicate(where),
            )
        ] += 1
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            # UNIQUE 제약에는 partial predicate 가 없다 (그건 partial unique **인덱스** 쪽이다).
            signatures[
                _index_signature(tuple(column.name for column in constraint.columns), unique=True)
            ] += 1
    return signatures


def _db_index_signatures(
    schema: str,
    table_name: str,
    indexes: list[dict[str, Any]],
    unique_constraints: list[dict[str, Any]],
    primary_key: dict[str, Any],
) -> Counter[IndexSignature]:
    """Inspector 의 Index + UNIQUE 를 모델과 같은 구조 서명으로 모은다."""
    signatures: Counter[IndexSignature] = Counter()
    primary_key_name = primary_key.get("name")
    primary_key_columns = tuple(primary_key.get("constrained_columns") or ())

    for index in indexes:
        column_names = tuple(index.get("column_names") or ())
        index_name = index.get("name")
        if index_name == primary_key_name and column_names == primary_key_columns:
            # PK 를 지탱하는 암묵 인덱스는 SQLModel `table.indexes` 소유가 아니다.
            continue
        if (schema, table_name, index_name) in _TIMESCALE_OWNED_INDEXES:
            # hypertable 이 만드는 시간 인덱스는 TimescaleDB 소유다.
            continue
        if index.get("duplicates_constraint"):
            # PostgreSQL reflection 은 UNIQUE constraint 의 보조 인덱스를 함께 낼 수 있다.
            # 아래 get_unique_constraints() 경로에서 한 번만 센다.
            continue
        where = (index.get("dialect_options") or {}).get("postgresql_where")
        signatures[
            _index_signature(
                column_names, bool(index.get("unique")), _normalize_index_predicate(where)
            )
        ] += 1

    for constraint in unique_constraints:
        signatures[_index_signature(tuple(constraint.get("column_names") or ()), unique=True)] += 1
    return signatures


def _index_drifts_for_table(
    schema: str,
    table_name: str,
    db_indexes: Counter[IndexSignature],
    metadata_indexes: Counter[IndexSignature],
) -> set[IndexDrift]:
    """한 테이블의 모델→DB와 DB→모델 인덱스/UNIQUE drift를 모두 수집한다."""
    drifts: set[IndexDrift] = set()
    for (column_names, unique, where), count in (metadata_indexes - db_indexes).items():
        drifts.add((schema, table_name, "model_only", column_names, unique, where, count))
    for (column_names, unique, where), count in (db_indexes - metadata_indexes).items():
        drifts.add((schema, table_name, "db_only", column_names, unique, where, count))
    return drifts


def _assert_no_new_index_drifts(
    observed_index_drifts: set[IndexDrift],
    baseline: frozenset[IndexDrift] = _INDEX_DRIFT_BASELINE,
) -> None:
    """동결 baseline 밖의 인덱스/UNIQUE drift는 검사 실패로 만든다."""
    new_index_drifts = observed_index_drifts - baseline
    assert not new_index_drifts, (
        "새 index/UNIQUE drift 발견 (schema, table, direction, columns, unique, where, count): "
        f"{sorted(new_index_drifts)}. 기존 drift만 허용하려면 "
        "_INDEX_DRIFT_BASELINE에 정확한 7-튜플을 동결하라."
    )


def _metadata_check_constraint_names(table: Table) -> set[str]:
    """SQLModel metadata에 선언된 명명 CHECK 제약 이름을 모은다."""
    names: set[str] = set()
    for constraint in table.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        assert isinstance(constraint.name, str) and constraint.name, (
            f"Table '{table.fullname}'의 CheckConstraint에 이름이 없다. PostgreSQL 자동 이름은 "
            "metadata 이름 집합과 안정적으로 비교할 수 없으므로, 현존 제약이면 정확한 양방향 "
            "drift를 _CHECK_CONSTRAINT_DRIFT_BASELINE에 동결하고 이유를 남겨라."
        )
        names.add(constraint.name)
    return names


def _db_check_constraint_names(
    schema: str, table_name: str, check_constraints: list[dict[str, Any]]
) -> set[str]:
    """Inspector CHECK 목록에서 명시적으로 허용된 TimescaleDB 소유분을 제외한다."""
    names: set[str] = set()
    for constraint in check_constraints:
        constraint_name = constraint.get("name")
        assert isinstance(constraint_name, str) and constraint_name, (
            f"Table '{schema}.{table_name}'의 Inspector CHECK에 이름이 없다 — 이름 집합 비교를 "
            "계속하면 무의미하다"
        )
        if (schema, table_name, constraint_name) in _TIMESCALE_OWNED_CHECK_CONSTRAINTS:
            # TimescaleDB가 소유한 제약은 metadata에 선언하면 create_all 경로가 중복 생성할 수 있다.
            continue
        names.add(constraint_name)
    return names


def _check_constraint_drifts_for_table(
    schema: str,
    table_name: str,
    db_constraint_names: set[str],
    metadata_constraint_names: set[str],
) -> set[CheckConstraintDrift]:
    """한 테이블의 CHECK 이름 집합을 모델→DB와 DB→모델 양방향으로 비교한다.

    CHECK 식은 비교하지 않는다. PostgreSQL은 enum cast를 붙이고 `IN (...)`을 `= ANY(ARRAY...)`로
    재작성해 같은 제약도 구조가 달라지므로, 식 비교는 상시 잡음을 만들어 이 축을 꺼지게 한다.
    이름 집합은 제약의 조용한 소실과 migration-only 제약을 정확히 잡는다. 리터럴 집합 정확성은
    `test_deactivation_reason_check_matches_the_enum`가 `pg_get_constraintdef()`로 별도 검증한다.
    """
    drifts: set[CheckConstraintDrift] = set()
    for constraint_name in metadata_constraint_names - db_constraint_names:
        drifts.add((schema, table_name, "model_only", constraint_name))
    for constraint_name in db_constraint_names - metadata_constraint_names:
        drifts.add((schema, table_name, "db_only", constraint_name))
    return drifts


def _assert_no_new_check_constraint_drifts(
    observed_check_constraint_drifts: set[CheckConstraintDrift],
    baseline: frozenset[CheckConstraintDrift] = _CHECK_CONSTRAINT_DRIFT_BASELINE,
) -> None:
    """동결 baseline 밖의 CHECK 이름 drift는 검사 실패로 만든다."""
    new_check_constraint_drifts = observed_check_constraint_drifts - baseline
    assert not new_check_constraint_drifts, (
        "새 CHECK constraint drift 발견 (schema, table, direction, constraint_name): "
        f"{sorted(new_check_constraint_drifts)}. 기존 drift만 허용하려면 "
        "_CHECK_CONSTRAINT_DRIFT_BASELINE에 정확한 4-튜플을 동결하라."
    )


def test_check_constraint_name_drifts_detects_a_model_only_name() -> None:
    """모델에만 남은 CHECK 이름은 migration 누락으로 잡힌다."""
    assert _check_constraint_drifts_for_table(
        "trading",
        "alert_rules",
        set(),
        {"ck_alert_rules_type_threshold"},
    ) == {("trading", "alert_rules", "model_only", "ck_alert_rules_type_threshold")}


def test_check_constraint_name_drifts_detects_a_db_only_name() -> None:
    """migration에만 남은 CHECK 이름은 metadata 누락으로 잡힌다."""
    assert _check_constraint_drifts_for_table(
        "trading",
        "alert_rules",
        {"ck_alert_rules_type_threshold"},
        set(),
    ) == {("trading", "alert_rules", "db_only", "ck_alert_rules_type_threshold")}


def _is_externally_owned_db_only_table(schema: str, table_name: str) -> bool:
    """DB→모델 비교에서 우리 SQLModel 엔티티 소유가 아닌 표만 제외한다."""
    # `alembic_version` 은 Alembic 이 스스로 만들고 관리하는 상태 메타라 우리 모델에 없다.
    #
    # ★★**`auth_*` 를 여기서 뺐다** (2026-08-18 적대 리뷰 P2). 종전 주석은 그것을 「Better Auth 가
    #   읽고 쓰는 외부 소유 표」라 적었는데 **코드 대조로 거짓이었다** — `src/auth/better_auth_tables.py`
    #   가 다섯 표를 **`SQLModel.metadata` 에 직접 선언**하고(`sa.Table(..., SQLModel.metadata, ...)`)
    #   DDL 도 이 저장소의 alembic revision 이 소유한다. 그 파일의 머리 주석이 스스로 말한다 —
    #   그렇게 선언한 이유가 **`alembic check` 가 이 5개를 보게 하려는 것**이었다.
    #   접두 wildcard 로 빼면 선언을 하나 빠뜨리거나 migration 이 여분 `auth_*` 를 만들어도
    #   DB-only 비교가 조용히 통과한다 — 즉 지키려던 바로 그 대상을 가린다.
    return schema == "public" and table_name == "alembic_version"


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
    """migration-only schema와 SQLModel.metadata가 양방향으로 일치하는지 검증.

    Migration drift 방지 — 모델 변경 시 Alembic migration 작성 누락과 DB-only 표를 검출한다.
    컬럼 이름·type·nullable·server default 및 Index/UNIQUE·CHECK 이름을 비교한다.
    """
    # create_all fixture가 만든 현재 metadata가 아니라 migration DDL만 검사해야 모델 변이가
    # 실제 Alembic 경로에서 red가 된다. `downgrade base` → `upgrade head`로 강제한다.
    monkeypatch.chdir(_BACKEND_ROOT)
    cfg = _alembic_cfg()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    # Sprint 19 BL-083: 격리 stack 호환 위해 conftest 우선순위 함수 사용.
    db_url = _resolved_test_db_url()
    engine = create_async_engine(db_url, poolclass=NullPool)

    # metadata가 사용하는 schema 목록 (None은 default = public)
    schemas = {t.schema or "public" for t in SQLModel.metadata.tables.values()}
    assert schemas, "SQLModel metadata schema 목록이 비었다 — 동등성 검사를 계속하면 무의미하다"

    try:
        async with engine.connect() as conn:

            def inspect_alembic_schema(sync_conn: Any) -> dict[tuple[str, str], dict[str, Any]]:
                inspector = inspect(sync_conn)
                tables: dict[tuple[str, str], dict[str, Any]] = {}
                for schema in schemas:
                    for table_name in inspector.get_table_names(schema=schema):
                        columns = inspector.get_columns(table_name, schema=schema)
                        assert columns, (
                            f"Table '{schema}.{table_name}'의 Inspector column 목록이 비었다 — "
                            "동등성 검사를 계속하면 무의미하다"
                        )
                        tables[(schema, table_name)] = {
                            "columns": columns,
                            "indexes": inspector.get_indexes(table_name, schema=schema),
                            "unique_constraints": inspector.get_unique_constraints(
                                table_name, schema=schema
                            ),
                            "check_constraints": inspector.get_check_constraints(
                                table_name, schema=schema
                            ),
                            "primary_key": inspector.get_pk_constraint(table_name, schema=schema),
                        }
                return tables

            alembic_tables = await conn.run_sync(inspect_alembic_schema)
    finally:
        await engine.dispose()

    # SQLModel metadata 등록된 모델 테이블 — (schema, name) 키로 매핑
    metadata_tables = {(t.schema or "public", t.name): t for t in SQLModel.metadata.tables.values()}
    assert metadata_tables, (
        "SQLModel metadata table 목록이 비었다 — 동등성 검사를 계속하면 무의미하다"
    )
    assert alembic_tables, (
        "Alembic Inspector table 목록이 비었다 — 동등성 검사를 계속하면 무의미하다"
    )

    missing_tables = set(metadata_tables) - set(alembic_tables)
    assert not missing_tables, (
        "SQLModel metadata에만 있는 table: "
        f"{sorted(missing_tables)}. Migration 작성 누락 또는 drift 발생."
    )
    db_only_tables = {
        table_key
        for table_key in set(alembic_tables) - set(metadata_tables)
        if not _is_externally_owned_db_only_table(*table_key)
    }
    assert not db_only_tables, (
        "Alembic DB에만 있는 table: "
        f"{sorted(db_only_tables)}. 모델/metadata 등록 누락 또는 drift 발생."
    )

    observed_type_drifts: set[TypeDrift] = set()
    observed_nullable_drifts: set[NullableDrift] = set()
    observed_default_drifts: set[DefaultDrift] = set()
    for (schema, table_name), metadata_table in metadata_tables.items():
        full_name = f"{schema}.{table_name}"
        metadata_columns = {column.name: column for column in metadata_table.columns}
        assert metadata_columns, (
            f"Table '{full_name}'의 metadata column 목록이 비었다 — 동등성 검사를 계속하면 무의미하다"
        )
        db_table = alembic_tables[(schema, table_name)]
        db_columns = {column["name"]: column for column in db_table["columns"]}
        missing_columns = set(metadata_columns) - set(db_columns)
        assert not missing_columns, (
            f"Table '{full_name}'의 metadata column이 DB에 없다: {sorted(missing_columns)}. "
            "Migration 누락 또는 drift 발생."
        )
        db_only_columns = set(db_columns) - set(metadata_columns)
        assert not db_only_columns, (
            f"Table '{full_name}'의 DB-only column: {sorted(db_only_columns)}. "
            "모델/metadata 등록 누락 또는 drift 발생."
        )

        observed_type_drifts.update(
            _type_drifts_for_table(
                schema,
                table_name,
                {name: column["type"] for name, column in db_columns.items()},
                {name: column.type for name, column in metadata_columns.items()},
            )
        )
        observed_nullable_drifts.update(
            _nullable_drifts_for_table(
                schema,
                table_name,
                {name: bool(column["nullable"]) for name, column in db_columns.items()},
                {name: bool(column.nullable) for name, column in metadata_columns.items()},
            )
        )
        # 이 축은 DB에 DDL로 존재하는 server_default만 대조한다. SQLModel의 python-side
        # default/default_factory는 Inspector에 나타나지 않으므로 여기에 넣지 않는다.
        observed_default_drifts.update(
            _default_drifts_for_table(
                schema,
                table_name,
                {name: column["default"] for name, column in db_columns.items()},
                {name: column.server_default for name, column in metadata_columns.items()},
            )
        )

    _assert_no_new_type_drifts(observed_type_drifts)
    _assert_no_new_nullable_drifts(observed_nullable_drifts)

    # nullable 축이 기존 drift를 5건 넘겨 동결됐다면, 정지 규칙상 이 회차는 여기서 끝낸다.
    # 새 nullable drift는 위 단언에서 먼저 red가 나므로 baseline 밖 항목을 가리지 않는다.
    if len(_NULLABLE_DRIFT_BASELINE) > 5:
        return

    # ★★**축은 켜진 순서대로 놓는다 — 정지 규칙이 cascading `return` 이기 때문이다** ([BL-803], 2026-08-18).
    #   정지 규칙은 「이 축이 시끄러우면 그 **뒤** 축은 이 회차에 얹지 마라」는 뜻이고, 그래서
    #   **뒤에 오는 축일수록 나중에 켜진 축**이어야 한다. 이 회차의 초판은 새 `default` 축을
    #   index 축 **앞**에 뒀는데, `default` baseline 이 6건(>5)이라 그 `return` 이
    #   [BL-749] 가 방금 착지시킨 **index 축을 통째로 끄고 있었다** — 새 축이 낡은 축을
    #   조용히 죽이는 fail-open 이다. 그래서 순서를 type → nullable → index → CHECK → default 로 둔다
    #   (이 목록은 2026-08-18 [BL-806] 까지 뒤 둘이 뒤바뀐 채였다 — 실제 코드가 늘 이 순서였다).
    observed_index_drifts: set[IndexDrift] = set()
    for (schema, table_name), metadata_table in metadata_tables.items():
        db_table = alembic_tables[(schema, table_name)]
        observed_index_drifts.update(
            _index_drifts_for_table(
                schema,
                table_name,
                _db_index_signatures(
                    schema,
                    table_name,
                    db_table["indexes"],
                    db_table["unique_constraints"],
                    db_table["primary_key"],
                ),
                _metadata_index_signatures(metadata_table),
            )
        )

    _assert_no_new_index_drifts(observed_index_drifts)

    # index 축이 기존 drift를 5건 넘겨 동결됐다면, 정지 규칙상 이 회차는 여기서 끝낸다.
    if len(_INDEX_DRIFT_BASELINE) > 5:
        return

    observed_check_constraint_drifts: set[CheckConstraintDrift] = set()
    for (schema, table_name), metadata_table in metadata_tables.items():
        db_table = alembic_tables[(schema, table_name)]
        observed_check_constraint_drifts.update(
            _check_constraint_drifts_for_table(
                schema,
                table_name,
                _db_check_constraint_names(
                    schema,
                    table_name,
                    db_table["check_constraints"],
                ),
                _metadata_check_constraint_names(metadata_table),
            )
        )

    _assert_no_new_check_constraint_drifts(observed_check_constraint_drifts)

    # CHECK 축이 기존 drift를 5건 넘겨 동결됐다면, 정지 규칙상 이 회차는 여기서 끝낸다.
    if len(_CHECK_CONSTRAINT_DRIFT_BASELINE) > 5:
        return

    # ★★**`default` 축이 마지막인 것은 의도다.** [BL-803] 당시에는 이 축의 baseline 이 **6건(>5)**
    #   이라 바로 아래 정지 규칙이 **반드시 발화했고**, 앞에 두면 그 `return` 이 뒤 축을 통째로 껐다.
    #   실제로 초판이 그랬고, `ck_alert_rules_type_threshold` 이름을 바꾸는 변이가
    #   **27 passed 로 통과**해서 CHECK 축이 죽어 있음이 드러났다(2026-08-18 음성 대조).
    #   ★**[BL-806] 이 baseline 을 6 → 0 으로 비워 그 `return` 은 이제 발화하지 않는다**
    #     (2026-08-18). 이 축이 마지막이라 지금은 무해하지만 — 뒤에 축을 더 얹을 거라면
    #     그때 이 자리가 다시 fail-open 지점이 된다는 뜻이다.
    #   ⇒ **새 축은 항상 맨 뒤에, baseline 이 큰 축일수록 더 뒤에 둔다.**
    _assert_no_new_default_drifts(observed_default_drifts)

    # default 축이 기존 drift를 5건 넘겨 동결됐다면, 정지 규칙상 이 회차는 여기서 끝낸다.
    # 새 default drift는 위 단언에서 먼저 red가 나므로 baseline 밖 항목을 가리지 않는다.
    if len(_DEFAULT_DRIFT_BASELINE) > 5:
        return


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
