"""Interpreter 커버리지 보강 테스트.

누락된 브랜치:
- BinOp: -, *, /, %, comparisons (<=, >=, ==, !=), logical and/or (scalar), not (scalar)
- BinOp: unknown operator → PineRuntimeError
- HistoryRef: non-series target → PineRuntimeError
- evaluate_expression: unknown node type → PineRuntimeError
- IfStmt: else_body 실행
- ForLoop 실행 → PineUnsupportedError
- _execute_fncall_stmt: strategy.exit 인자 없음 (no-op), plot/indicator/alert 등 no-op
- _gate_as_bool_series: bool gate(True/False), scalar bool gate
- Environment.lookup: undefined identifier → PineRuntimeError
- IfExpr: scalar 조건 분기 (then vs else)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine.errors import PineRuntimeError, PineUnsupportedError
from src.strategy.pine.interpreter import (
    Environment,
    _combine_gate,
    _gate_as_bool_series,
    evaluate_expression,
    execute_program,
)
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse, parse_expression

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _env(n: int = 5) -> Environment:
    close = pd.Series([10.0, 11.0, 12.0, 11.5, 10.8])
    high = close + 0.5
    low = close - 0.5
    return Environment.with_ohlcv(
        open_=close - 0.1,
        high=high,
        low=low,
        close=close,
        volume=pd.Series([100.0] * n),
    )


def _eval(src: str, env: Environment | None = None):
    env = env or _env()
    return evaluate_expression(parse_expression(tokenize(src)), env)


def _ohlcv(n: int = 10) -> dict[str, pd.Series]:
    close = pd.Series(np.linspace(10.0, 20.0, n))
    return {
        "open_": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": pd.Series([100.0] * n),
    }


# ---------------------------------------------------------------------------
# BinOp: 나머지 산술/비교 연산자
# ---------------------------------------------------------------------------


def test_binop_subtraction():
    assert _eval("5 - 3") == 2


def test_binop_multiplication():
    assert _eval("4 * 3") == 12


def test_binop_division():
    assert _eval("10 / 4") == 2.5


def test_binop_modulo():
    assert _eval("10 % 3") == 1


def test_binop_lte_series():
    result = _eval("close <= 11")
    expected = pd.Series([True, True, False, False, True])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_binop_gte_series():
    result = _eval("close >= 11")
    expected = pd.Series([False, True, True, True, False])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_binop_eq_scalar():
    assert _eval("3 == 3") is True
    assert _eval("3 == 4") is False


def test_binop_ne_scalar():
    assert _eval("3 != 4") is True
    assert _eval("3 != 3") is False


def test_binop_logical_and_scalar():
    assert _eval("true and true") is True
    assert _eval("true and false") is False


def test_binop_logical_or_scalar():
    assert _eval("false or true") is True
    assert _eval("false or false") is False


def test_binop_not_scalar():
    # not은 (True, operand)로 정규화됨 — 파서 레벨에서 처리
    assert _eval("not true") is False
    assert _eval("not false") is True


def test_binop_unknown_operator_raises():
    """PineRuntimeError: unknown operator는 직접 BinOp 노드 생성으로 테스트."""
    from src.strategy.pine.ast_nodes import BinOp, Literal
    from src.strategy.pine.types import SourceSpan

    span = SourceSpan(line=1, column=1, length=1)
    node = BinOp(
        left=Literal(value=1, source_span=span),
        op="^^",  # 존재하지 않는 연산자
        right=Literal(value=2, source_span=span),
        source_span=span,
    )
    env = _env()
    with pytest.raises(PineRuntimeError, match="unknown operator"):
        evaluate_expression(node, env)


# ---------------------------------------------------------------------------
# HistoryRef: non-series 에러
# ---------------------------------------------------------------------------


def test_history_ref_on_non_series_raises():
    """history reference on scalar → PineRuntimeError."""
    src = "42[1]"
    with pytest.raises(PineRuntimeError, match="history reference on non-series"):
        _eval(src)


# ---------------------------------------------------------------------------
# evaluate_expression: unknown node type
# ---------------------------------------------------------------------------


def test_evaluate_unknown_node_type_raises():
    """Program 노드는 evaluate_expression이 처리할 수 없어 PineRuntimeError 발생."""
    from src.strategy.pine.ast_nodes import Program
    from src.strategy.pine.types import SourceSpan

    # Program 노드는 모든 isinstance 체크를 통과하지 못하므로 "cannot evaluate" 에러
    span = SourceSpan(line=1, column=1, length=0)
    program_as_expr = Program(statements=(), source_span=span, version=5)
    with pytest.raises(PineRuntimeError, match="cannot evaluate node type"):
        evaluate_expression(program_as_expr, _env())


# ---------------------------------------------------------------------------
# Environment.lookup: undefined identifier
# ---------------------------------------------------------------------------


def test_lookup_undefined_raises():
    env = _env()
    with pytest.raises(PineRuntimeError, match="undefined identifier"):
        env.lookup("no_such_var")


# ---------------------------------------------------------------------------
# IfExpr: scalar 조건
# ---------------------------------------------------------------------------


def test_ifexpr_scalar_true_branch():
    # scalar 조건 true → then 반환
    assert _eval("true ? 1 : 2") == 1


def test_ifexpr_scalar_false_branch():
    assert _eval("false ? 1 : 2") == 2


# ---------------------------------------------------------------------------
# IfStmt: else_body
# ---------------------------------------------------------------------------


def test_if_stmt_else_body_executes():
    src = """//@version=5
if close > 50
    strategy.entry("Long", strategy.long)
else
    strategy.close("Long")
"""
    # close=[10..20] — close > 50은 항상 False → else_body (strategy.close) 실행
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    assert result.exits.all()
    assert not result.entries.any()


# ---------------------------------------------------------------------------
# ForLoop: execute_program raises PineUnsupportedError
# ---------------------------------------------------------------------------


def test_for_loop_execution_raises_unsupported():
    src = """for i = 0 to 5
    x = i
"""
    with pytest.raises(PineUnsupportedError, match="for loop"):
        execute_program(parse(tokenize(src)), **_ohlcv())


# ---------------------------------------------------------------------------
# _execute_fncall_stmt: strategy.exit 인자 없음 (no-op)
# ---------------------------------------------------------------------------


def test_strategy_exit_no_bracket_raises_unsupported():
    # stop/limit 없는 strategy.exit은 Unsupported
    src = """//@version=5
strategy("X")
strategy.exit("tp", "Long")
"""
    with pytest.raises(PineUnsupportedError) as ei:
        execute_program(parse(tokenize(src)), **_ohlcv())
    assert "strategy.exit" in ei.value.feature


# ---------------------------------------------------------------------------
# _execute_fncall_stmt: plot / indicator / alert no-op
# ---------------------------------------------------------------------------


def test_plot_and_indicator_are_noops():
    src = """//@version=5
indicator("MyIndicator")
plot(close)
plotshape(close > 15)
bgcolor(close > 15 ? close : close)
barcolor(close > 15 ? close : close)
alert("test")
alertcondition(close > 15)
fill(close, close)
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    assert not result.entries.any()
    assert not result.exits.any()


# ---------------------------------------------------------------------------
# _gate_as_bool_series: 다양한 gate 타입
# ---------------------------------------------------------------------------


def test_gate_as_bool_series_none():
    idx = pd.RangeIndex(3)
    s = _gate_as_bool_series(None, idx)
    assert s.all()


def test_gate_as_bool_series_true():
    idx = pd.RangeIndex(3)
    s = _gate_as_bool_series(True, idx)
    assert s.all()


def test_gate_as_bool_series_false():
    idx = pd.RangeIndex(3)
    s = _gate_as_bool_series(False, idx)
    assert not s.any()


def test_gate_as_bool_series_series():
    idx = pd.RangeIndex(3)
    gate = pd.Series([True, False, True], index=idx)
    s = _gate_as_bool_series(gate, idx)
    pd.testing.assert_series_equal(s, pd.Series([True, False, True], index=idx))


def test_gate_as_bool_series_scalar_int():
    idx = pd.RangeIndex(3)
    s = _gate_as_bool_series(1, idx)
    assert s.all()


# ---------------------------------------------------------------------------
# _combine_gate 테스트
# ---------------------------------------------------------------------------


def test_combine_gate_none_returns_cond():
    cond = pd.Series([True, False, True])
    result = _combine_gate(None, cond)
    pd.testing.assert_series_equal(result, cond)


def test_combine_gate_scalars():
    assert _combine_gate(True, True) is True
    assert _combine_gate(True, False) is False


def test_combine_gate_series_and_scalar():
    gate = pd.Series([True, True, False])
    cond = True
    result = _combine_gate(gate, cond)
    assert isinstance(result, pd.Series)


# ---------------------------------------------------------------------------
# interpreter input.* / timestamp no-op
# ---------------------------------------------------------------------------


def test_input_defval_returns_first_arg():
    src = """//@version=5
strategy("X")
length = input.int(14)
fast = ta.ema(close, length)
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    # length=14 스칼라로 bind됨, 오류 없이 실행
    assert result is not None


def test_timestamp_returns_zero():
    """timestamp(...)는 0 반환 — 시간 윈도우 비활성화."""
    src = """//@version=5
t = timestamp(2020, 1, 1, 0, 0)
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    assert result.metadata["vars"]["t"] == 0
