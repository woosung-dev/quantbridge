"""BL-453 평문 String StrEnum 컬럼의 선언·주석 계약을 검사한다."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from src.trading import models as trading_models

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MODELS_PATH = _BACKEND_ROOT / "src" / "trading" / "models.py"


@dataclass(frozen=True)
class _StringColumn:
    class_name: str
    field_name: str
    has_contract_comment: bool

    @property
    def identity(self) -> tuple[str, str]:
        return self.class_name, self.field_name


def _is_call_named(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name


def _strenum_bindings(namespace: dict[str, object]) -> dict[str, type[StrEnum]]:
    bindings: dict[str, type[StrEnum]] = {}
    for name, value in namespace.items():
        if isinstance(value, type) and issubclass(value, StrEnum):
            bindings[name] = value
    return bindings


def _is_string_column(column: ast.Call) -> bool:
    type_candidates = list(column.args[1:2])
    type_candidates.extend(keyword.value for keyword in column.keywords if keyword.arg == "type_")
    return any(_is_call_named(candidate, "String") for candidate in type_candidates)


def _has_string_sa_column(field_call: ast.Call) -> bool:
    if not _is_call_named(field_call, "Field"):
        return False

    return any(
        keyword.arg == "sa_column"
        and _is_call_named(keyword.value, "Column")
        and _is_string_column(keyword.value)
        for keyword in field_call.keywords
    )


def _has_contract_comment(source_lines: list[str], lineno: int) -> bool:
    comment_lines: list[str] = []
    line_index = lineno - 2
    while line_index >= 0 and source_lines[line_index].lstrip().startswith("#"):
        comment_lines.append(source_lines[line_index])
        line_index -= 1
    return any("BL-453" in line for line in comment_lines)


def _collect_string_columns(
    tree: ast.Module, source_lines: list[str], strenum_bindings: dict[str, type[StrEnum]]
) -> list[_StringColumn]:
    columns: list[_StringColumn] = []
    for model in tree.body:
        if not isinstance(model, ast.ClassDef):
            continue
        for field in model.body:
            if not (
                isinstance(field, ast.AnnAssign)
                and isinstance(field.target, ast.Name)
                and isinstance(field.annotation, ast.Name)
                and field.annotation.id in strenum_bindings
                and isinstance(field.value, ast.Call)
                and _has_string_sa_column(field.value)
            ):
                continue
            columns.append(
                _StringColumn(
                    class_name=model.name,
                    field_name=field.target.id,
                    has_contract_comment=_has_contract_comment(source_lines, field.lineno),
                )
            )
    return columns


def _models_string_columns() -> list[_StringColumn]:
    source = _MODELS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_MODELS_PATH))
    return _collect_string_columns(
        tree,
        source.splitlines(),
        _strenum_bindings(vars(trading_models)),
    )


def strenum_string_columns() -> list[tuple[str, str]]:
    """`sa_column=Column(..., String(...))` 위에 StrEnum 주석이 얹힌 필드 전부.
    (클래스명, 필드명).
    """
    return [column.identity for column in _models_string_columns()]


def uncontracted_columns() -> list[tuple[str, str]]:
    """그중 BL-453 계약 주석을 달지 않은 것. 이것이 위반 census 다."""
    return [
        column.identity for column in _models_string_columns() if not column.has_contract_comment
    ]


def test_strenum_string_column_census_has_positive_control() -> None:
    columns = strenum_string_columns()

    assert len(columns) >= 6, f"BL-453 대상 수집기가 비었거나 축소됐다: {columns}"


def test_every_collected_column_has_a_bl453_contract_comment() -> None:
    assert uncontracted_columns() == []


def test_collector_distinguishes_string_columns_and_contract_comments() -> None:
    class FixtureStatus(StrEnum):
        active = "active"

    source = """
class FixtureModel:
    # BL-453 — 재조회 시 plain str 이다.
    contracted: FixtureStatus = Field(
        sa_column=Column("contracted", type_=String(16))
    )
    native_enum: FixtureStatus = Field(
        sa_column=Column("native_enum", sa.Enum(FixtureStatus))
    )
    uncontracted: FixtureStatus = Field(
        sa_column=Column("uncontracted", String(16))
    )
"""
    columns = _collect_string_columns(
        ast.parse(source),
        source.splitlines(),
        _strenum_bindings({"FixtureStatus": FixtureStatus}),
    )

    assert [(column.identity, column.has_contract_comment) for column in columns] == [
        (("FixtureModel", "contracted"), True),
        (("FixtureModel", "uncontracted"), False),
    ]
