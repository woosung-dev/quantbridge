"""SSOT parity invariant audit — Sprint 29 Slice C.

drift 차단 자동 감지:
- STDLIB_NAMES ⊆ SUPPORTED_FUNCTIONS
- _RENDERING_FACTORIES.keys() ⊆ SUPPORTED_FUNCTIONS
- _V4_ALIASES.values() ⊆ STDLIB_NAMES
- interpreter._ATTR_CONSTANTS prefixes ⊆ coverage._ENUM_PREFIXES
"""

from src.strategy.pine_v2.coverage import (
    _ENUM_PREFIXES,
    SUPPORTED_FUNCTIONS,
)
from src.strategy.pine_v2.interpreter import (
    _ATTR_CONSTANTS,
    _RENDERING_FACTORIES,
    STDLIB_NAMES,
)


def test_stdlib_names_subset_of_supported_functions():
    """interpreter.STDLIB_NAMES (ta.*/math.*) 가 모두 coverage.SUPPORTED_FUNCTIONS 에 등록."""
    diff = STDLIB_NAMES - SUPPORTED_FUNCTIONS
    assert not diff, f"STDLIB_NAMES not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_rendering_factories_subset_of_supported_functions():
    """interpreter._RENDERING_FACTORIES (line.*/box.*/label.*/table.*) 가 SUPPORTED_FUNCTIONS 에 등록."""
    diff = set(_RENDERING_FACTORIES.keys()) - SUPPORTED_FUNCTIONS
    assert not diff, f"_RENDERING_FACTORIES keys not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_v4_aliases_targets_in_stdlib():
    """interpreter._V4_ALIASES (atr/sma/ema 등 V4 short → V5 ta.*) 의 target 이 STDLIB_NAMES 에 등록."""
    try:
        from src.strategy.pine_v2.interpreter import _V4_ALIASES
    except ImportError:
        import pytest

        pytest.skip("_V4_ALIASES not exported from interpreter.py")

    diff = set(_V4_ALIASES.values()) - STDLIB_NAMES
    assert not diff, f"_V4_ALIASES targets not in STDLIB_NAMES: {sorted(diff)}"


def test_attr_constants_prefixes_subset_of_enum_prefixes():
    """interpreter._ATTR_CONSTANTS 의 dotted key prefix 가 coverage._ENUM_PREFIXES 와 일관."""
    attr_prefixes = {key.split(".", 1)[0] + "." for key in _ATTR_CONSTANTS}
    enum_prefix_set = set(_ENUM_PREFIXES)
    diff = attr_prefixes - enum_prefix_set
    assert not diff, (
        f"_ATTR_CONSTANTS prefixes not in _ENUM_PREFIXES: {sorted(diff)}. "
        "coverage 가 enum 의 attribute access (예: location.absolute) 를 인식하지 못함."
    )
