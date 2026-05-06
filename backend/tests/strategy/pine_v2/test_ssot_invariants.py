"""SSOT parity invariant audit — Sprint 29 Slice C.

drift 차단 자동 감지:
- STDLIB_NAMES ⊆ SUPPORTED_FUNCTIONS (interpreter ta.* + na/nz 가 coverage 에 등록)
- _RENDERING_FACTORIES.keys() ⊆ SUPPORTED_FUNCTIONS (drawing 메서드가 coverage 에 등록)
- _V4_ALIASES.values() ⊆ SUPPORTED_FUNCTIONS (V4 alias target 이 coverage 에서 인식)
- interpreter._ATTR_CONSTANTS prefixes ⊆ coverage._ENUM_PREFIXES ∪ _CONST_VALUE_PREFIXES
  (enum prefix 이거나 사용자-friendly const value prefix)
"""

from src.strategy.pine_v2.coverage import (
    _ENUM_PREFIXES,
    _STRATEGY_CONSTANTS_EXTRA,
    SUPPORTED_FUNCTIONS,
)
from src.strategy.pine_v2.interpreter import (
    _ATTR_CONSTANTS,
    _RENDERING_FACTORIES,
    _V4_ALIASES,
    STDLIB_NAMES,
)

# _ATTR_CONSTANTS 안 const value (enum 이 아니라 사용자-friendly alias) prefix.
# 예: strategy.long="long" / line.style_dashed="dashed" — coverage._ENUM_PREFIXES
# 가 prefix lookup 으로 enum 만 인식. const value prefix 는 별도 화이트리스트.
_CONST_VALUE_PREFIXES = frozenset({"strategy.", "line."})


def test_stdlib_names_subset_of_supported_functions():
    """interpreter.STDLIB_NAMES (ta.* + na/nz) 가 모두 coverage.SUPPORTED_FUNCTIONS 에 등록."""
    diff = STDLIB_NAMES - SUPPORTED_FUNCTIONS
    assert not diff, f"STDLIB_NAMES not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_rendering_factories_subset_of_supported_functions():
    """interpreter._RENDERING_FACTORIES (line.*/box.*/label.*/table.*) 가 SUPPORTED_FUNCTIONS 에 등록."""
    diff = set(_RENDERING_FACTORIES.keys()) - SUPPORTED_FUNCTIONS
    assert not diff, f"_RENDERING_FACTORIES keys not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_v4_aliases_targets_in_supported_functions():
    """interpreter._V4_ALIASES (atr→ta.atr / max→math.max 등) 의 target 이 coverage.SUPPORTED_FUNCTIONS 에 등록.

    V4 alias 가 interpreter._eval_call 에서 dispatch 되려면 target 이 supported 의무.
    STDLIB_NAMES 가 ta.* + na/nz 만 포함하므로 (math.* 별도 dispatch), 더 넓은
    SUPPORTED_FUNCTIONS 로 검증.
    """
    diff = set(_V4_ALIASES.values()) - SUPPORTED_FUNCTIONS
    assert not diff, f"_V4_ALIASES targets not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


# BL-185 Sprint 37 PR1 TDD-1.3: Pine strategy() default_qty_type 3 종 explicit 등록 검증.
# 이전 prefix-only 검증 (test_attr_constants_prefixes_known_to_coverage) 은 'strategy.' prefix
# 통과만으로 OK 판정 → strategy.fixed / cash / percent_of_equity 가 _ATTR_CONSTANTS 에 빠져도
# 통과하는 false-pass 가능. explicit 검증으로 drift 차단.
_BL185_DEFAULT_QTY_TYPES: frozenset[str] = frozenset(
    {
        "strategy.fixed",
        "strategy.cash",
        "strategy.percent_of_equity",
    }
)


def test_default_qty_type_constants_in_attr_constants():
    """BL-185: Pine strategy(default_qty_type=...) 3종이 interpreter._ATTR_CONSTANTS 에 명시 등록.

    interpreter 가 `strategy.percent_of_equity` 같은 attribute access 를 evaluate 할 때
    실제 string value 를 반환하려면 _ATTR_CONSTANTS dict 에 명시 매핑 필요.
    coverage._STRATEGY_CONSTANTS_EXTRA 에는 이미 등록되어 있으나, _ATTR_CONSTANTS (interpreter)
    에 등록되지 않으면 사용자 strategy 가 `t = strategy.percent_of_equity` 같이 변수에
    저장 후 사용 시 silent fail.
    """
    missing = _BL185_DEFAULT_QTY_TYPES - set(_ATTR_CONSTANTS.keys())
    assert not missing, (
        f"BL-185: _ATTR_CONSTANTS 에 default_qty_type 상수 누락: {sorted(missing)}. "
        "interpreter 가 attribute access 를 evaluate 못 함 → 사용자 strategy 의 "
        "`t = strategy.percent_of_equity` 패턴 silent fail."
    )


def test_default_qty_type_constants_subset_of_strategy_constants_extra():
    """BL-185: BL-185 default_qty_type 3종이 coverage._STRATEGY_CONSTANTS_EXTRA 에 명시 등록.

    coverage 가 `strategy.percent_of_equity` 등의 attribute access 를 SUPPORTED_ATTRIBUTES 로
    인식 못 하면 preflight (lazy validation) 가 false reject.
    """
    missing = _BL185_DEFAULT_QTY_TYPES - _STRATEGY_CONSTANTS_EXTRA
    assert not missing, (
        f"BL-185: coverage._STRATEGY_CONSTANTS_EXTRA 에 default_qty_type 누락: {sorted(missing)}"
    )


def test_attr_constants_prefixes_known_to_coverage():
    """interpreter._ATTR_CONSTANTS 의 dotted key prefix 가 coverage 에 인식.

    - enum prefix (extend./shape./location./size./position./color./...) ⊆ _ENUM_PREFIXES
    - const value prefix (strategy./line.) ⊆ _CONST_VALUE_PREFIXES (사용자-friendly alias)

    합집합에 없는 prefix 발견 시 drift — coverage 가 attribute access 를 인식 못 함.
    """
    attr_prefixes = {key.split(".", 1)[0] + "." for key in _ATTR_CONSTANTS}
    known_prefixes = set(_ENUM_PREFIXES) | _CONST_VALUE_PREFIXES
    diff = attr_prefixes - known_prefixes
    assert not diff, (
        f"_ATTR_CONSTANTS prefixes not in known prefixes: {sorted(diff)}. "
        f"_ENUM_PREFIXES={sorted(_ENUM_PREFIXES)}, _CONST_VALUE_PREFIXES={sorted(_CONST_VALUE_PREFIXES)}. "
        "neither enum 도 사용자-friendly const value prefix 도 아님 — drift."
    )
