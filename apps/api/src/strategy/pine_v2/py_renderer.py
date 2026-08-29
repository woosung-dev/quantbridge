"""[ADR-042] Pine AST → **읽기 전용** Python 렌더러.

★★**이 모듈의 산출물은 어디서도 실행되지 않는다.** `exec`/`eval`/`compile`/`import` 경로를
만들지 않으며, 그 **부재를 테스트가 집행한다**(`tests/strategy/pine_v2/test_py_renderer_not_executed.py`).
용도는 하나 — 사용자가 「이 전략이 무엇을 하는가」를 읽는 것이다.

★**의미 보존을 보증하지 않는다.** 읽기용 근사이고 진실은 언제나 원본 Pine 이다. 그래서
`source_map` 이 모든 출력 줄을 원본 줄에 묶고, 화면이 둘을 나란히 둔다.

★**못 렌더하는 노드를 조용히 빼지 않는다** — `pynescript.ast.unparse` 로 **원본 Pine 을 되살려
주석으로 보존**한다. 빠지면 사용자가 없는 로직을 없다고 믿는다([ADR-042] §트레이드오프).

출처: [ADR-004](../../../../docs/adr/004-pine-parser-approach-selection.md) 이 접근 2(exec)를
「영구 불채택」하면서 그 이점 하나(「생성 Python 을 사람이 읽을 수 있어 투명성」)만 살려 둔 대안이다.
2026-04-15 에 적혔고 2026-08-27 까지 구현된 적이 없다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from pynescript import ast as pyne_ast

from src.strategy.pine_v2.parser_adapter import parse_to_ast

_INDENT = "    "

# Pine 연산자 → Python. 없는 것은 `_UNKNOWN_OP` 로 떨어져 원문이 보존된다.
_BINOP: dict[str, str] = {
    "Add": "+",
    "Sub": "-",
    "Mult": "*",
    "Div": "/",
    "Mod": "%",
}
_CMPOP: dict[str, str] = {
    "Eq": "==",
    "NotEq": "!=",
    "Lt": "<",
    "LtE": "<=",
    "Gt": ">",
    "GtE": ">=",
}
_BOOLOP: dict[str, str] = {"And": "and", "Or": "or"}
_UNARYOP: dict[str, str] = {"USub": "-", "UAdd": "+", "Not": "not "}
_UNKNOWN_OP = "?"

_HEADER = """\
# ─────────────────────────────────────────────────────────────────────────────
# 이 전략이 무엇을 하는가 — 읽기 전용 Python 뷰
#
# ★이 코드는 실행되지 않습니다. 원본 Pine Script 를 읽기 쉽게 옮긴 것이고,
#   실제로 도는 것은 Pine 인터프리터(pine_v2)입니다. 진실은 언제나 원본 Pine 입니다.
#
# 읽는 법 두 가지.
#   · `x[1]` 은 리스트 색인이 아니라 **한 봉 전의 값**입니다(`x[0]` = 현재 봉).
#   · 모든 줄은 **봉마다 한 번씩** 위에서 아래로 다시 실행됩니다.
# ─────────────────────────────────────────────────────────────────────────────
"""


@dataclass
class PythonView:
    """렌더 결과.

    `source_map` 은 `(python 줄번호, pine 줄번호)` 쌍이고 **1-based** 다. Pine 줄을 알 수 없는
    출력 줄(헤더·빈 줄)은 아예 등장하지 않는다 — 없는 대응을 지어내지 않는다.
    """

    code: str
    source_map: list[tuple[int, int]] = field(default_factory=list)
    # 원본을 주석으로 보존한 노드 수. 0 이 아니면 화면이 「일부는 원문으로 남겼습니다」를 말해야 한다.
    unrendered: int = 0


class _Renderer:
    def __init__(self) -> None:
        self._lines: list[str] = []
        self._map: list[tuple[int, int]] = []
        self.unrendered = 0

    # ── 출력 ─────────────────────────────────────────────────────────────
    def _emit(self, text: str, depth: int, node: Any | None = None) -> None:
        self._lines.append(_INDENT * depth + text if text else "")
        line_no = getattr(node, "lineno", None) if node is not None else None
        if isinstance(line_no, int):
            self._map.append((len(self._lines), line_no))

    def _preserve(self, node: Any, depth: int, why: str) -> None:
        """못 옮기는 노드는 **원본 Pine 을 주석으로 되살린다**. 조용히 빼지 않는다."""
        self.unrendered += 1
        try:
            original = pyne_ast.unparse(node).rstrip("\n")
        except Exception:
            original = "<원본을 되살리지 못했습니다>"
        for i, raw in enumerate(original.splitlines() or [""]):
            prefix = f"# [{why}] " if i == 0 else "#   "
            self._emit(prefix + raw, depth, node if i == 0 else None)

    # ── 문(statement) ────────────────────────────────────────────────────
    def stmts(self, body: Any, depth: int) -> None:
        items = body if isinstance(body, list) else [body]
        emitted = False
        for node in items:
            if not isinstance(node, pyne_ast.AST):
                continue
            self.stmt(node, depth)
            emitted = True
        if not emitted:
            self._emit("pass", depth)

    def stmt(self, node: Any, depth: int) -> None:
        name = type(node).__name__
        handler = getattr(self, f"_stmt_{name}", None)
        if handler is None:
            self._preserve(node, depth, "원문 보존")
            return
        handler(node, depth)

    # ★Pine 은 `if`/`for`/`switch` 를 **식으로도** 쓸 수 있어 pynescript 가 문 레벨의 그것들도
    #   `Expr` 로 감싼다(실측 2026-08-27). 그대로 `expr()` 로 보내면 블록이 통째로 「원문 보존」
    #   폴백에 떨어져 **전략의 진입 조건이 주석이 된다.** 감싼 것을 벗겨 문으로 되돌린다.
    _STATEMENT_IN_EXPR = ("If", "ForTo", "ForIn", "Switch", "FunctionDef", "Break", "Continue")

    def _stmt_Expr(self, node: Any, depth: int) -> None:
        inner = getattr(node, "value", None)
        if inner is not None and type(inner).__name__ in self._STATEMENT_IN_EXPR:
            self.stmt(inner, depth)
            return
        self._emit(self.expr(node.value), depth, node)

    def _stmt_Assign(self, node: Any, depth: int) -> None:
        target = self.expr(node.target)
        value = self.expr(node.value)
        # ★`mode` 는 문자열이 아니라 **노드**다(`Var()` / `VarIp()` / None). 실측 2026-08-27 —
        #   문자열로 비교하면 조용히 항상 거짓이라 `var` 표시가 통째로 사라진다.
        mode = type(getattr(node, "mode", None)).__name__
        note = ""
        if mode == "Var":
            note = "  # var: 최초 1회만 초기화되고 봉을 넘어 값을 유지합니다"
        elif mode == "VarIp":
            note = "  # varip: 봉 안에서도 갱신되며 값을 유지합니다"
        self._emit(f"{target} = {value}{note}", depth, node)

    def _stmt_ReAssign(self, node: Any, depth: int) -> None:
        # Pine `:=` 는 이미 선언된 변수의 재대입이다. Python 에는 구분이 없어 주석으로 남긴다.
        self._emit(f"{self.expr(node.target)} = {self.expr(node.value)}  # := 재대입", depth, node)

    def _stmt_If(self, node: Any, depth: int) -> None:
        self._emit(f"if {self.expr(node.test)}:", depth, node)
        self.stmts(node.body, depth + 1)
        orelse = getattr(node, "orelse", None)
        if not orelse:
            return
        items = orelse if isinstance(orelse, list) else [orelse]
        # `else if` 는 orelse 가 If 하나인 형태다 — elif 로 접는다.
        if len(items) == 1 and isinstance(items[0], pyne_ast.If):
            inner = items[0]
            self._emit(f"elif {self.expr(inner.test)}:", depth, inner)
            self.stmts(inner.body, depth + 1)
            nested = getattr(inner, "orelse", None)
            if nested:
                self._emit("else:", depth)
                self.stmts(nested, depth + 1)
            return
        self._emit("else:", depth)
        self.stmts(items, depth + 1)

    def _stmt_ForTo(self, node: Any, depth: int) -> None:
        target = self.expr(node.target)
        start = self.expr(node.start)
        end = self.expr(node.end)
        step = getattr(node, "step", None)
        # ★Pine `for i = a to b` 는 **b 를 포함**한다. range 는 배제하므로 +1 이 필요하다.
        args = f"{start}, {end} + 1" + (f", {self.expr(step)}" if step is not None else "")
        self._emit(
            f"for {target} in range({args}):  # Pine 의 to 는 끝값을 포함합니다", depth, node
        )
        self.stmts(node.body, depth + 1)

    def _stmt_FunctionDef(self, node: Any, depth: int) -> None:
        params = ", ".join(self._param(p) for p in (getattr(node, "args", None) or []))
        self._emit(f"def {node.name}({params}):", depth, node)
        body = node.body if isinstance(node.body, list) else [node.body]
        # Pine 함수는 마지막 식의 값을 돌려준다 — 그 사실을 return 으로 드러낸다.
        for item in body[:-1]:
            self.stmt(item, depth + 1)
        last = body[-1] if body else None
        last_inner = getattr(last, "value", None) if isinstance(last, pyne_ast.Expr) else None
        if last_inner is not None and type(last_inner).__name__ in self._STATEMENT_IN_EXPR:
            # 마지막이 `if`/`for` 블록이면 반환식이 아니다 — 감싸면 블록이 통째로 원문 폴백에 떨어진다.
            self.stmt(last_inner, depth + 1)
        elif isinstance(last, pyne_ast.Expr):
            self._emit(
                f"return {self.expr(last.value)}  # Pine 은 마지막 식이 반환값입니다",
                depth + 1,
                last,
            )
        elif last is not None:
            self.stmt(last, depth + 1)
        else:
            self._emit("pass", depth + 1)

    def _stmt_Switch(self, node: Any, depth: int) -> None:
        subject = getattr(node, "subject", None)
        cases = getattr(node, "cases", None) or []
        self._emit(
            "# switch — Pine 의 분기식입니다. 아래 if/elif 는 같은 뜻으로 옮긴 것입니다.",
            depth,
            node,
        )
        first = True
        for case in cases:
            pattern = getattr(case, "pattern", None)
            if pattern is None:
                self._emit("else:", depth)
            else:
                cond = (
                    f"{self.expr(subject)} == {self.expr(pattern)}"
                    if subject is not None
                    else self.expr(pattern)
                )
                self._emit(f"{'if' if first else 'elif'} {cond}:", depth, case)
                first = False
            self.stmts(getattr(case, "body", None), depth + 1)

    def _stmt_Break(self, node: Any, depth: int) -> None:
        self._emit("break", depth, node)

    def _stmt_Continue(self, node: Any, depth: int) -> None:
        self._emit("continue", depth, node)

    def _param(self, p: Any) -> str:
        name = getattr(p, "name", None) or "_"
        default = getattr(p, "default", None)
        return f"{name}={self.expr(default)}" if default is not None else str(name)

    # ── 식(expression) ───────────────────────────────────────────────────
    def expr(self, node: Any) -> str:
        if node is None:
            return "None"
        name = type(node).__name__
        handler = getattr(self, f"_expr_{name}", None)
        if handler is None:
            self.unrendered += 1
            try:
                return f"({pyne_ast.unparse(node).strip()})  # 원문"
            except Exception:
                return "<원문 미상>"
        # `_expr_*` 메서드는 모두 str을 반환한다. 동적 조회만 그 정보를 mypy에서 감춘다.
        return cast(Callable[[Any], str], handler)(node)

    def _expr_Name(self, node: Any) -> str:
        return str(node.id)

    def _expr_Constant(self, node: Any) -> str:
        value = node.value
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, str):
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"'
        if value is None:
            return "na"  # Pine 의 na 는 Python None 이 아니므로 이름을 보존한다
        return str(value)

    def _expr_Attribute(self, node: Any) -> str:
        return f"{self.expr(node.value)}.{node.attr}"

    def _expr_Subscript(self, node: Any) -> str:
        return f"{self.expr(node.value)}[{self.expr(node.slice)}]"

    def _expr_Tuple(self, node: Any) -> str:
        inner = ", ".join(self.expr(e) for e in (node.elts or []))
        return f"({inner})"

    def _expr_Call(self, node: Any) -> str:
        parts = []
        for arg in getattr(node, "args", None) or []:
            value = self.expr(getattr(arg, "value", arg))
            label = getattr(arg, "name", None)
            parts.append(f"{label}={value}" if label else value)
        return f"{self.expr(node.func)}({', '.join(parts)})"

    def _expr_BinOp(self, node: Any) -> str:
        op = _BINOP.get(type(node.op).__name__, _UNKNOWN_OP)
        return f"({self.expr(node.left)} {op} {self.expr(node.right)})"

    def _expr_Compare(self, node: Any) -> str:
        out = self.expr(node.left)
        ops = node.ops if isinstance(node.ops, list) else [node.ops]
        comparators = node.comparators if isinstance(node.comparators, list) else [node.comparators]
        for op, right in zip(ops, comparators, strict=False):
            out += f" {_CMPOP.get(type(op).__name__, _UNKNOWN_OP)} {self.expr(right)}"
        return f"({out})"

    def _expr_BoolOp(self, node: Any) -> str:
        op = _BOOLOP.get(type(node.op).__name__, _UNKNOWN_OP)
        inner = f" {op} ".join(self.expr(v) for v in (node.values or []))
        return f"({inner})"

    def _expr_UnaryOp(self, node: Any) -> str:
        op = _UNARYOP.get(type(node.op).__name__, _UNKNOWN_OP)
        return f"({op}{self.expr(node.operand)})"

    def _expr_Conditional(self, node: Any) -> str:
        return f"({self.expr(node.body)} if {self.expr(node.test)} else {self.expr(node.orelse)})"

    # ── 진입점 ───────────────────────────────────────────────────────────
    def run(self, tree: Any) -> PythonView:
        for line in _HEADER.splitlines():
            self._emit(line, 0)
        self._emit("", 0)
        body = getattr(tree, "body", None)
        self.stmts(body if body is not None else tree, 0)
        return PythonView(
            code="\n".join(self._lines) + "\n",
            source_map=self._map,
            unrendered=self.unrendered,
        )


def render_python(source: str) -> PythonView:
    """Pine 소스를 읽기 전용 Python 뷰로 옮긴다. **실행하지 않는다.**

    파싱에 실패하면 호출자가 처리한다 — `parse_to_ast` 의 예외를 삼키지 않는다.
    ★파싱 비용은 `parse_to_ast` 의 캐시에 얹힌다(같은 소스면 L1/L2 hit).
    """
    return _Renderer().run(parse_to_ast(source))
