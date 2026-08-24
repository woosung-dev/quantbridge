"""BL-453 대상: StrEnum 주석이지만 평문 String 컬럼인 필드를 AST로 파생한다."""

from __future__ import annotations

import ast
from pathlib import Path

_MODELS_PATH = Path(__file__).resolve().parents[2] / "src" / "trading" / "models.py"

# 제어군: 2026-08-24 재측정한 BL-453 대상. 대상 목록은 파생 결과가 아니라 대조용이다.
_EXPECTED_GUARDED_FIELDS = {
    ("LiveSignalSession", "interval"),
    ("LiveSignalEvent", "status"),
    ("AlertRule", "rule_type"),
    ("AlertRule", "channel"),
    ("ExchangeExit", "classification"),
    ("ExchangeExit", "attribution_confidence"),
}

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
