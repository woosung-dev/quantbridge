"""pynescript AST를 순회하며 노드 통계 계산. 회귀 baseline 용도."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pynescript import ast as pyne_ast


def _walk(node: Any) -> Iterator[Any]:
    """pynescript AST 재귀 순회 — 노드와 자식을 yield."""
    yield node
    for child in pyne_ast.iter_child_nodes(node):
        yield from _walk(child)


def count_nodes(ast_root: Any) -> int:
    """AST 총 노드 개수."""
    return sum(1 for _ in _walk(ast_root))


def count_node_types(ast_root: Any) -> int:
    """AST 노드 고유 타입 개수."""
    return len({type(node).__name__ for node in _walk(ast_root)})
