"""Repository 경계 밖의 SQL select 호출 census.

대상은 ``src/**/*.py`` 중 repository 경로와 3-Layer 예외 디렉터리를 뺀 파일이다.
``select`` 동명이인(numpy 등)은 ``sqlmodel`` 또는 ``sqlalchemy`` import가 바인딩한
이름일 때만 센다.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent.parent
_SOURCE_ROOT = _BACKEND_ROOT / "src"
_EXCLUDED_DIRECTORIES = frozenset(
    {"market_data", "realtime", "health", "tasks", "scripts", "common", "core"}
)
_SQL_MODULE_PREFIXES = ("sqlalchemy", "sqlmodel")


@dataclass(frozen=True)
class _SelectCall:
    path: str
    lineno: int


def _is_sql_module(module: str) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.") for prefix in _SQL_MODULE_PREFIXES
    )


def _scoped_source_paths() -> list[Path]:
    paths: list[Path] = []
    for path in sorted(_SOURCE_ROOT.rglob("*.py")):
        relative_path = path.relative_to(_SOURCE_ROOT)
        if "repositor" in relative_path.as_posix():
            continue
        if any(part in _EXCLUDED_DIRECTORIES for part in relative_path.parts[:-1]):
            continue
        paths.append(path)
    return paths


def _select_bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    direct_bindings: set[str] = set()
    module_bindings: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and _is_sql_module(node.module or ""):
            direct_bindings.update(
                alias.asname or alias.name for alias in node.names if alias.name == "select"
            )
        if isinstance(node, ast.Import):
            module_bindings.update(
                alias.asname or alias.name.split(".", maxsplit=1)[0]
                for alias in node.names
                if _is_sql_module(alias.name)
            )

    return direct_bindings, module_bindings


def _is_bound_select_call(
    call: ast.Call, direct_bindings: set[str], module_bindings: set[str]
) -> bool:
    if isinstance(call.func, ast.Name):
        return call.func.id in direct_bindings
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "select"
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id in module_bindings
    )


def _select_calls(path: Path) -> list[_SelectCall]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    direct_bindings, module_bindings = _select_bindings(tree)
    relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
    return [
        _SelectCall(path=relative_path, lineno=node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _is_bound_select_call(node, direct_bindings, module_bindings)
    ]


def _dependency_paths() -> list[Path]:
    return sorted(_SOURCE_ROOT.glob("*/dependencies.py"))


def test_select_collector_ignores_non_sql_select_names() -> None:
    tree = ast.parse(
        """
from numpy import select as numpy_select
from sqlalchemy import select as sqlalchemy_select
import numpy as np
import sqlalchemy as sa
import sqlmodel as sm

numpy_select([])
sqlalchemy_select(User)
np.select([])
sa.select(User)
sm.select(Model)
"""
    )
    direct_bindings, module_bindings = _select_bindings(tree)
    calls = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _is_bound_select_call(node, direct_bindings, module_bindings)
    ]

    assert calls == [9, 11, 12]


def test_repository_boundary_census_has_positive_control() -> None:
    paths = _scoped_source_paths()
    calls = [call for path in paths for call in _select_calls(path)]

    assert len(paths) >= 60
    assert len(calls) >= 6


def test_only_trading_dependencies_contain_scoped_select_calls() -> None:
    dependency_paths = _dependency_paths()
    paths_with_calls = {
        path.relative_to(_REPOSITORY_ROOT).as_posix()
        for path in dependency_paths
        if _select_calls(path)
    }

    assert len(dependency_paths) == 8
    assert paths_with_calls == {"apps/api/src/trading/dependencies.py"}
