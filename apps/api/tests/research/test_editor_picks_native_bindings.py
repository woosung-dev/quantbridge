"""native 검증에서 원문 위치의 열만 보강하고 검토한 의미는 보존한다."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks.execution import implementation
from tools.research.editor_picks.verification import native_bindings


def item():
    reviewed = [
        {"function": "plotshape", "line": 10, "direction": "long"},
        {"function": "alertcondition", "line": 12, "direction": "short", "when": "truthy"},
    ]
    return {
        "signal_bindings": reviewed,
        "adaptation": {"bindings": [{**row, "column": 0, "converted_line": 99} for row in reviewed]},
    }


def test_native_binding_only_adds_the_unique_source_column():
    value = item()
    before = copy.deepcopy(value)
    observed = native_bindings(value)
    assert observed == [{**row, "column": 0} for row in value["signal_bindings"]]
    assert value == before
    value["signal_bindings"][0]["column"] = 0
    assert native_bindings(value) == observed
    assert "apps/api/scripts/pine_validation/native_capture.py" in implementation()


@pytest.mark.parametrize("change", ("duplicate", "direction", "when", "column", "invalid_column"))
def test_native_binding_rejects_ambiguity_or_changed_meaning(change):
    value = item()
    candidates = value["adaptation"]["bindings"]
    if change == "duplicate":
        candidates[1] = dict(candidates[0])
    elif change == "direction":
        candidates[0]["direction"] = "short"
    elif change == "when":
        candidates[0]["when"] = "false"
    elif change == "column":
        value["signal_bindings"][0]["column"] = 1
    else:
        candidates[0]["column"] = True
    with pytest.raises(ValueError):
        native_bindings(value)
