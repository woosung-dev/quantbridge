"""`record_metric_safely` 인자 평가 시점의 `.labels()` 호출 census."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent.parent
_SOURCE_ROOT = _BACKEND_ROOT / "src"


# `record_metric_safely(qb_x.labels(...).inc)`는 `.labels()`가 가드보다 먼저 평가된다.
# 다음 step이 실제 호출부를 감싸기 전의 분포를 동결한다.
_FROZEN_LABELS_OUTSIDE_GUARD: dict[str, int] = {
    "apps/api/src/tasks/live_signal.py": 14,
}

_EXPECTED_LAMBDA_WRAPPED_LABELS: dict[str, int] = {
    "apps/api/src/common/metrics.py": 1,
    "apps/api/src/common/metrics_multiproc.py": 2,
    "apps/api/src/tasks/trading.py": 1,
}


@dataclass(frozen=True)
class _LabelSite:
    path: str
    lineno: int


def _contains_labels_call(expression: ast.expr) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "labels"
        for node in ast.walk(expression)
    )


def _label_guard_sites() -> tuple[list[_LabelSite], list[_LabelSite]]:
    outside_guard: list[_LabelSite] = []
    lambda_wrapped: list[_LabelSite] = []
    for path in sorted(_SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "record_metric_safely"
                and node.args
            ):
                continue
            first_argument = node.args[0]
            if not _contains_labels_call(first_argument):
                continue
            site = _LabelSite(path=relative_path, lineno=node.lineno)
            if isinstance(first_argument, ast.Lambda):
                lambda_wrapped.append(site)
            else:
                outside_guard.append(site)
    return outside_guard, lambda_wrapped


def _failure_message(actual: Counter[str], sites: list[_LabelSite]) -> str:
    added_sites: list[_LabelSite] = []
    for path, actual_count in actual.items():
        frozen_count = _FROZEN_LABELS_OUTSIDE_GUARD.get(path, 0)
        if actual_count > frozen_count:
            path_sites = sorted(
                (site for site in sites if site.path == path), key=lambda site: site.lineno
            )
            added_sites.extend(path_sites[frozen_count:])

    reduced_entries = [
        (path, actual.get(path, 0))
        for path, frozen_count in _FROZEN_LABELS_OUTSIDE_GUARD.items()
        if actual.get(path, 0) < frozen_count
    ]
    lines = [
        "Labels outside metric guard census diverged from the frozen baseline.",
        "새 위반 (file, lineno):",
    ]
    lines.extend(f"  ({site.path}, {site.lineno})" for site in added_sites)
    lines.append("줄어든 항목 (_FROZEN_LABELS_OUTSIDE_GUARD에서 이 항목을 삭제해라):")
    lines.extend(
        f"  {path}: 이 항목을 _FROZEN_LABELS_OUTSIDE_GUARD에서 삭제해라 (실측 {count})"
        for path, count in reduced_entries
    )
    return "\n".join(lines)


def test_labels_outside_guard_matches_the_frozen_set() -> None:
    outside_guard, _ = _label_guard_sites()
    actual = Counter(site.path for site in outside_guard)

    assert actual == _FROZEN_LABELS_OUTSIDE_GUARD, _failure_message(actual, outside_guard)


def test_lambda_wrapped_labels_are_not_flagged() -> None:
    outside_guard, lambda_wrapped = _label_guard_sites()

    assert Counter(site.path for site in lambda_wrapped) == _EXPECTED_LAMBDA_WRAPPED_LABELS
    assert not set(outside_guard) & set(lambda_wrapped)
