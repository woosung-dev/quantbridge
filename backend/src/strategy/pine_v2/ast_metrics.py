"""pynescript AST를 순회하며 노드 통계 계산. 회귀 baseline 용도.

Path β Stage 2 확장 (2026-04-23):
- `edge_digest` — 부모-자식 타입 쌍 정렬 리스트의 sha256 hex
- AST 구조 (edge shape) 가 pynescript 버전 / corpus 편집 간 drift 를 감지
"""
from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import Any

from pynescript import ast as pyne_ast


def _walk(node: Any) -> Iterator[Any]:
    """pynescript AST 재귀 순회 — 노드와 자식을 yield."""
    yield node
    for child in pyne_ast.iter_child_nodes(node):
        yield from _walk(child)


def _walk_edges(node: Any) -> Iterator[tuple[str, str]]:
    """(parent_type, child_type) 쌍을 재귀 yield. root 는 (ROOT, root_type) 로 한 번."""
    yield ("__ROOT__", type(node).__name__)
    for child in pyne_ast.iter_child_nodes(node):
        yield (type(node).__name__, type(child).__name__)
        yield from _walk_edges(child)


def count_nodes(ast_root: Any) -> int:
    """AST 총 노드 개수."""
    return sum(1 for _ in _walk(ast_root))


def count_node_types(ast_root: Any) -> int:
    """AST 노드 고유 타입 개수."""
    return len({type(node).__name__ for node in _walk(ast_root)})


def compute_edge_digest(ast_root: Any) -> str:
    """AST 의 부모-자식 edge shape 를 sha256 hex 로 압축.

    Path β P-1 AST Shape Parity (ADR-013 §4.1). edge 다중집합을 정렬한 뒤
    `parent_type|child_type` 형식으로 직렬화하여 sha256 hash.

    - count_nodes / count_node_types 는 scalar 가 같으면 통과 — 구조 변경을 못 잡음
    - edge_digest 는 **부모→자식 쌍의 다중집합** 을 fingerprint → 구조 drift 감지
    - `Assign(left=BinaryOp, right=Literal)` 가 `Assign(left=Literal, right=BinaryOp)` 로
      바뀌면 edge 다중집합이 같으므로 못 잡음 (P-1 한계, P-3 가 커버)
    """
    edges = sorted(f"{p}|{c}" for p, c in _walk_edges(ast_root))
    joined = "\n".join(edges).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()
