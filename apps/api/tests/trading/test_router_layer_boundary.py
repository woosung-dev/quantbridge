"""라우터가 Repository·AsyncSession 경계를 넘지 않는지 AST로 검사한다."""

import ast
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"
_TRADING_ROUTER = _SOURCE_ROOT / "trading" / "router.py"


def _router_trees() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in sorted(_SOURCE_ROOT.glob("*/router.py"))
    ]


def _display_path(path: Path) -> str:
    return path.relative_to(_SOURCE_ROOT.parent).as_posix()


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _is_get_async_session_import(node: ast.Import | ast.ImportFrom) -> bool:
    return any(
        name is not None and name.split(".")[-1] == "get_async_session"
        for alias in node.names
        for name in (alias.name, alias.asname)
    )


def _repository_import_violation(node: ast.Import | ast.ImportFrom) -> str | None:
    """Repository 심볼·모듈을 라우터가 import 하는 자리를 잡는다.

    ★호출 이름만 보면 `import OrderRepository as _OR` + `_OR(session)` 로 우회된다
    (2026-08-19 변이 실측: 호출 검사만으로는 초록이었다). import 표면을 함께 재야 막힌다.
    """
    module = getattr(node, "module", None) or ""
    if "repositor" in module:
        return f"{module} import"
    for alias in node.names:
        if alias.name.endswith("Repository") or "repositor" in alias.name:
            return f"{alias.name} import"
    return None


def _is_router_decorator(decorator: ast.expr) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "router"
    )


def _route_count(tree: ast.Module) -> int:
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_is_router_decorator(decorator) for decorator in node.decorator_list)
        for node in ast.walk(tree)
    )


def test_routers_do_not_instantiate_repositories() -> None:
    violations: list[str] = []
    for path, tree in _router_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and (_call_name(node) or "").endswith("Repository"):
                violations.append(f"{_display_path(path)}:{node.lineno}:{_call_name(node)}")
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = _repository_import_violation(node)
                if imported is not None:
                    violations.append(f"{_display_path(path)}:{node.lineno}:{imported}")

    assert not violations, (
        "라우터에서 Repository를 직접 조립했습니다:\n"
        + "\n".join(violations)
        + "\nRepository 조립은 `dependencies.py` 가 유일한 자리다 (AGENTS.md §3)"
    )


def test_routers_do_not_take_async_session() -> None:
    violations: list[str] = []
    for path, tree in _router_trees():
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and _is_get_async_session_import(
                node
            ):
                violations.append(f"{_display_path(path)}:{node.lineno}:get_async_session import")
            elif (isinstance(node, ast.Name) and node.id == "get_async_session") or (
                isinstance(node, ast.Attribute) and node.attr == "get_async_session"
            ):
                violations.append(f"{_display_path(path)}:{node.lineno}:get_async_session")
            elif isinstance(node, ast.arg) and node.annotation is not None:
                annotation = ast.unparse(node.annotation)
                if "AsyncSession" in annotation:
                    violations.append(f"{_display_path(path)}:{node.lineno}:{annotation}")

    assert not violations, "라우터가 AsyncSession을 직접 받습니다:\n" + "\n".join(violations)


def test_router_scan_is_not_vacuous() -> None:
    router_trees = _router_trees()
    route_counts = {path: _route_count(tree) for path, tree in router_trees}

    assert len(router_trees) >= 8, (
        f"라우터 스캔 대상이 {len(router_trees)}개다 — 경로가 틀려 0건이라 통과하면 안 된다"
    )
    assert sum(route_counts.values()) >= 55, (
        f"라우터 데코레이터가 {sum(route_counts.values())}개다 — 경로가 틀려 0건이라 통과하면 안 된다"
    )
    assert route_counts.get(_TRADING_ROUTER, 0) >= 20, (
        f"trading/router.py 라우트가 {route_counts.get(_TRADING_ROUTER, 0)}개다 — "
        "경로가 틀려 0건이라 통과하면 안 된다"
    )
