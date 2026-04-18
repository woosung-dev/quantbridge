"""Phase -1 E2 baseline parity 회귀 — pynescript 0.3.0이 6 corpus를 파싱하여
E2 실측과 동일한 AST 노드 타입/총수를 생산하는지 검증.

드리프트 조건:
- pynescript 버전 변경 → baseline.json 의도적 갱신 필요
- corpus 편집 → 해서는 안 됨 (Phase -1 frozen snapshot)
- 이 테스트가 실패하면 Tier-0 진입 전 반드시 조사
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.strategy.pine_v2.ast_metrics import count_node_types, count_nodes
from src.strategy.pine_v2.parser_adapter import parse_to_ast

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_BASELINE: dict[str, dict[str, int]] = json.loads(
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
