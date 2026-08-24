"""BL-453 대상: StrEnum 주석이지만 평문 String 컬럼인 필드를 AST로 파생한다."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MODELS_PATH = _BACKEND_ROOT / "src" / "trading" / "models.py"
_SCANNED_DIRECTORIES = (_BACKEND_ROOT / "src" / "trading", _BACKEND_ROOT / "src" / "tasks")
_MIN_SCANNED_FILES = 70
_ENUM_ACCESSORS = frozenset({"value", "name"})

_STR_ENUM_GUARD_FAILURE_MESSAGE = """
BL-453 plain-string StrEnum access guard:
(a) 대상 필드는 trading/models.py에서 StrEnum 주석 + Field(sa_column=Column(..., String(N), ...))로 파생한다.
(b) 대상은 src/trading 과 src/tasks 안의 직접 속성 접근 ``row.<field>.value`` / ``row.<field>.name`` 이다.
(c) allowlist는 (파일, 속성, 비어 있지 않은 사유) 3튜플이며, 각 항목은 실제 AST hit 하나와 대응해야 한다.
못 잡는 것: 별칭(``c = row.channel; c.value``), getattr 같은 동적 접근, 그리고 스코프 밖 파일이다.
""".strip()

# `ChannelTally.channel`은 AlertRule.channel DB 필드가 아니라 LedgerChannel 메모리 dataclass 값이다.
# 동일 속성 접근 3건은 각 오류 메시지 분기이며, 수가 바뀌면 Counter 대조가 red가 된다.
_ALLOWLIST: tuple[tuple[str, str, str], ...] = (
    (
        "src/trading/entry_completeness.py",
        "channel.value",
        "ChannelTally.channel은 LedgerChannel 메모리 dataclass 값이다.",
    ),
    (
        "src/trading/entry_completeness.py",
        "channel.value",
        "채널 분할 오류 메시지는 AlertRule ORM 행을 읽지 않는다.",
    ),
    (
        "src/trading/entry_completeness.py",
        "channel.value",
        "후보·부분집합 검증은 메모리 원장 집계만 사용한다.",
    ),
)


@dataclass(frozen=True, slots=True)
class _StrEnumAccess:
    path: str
    lineno: int
    field: str
    accessor: str

    @property
    def attribute(self) -> str:
        return f"{self.field}.{self.accessor}"

    @property
    def allowlist_key(self) -> tuple[str, str]:
        return self.path, self.attribute


# 제어군: 2026-08-24 재측정한 BL-453 대상. 대상 목록은 파생 결과가 아니라 대조용이다.
_EXPECTED_GUARDED_FIELDS = {
    ("LiveSignalSession", "interval"),
    ("LiveSignalEvent", "status"),
    ("AlertRule", "rule_type"),
    ("AlertRule", "channel"),
    ("ExchangeExit", "classification"),
    ("ExchangeExit", "attribution_confidence"),
}

_COMMENT_CONTRACT_FIELDS = frozenset(
    {
        ("LiveSignalSession", "interval"),
        ("LiveSignalEvent", "status"),
        ("AlertRule", "rule_type"),
        ("AlertRule", "channel"),
        ("ExchangeExit", "classification"),
    }
)
_COMMENT_CONTRACT_MARKERS = frozenset(
    {
        "Sprint 26 Phase D fix",
        "명시적 String 컬럼",
        "`.value`/`.name` 금지",
        "`==`/`!=`/`str()` 만 쓸 것.",
        "apps/api/tests/trading/test_no_strenum_value_access.py",
    }
)

# SQLModel이 native PG enum으로 자동 생성해 재조회 시 StrEnum으로 재캐스팅하는 안전한 필드다.
_NATIVE_ENUM_FIELDS = {
    ("ExchangeAccount", "exchange"),
    ("ExchangeAccount", "mode"),
    ("Order", "side"),
    ("Order", "type"),
    ("Order", "state"),
    ("KillSwitchEvent", "trigger_type"),
    ("FundingRate", "exchange"),
}


def _is_call_named(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name


def _strenum_names(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(isinstance(base, ast.Name) and base.id == "StrEnum" for base in node.bases)
    }


def _has_plain_string_column(field_call: ast.Call) -> bool:
    if not _is_call_named(field_call, "Field"):
        return False

    for keyword in field_call.keywords:
        if keyword.arg != "sa_column" or not _is_call_named(keyword.value, "Column"):
            continue
        if any(_is_call_named(argument, "String") for argument in keyword.value.args):
            return True
    return False


def _derive_guarded_fields() -> set[tuple[str, str]]:
    """`StrEnum` 주석 + `Field(sa_column=Column(..., String(N), ...))`만 수집한다."""
    tree = ast.parse(_MODELS_PATH.read_text(encoding="utf-8"), filename=str(_MODELS_PATH))
    strenum_names = _strenum_names(tree)
    guarded_fields: set[tuple[str, str]] = set()

    for model in tree.body:
        if not isinstance(model, ast.ClassDef):
            continue
        for field in model.body:
            if not (
                isinstance(field, ast.AnnAssign)
                and isinstance(field.target, ast.Name)
                and isinstance(field.annotation, ast.Name)
                and field.annotation.id in strenum_names
                and isinstance(field.value, ast.Call)
                and _has_plain_string_column(field.value)
            ):
                continue
            guarded_fields.add((model.name, field.target.id))

    return guarded_fields


def _comment_lines_before_or_on_field(source_lines: list[str], field_lineno: int) -> list[str]:
    comment_lines = [source_lines[field_lineno - 1]]
    line_index = field_lineno - 2

    while line_index >= 0 and source_lines[line_index].lstrip().startswith("#"):
        comment_lines.append(source_lines[line_index])
        line_index -= 1

    return comment_lines


def _comment_contract_markers_by_field() -> dict[tuple[str, str], set[str]]:
    source = _MODELS_PATH.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    tree = ast.parse(source, filename=str(_MODELS_PATH))
    markers_by_field: dict[tuple[str, str], set[str]] = {}

    for model in tree.body:
        if not isinstance(model, ast.ClassDef):
            continue
        for field in model.body:
            if not isinstance(field, ast.AnnAssign) or not isinstance(field.target, ast.Name):
                continue
            identity = model.name, field.target.id
            if identity not in _COMMENT_CONTRACT_FIELDS:
                continue
            comment = "\n".join(_comment_lines_before_or_on_field(source_lines, field.lineno))
            markers_by_field[identity] = {
                marker for marker in _COMMENT_CONTRACT_MARKERS if marker in comment
            }

    return markers_by_field


def _scoped_source_paths() -> list[Path]:
    return sorted(path for directory in _SCANNED_DIRECTORIES for path in directory.rglob("*.py"))


def _direct_guarded_field_access(
    node: ast.AST, guarded_field_names: set[str]
) -> tuple[str, str] | None:
    if not (
        isinstance(node, ast.Attribute)
        and node.attr in _ENUM_ACCESSORS
        and isinstance(node.value, ast.Attribute)
        and node.value.attr in guarded_field_names
    ):
        return None
    return node.value.attr, node.attr


def _scoped_strenum_accesses() -> list[_StrEnumAccess]:
    guarded_field_names = {field for _, field in _derive_guarded_fields()}
    accesses: list[_StrEnumAccess] = []

    for path in _scoped_source_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(_BACKEND_ROOT).as_posix()
        for node in ast.walk(tree):
            access = _direct_guarded_field_access(node, guarded_field_names)
            if access is None:
                continue
            field, accessor = access
            accesses.append(_StrEnumAccess(relative_path, node.lineno, field, accessor))

    return sorted(accesses, key=lambda access: (access.path, access.lineno))


def _assert_allowlist_reasons(entries: tuple[tuple[str, str, str], ...]) -> None:
    missing_reasons = [
        (path, attribute) for path, attribute, reason in entries if not reason.strip()
    ]

    assert not missing_reasons, (
        f"{_STR_ENUM_GUARD_FAILURE_MESSAGE}\nallowlist 사유가 비었다: {missing_reasons}"
    )


def _allowlist_counts(entries: tuple[tuple[str, str, str], ...]) -> Counter[tuple[str, str]]:
    _assert_allowlist_reasons(entries)
    return Counter((path, attribute) for path, attribute, _ in entries)


def _unallowlisted_accesses(accesses: list[_StrEnumAccess]) -> list[_StrEnumAccess]:
    remaining_allowances = _allowlist_counts(_ALLOWLIST)
    violations: list[_StrEnumAccess] = []
    for access in accesses:
        if remaining_allowances[access.allowlist_key] == 0:
            violations.append(access)
            continue
        remaining_allowances[access.allowlist_key] -= 1
    return violations


def _format_accesses(accesses: list[_StrEnumAccess]) -> list[str]:
    return [f"{access.path}:{access.lineno}: {access.attribute}" for access in accesses]


def test_derives_all_known_plain_string_strenum_fields() -> None:
    """BL-453 규칙: 새 세션 재조회 시 plain str인 StrEnum 필드를 빠짐없이 파생한다."""
    derived_fields = _derive_guarded_fields()
    missing_fields = _EXPECTED_GUARDED_FIELDS - derived_fields

    assert len(derived_fields) >= 6, (
        "StrEnum + 명시적 String Column 파생 결과가 6건 미만이다. "
        "AST 파생 규칙 또는 models.py 선언을 확인하라. "
        f"실제: {sorted(derived_fields)}"
    )
    assert not missing_fields, (
        "BL-453 대조군 필드가 AST 파생 결과에 없다. "
        f"누락: {sorted(missing_fields)}; 실제: {sorted(derived_fields)}"
    )


def test_derivation_is_nonempty_and_excludes_native_enums() -> None:
    """공허한 가드와 `sa_column` 없는 native PG enum 위양성을 함께 막는다."""
    derived_fields = _derive_guarded_fields()
    unexpected_native_enums = _NATIVE_ENUM_FIELDS & derived_fields

    assert derived_fields, (
        "BL-453 파생 결과가 비었다. models.py를 읽지 못했거나 "
        "StrEnum + Column(..., String(N)) 규칙이 무력화됐다."
    )
    assert not unexpected_native_enums, (
        "sa_column 없는 native PG enum 필드가 BL-453 대상에 들어왔다. "
        f"위양성: {sorted(unexpected_native_enums)}"
    )


def test_strenum_string_column_fields_carry_the_ban_comment() -> None:
    markers_by_field = _comment_contract_markers_by_field()

    assert len(_COMMENT_CONTRACT_FIELDS) == 5, (
        "BL-453 선언부 주석 제어군은 정확히 5개 필드여야 한다. "
        f"실제: {sorted(_COMMENT_CONTRACT_FIELDS)}"
    )
    assert set(markers_by_field) == _COMMENT_CONTRACT_FIELDS, (
        "BL-453 선언부 주석 검사 대상이 AST에서 누락되었거나 늘었다. "
        f"실제: {sorted(markers_by_field)}"
    )
    missing_markers = {
        identity: sorted(_COMMENT_CONTRACT_MARKERS - markers)
        for identity, markers in markers_by_field.items()
        if _COMMENT_CONTRACT_MARKERS - markers
    }

    assert not missing_markers, (
        f"BL-453 평문 String StrEnum 필드의 금지 주석이 불완전하다. 누락: {missing_markers}"
    )


def test_no_unallowlisted_plain_string_strenum_value_accesses() -> None:
    accesses = _scoped_strenum_accesses()
    violations = _unallowlisted_accesses(accesses)

    assert not violations, (
        f"{_STR_ENUM_GUARD_FAILURE_MESSAGE}\n"
        f"allowlist 밖 접근: {_format_accesses(violations)}\n"
        f"스코프 전체 hit: {_format_accesses(accesses)}"
    )


def test_direct_access_scanner_classifies_the_synthetic_fixture() -> None:
    fixture = ast.parse(
        """
row.classification.value
row.attribution_confidence.name
row.state.value
alias = row.classification
alias.value
getattr(row, "classification").value
"""
    )
    guarded_field_names = {field for _, field in _derive_guarded_fields()}
    accesses = {
        access
        for node in ast.walk(fixture)
        if (access := _direct_guarded_field_access(node, guarded_field_names)) is not None
    }

    assert accesses == {("classification", "value"), ("attribution_confidence", "name")}


def test_guard_scans_a_nonempty_scope() -> None:
    scanned_paths = _scoped_source_paths()

    assert len(scanned_paths) >= _MIN_SCANNED_FILES, (
        f"{_STR_ENUM_GUARD_FAILURE_MESSAGE}\n"
        f"스캔 파일 수가 {_MIN_SCANNED_FILES} 미만이다: {len(scanned_paths)}"
    )


def test_all_allowlist_entries_match_scoped_accesses() -> None:
    accesses = _scoped_strenum_accesses()
    expected_counts = _allowlist_counts(_ALLOWLIST)
    actual_counts = Counter(access.allowlist_key for access in accesses)
    matched_count = sum((expected_counts & actual_counts).values())

    assert len(_ALLOWLIST) == 3, "BL-453 allowlist 제어군은 메모리 channel.value 3건이다."
    assert matched_count == len(_ALLOWLIST), (
        f"{_STR_ENUM_GUARD_FAILURE_MESSAGE}\n"
        f"매치한 allowlist 수: {matched_count}/{len(_ALLOWLIST)}; "
        f"기대: {expected_counts}; 실제: {actual_counts}"
    )


def test_allowlist_requires_a_nonempty_reason() -> None:
    with pytest.raises(AssertionError, match="사유"):
        _assert_allowlist_reasons((("src/trading/entry_completeness.py", "channel.value", ""),))


def test_guard_does_not_scan_other_domains() -> None:
    scanned_paths = {path.relative_to(_BACKEND_ROOT).as_posix() for path in _scoped_source_paths()}

    assert scanned_paths, f"{_STR_ENUM_GUARD_FAILURE_MESSAGE}\n스캔 범위가 비었다."
    assert all(path.startswith(("src/trading/", "src/tasks/")) for path in scanned_paths), (
        f"{_STR_ENUM_GUARD_FAILURE_MESSAGE}\n스코프 밖 파일: {sorted(scanned_paths)}"
    )
    assert "src/backtest/service.py" not in scanned_paths, (
        f"{_STR_ENUM_GUARD_FAILURE_MESSAGE}\nbacktest는 이 가드의 스코프 밖이어야 한다."
    )
