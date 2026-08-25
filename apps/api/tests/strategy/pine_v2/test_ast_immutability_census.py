"""공유 pynescript AST 불변성 census.

대상은 ``apps/api/src/strategy`` 와 ``apps/api/src/backtest`` 의 Python 소스다.
AST 파생 이름은 같은 lexical scope 안에서 (a) ``parse_to_ast(...)`` 또는
``pyne_ast.parse(...)`` 반환값을 받는 지역 이름, (b) 그 이름의 attribute/subscript
표현식을 다시 지역 이름에 대입한 결과로만 정의한다. 이 좁은 규칙으로 AST 노드와 그
``body`` 같은 가변 컨테이너를 함께 추적하되, 일반 객체와 리스트는 세지 않는다.

못 잡는 것: 이름 별칭, ``getattr`` 같은 동적 접근, ``pyne_ast`` 외 모듈 alias, 함수
인자·반환값을 통한 전달, 그리고 AST 파생 표현식을 새 이름에 저장하지 않은 복잡한 data flow.
이 경계는 음성 대조가 정상 지역 컨테이너를 세지 않음을, 양성 대조가 지원하는 모든 mutation
형태를 잡음을 함께 증명한다.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

_IN_PLACE_LIST_METHODS = frozenset(
    {"append", "extend", "insert", "pop", "remove", "clear", "sort", "reverse"}
)
_API_ROOT = Path(__file__).resolve().parents[3]
_REPOSITORY_ROOT = _API_ROOT.parent.parent
_SOURCE_ROOT = _API_ROOT / "src"
_SCANNED_DIRECTORIES = ("strategy", "backtest")
_MINIMUM_SCANNED_FILES = 50


@dataclass(frozen=True)
class _MutationSite:
    path: str
    lineno: int
    kind: str


class _AstMutationCollector(ast.NodeVisitor):
    """정의된 AST 파생 이름에 대한 가변 연산만 수집한다."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._derived_names: set[str] = set()
        self.sites: list[_MutationSite] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_new_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_new_scope(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_new_scope(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        self._bind_targets(node.targets, self._is_derived_expression(node.value))

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)
        if node.value is not None:
            self._bind_target(node.target, self._is_derived_expression(node.value))

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.generic_visit(node)
        self._bind_target(node.target, self._is_derived_expression(node.value))

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.generic_visit(node)
        self._bind_target(node.target, False)

    def visit_Delete(self, node: ast.Delete) -> None:
        self.generic_visit(node)
        self._bind_targets(node.targets, False)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)) and self._is_derived_expression(node.value):
            self._record(
                node, "attribute-store" if isinstance(node.ctx, ast.Store) else "attribute-del"
            )
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)) and self._is_derived_expression(node.value):
            self._record(
                node, "subscript-store" if isinstance(node.ctx, ast.Store) else "subscript-del"
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in {"setattr", "delattr"}:
            if node.args and self._is_derived_expression(node.args[0]):
                self._record(node, node.func.id)
        elif (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _IN_PLACE_LIST_METHODS
            and self._is_derived_expression(node.func.value)
        ):
            self._record(node, "list-method")
        self.generic_visit(node)

    def _visit_new_scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> None:
        outer_derived_names = self._derived_names
        self._derived_names = set()
        self.generic_visit(node)
        self._derived_names = outer_derived_names

    def _bind_targets(self, targets: list[ast.expr], is_derived: bool) -> None:
        for target in targets:
            self._bind_target(target, is_derived)

    def _bind_target(self, target: ast.expr, is_derived: bool) -> None:
        if isinstance(target, ast.Name):
            if is_derived:
                self._derived_names.add(target.id)
            else:
                self._derived_names.discard(target.id)
            return
        if isinstance(target, (ast.List, ast.Tuple)):
            for element in target.elts:
                self._bind_target(element, is_derived)

    def _is_derived_expression(self, expression: ast.expr) -> bool:
        if isinstance(expression, ast.Name):
            return expression.id in self._derived_names
        if isinstance(expression, (ast.Attribute, ast.Subscript)):
            return self._is_derived_expression(expression.value)
        if not isinstance(expression, ast.Call):
            return False
        if isinstance(expression.func, ast.Name):
            return expression.func.id == "parse_to_ast"
        return (
            isinstance(expression.func, ast.Attribute)
            and isinstance(expression.func.value, ast.Name)
            and expression.func.value.id == "pyne_ast"
            and expression.func.attr == "parse"
        )

    def _record(self, node: ast.AST, kind: str) -> None:
        self.sites.append(_MutationSite(path=self._path, lineno=node.lineno, kind=kind))


def _collect_mutation_sites(source: str, path: str = "<synthetic>") -> list[_MutationSite]:
    collector = _AstMutationCollector(path)
    collector.visit(ast.parse(source, filename=path))
    return collector.sites


def _source_files() -> list[Path]:
    return sorted(
        source_file
        for directory in _SCANNED_DIRECTORIES
        for source_file in (_SOURCE_ROOT / directory).rglob("*.py")
    )


def _collect_project_mutation_sites() -> tuple[list[Path], list[_MutationSite]]:
    source_files = _source_files()
    sites: list[_MutationSite] = []
    for source_file in source_files:
        relative_path = source_file.relative_to(_REPOSITORY_ROOT).as_posix()
        sites.extend(
            _collect_mutation_sites(source_file.read_text(encoding="utf-8"), relative_path)
        )
    return source_files, sites


def test_ast_immutability_census_scans_project_sources() -> None:
    """공유 AST를 변형하는 정적 연산은 strategy/backtest 소스에 없어야 한다."""
    source_files, sites = _collect_project_mutation_sites()

    assert len(source_files) >= _MINIMUM_SCANNED_FILES
    assert sites == []


@pytest.mark.parametrize(
    ("source", "expected_kind"),
    [
        ("tree = parse_to_ast(source)\ntree.body = []\n", "attribute-store"),
        ("tree = parse_to_ast(source)\ndel tree.body\n", "attribute-del"),
        ("tree = parse_to_ast(source)\ntree.body[0] = value\n", "subscript-store"),
        ("tree = parse_to_ast(source)\ndel tree.body[0]\n", "subscript-del"),
        ("tree = parse_to_ast(source)\nsetattr(tree, 'body', [])\n", "setattr"),
        ("tree = pyne_ast.parse(source)\ndelattr(tree, 'body')\n", "delattr"),
        (
            "tree = parse_to_ast(source)\nbody = tree.body\nbody.append(statement)\n",
            "list-method",
        ),
    ],
)
def test_ast_immutability_census_detects_each_mutation_pattern(
    source: str, expected_kind: str
) -> None:
    """양성 대조: 지원하는 AST 변형 문법은 각 패턴별로 반드시 검출한다."""
    sites = _collect_mutation_sites(source)

    assert [site.kind for site in sites] == [expected_kind]


def test_ast_immutability_census_ignores_unrelated_mutable_values() -> None:
    """음성 대조: 일반 리스트·dict·dataclasses.replace는 AST 변형이 아니다."""
    source = """
from dataclasses import dataclass, replace

items = []
items.append("normal")
payload = {}
payload["body"] = []

@dataclass
class Config:
    body: list[int]

config = Config(body=[])
copied = replace(config, body=[])
"""

    assert _collect_mutation_sites(source) == []
