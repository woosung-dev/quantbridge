"""Metric AST guard가 기록한 별칭·동적 접근 사각을 동결한다.

대상은 ``apps/api/src/**/*.py`` 전체다.

(a) ``name = qb_metric`` 형태의 metric 별칭 대입.
(b) ``module_alias.qb_metric`` 형태의 모듈 별칭 경유 접근.
(c) ``getattr(anything, "qb_metric")`` 형태의 동적 접근.

이 검사는 세 형태의 흐름·재대입을 해석하지 않는다. 현재 hit을 경로별로 동결해
새 유입만 막고, 합성 양성·음성 대조로 스캐너의 도달성과 구분력을 함께 검증한다.
"""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent.parent
_SOURCE_ROOT = _BACKEND_ROOT / "src"

# 2026-08-25 실측: render fallback의 모듈 별칭 접근 1건이 남아 있다.
_FROZEN_ALIAS_ACCESS: dict[str, int] = {
    "apps/api/src/common/metrics_multiproc.py": 1,
}


@dataclass(frozen=True, slots=True)
class _MetricAliasAccess:
    path: str
    lineno: int
    kind: str


def _alias_assignment_count(node: ast.Assign | ast.AnnAssign) -> int:
    if not isinstance(node.value, ast.Name) or not node.value.id.startswith("qb_"):
        return 0
    targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
    return sum(isinstance(target, ast.Name) for target in targets)


def _is_module_alias_access(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.attr.startswith("qb_")
    )


def _is_dynamic_metric_access(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
        and node.args[1].value.startswith("qb_")
    )


def _metric_alias_accesses(tree: ast.AST, path: str) -> list[_MetricAliasAccess]:
    accesses: list[_MetricAliasAccess] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            accesses.extend(
                _MetricAliasAccess(path, node.lineno, "alias_assignment")
                for _ in range(_alias_assignment_count(node))
            )
        if _is_module_alias_access(node):
            accesses.append(_MetricAliasAccess(path, node.lineno, "module_alias"))
        if _is_dynamic_metric_access(node):
            accesses.append(_MetricAliasAccess(path, node.lineno, "dynamic_access"))
    return accesses


def _source_paths() -> list[Path]:
    return sorted(_SOURCE_ROOT.rglob("*.py"))


def _actual_alias_access_map() -> dict[str, int]:
    counts: Counter[str] = Counter()
    for path in _source_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        counts.update(access.path for access in _metric_alias_accesses(tree, relative_path))
    return dict(sorted(counts.items()))


def test_metric_alias_access_matches_the_frozen_map() -> None:
    assert _actual_alias_access_map() == _FROZEN_ALIAS_ACCESS


def test_metric_alias_scanner_detects_synthetic_violations() -> None:
    tree = ast.parse(
        """
alias = qb_alias_metric
module_alias.qb_module_metric.inc()
getattr(module, "qb_dynamic_metric").inc()
"""
    )

    accesses = _metric_alias_accesses(tree, "synthetic.py")

    assert len(accesses) >= 3
    assert {access.kind for access in accesses} == {
        "alias_assignment",
        "module_alias",
        "dynamic_access",
    }


def test_metric_alias_scanner_ignores_non_metric_names() -> None:
    tree = ast.parse(
        """
alias = ordinary_counter
module_alias.ordinary_counter.inc()
getattr(module, "ordinary_counter").inc()
"""
    )

    assert _metric_alias_accesses(tree, "synthetic.py") == []
