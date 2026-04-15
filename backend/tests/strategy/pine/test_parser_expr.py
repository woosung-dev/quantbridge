"""Parser 표현식 테스트 — T11 TDD."""
from __future__ import annotations

from src.strategy.pine.ast_nodes import (
    BinOp,
    FnCall,
    HistoryRef,
    Ident,
    IfExpr,
    Kwarg,
    Literal,
)
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse_expression

# ---------------------------------------------------------------------------
# 리터럴
# ---------------------------------------------------------------------------


def test_integer_literal() -> None:
    tokens = tokenize("42")
    node = parse_expression(tokens)
    assert isinstance(node, Literal)
    assert node.value == 42


def test_float_literal() -> None:
    tokens = tokenize("3.14")
    node = parse_expression(tokens)
    assert isinstance(node, Literal)
    assert abs(node.value - 3.14) < 1e-9  # type: ignore[operator]


def test_string_literal() -> None:
    tokens = tokenize('"hello"')
    node = parse_expression(tokens)
    assert isinstance(node, Literal)
    assert node.value == "hello"


def test_true_literal() -> None:
    tokens = tokenize("true")
    node = parse_expression(tokens)
    assert isinstance(node, Literal)
    assert node.value is True


def test_false_literal() -> None:
    tokens = tokenize("false")
    node = parse_expression(tokens)
    assert isinstance(node, Literal)
    assert node.value is False


# ---------------------------------------------------------------------------
# 식별자
# ---------------------------------------------------------------------------


def test_simple_ident() -> None:
    tokens = tokenize("close")
    node = parse_expression(tokens)
    assert isinstance(node, Ident)
    assert node.name == "close"


def test_dotted_ident() -> None:
    tokens = tokenize("ta.sma")
    node = parse_expression(tokens)
    assert isinstance(node, Ident)
    assert node.name == "ta.sma"


# ---------------------------------------------------------------------------
# 이항 연산자
# ---------------------------------------------------------------------------


def test_addition() -> None:
    tokens = tokenize("1 + 2")
    node = parse_expression(tokens)
    assert isinstance(node, BinOp)
    assert node.op == "+"
    assert isinstance(node.left, Literal) and node.left.value == 1
    assert isinstance(node.right, Literal) and node.right.value == 2


def test_operator_precedence() -> None:
    # 1 + 2 * 3  →  1 + (2 * 3)
    tokens = tokenize("1 + 2 * 3")
    node = parse_expression(tokens)
    assert isinstance(node, BinOp)
    assert node.op == "+"
    assert isinstance(node.right, BinOp)
    assert node.right.op == "*"


def test_comparison() -> None:
    tokens = tokenize("close > open")
    node = parse_expression(tokens)
    assert isinstance(node, BinOp)
    assert node.op == ">"


def test_equality() -> None:
    tokens = tokenize("a == b")
    node = parse_expression(tokens)
    assert isinstance(node, BinOp)
    assert node.op == "=="


def test_and_or() -> None:
    # a or b and c  →  a or (b and c)  — and binds tighter than or
    tokens = tokenize("a or b and c")
    node = parse_expression(tokens)
    assert isinstance(node, BinOp)
    assert node.op == "or"
    assert isinstance(node.right, BinOp)
    assert node.right.op == "and"


# ---------------------------------------------------------------------------
# 단항 연산자
# ---------------------------------------------------------------------------


def test_unary_minus() -> None:
    # 단항 마이너스 → BinOp(op="-", left=Literal(0), right=operand)
    tokens = tokenize("-close")
    node = parse_expression(tokens)
    assert isinstance(node, BinOp)
    assert node.op == "-"
    assert isinstance(node.left, Literal) and node.left.value == 0
    assert isinstance(node.right, Ident) and node.right.name == "close"


def test_not_expr() -> None:
    # not x → BinOp(op="not", left=Literal(True), right=x)
    tokens = tokenize("not x")
    node = parse_expression(tokens)
    assert isinstance(node, BinOp)
    assert node.op == "not"
    assert isinstance(node.left, Literal) and node.left.value is True
    assert isinstance(node.right, Ident) and node.right.name == "x"


# ---------------------------------------------------------------------------
# 히스토리 참조
# ---------------------------------------------------------------------------


def test_history_ref() -> None:
    tokens = tokenize("close[1]")
    node = parse_expression(tokens)
    assert isinstance(node, HistoryRef)
    assert isinstance(node.target, Ident) and node.target.name == "close"
    assert isinstance(node.offset, Literal) and node.offset.value == 1


# ---------------------------------------------------------------------------
# 함수 호출
# ---------------------------------------------------------------------------


def test_fn_call_no_args() -> None:
    tokens = tokenize("bar()")
    node = parse_expression(tokens)
    assert isinstance(node, FnCall)
    assert node.name == "bar"
    assert node.args == ()
    assert node.kwargs == ()


def test_fn_call_positional_args() -> None:
    tokens = tokenize("ta.sma(close, 14)")
    node = parse_expression(tokens)
    assert isinstance(node, FnCall)
    assert node.name == "ta.sma"
    assert len(node.args) == 2
    assert isinstance(node.args[0], Ident) and node.args[0].name == "close"
    assert isinstance(node.args[1], Literal) and node.args[1].value == 14


def test_fn_call_kwargs() -> None:
    tokens = tokenize("ta.rsi(source=close, length=14)")
    node = parse_expression(tokens)
    assert isinstance(node, FnCall)
    assert node.name == "ta.rsi"
    assert node.args == ()
    assert len(node.kwargs) == 2
    assert isinstance(node.kwargs[0], Kwarg)
    assert node.kwargs[0].key == "source"
    assert isinstance(node.kwargs[0].value, Ident)


# ---------------------------------------------------------------------------
# 3항 조건 표현식 (ternary)
# ---------------------------------------------------------------------------


def test_ternary_expr() -> None:
    tokens = tokenize("a > b ? 1 : 2")
    node = parse_expression(tokens)
    assert isinstance(node, IfExpr)
    assert isinstance(node.cond, BinOp) and node.cond.op == ">"
    assert isinstance(node.then, Literal) and node.then.value == 1
    assert isinstance(node.else_, Literal) and node.else_.value == 2
