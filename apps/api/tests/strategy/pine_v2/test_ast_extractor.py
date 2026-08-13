"""AST 구조화 내용 추출기 회귀 테스트 (Day 7).

ast_content_report.json fixture와 strict equality + 구조적 invariants 검증.
Week 2 Pine AST interpreter가 필요로 할 메타데이터가 전부 보존되는지 확인.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.strategy.pine_v2.ast_extractor import extract_content

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_REPORT: dict[str, dict] = json.loads(
    (_CORPUS_DIR / "ast_content_report.json").read_text()
)


@pytest.mark.parametrize("script_name", sorted(_REPORT.keys()))
def test_extract_content_matches_baseline(script_name: str) -> None:
    source = (_CORPUS_DIR / f"{script_name}.pine").read_text()
    actual = extract_content(source).to_dict()
    expected = _REPORT[script_name]

    assert actual == expected, (
        f"{script_name}: content 추출 드리프트\n"
        f"  expected keys: {list(expected.keys())}\n"
        f"  actual keys:   {list(actual.keys())}"
    )


@pytest.mark.parametrize(("script_name", "kind"), [
    ("s1_pbr", "strategy"),
    ("s2_utbot", "strategy"),
    ("s3_rsid", "strategy"),
    ("i1_utbot", "indicator"),
    ("i2_luxalgo", "indicator"),
    ("i3_drfx", "indicator"),
])
def test_declaration_kind_matches_track(script_name: str, kind: str) -> None:
    assert _REPORT[script_name]["declaration"]["kind"] == kind


def test_s3_rsid_captures_strategy_kwargs() -> None:
    """s3_rsid는 strategy() 선언에 initial_capital/commission 등 7개 kwarg 포함.

    Week 2 interpreter가 초기자본·수수료·pyramiding 을 반영하려면 이 정보 필수.
    """
    args = _REPORT["s3_rsid"]["declaration"]["args"]
    arg_names = {a["name"] for a in args if a["name"] is not None}
    # 표제만 확인 (값 형식은 pine_v2 interpreter Week 2에서 처리)
    assert len(args) == 7, f"s3_rsid strategy() 에 7개 arg 기대, 실측 {len(args)}"
    assert any(n in arg_names for n in ("initial_capital", "commission_type", "commission_value", "pyramiding", "overlay")), (
        f"주요 strategy kwarg 누락: {arg_names}"
    )


def test_i2_luxalgo_uses_v5_typed_inputs() -> None:
    """i2_luxalgo는 Pine v5 `input.int/float/string` 사용 — 유형 보존 확인."""
    inputs = _REPORT["i2_luxalgo"]["inputs"]
    types = {i["input_type"] for i in inputs}
    # v5+ 는 input.int / input.float / input.string 등 타이핑 필수
    assert {"int", "float", "string"}.issubset(types | {"bool", "color"}), (
        f"v5 typed input 감지 실패: {types}"
    )


def test_s1_pbr_has_two_strategy_entry_calls() -> None:
    """s1_pbr는 Long/Short 진입 단순 OCO — strategy.entry 정확히 2회."""
    calls = _REPORT["s1_pbr"]["strategy_calls"]
    assert len(calls) == 2
    assert all(c["name"] == "strategy.entry" for c in calls)


def test_s3_rsid_uses_strategy_close_pattern() -> None:
    """s3_rsid는 entry 1 + close 2 (Long·Short 각 1) 패턴."""
    calls = _REPORT["s3_rsid"]["strategy_calls"]
    entries = [c for c in calls if c["name"] == "strategy.entry"]
    closes = [c for c in calls if c["name"] == "strategy.close"]
    assert len(entries) == 1
    assert len(closes) == 2


def test_i2_luxalgo_var_declarations_extracted() -> None:
    """i2_luxalgo는 9개 var 선언 (upper, lower, slope_ph 등)."""
    vars_ = _REPORT["i2_luxalgo"]["var_declarations"]
    assert len(vars_) == 9
    names = {v["var_name"] for v in vars_}
    assert "upper" in names
    assert "lower" in names


def test_i3_drfx_has_many_var_declarations_with_arrays() -> None:
    """i3_drfx는 24개 var 선언, 상당수가 array.new_* 초기화 (Pine arrays)."""
    vars_ = _REPORT["i3_drfx"]["var_declarations"]
    assert len(vars_) == 24
    array_decls = [v for v in vars_ if "array.new_" in v["initial_expr"]]
    assert len(array_decls) >= 5, (
        "Pine 배열 컬렉션을 var로 선언하는 패턴이 Week 2-3 interpreter 과제"
    )
    # 모두 kind는 var 또는 varip
    assert all(v["kind"] in ("var", "varip") for v in vars_)


def test_track_s_scripts_have_strategy_calls() -> None:
    """Track S corpus는 strategy.* 실행 호출이 반드시 있어야."""
    for name in ("s1_pbr", "s2_utbot", "s3_rsid"):
        calls = _REPORT[name]["strategy_calls"]
        assert len(calls) > 0, f"{name}은 strategy()인데 strategy.* 호출 0"


def test_track_a_scripts_have_no_strategy_calls() -> None:
    """Track A corpus는 indicator이므로 strategy.* 실행 호출 없음 — ADR-011 §3 3-Track 판별 교차 확인."""
    for name in ("i1_utbot", "i2_luxalgo", "i3_drfx"):
        calls = _REPORT[name]["strategy_calls"]
        assert len(calls) == 0, f"{name}은 indicator인데 strategy.* 호출 {len(calls)}개"


def test_total_extracted_counts() -> None:
    """corpus 전체 합계 — 요약 수치가 drift하면 테스트 실패."""
    total_inputs = sum(len(r["inputs"]) for r in _REPORT.values())
    total_vars = sum(len(r["var_declarations"]) for r in _REPORT.values())
    total_strategy_calls = sum(len(r["strategy_calls"]) for r in _REPORT.values())
    assert total_inputs == 57, f"total inputs drift (실측 {total_inputs})"
    assert total_vars == 33, f"total var/varip drift (실측 {total_vars})"
    assert total_strategy_calls == 7, f"total strategy.* drift (실측 {total_strategy_calls})"
