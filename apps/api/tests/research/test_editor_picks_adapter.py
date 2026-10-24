"""원문 포지션 조건을 보존하고 연구에서 생성한 진입 guard만 제거한다."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import catalogue
from tools.research.editor_picks.common import sha

from scripts.pine_validation.strategy_adapter import adapt_strategy

SOURCE = """//@version=5
indicator("Guard preservation", overlay=true)
qb_adapt_long_submitted = close > open
original_position_check = strategy.position_size <= 0
if original_position_check
    original_position_check := strategy.position_size >= 0
long_signal = close > open
short_signal = close < open
plotshape(long_signal)
plotshape(short_signal)
"""
BINDINGS = [
    {"line": 9, "function": "plotshape", "direction": "long"},
    {"line": 10, "function": "plotshape", "direction": "short"},
]


def test_raw_adapter_only_removes_generated_position_guards():
    base = adapt_strategy(SOURCE, BINDINGS, fixed_quantity=None)
    adapted = catalogue.raw_signal_strategy(base)
    for text in (
        "original_position_check = strategy.position_size <= 0",
        "    original_position_check := strategy.position_size >= 0",
        "qb_adapt_long_submitted = close > open",
    ):
        assert text in adapted.strategy_source
    assert "and strategy.position_size" not in adapted.strategy_source
    assert "and not qb_adapt_long_submitted_" in adapted.strategy_source
    assert adapted.source_sha256 == sha(SOURCE.encode()) == base.source_sha256
    assert adapted.converted_sha256 == sha(adapted.strategy_source.encode())
    assert adapted.converted_sha256 != base.converted_sha256
    assert adapted.source_line_map == base.source_line_map
    assert adapted.strategy_source.count("\n") == base.strategy_source.count("\n")
    # 함수는 원래 변환 객체도 변경하지 않는다.
    assert "and strategy.position_size" in base.strategy_source


def test_raw_adapter_fails_closed_on_missing_or_duplicate_generated_guard():
    base = adapt_strategy(SOURCE, BINDINGS, fixed_quantity=None)
    with pytest.raises(ValueError, match="고유 position guard"):
        catalogue.raw_signal_strategy(catalogue.raw_signal_strategy(base))
    guard = next(
        line for line in base.strategy_source.splitlines() if line.startswith("if qb_condition_9_0")
    )
    duplicate = replace(base, strategy_source=base.strategy_source + guard + "\n")
    with pytest.raises(ValueError, match="고유 position guard"):
        catalogue.raw_signal_strategy(duplicate)


def test_screening_semantics_include_raw_adapter(monkeypatch):
    before = catalogue._screen_implementation_hash()
    monkeypatch.setattr(
        catalogue, "raw_signal_strategy", test_raw_adapter_only_removes_generated_position_guards
    )
    assert catalogue._screen_implementation_hash() != before
