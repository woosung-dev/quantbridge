"""명세의 신뢰 경계와 생성 산출물의 실제 parser 계약을 검증한다."""

from __future__ import annotations

import ast
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from tools.research.strategy_catalogue30 import candidates

from src.strategy.code_runtime.compiler import compile_strategy
from src.strategy.code_runtime.spec import StrategySpec, UnsupportedStrategySpec
from src.strategy.pine_v2.coverage import analyze_coverage


@pytest.fixture
def spec_data() -> dict:
    return deepcopy(candidates()[0]["reference_spec"])


@pytest.mark.parametrize(
    "field,value",
    [("raw_code", "danger()"), ("fill_timing", "bar_close"), ("risk_policy", "omit_stops")],
)
def test_spec_rejects_code_injection_and_execution_contract_changes(
    spec_data: dict, field: str, value: str
) -> None:
    spec_data[field] = value
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(spec_data)


@pytest.mark.parametrize(
    "reference",
    [
        {"series": "missing"},
        {"series": "close", "offset": -1},
        {"series": "ema20", "output": "upper"},
        {"constant": float("nan")},
        {"series": "close", "constant": 1},
        {"series": "__import__('os')"},
    ],
)
def test_spec_rejects_invalid_or_future_references(spec_data: dict, reference: dict) -> None:
    spec_data["long_entry"]["left"] = reference
    with pytest.raises(ValidationError):
        StrategySpec.model_validate(spec_data)


def test_duplicate_indicator_id_is_rejected(spec_data: dict) -> None:
    spec_data["indicators"].append(deepcopy(spec_data["indicators"][0]))
    with pytest.raises(ValidationError, match="중복"):
        StrategySpec.model_validate(spec_data)


def test_condition_complexity_is_bounded(spec_data: dict) -> None:
    condition = {"op": "true"}
    for _ in range(13):
        condition = {"op": "not", "children": [condition]}
    spec_data["long_entry"] = condition
    with pytest.raises(ValidationError, match="깊이"):
        StrategySpec.model_validate(spec_data)


def test_catalogue_has_exactly_30_unique_frozen_rule_sets() -> None:
    rows = candidates()
    assert [row["id"] for row in rows] == [f"{n:02}" for n in range(1, 31)]
    json.dumps(rows, allow_nan=False)
    for row in rows:
        assert row["source_status"] == "indicator_definition_project_variant"
        assert all(
            row["rules"][key]
            for key in (
                "long_entry",
                "short_entry",
                "long_invalidation",
                "short_invalidation",
                "risk",
            )
        )
        assert row["source_urls"]
    rows[0]["rules"]["long_entry"] = "changed"
    assert candidates()[0]["rules"]["long_entry"] != "changed"


_REFERENCES = [row for row in candidates() if row["reference_spec"]]


@pytest.mark.parametrize("row", _REFERENCES, ids=lambda row: row["id"])
def test_supported_python_artifacts_compile_without_execution(row: dict) -> None:
    code = compile_strategy(row["reference_spec"], "python")
    tree = ast.parse(code)
    assert any(isinstance(node, ast.FunctionDef) and node.name == "on_bar" for node in tree.body)
    compile(tree, "generated_strategy", "exec")


@pytest.mark.parametrize("row", _REFERENCES, ids=lambda row: row["id"])
def test_pine_export_is_runnable_or_explicitly_unsupported(row: dict) -> None:
    if row["id"] in {"18", "24", "25", "26", "27"}:
        with pytest.raises(UnsupportedStrategySpec, match="lowering"):
            compile_strategy(row["reference_spec"], "pine")
        return
    result = analyze_coverage(compile_strategy(row["reference_spec"], "pine"))
    assert result.is_runnable, result.all_unsupported
    assert not result.has_degraded


def test_unsupported_pattern_is_not_replaced_with_simple_signal(spec_data: dict) -> None:
    spec_data["indicators"][0]["kind"] = "supertrend"
    with pytest.raises(UnsupportedStrategySpec, match="supertrend"):
        compile_strategy(spec_data, "python")


def test_title_is_data_and_cannot_add_python_statements(spec_data: dict) -> None:
    spec_data["title"] = '"); __import__("os").system("touch escaped"); #'
    tree = ast.parse(compile_strategy(spec_data, "python"))
    assignment = tree.body[0]
    assert isinstance(assignment, ast.Assign)
    assert ast.literal_eval(assignment.value)["title"] == spec_data["title"]
