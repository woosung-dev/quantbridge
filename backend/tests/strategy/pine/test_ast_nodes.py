"""AST 노드 dataclass 단위 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.ast_nodes import (
    Assign,
    BinOp,
    FnCall,
    ForLoop,
    HistoryRef,
    Ident,
    IfExpr,
    IfStmt,
    Kwarg,
    Literal,
    Program,
    TupleReturn,
    VarDecl,
)
from src.strategy.pine.types import SourceSpan

SPAN = SourceSpan(line=1, column=0, length=1)


# ── 1. Literal ──────────────────────────────────────────────────────────────

def test_literal_int() -> None:
    node = Literal(source_span=SPAN, value=42)
    assert node.value == 42
    assert node.source_span == SPAN
    assert node.annotations == {}


def test_literal_frozen() -> None:
    node = Literal(source_span=SPAN, value=1.0)
    with pytest.raises((AttributeError, TypeError)):
        node.value = 2.0  # type: ignore[misc]


# ── 2. Ident ─────────────────────────────────────────────────────────────────

def test_ident_basic() -> None:
    node = Ident(source_span=SPAN, name="close")
    assert node.name == "close"


# ── 3. BinOp ─────────────────────────────────────────────────────────────────

def test_binop_basic() -> None:
    left = Literal(source_span=SPAN, value=1)
    right = Literal(source_span=SPAN, value=2)
    node = BinOp(source_span=SPAN, op="+", left=left, right=right)
    assert node.op == "+"
    assert node.left is left
    assert node.right is right


# ── 4. Kwarg ─────────────────────────────────────────────────────────────────

def test_kwarg_basic() -> None:
    val = Literal(source_span=SPAN, value=14)
    node = Kwarg(source_span=SPAN, key="length", value=val)
    assert node.key == "length"
    assert node.value is val


# ── 5. FnCall ────────────────────────────────────────────────────────────────

def test_fncall_no_args() -> None:
    node = FnCall(source_span=SPAN, name="bar", args=(), kwargs=())
    assert node.name == "bar"
    assert node.args == ()
    assert node.kwargs == ()


def test_fncall_with_args() -> None:
    arg = Literal(source_span=SPAN, value=14)
    kw = Kwarg(source_span=SPAN, key="src", value=Ident(source_span=SPAN, name="close"))
    node = FnCall(source_span=SPAN, name="ta.sma", args=(arg,), kwargs=(kw,))
    assert len(node.args) == 1
    assert len(node.kwargs) == 1


# ── 6. VarDecl ───────────────────────────────────────────────────────────────

def test_vardecl_basic() -> None:
    val = Literal(source_span=SPAN, value=0)
    node = VarDecl(source_span=SPAN, name="x", is_var=False, type_hint=None, expr=val)
    assert node.name == "x"
    assert node.is_var is False
    assert node.type_hint is None
    assert node.expr is val


# ── 7. Assign ────────────────────────────────────────────────────────────────

def test_assign_basic() -> None:
    target = Ident(source_span=SPAN, name="x")
    val = Literal(source_span=SPAN, value=1)
    node = Assign(source_span=SPAN, target=target, op=":=", value=val)
    assert node.target is target
    assert node.op == ":="
    assert node.value is val


# ── 8. IfExpr ────────────────────────────────────────────────────────────────

def test_ifexpr_basic() -> None:
    cond = Literal(source_span=SPAN, value=True)
    then = Literal(source_span=SPAN, value=1)
    else_ = Literal(source_span=SPAN, value=0)
    node = IfExpr(source_span=SPAN, cond=cond, then=then, else_=else_)
    assert node.cond is cond
    assert node.then is then
    assert node.else_ is else_


# ── 9. IfStmt ────────────────────────────────────────────────────────────────

def test_ifstmt_no_else() -> None:
    cond = Literal(source_span=SPAN, value=True)
    target = Ident(source_span=SPAN, name="x")
    body = (Assign(source_span=SPAN, target=target, op=":=", value=Literal(source_span=SPAN, value=1)),)
    node = IfStmt(source_span=SPAN, cond=cond, body=body, else_body=())
    assert node.else_body == ()


# ── 10. ForLoop ──────────────────────────────────────────────────────────────

def test_forloop_basic() -> None:
    start = Literal(source_span=SPAN, value=0)
    end = Literal(source_span=SPAN, value=10)
    target = Ident(source_span=SPAN, name="i")
    body = (Assign(source_span=SPAN, target=target, op=":=", value=Literal(source_span=SPAN, value=0)),)
    node = ForLoop(source_span=SPAN, var_name="i", start=start, end=end, body=body)
    assert node.var_name == "i"
    assert node.start is start
    assert node.end is end
    assert node.step is None


# ── 11. HistoryRef ───────────────────────────────────────────────────────────

def test_historyref_basic() -> None:
    target = Ident(source_span=SPAN, name="close")
    offset = Literal(source_span=SPAN, value=1)
    node = HistoryRef(source_span=SPAN, target=target, offset=offset)
    assert node.target is target
    assert node.offset is offset


# ── 12. TupleReturn ──────────────────────────────────────────────────────────

def test_tuplereturn_basic() -> None:
    a = Literal(source_span=SPAN, value=1)
    b = Literal(source_span=SPAN, value=2)
    node = TupleReturn(source_span=SPAN, values=(a, b))
    assert len(node.values) == 2


# ── 13. Program ──────────────────────────────────────────────────────────────

def test_program_basic() -> None:
    stmt = VarDecl(
        source_span=SPAN,
        name="y",
        is_var=False,
        type_hint=None,
        expr=Literal(source_span=SPAN, value=99),
    )
    node = Program(source_span=SPAN, version=5, statements=(stmt,))
    assert node.version == 5
    assert len(node.statements) == 1


# ── 14. annotations 독립성 ───────────────────────────────────────────────────

def test_annotations_independent() -> None:
    """annotations 딕셔너리는 인스턴스마다 독립적이어야 한다."""
    a = Literal(source_span=SPAN, value=1)
    b = Literal(source_span=SPAN, value=2)
    a.annotations["tag"] = "entry"
    assert "tag" not in b.annotations
