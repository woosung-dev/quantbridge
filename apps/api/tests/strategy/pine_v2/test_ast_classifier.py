"""AST 분류기 회귀 — 6 corpus 프로파일이 기록된 baseline과 완전 일치해야 한다.

fixture `ast_structure_report.json`은 Phase -1 Day 2 스냅샷.
- pynescript 버전 갱신 → fixture도 동일 커밋에서 재생성·검토
- corpus 편집 금지 (Phase -1 frozen snapshot)
- 분류기 로직 변경 시 (분류 규칙 추가 등) → fixture 재생성 + PR에서 근거 기술

추가: 구조적 invariants(track 값 집합, declaration 값 집합) 검증.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.strategy.pine_v2.ast_classifier import classify_script

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_REPORT: dict[str, dict] = json.loads(
    (_CORPUS_DIR / "ast_structure_report.json").read_text()
)

_VALID_TRACKS = {"S", "A", "M", "unknown"}
_VALID_DECLARATIONS = {"strategy", "indicator", "library", "unknown"}


@pytest.mark.parametrize("script_name", sorted(_REPORT.keys()))
def test_classify_script_matches_baseline(script_name: str) -> None:
    source = (_CORPUS_DIR / f"{script_name}.pine").read_text()
    actual = classify_script(source).to_dict()
    expected = _REPORT[script_name]

    assert actual == expected, (
        f"{script_name}: 프로파일 드리프트\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}\n"
        "pynescript 버전 갱신 또는 분류 규칙 변경 시 "
        "ast_structure_report.json을 동일 커밋에서 재생성하세요."
    )


@pytest.mark.parametrize("script_name", sorted(_REPORT.keys()))
def test_profile_structural_invariants(script_name: str) -> None:
    """track / declaration 값이 enum 범위 내인지 — 분류기 하자 감지."""
    profile = _REPORT[script_name]
    assert profile["track"] in _VALID_TRACKS
    assert profile["declaration"] in _VALID_DECLARATIONS
    # Track S는 strategy_calls가 1개 이상 있어야 자연스러움(하지만 필수 아님)
    if profile["track"] == "S":
        assert profile["declaration"] == "strategy"
    # Track A는 alert_count > 0
    if profile["track"] == "A":
        assert profile["alert_count"] > 0
    # Track M은 indicator/library + alert 없음
    if profile["track"] == "M":
        assert profile["declaration"] in ("indicator", "library")
        assert profile["alert_count"] == 0
