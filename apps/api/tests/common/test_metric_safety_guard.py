"""live_signal 업무 결과 경로의 raw metric mutation census."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent.parent
_TARGET_PATH = _BACKEND_ROOT / "src/tasks/live_signal.py"
_MUTATION_METHODS = frozenset({"inc", "dec", "observe", "set"})


@dataclass(frozen=True)
class _MetricSite:
    path: str
    lineno: int
    is_raw: bool


def _root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, (ast.Attribute, ast.Call)):
        current = current.value if isinstance(current, ast.Attribute) else current.func
    return current.id if isinstance(current, ast.Name) else None


def _is_metric_mutation(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr in _MUTATION_METHODS
        and (_root_name(node) or "").startswith("qb_")
    )


def _is_metric_mutation_call(node: ast.Call) -> bool:
    return _is_metric_mutation(node.func)


def _is_safe_wrapper(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Name) and node.func.id == "record_metric_safely"


class _MetricSiteCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self._path = path
        self._safe_wrapper_depth = 0
        self._try_body_depth = 0
        self.sites: list[_MetricSite] = []

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_try_body(node.body)
        for handler in node.handlers:
            self._visit_try_body(handler.body)
        self._visit_try_body(node.finalbody)
        for statement in node.orelse:
            self.visit(statement)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_safe_wrapper(node):
            self._visit_safe_wrapper(node)
            return
        if _is_metric_mutation_call(node):
            self._record(node)
        self.generic_visit(node)

    def _visit_try_body(self, statements: list[ast.stmt]) -> None:
        self._try_body_depth += 1
        for statement in statements:
            self.visit(statement)
        self._try_body_depth -= 1

    def _visit_safe_wrapper(self, node: ast.Call) -> None:
        self._safe_wrapper_depth += 1
        for argument in (*node.args, *(keyword.value for keyword in node.keywords)):
            if _is_metric_mutation(argument):
                self._record(argument)
            else:
                self.visit(argument)
        self._safe_wrapper_depth -= 1

    def _record(self, node: ast.AST) -> None:
        self.sites.append(
            _MetricSite(
                path=self._path,
                lineno=node.lineno,
                is_raw=self._try_body_depth > 0 and self._safe_wrapper_depth == 0,
            )
        )


def _collect_metric_sites(tree: ast.AST, path: str) -> list[_MetricSite]:
    collector = _MetricSiteCollector(path)
    collector.visit(tree)
    return sorted(collector.sites, key=lambda site: site.lineno)


def _target_metric_sites() -> list[_MetricSite]:
    tree = ast.parse(_TARGET_PATH.read_text(encoding="utf-8"), filename=str(_TARGET_PATH))
    path = _TARGET_PATH.relative_to(_REPOSITORY_ROOT).as_posix()
    return _collect_metric_sites(tree, path)


def all_metric_sites() -> list[tuple[str, int]]:
    """스캔 대상에서 찾은 모든 qb_* metric mutation 호출. (상대경로, lineno)."""
    return [(site.path, site.lineno) for site in _target_metric_sites()]


def raw_metric_sites() -> list[tuple[str, int]]:
    """try/except/finally 본문 안의 record_metric_safely로 감싸이지 않은 qb_* mutation 호출."""
    return [(site.path, site.lineno) for site in _target_metric_sites() if site.is_raw]


def test_metric_census_finds_all_live_signal_mutations() -> None:
    assert len(all_metric_sites()) >= 30


def test_raw_metric_census_matches_frozen_control_count() -> None:
    assert len(raw_metric_sites()) == 0


def test_metric_collector_distinguishes_try_context_and_safe_wrapper() -> None:
    tree = ast.parse(
        """
qb_outside.inc()
try:
    qb_raw.inc()
    record_metric_safely(qb_safe.inc)
    qb_labeled.labels(kind="test").inc()
except Exception:
    qb_except.observe(1)
else:
    qb_else.dec()
finally:
    qb_final.set(1)
"""
    )

    sites = _collect_metric_sites(tree, "inline.py")
    raw_lines = {site.lineno for site in sites if site.is_raw}

    assert len(sites) == 7
    assert raw_lines == {4, 6, 8, 12}
