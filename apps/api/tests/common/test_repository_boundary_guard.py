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
    # ★`tasks` 는 2026-09-06 에 이 목록에서 빠졌다. 종전에는 9,775줄이 통째로 census 밖이라
    #   「경계 밖 DB 접근 0건」이라는 초록이 **tasks/ 를 안 본 결과**였다. 편입 시점 실측:
    #   축①(select) 0건 · 축②(리치스루) 0건 · 축③(raw SQL) 0건 — 기존 세 축은 아무것도
    #   새로 잡지 않았고, 아래 네 번째 축만 6건을 잡았다.
    {"market_data", "realtime", "health", "scripts", "common", "core"}
)
_SQL_MODULE_PREFIXES = ("sqlalchemy", "sqlmodel")


@dataclass(frozen=True)
class _SelectCall:
    path: str
    lineno: int
    function_name: str


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


class _SelectCallCollector(ast.NodeVisitor):
    def __init__(self, path: str, direct_bindings: set[str], module_bindings: set[str]) -> None:
        self._path = path
        self._direct_bindings = direct_bindings
        self._module_bindings = module_bindings
        self._scope: list[str] = []
        self.calls: list[_SelectCall] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scoped(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_scoped(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_scoped(node, node.name)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_bound_select_call(node, self._direct_bindings, self._module_bindings):
            self.calls.append(
                _SelectCall(
                    path=self._path,
                    lineno=node.lineno,
                    function_name=".".join(self._scope) or "<module>",
                )
            )
        self.generic_visit(node)

    def _visit_scoped(self, node: ast.AST, name: str) -> None:
        self._scope.append(name)
        self.generic_visit(node)
        self._scope.pop()


def _select_calls(path: Path) -> list[_SelectCall]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    direct_bindings, module_bindings = _select_bindings(tree)
    relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
    collector = _SelectCallCollector(relative_path, direct_bindings, module_bindings)
    collector.visit(tree)
    return collector.calls


def _dependency_paths() -> list[Path]:
    return sorted(_SOURCE_ROOT.glob("*/dependencies.py"))


# 동결된 기지 위반 — 지금은 비어 있다(경계 밖 `select(` 0건).
# ★비어 있는 동안 「동결분이 아직 남아 있다」쪽 대칭 검사를 두지 마라 — `actual >= frozenset()`
#   은 **항상 참**이라 판별력이 0이면서 통과 수만 늘린다(2026-08-24 제거).
#   이 집합이 비지 않게 되는 날 그 검사를 함께 되살려라.
_FROZEN_VIOLATIONS = frozenset()


def _actual_violations() -> set[tuple[str, str]]:
    return {
        (call.path, call.function_name)
        for path in _scoped_source_paths()
        for call in _select_calls(path)
    }


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


def test_repository_boundary_census_is_clean() -> None:
    paths = _scoped_source_paths()
    calls = [call for path in paths for call in _select_calls(path)]

    assert len(paths) >= 60
    assert calls == []


def test_dependencies_do_not_contain_scoped_select_calls() -> None:
    dependency_paths = _dependency_paths()
    paths_with_calls = {
        path.relative_to(_REPOSITORY_ROOT).as_posix()
        for path in dependency_paths
        if _select_calls(path)
    }

    assert len(dependency_paths) == 8
    assert paths_with_calls == set()


def test_repository_select_calls_are_excluded_from_the_census() -> None:
    repository_path = _SOURCE_ROOT / "trading/repositories/order_repository.py"
    paths = _scoped_source_paths()

    assert _select_calls(repository_path)
    # ★공허화 대조 — 경로 수집기가 죽어 빈 리스트를 내면 아래 `not in` 은 자명하게 참이라
    #   「repository 가 census 밖이다」를 증명하지 않는다. 위 `_select_calls` 는 select 수집기만
    #   지키고 경로 수집기는 아무도 안 봤다.
    assert len(paths) >= 60
    assert repository_path not in paths


def test_repository_boundary_violations_do_not_expand_beyond_the_frozen_census() -> None:
    actual = _actual_violations()

    assert actual <= _FROZEN_VIOLATIONS, actual - _FROZEN_VIOLATIONS


# ─────────────────────────────────────────────────────────────────────────────
# 두 번째 축 — Repository **리치스루**(`repo.session.<...>`)
#
# ★위의 census 는 이름이 말하는 그대로 **`select(` 호출만** 센다. 그래서 `repo.session.get(...)`
#   처럼 repository 를 뚫고 세션을 직접 쓰는 경로는 **한 건도 세지 않는다** — 그런데도 원장은
#   그 0 을 「Repository 경계 밖 접근 0건」으로 읽어 왔다([BL-763]). 재는 것을 늘려 그 간극을 없앤다.
#   `AsyncSession` 은 Repository 만 보유한다(apps/api/AGENTS.md §3).
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _SessionReachThrough:
    path: str
    lineno: int
    expression: str


def _is_repository_receiver(node: ast.expr) -> bool:
    """`self._events_repo` · `order_repo` 처럼 이름에 repo 가 든 수신자만 참."""
    return "repo" in ast.unparse(node).lower()


def _session_reach_throughs(path: Path) -> list[_SessionReachThrough]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
    found: list[_SessionReachThrough] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or node.attr != "session":
            continue
        if not _is_repository_receiver(node.value):
            continue
        found.append(
            _SessionReachThrough(
                path=relative_path,
                lineno=node.lineno,
                expression=ast.unparse(node),
            )
        )
    return found


def test_reach_through_detector_separates_repository_receivers() -> None:
    """양성/음성 대조 — repository 수신자만 세고 그 밖의 `.session` 은 안 센다."""
    tree = ast.parse(
        """
await self._events_repo.session.get(ExchangeAccount, account_id)
await order_repo.session.execute(stmt)
await self._repo.commit()
await request.session.get(x)
self.session.get(y)
"""
    )
    hits = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "session"
        and _is_repository_receiver(node.value)
    ]

    assert hits == ["self._events_repo.session", "order_repo.session"]


def test_no_service_reaches_through_a_repository_to_its_session() -> None:
    paths = _scoped_source_paths()
    violations = {
        (reach.path, reach.lineno, reach.expression)
        for path in paths
        for reach in _session_reach_throughs(path)
    }

    assert len(paths) >= 60  # 공허화 대조 — 축① 과 같은 하한
    assert violations == set(), (
        "Repository 를 뚫고 AsyncSession 을 직접 쓴다 (apps/api/AGENTS.md §3): "
        f"{sorted(violations)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 세 번째 축 — Repository 밖에서 **raw SQL 을 실행**하는 경로
#
# ★첫 축은 `select(` 만, 두 번째 축은 `repo.session` 리치스루만 센다. `session.execute(text("INSERT …"))`
#   는 둘 다에 안 걸려서 `trading/funding.py` 의 멱등 INSERT 가 오래 Repository 밖에 있었다
#   (2026-08-30 아키텍처 감사). 실행되는 raw SQL 만 센다 — `server_default=text("NOW()")` 같은
#   컬럼 기본값은 DDL 이라 세지 않는다.
# ─────────────────────────────────────────────────────────────────────────────


def _executed_raw_sql(path: Path) -> list[tuple[str, int]]:
    """`<something>.execute(text(...))` 형태만 센다."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "execute" or not node.args:
            continue
        first = node.args[0]
        if (
            isinstance(first, ast.Call)
            and isinstance(first.func, ast.Name)
            and first.func.id == "text"
        ):
            found.append((relative_path, node.lineno))
    return found


def test_raw_sql_detector_ignores_column_defaults_and_orm_statements() -> None:
    """양성/음성 대조 — 실행되는 raw SQL 만 세고 DDL 기본값·ORM 문장은 안 센다."""
    tree = ast.parse(
        """
await session.execute(text("INSERT INTO t VALUES (1)"))
await conn.execute(text("SELECT 1"))
await session.execute(select(Model))
Field(sa_column=Column(server_default=text("NOW()")))
session.execute()
"""
    )
    hits = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
        and node.args
        and isinstance(node.args[0], ast.Call)
        and isinstance(node.args[0].func, ast.Name)
        and node.args[0].func.id == "text"
    ]

    assert hits == [2, 3]


def test_no_raw_sql_is_executed_outside_the_repository_layer() -> None:
    paths = _scoped_source_paths()
    violations = {hit for path in paths for hit in _executed_raw_sql(path)}

    assert len(paths) >= 60  # 공허화 대조 — 축① 과 같은 하한
    assert violations == set(), (
        f"raw SQL 실행은 Repository 층만 한다 (apps/api/AGENTS.md §3): {sorted(violations)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 네 번째 축 — Repository 밖에서 **세션으로 직접 ORM 엔티티를 조회**하는 경로
#
# ★앞의 세 축은 `select(` · `repo.session` 리치스루 · `session.execute(text(...))` 만 센다.
#   `session.get(ExchangeAccount, id)` 는 셋 다에 안 걸린다 — 쿼리를 만들지도, repository 를
#   뚫지도, raw SQL 을 쓰지도 않기 때문이다. 그래서 `tasks/trading.py` 가 이미
#   `ExchangeAccountRepository.get_by_id` 를 가진 채로 6곳에서 세션을 직접 조회하고 있었다
#   (2026-09-06 아키텍처 감사).
#
# ★**수신자 이름에 `session` 이 들어가고 첫 인자가 대문자로 시작하는 Name** 일 때만 센다.
#   `dict.get("k")` · `mapping.get(key)` · `response.get(Model)` 같은 동명이인을 피하는 최소 조건이다.
# ─────────────────────────────────────────────────────────────────────────────


def _session_entity_gets(path: Path) -> list[tuple[str, int, str]]:
    """`<...session...>.get(Model, ...)` 형태만 센다."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
    found: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get" or not node.args:
            continue
        receiver = node.func.value
        if isinstance(receiver, ast.Name):
            receiver_name = receiver.id
        elif isinstance(receiver, ast.Attribute):
            receiver_name = receiver.attr
        else:
            continue
        if "session" not in receiver_name.lower():
            continue
        first = node.args[0]
        if isinstance(first, ast.Name) and first.id[:1].isupper():
            found.append((relative_path, node.lineno, first.id))
    return found


def test_session_entity_get_detector_separates_lookalikes() -> None:
    """양성/음성 대조 — 세션의 ORM 조회만 세고 dict.get·소문자 인자는 안 센다."""
    tree = ast.parse(
        """
await session.get(ExchangeAccount, account_id)
await self._session.get(Order, order_id)
payload.get("exchange_account_id")
mapping.get(key)
session.get(some_lowercase_var)
cache.get(ExchangeAccount, account_id)
"""
    )
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get" or not node.args:
            continue
        receiver = node.func.value
        if isinstance(receiver, ast.Name):
            receiver_name = receiver.id
        elif isinstance(receiver, ast.Attribute):
            receiver_name = receiver.attr
        else:
            continue
        if "session" not in receiver_name.lower():
            continue
        first = node.args[0]
        if isinstance(first, ast.Name) and first.id[:1].isupper():
            hits.append(node.lineno)

    # 2·3 만 잡는다 — 4(dict 문자열 키) · 5(dict 변수 키) · 6(소문자 인자) · 7(session 아님)은 뺀다.
    assert hits == [2, 3]


def test_no_entity_is_loaded_through_a_session_outside_the_repository_layer() -> None:
    paths = _scoped_source_paths()
    violations = {hit for path in paths for hit in _session_entity_gets(path)}

    # ★공허화 대조 — 수집기가 죽어 스코프가 비면 이 단언은 **아무것도 안 재고 초록**이다.
    #   축① `test_repository_boundary_census_is_clean` 이 쓰는 것과 같은 하한이다.
    assert len(paths) >= 60
    assert violations == set(), (
        "ORM 엔티티 조회는 Repository 층만 한다 (apps/api/AGENTS.md §3) — "
        f"해당 Repository 의 `get_by_id` 를 써라: {sorted(violations)}"
    )
