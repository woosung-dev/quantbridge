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
    node = Literal(value=42, source_span=SPAN)
    assert node.value == 42
    assert node.source_span == SPAN
    assert node.annotations == {}


def test_literal_frozen() -> None:
    node = Literal(value=1.0, source_span=SPAN)
    with pytest.raises((AttributeError, TypeError)):
        node.value = 2.0  # type: ignore[misc]


# ── 2. Ident ─────────────────────────────────────────────────────────────────

def test_ident_basic() -> None:
    node = Ident(name="close", source_span=SPAN)
    assert node.name == "close"


# ── 3. BinOp ─────────────────────────────────────────────────────────────────

def test_binop_basic() -> None:
    left = Literal(value=1, source_span=SPAN)
    right = Literal(value=2, source_span=SPAN)
    node = BinOp(op="+", left=left, right=right, source_span=SPAN)
    assert node.op == "+"
    assert node.left is left
    assert node.right is right


# ── 4. Kwarg ─────────────────────────────────────────────────────────────────

def test_kwarg_basic() -> None:
    val = Literal(value=14, source_span=SPAN)
    node = Kwarg(key="length", value=val, source_span=SPAN)
    assert node.key == "length"
    assert node.value is val


# ── 5. FnCall ────────────────────────────────────────────────────────────────

def test_fncall_no_args() -> None:
    node = FnCall(name="bar", args=(), kwargs=(), source_span=SPAN)
    assert node.name == "bar"
    assert node.args == ()
    assert node.kwargs == ()


def test_fncall_with_args() -> None:
    arg = Literal(value=14, source_span=SPAN)
    kw = Kwarg(key="src", value=Ident(name="close", source_span=SPAN), source_span=SPAN)
    node = FnCall(name="ta.sma", args=(arg,), kwargs=(kw,), source_span=SPAN)
    assert len(node.args) == 1
    assert len(node.kwargs) == 1


# ── 6. VarDecl ───────────────────────────────────────────────────────────────

def test_vardecl_basic() -> None:
    val = Literal(value=0, source_span=SPAN)
    node = VarDecl(name="x", value=val, var_type=None, source_span=SPAN)
    assert node.name == "x"
    assert node.var_type is None


# ── 7. Assign ────────────────────────────────────────────────────────────────

def test_assign_basic() -> None:
    val = Literal(value=1, source_span=SPAN)
    node = Assign(name="x", value=val, source_span=SPAN)
    assert node.name == "x"
    assert node.value is val


# ── 8. IfExpr ────────────────────────────────────────────────────────────────

def test_ifexpr_basic() -> None:
    cond = Literal(value=True, source_span=SPAN)
    then = Literal(value=1, source_span=SPAN)
    else_ = Literal(value=0, source_span=SPAN)
    node = IfExpr(condition=cond, then_expr=then, else_expr=else_, source_span=SPAN)
    assert node.condition is cond
    assert node.then_expr is then
    assert node.else_expr is else_


# ── 9. IfStmt ────────────────────────────────────────────────────────────────

def test_ifstmt_no_else() -> None:
    cond = Literal(value=True, source_span=SPAN)
    body = (Assign(name="x", value=Literal(value=1, source_span=SPAN), source_span=SPAN),)
    node = IfStmt(condition=cond, then_body=body, else_body=(), source_span=SPAN)
    assert node.else_body == ()


# ── 10. ForLoop ──────────────────────────────────────────────────────────────

def test_forloop_basic() -> None:
    start = Literal(value=0, source_span=SPAN)
    end = Literal(value=10, source_span=SPAN)
    body = (Assign(name="i", value=Literal(value=0, source_span=SPAN), source_span=SPAN),)
    node = ForLoop(var="i", start=start, end=end, body=body, source_span=SPAN)
    assert node.var == "i"
    assert node.start is start
    assert node.end is end


# ── 11. HistoryRef ───────────────────────────────────────────────────────────

def test_historyref_basic() -> None:
    idx = Literal(value=1, source_span=SPAN)
    node = HistoryRef(name="close", index=idx, source_span=SPAN)
    assert node.name == "close"
    assert node.index is idx


# ── 12. TupleReturn ──────────────────────────────────────────────────────────

def test_tuplereturn_basic() -> None:
    a = Literal(value=1, source_span=SPAN)
    b = Literal(value=2, source_span=SPAN)
    node = TupleReturn(elements=(a, b), source_span=SPAN)
    assert len(node.elements) == 2


# ── 13. Program ──────────────────────────────────────────────────────────────

def test_program_basic() -> None:
    stmt = VarDecl(name="y", value=Literal(value=99, source_span=SPAN), var_type=None, source_span=SPAN)
    node = Program(version=5, body=(stmt,), source_span=SPAN)
    assert node.version == 5
    assert len(node.body) == 1


# ── 14. annotations 독립성 ───────────────────────────────────────────────────

def test_annotations_independent() -> None:
    """annotations 딕셔너리는 인스턴스마다 독립적이어야 한다."""
    a = Literal(value=1, source_span=SPAN)
    b = Literal(value=2, source_span=SPAN)
    a.annotations["tag"] = "entry"
    assert "tag" not in b.annotations
