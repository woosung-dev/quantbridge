"""Sprint 31 A (BL-159 + BL-161) — Pine v5/v6 collection types pre-flight.

dogfood Day 3 발견: 사용자 새 strategy "bs" (Pine v6, 12205 chars) 시도 시
backtest runtime fail (`Call to 'array.new_float' not supported in current scope`,
interpreter.py:880). Coverage Analyzer pre-flight false negative — `array.*` namespace
SUPPORTED 0건 + `_KNOWN_NAMESPACES` 미등록 → false positive 방지 명목으로 skip 됨.

Fix: `_KNOWN_NAMESPACES` 에 `array` / `matrix` / `map` 추가 → `_is_pine_namespace`
True 반환 → SUPPORTED_FUNCTIONS 에 없음 → unsupported_functions 자동 등록 → 422 reject.

Sprint Y1 trust layer 패턴 답습: pre-flight 단계에서 명시적 unsupported 노출.
"""

from __future__ import annotations

import pytest

from src.strategy.pine_v2.coverage import analyze_coverage

# ---------------------------------------------------------------------
# 1. array.* — 사용자 dogfood Day 3 root cause
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "func_call,fn_name",
    [
        ("array.new_float(0)", "array.new_float"),
        ("array.new_int(0)", "array.new_int"),
        ("array.new_bool(0)", "array.new_bool"),
        ("array.new_string(0)", "array.new_string"),
    ],
)
def test_array_new_typed_caught_as_unsupported(func_call: str, fn_name: str) -> None:
    """Pine v6 `array.new_<type>(...)` 가 pre-flight 에서 unsupported_functions 로 catch.

    dogfood Day 3 root cause: false negative → runtime fail.
    Sprint 31 A fix: `_KNOWN_NAMESPACES` 에 `array` 등록.
    """
    src = f"""
//@version=6
indicator("Buy Sell Signal")
arr = {func_call}
"""
    r = analyze_coverage(src)
    assert not r.is_runnable, (
        f"{fn_name} should be unsupported (Pine v6 array<type> 미지원). "
        f"unsupported_functions={r.unsupported_functions}"
    )
    assert fn_name in r.unsupported_functions, (
        f"expected {fn_name} in unsupported_functions, got {r.unsupported_functions}"
    )


def test_array_push_caught_as_unsupported() -> None:
    """`array.push(...)` 도 unsupported (mutation method)."""
    src = """
//@version=6
indicator("Buy Sell Signal")
myArr = array.new_float(0)
array.push(myArr, close)
"""
    r = analyze_coverage(src)
    assert not r.is_runnable
    assert "array.push" in r.unsupported_functions
    assert "array.new_float" in r.unsupported_functions


def test_array_pop_caught_as_unsupported() -> None:
    """`array.pop(...)` 도 unsupported."""
    src = """
//@version=6
indicator("BS")
myArr = array.new_float(0)
v = array.pop(myArr)
"""
    r = analyze_coverage(src)
    assert not r.is_runnable
    assert "array.pop" in r.unsupported_functions


def test_array_workaround_message_present() -> None:
    """Sprint Y1 trust layer 패턴: unsupported_calls 안에 workaround 안내 포함."""
    src = """
//@version=6
indicator("BS")
arr = array.new_float(10)
"""
    r = analyze_coverage(src)
    assert not r.is_runnable
    # unsupported_calls 안에 array.new_float 항목 + workaround 메시지.
    matched = [c for c in r.unsupported_calls if c["name"] == "array.new_float"]
    assert matched, f"unsupported_calls 에 array.new_float 누락. got={r.unsupported_calls}"
    call = matched[0]
    assert call["category"] == "syntax", (
        f"array.* 는 v6 type system 갭 (syntax category), got {call['category']}"
    )
    assert call["workaround"] is not None and "단일 series" in call["workaround"], (
        f"워크어라운드 안내 누락. got={call['workaround']}"
    )


# ---------------------------------------------------------------------
# 2. matrix.* / map.* — Pine v6 신규 collection types (BL-160 deferred)
# ---------------------------------------------------------------------


def test_matrix_new_caught_as_unsupported() -> None:
    """Pine v6 matrix<T> 신규 type — pre-flight 차단.

    NOTE: `matrix.new<float>(...)` generic syntax 는 regex `_CALL_RE`
    (`name\\s*\\(`) 와 직접 매칭 안 되므로 attribute 로 분류됨. 둘 중 하나에
    잡히면 OK (is_runnable=False 의무).
    """
    src = """
//@version=6
indicator("MatrixTest")
m = matrix.new<float>(5, 5, 0.0)
"""
    r = analyze_coverage(src)
    assert not r.is_runnable
    assert "matrix.new" in (r.unsupported_functions + r.unsupported_attributes)


def test_map_new_caught_as_unsupported() -> None:
    """Pine v6 map<K,V> 신규 type — pre-flight 차단.

    NOTE: `map.new<K,V>()` generic syntax 도 attribute 분류 가능 (위 matrix 동일).
    """
    src = """
//@version=6
indicator("MapTest")
m = map.new<string, float>()
"""
    r = analyze_coverage(src)
    assert not r.is_runnable
    assert "map.new" in (r.unsupported_functions + r.unsupported_attributes)


# ---------------------------------------------------------------------
# 3. SSOT invariant 회귀 — BL-159 추가가 다른 supported 회귀 0
# ---------------------------------------------------------------------


def test_existing_supported_still_runnable() -> None:
    """Sprint Y1 회귀: 기존 supported 함수가 여전히 runnable (회귀 0)."""
    src = """
//@version=5
strategy("Existing", overlay=true)
fast = ta.sma(close, 9)
slow = ta.sma(close, 21)
crossUp = ta.crossover(fast, slow)
strategy.entry("Long", strategy.long, when=crossUp)
"""
    r = analyze_coverage(src)
    assert r.is_runnable, (
        f"기존 supported 회귀: unsupported_functions={r.unsupported_functions}, "
        f"unsupported_attributes={r.unsupported_attributes}"
    )


def test_user_defined_namespace_not_false_positive() -> None:
    """사용자 변수 method 호출 (예: `myObj.update()`) 는 false positive 차단 유지.

    `array`/`matrix`/`map` 만 신규 namespace 등록 — 사용자 임의 namespace 는 여전히 skip.
    """
    src = """
//@version=5
indicator("FalsePositiveCheck")
foo = bar.baz()
"""
    r = analyze_coverage(src)
    # `bar` 는 _KNOWN_NAMESPACES 에 없음 → false positive 차단 (skip).
    assert "bar.baz" not in r.unsupported_functions, (
        f"사용자 namespace 가 잘못 catch 됨. unsupported_functions={r.unsupported_functions}"
    )


# ---------------------------------------------------------------------
# 4. dogfood Day 3 사용자 strategy "bs" 시뮬레이션 (snippet)
# ---------------------------------------------------------------------


def test_dogfood_day3_user_strategy_bs_pattern() -> None:
    """dogfood Day 3 사용자 Pine v6 strategy "bs" 패턴 — array.new_float pre-flight catch."""
    src = """
//@version=6
indicator("Buy Sell Signal", overlay=true)
length = input.int(14, "Length")
src = input.source(close, "Source")
buyLevels = array.new_float(0)
sellLevels = array.new_float(0)
if ta.crossover(src, ta.sma(src, length))
    array.push(buyLevels, src)
"""
    r = analyze_coverage(src)
    assert not r.is_runnable, "dogfood Day 3 root cause 가 여전히 false negative."
    assert "array.new_float" in r.unsupported_functions
    assert "array.push" in r.unsupported_functions
    # category 분류 확인
    by_name = {c["name"]: c for c in r.unsupported_calls}
    assert by_name["array.new_float"]["category"] == "syntax"
    assert by_name["array.push"]["category"] == "syntax"
