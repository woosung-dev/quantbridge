# Pine strategy() default_qty_type/default_qty_value 파싱 회귀 (BL-185, Sprint 37 PR1).
"""BL-185 TDD-1.1 RED — DeclarationInfo 에 default_qty_type/value 명시 필드 노출.

배경:
- ast_extractor 가 strategy() 호출의 모든 kwarg 를 args (list[ArgValue]) 에 보존하나,
  default_qty_type / default_qty_value 가 명시 필드로 노출되지 않아 backtest engine 이
  사용하지 못함. virtual_strategy.py 가 qty=1.0 hardcode → BL-185 결과 왜곡 root cause.
- TDD-1.1 = parser/config layer 만 다룸 (runtime 은 TDD-1.2 에서).

Acceptance:
1. strategy(..., default_qty_type=strategy.percent_of_equity, default_qty_value=30) 파싱.
2. strategy(..., default_qty_type=strategy.cash, default_qty_value=100) 파싱.
3. strategy(..., default_qty_type=strategy.fixed, default_qty_value=0.01) 파싱.
4. default_qty_type 미지정 시 두 필드 모두 None.
5. ScriptContent.to_dict() 에도 두 필드 포함 (FE/BE schema 직렬화 path).
"""
from __future__ import annotations

import pytest

from src.strategy.pine_v2.ast_extractor import extract_content


@pytest.mark.parametrize(
    ("qty_type_expr", "qty_value_expr"),
    [
        ("strategy.percent_of_equity", "30"),
        ("strategy.cash", "100"),
        ("strategy.fixed", "0.01"),
    ],
)
def test_extract_default_qty_kwargs(qty_type_expr: str, qty_value_expr: str) -> None:
    """strategy() kwarg 로 지정된 default_qty_type / default_qty_value 가 declaration 에 노출."""
    source = (
        '//@version=5\n'
        f'strategy("Test", overlay=true, '
        f'default_qty_type={qty_type_expr}, default_qty_value={qty_value_expr})\n'
    )
    content = extract_content(source)

    assert content.declaration.kind == "strategy"
    assert content.declaration.default_qty_type == qty_type_expr, (
        f"default_qty_type 노출 실패: expected={qty_type_expr!r}, "
        f"actual={content.declaration.default_qty_type!r}"
    )
    assert content.declaration.default_qty_value == qty_value_expr, (
        f"default_qty_value 노출 실패: expected={qty_value_expr!r}, "
        f"actual={content.declaration.default_qty_value!r}"
    )


def test_extract_default_qty_missing_returns_none() -> None:
    """strategy() 가 default_qty_* 미지정 시 두 필드 모두 None."""
    source = '//@version=5\nstrategy("NoQty", overlay=false)\n'
    content = extract_content(source)

    assert content.declaration.kind == "strategy"
    assert content.declaration.default_qty_type is None
    assert content.declaration.default_qty_value is None


def test_to_dict_includes_default_qty_fields() -> None:
    """ScriptContent.to_dict() 의 declaration 에 default_qty_type/value 포함."""
    source = (
        '//@version=5\n'
        'strategy("Test", default_qty_type=strategy.percent_of_equity, '
        'default_qty_value=30)\n'
    )
    decl_dict = extract_content(source).to_dict()["declaration"]

    assert "default_qty_type" in decl_dict, (
        f"to_dict() declaration 에 default_qty_type key 누락: {list(decl_dict.keys())}"
    )
    assert "default_qty_value" in decl_dict
    assert decl_dict["default_qty_type"] == "strategy.percent_of_equity"
    assert decl_dict["default_qty_value"] == "30"


def test_indicator_declaration_default_qty_is_none() -> None:
    """indicator() 호출은 strategy 가 아니므로 default_qty_* 필드 None 유지."""
    source = '//@version=5\nindicator("MyInd", overlay=true)\n'
    content = extract_content(source)

    assert content.declaration.kind == "indicator"
    assert content.declaration.default_qty_type is None
    assert content.declaration.default_qty_value is None
