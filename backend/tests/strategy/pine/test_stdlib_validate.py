"""AST 사전 검증(validate) 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.errors import PineUnsupportedError
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse
from src.strategy.pine.stdlib import validate_functions

# strategy.* / indicator / input.* 등은 "파서가 아는 구조적 호출"로 간주해 화이트리스트와 별도
# (인터프리터가 직접 처리). 여기선 ta.*, nz, na, math.* 등 "연산 함수" 화이트리스트를 검사.
_ALLOWED_NON_STDLIB = {
    "strategy",
    "strategy.entry",
    "strategy.close",
    "strategy.exit",
    "indicator",
    "input",
    "input.int",
    "input.float",
    "input.bool",
    "input.string",
    "plot",
    "plotshape",
    "bgcolor",
    "barcolor",
    "fill",
    "alert",
    "alertcondition",
    "timestamp",
    "color.new",
    "color.red",
    "color.green",
    "color.blue",
    "color.white",
    "color.black",
}


def _report(src: str) -> dict:
    prog = parse(tokenize(src))
    return validate_functions(prog, allowed_structural=_ALLOWED_NON_STDLIB)


def test_validate_ok_for_supported_functions():
    src = "x = ta.sma(close, 20)\ny = ta.crossover(close, x)\n"
    report = _report(src)
    assert "ta.sma" in report["functions_used"]
    assert "ta.crossover" in report["functions_used"]


def test_validate_raises_on_unsupported_ta_function():
    src = "x = ta.vwma(close, 20)\n"
    with pytest.raises(PineUnsupportedError) as ei:
        _report(src)
    assert ei.value.feature == "ta.vwma"
    assert ei.value.category == "function"


def test_validate_allows_structural_calls():
    # strategy.entry 같은 구조적 호출은 통과
    src = 'strategy.entry("Long", strategy.long)\n'
    # parse_stmt에선 strategy.long이 식별자라 함수 호출 아님
    report = _report(src)
    assert "strategy.entry" in report["functions_used"]
