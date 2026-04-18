"""AST 구조화 내용 추출기 (Day 7).

Week 2 Pine AST interpreter가 필요로 할 구조화된 전략 메타데이터 사전 추출:
- 선언 호출(`strategy()` / `indicator()` / `library()`) + **전체 kwarg** 보존
  (initial_capital, commission_type, commission_value, pyramiding, default_qty_type, overlay 등)
- `input.*()` 호출 — 유형(int/float/bool/string), 타겟 변수명, defval, title, min/max
- `var` / `varip` 선언 — pynescript AST에 Var/VarIp marker 자식 노드로 표기됨
- `strategy.*` 실행 호출 — entry / exit / close / close_all / cancel (positional + kwarg)

이 extractor는 분류기(L2)와 분리. L2는 카운트/Track 판정 중심, L7은 실제 값 보존.

공개 API:
- `extract_content(source: str) -> ScriptContent`
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

from pynescript import ast as pyne_ast

DeclarationKind = Literal["strategy", "indicator", "library", "unknown"]
VarKind = Literal["var", "varip"]


@dataclass(frozen=True)
class ArgValue:
    """단일 Call 인자 — positional이면 name=None, kwarg면 name 지정."""

    name: str | None
    value: str  # stringified

    def to_dict(self) -> dict[str, str | None]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True)
class DeclarationInfo:
    kind: DeclarationKind
    title: str | None
    args: list[ArgValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "args": [a.to_dict() for a in self.args],
        }


@dataclass(frozen=True)
class InputDecl:
    input_type: str  # int / float / bool / string / price / source / ...
    var_name: str
    defval: str | None
    title: str | None
    args: list[ArgValue] = field(default_factory=list)  # 전체 호출 인자 원본

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_type": self.input_type,
            "var_name": self.var_name,
            "defval": self.defval,
            "title": self.title,
            "args": [a.to_dict() for a in self.args],
        }


@dataclass(frozen=True)
class VarDecl:
    var_name: str
    initial_expr: str
    kind: VarKind

    def to_dict(self) -> dict[str, Any]:
        return {
            "var_name": self.var_name,
            "kind": self.kind,
            "initial_expr": self.initial_expr,
        }


@dataclass(frozen=True)
class StrategyCall:
    name: str  # "strategy.entry" | "strategy.exit" | "strategy.close" 등
    args: list[ArgValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "args": [a.to_dict() for a in self.args]}


@dataclass(frozen=True)
class ScriptContent:
    declaration: DeclarationInfo
    inputs: list[InputDecl]
    var_declarations: list[VarDecl]
    strategy_calls: list[StrategyCall]

    def to_dict(self) -> dict[str, Any]:
        return {
            "declaration": self.declaration.to_dict(),
            "inputs": [i.to_dict() for i in self.inputs],
            "var_declarations": [v.to_dict() for v in self.var_declarations],
            "strategy_calls": [s.to_dict() for s in self.strategy_calls],
        }


# ---- stringify (공용) -----------------------------------------------


def _stringify(node: Any) -> str:
    """AST 노드를 읽을 수 있는 문자열로 근사 복원."""
    if isinstance(node, pyne_ast.Constant):
        return repr(node.value) if isinstance(node.value, str) else str(node.value)
    if isinstance(node, pyne_ast.Name):
        return node.id
    if isinstance(node, pyne_ast.Attribute):
        return f"{_stringify(node.value)}.{node.attr}"
    if isinstance(node, pyne_ast.BinOp):
        op = type(node.op).__name__
        return f"{_stringify(node.left)} {op} {_stringify(node.right)}"
    if isinstance(node, pyne_ast.UnaryOp):
        return f"not {_stringify(node.operand)}"
    if isinstance(node, pyne_ast.Compare):
        left = _stringify(node.left)
        comps = getattr(node, "comparators", [])
        if comps:
            return f"{left} <cmp> {_stringify(comps[0])}"
        return left
    if isinstance(node, pyne_ast.Call):
        func = _stringify(node.func)
        args = ", ".join(
            _stringify(a.value if isinstance(a, pyne_ast.Arg) else a)
            for a in node.args[:3]
        )
        if len(node.args) > 3:
            args += ", ..."
        return f"{func}({args})"
    return f"<{type(node).__name__}>"


def _call_name(node: Any) -> str | None:
    """Call의 함수명을 'strategy', 'indicator', 'input.int', 'strategy.entry' 등으로 반환."""
    if not isinstance(node, pyne_ast.Call):
        return None
    func = node.func
    if isinstance(func, pyne_ast.Name):
        return func.id
    if isinstance(func, pyne_ast.Attribute):
        parts: list[str] = []
        cur: Any = func
        while isinstance(cur, pyne_ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, pyne_ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _extract_args(call_node: Any) -> list[ArgValue]:
    """Call 노드의 Arg 리스트에서 ArgValue 목록 추출."""
    out: list[ArgValue] = []
    for a in call_node.args:
        if isinstance(a, pyne_ast.Arg):
            name = getattr(a, "name", None)
            out.append(ArgValue(name=name, value=_stringify(a.value)))
        else:
            out.append(ArgValue(name=None, value=_stringify(a)))
    return out


def _get_arg(args: list[ArgValue], position: int, name: str | None = None) -> str | None:
    """위치 또는 name으로 ArgValue 조회, 없으면 None.

    Pine은 positional + kwarg 혼용 — 1st positional이 없으면 name으로 재탐색.
    """
    if position < len(args):
        cand = args[position]
        if cand.name is None or cand.name == name:
            return cand.value
    if name is not None:
        for a in args:
            if a.name == name:
                return a.value
    return None


def _strip_string_quotes(s: str | None) -> str | None:
    """`'hello'` → `hello` (repr 껍질 제거)."""
    if s is None:
        return None
    if len(s) >= 2 and ((s[0] == s[-1] == "'") or (s[0] == s[-1] == '"')):
        return s[1:-1]
    return s


# ---- AST 순회 ---------------------------------------------------------


def _walk(node: Any) -> Iterator[Any]:
    yield node
    for child in pyne_ast.iter_child_nodes(node):
        yield from _walk(child)


def _detect_var_kind(assign_node: Any) -> VarKind | None:
    """Assign의 자식에서 Var / VarIp marker 노드를 찾아 kind 반환."""
    for child in pyne_ast.iter_child_nodes(assign_node):
        cls = type(child).__name__
        if cls == "Var":
            return "var"
        if cls == "VarIp":
            return "varip"
    return None


# ---- 추출 로직 --------------------------------------------------------


def _extract_declaration(tree: Any) -> DeclarationInfo:
    """top-level body에서 strategy/indicator/study/library 선언 추출."""
    for stmt in getattr(tree, "body", []):
        expr_val = getattr(stmt, "value", stmt)
        if not isinstance(expr_val, pyne_ast.Call):
            continue
        name = _call_name(expr_val)
        if name == "strategy":
            kind: DeclarationKind = "strategy"
        elif name in ("indicator", "study"):
            kind = "indicator"
        elif name == "library":
            kind = "library"
        else:
            continue
        args = _extract_args(expr_val)
        # title은 positional 0 (첫 positional) 또는 name='title'
        title_raw = _get_arg(args, 0, name="title")
        title = _strip_string_quotes(title_raw)
        return DeclarationInfo(kind=kind, title=title, args=args)
    return DeclarationInfo(kind="unknown", title=None, args=[])


def _extract_inputs(tree: Any) -> list[InputDecl]:
    """전체 트리에서 `input*` 호출을 찾아 선언 추출.

    패턴:
    - `x = input(defval, title, ...)` — input 통합 함수
    - `x = input.int(defval, title, minval=, maxval=)` — 타입별
    - `x = input.float(...)`, `input.bool`, `input.string`, `input.price`, `input.source` 등
    """
    inputs: list[InputDecl] = []
    for node in _walk(tree):
        if not isinstance(node, pyne_ast.Assign):
            continue
        # 대상 변수
        targets_attr = getattr(node, "targets", None)
        target_list = targets_attr if targets_attr else [getattr(node, "target", None)]
        value = getattr(node, "value", None)
        if value is None or not isinstance(value, pyne_ast.Call):
            continue
        name = _call_name(value)
        if name is None:
            continue
        if not (name == "input" or name.startswith("input.")):
            continue

        # var_name: 첫 Name 타겟 (None·non-Name 엔트리는 스킵)
        var_name = next(
            (t.id for t in target_list if isinstance(t, pyne_ast.Name)),
            "",
        )
        if not var_name:
            continue

        input_type = name.split(".", 1)[1] if "." in name else "generic"
        args = _extract_args(value)
        defval = _get_arg(args, 0, name="defval")
        title = _strip_string_quotes(_get_arg(args, 1, name="title"))

        inputs.append(InputDecl(
            input_type=input_type,
            var_name=var_name,
            defval=defval,
            title=title,
            args=args,
        ))
    return inputs


def _extract_var_declarations(tree: Any) -> list[VarDecl]:
    """전체 트리에서 `var`/`varip`로 선언된 Assign 추출 (Pine 키워드, 함수 내부 포함)."""
    decls: list[VarDecl] = []
    for node in _walk(tree):
        if not isinstance(node, pyne_ast.Assign):
            continue
        kind = _detect_var_kind(node)
        if kind is None:
            continue
        # 타겟 변수명
        targets_attr = getattr(node, "targets", None)
        target_list = targets_attr if targets_attr else [getattr(node, "target", None)]
        var_name = ""
        for t in target_list:
            if isinstance(t, pyne_ast.Name):
                var_name = t.id
                break
        if not var_name:
            continue
        initial = _stringify(node.value) if getattr(node, "value", None) is not None else ""
        decls.append(VarDecl(var_name=var_name, initial_expr=initial, kind=kind))
    return decls


_STRATEGY_EXEC_CALLS = {
    "strategy.entry",
    "strategy.exit",
    "strategy.close",
    "strategy.close_all",
    "strategy.cancel",
    "strategy.cancel_all",
    "strategy.order",
}


def _extract_strategy_calls(tree: Any) -> list[StrategyCall]:
    """전체 트리에서 strategy.* 실행 호출 추출."""
    calls: list[StrategyCall] = []
    for node in _walk(tree):
        if not isinstance(node, pyne_ast.Call):
            continue
        name = _call_name(node)
        if name in _STRATEGY_EXEC_CALLS:
            calls.append(StrategyCall(name=name, args=_extract_args(node)))
    return calls


def extract_content(source: str) -> ScriptContent:
    """Pine 소스의 구조화 내용을 ScriptContent로 추출."""
    tree = pyne_ast.parse(source)
    return ScriptContent(
        declaration=_extract_declaration(tree),
        inputs=_extract_inputs(tree),
        var_declarations=_extract_var_declarations(tree),
        strategy_calls=_extract_strategy_calls(tree),
    )
