"""Phase -1 E2 baseline parity 회귀 — pynescript 0.3.0이 6 corpus를 파싱하여
E2 실측과 동일한 AST 노드 타입/총수/edge shape 를 생산하는지 검증.

드리프트 조건:
- pynescript 버전 변경 → baseline.json 의도적 갱신 필요
- corpus 편집 → 해서는 안 됨 (Phase -1 frozen snapshot)
- 이 테스트가 실패하면 Tier-0 진입 전 반드시 조사

Path β Stage 2 확장 (2026-04-23):
- 기존 types/nodes 수치 외에 **edge_digest** (부모-자식 edge shape sha256) 추가
- Path β Trust Layer CI 의 **P-1 AST Shape Parity** 레이어 (ADR-013 §4.1)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.strategy.pine_v2.ast_metrics import (
    compute_edge_digest,
    count_node_types,
    count_nodes,
)
from src.strategy.pine_v2.parser_adapter import parse_to_ast

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_BASELINE: dict[str, dict[str, Any]] = json.loads(
    (_CORPUS_DIR / "baseline.json").read_text()
)


@pytest.mark.parametrize("script_name", sorted(_BASELINE.keys()))
def test_pynescript_ast_matches_phase_minus_1_baseline(script_name: str) -> None:
    source = (_CORPUS_DIR / f"{script_name}.pine").read_text()
    ast_root = parse_to_ast(source)

    expected = _BASELINE[script_name]
    actual_types = count_node_types(ast_root)
    actual_nodes = count_nodes(ast_root)

    assert actual_types == expected["types"], (
        f"{script_name}: 노드 타입 수 드리프트 "
        f"(실측 {actual_types}, 기대 {expected['types']}). "
        "pynescript 버전 변경 시 baseline.json도 동일 커밋에서 갱신하세요."
    )
    assert actual_nodes == expected["nodes"], (
        f"{script_name}: 총 노드 수 드리프트 "
        f"(실측 {actual_nodes}, 기대 {expected['nodes']})."
    )


@pytest.mark.parametrize("script_name", sorted(_BASELINE.keys()))
def test_pynescript_ast_edge_digest_matches_baseline(script_name: str) -> None:
    """Path β P-1: 부모-자식 edge shape sha256 digest 가 baseline 과 일치.

    types/nodes 수치만으로는 구조 drift (예: `Assign(BinaryOp, Literal)` vs
    `Assign(Literal, BinaryOp)` 같은 자리 바뀜) 를 못 잡음. edge_digest 는
    부모-자식 쌍의 정렬 다중집합 sha256 → 구조 수준 drift 감지.

    실패 시 원인 후보:
    - pynescript 버전 업그레이드 시 AST 구조 변경
    - corpus .pine 파일 의도치 않은 수정
    """
    source = (_CORPUS_DIR / f"{script_name}.pine").read_text()
    ast_root = parse_to_ast(source)

    expected_digest = _BASELINE[script_name].get("edge_digest")
    if expected_digest is None:
        pytest.skip(f"{script_name}: baseline 에 edge_digest 없음 (regen 필요)")

    actual_digest = compute_edge_digest(ast_root)

    assert actual_digest == expected_digest, (
        f"{script_name}: AST edge_digest 드리프트\n"
        f"  실측: {actual_digest}\n"
        f"  기대: {expected_digest}\n"
        "pynescript 버전 또는 corpus .pine 파일 변경 여부 확인 후 "
        "baseline.json 을 동일 커밋에서 갱신하세요."
    )
