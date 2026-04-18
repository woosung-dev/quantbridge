"""Sprint 8c — user-defined function (`=>`) 단위 테스트."""
from __future__ import annotations

import math
import pandas as pd
import pytest
from pynescript import ast as pyne_ast

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter, PineRuntimeError
from src.strategy.pine_v2.runtime import PersistentStore


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1.0] * len(closes),
    })


def _interp(closes: list[float]) -> Interpreter:
    bar = BarContext(_ohlcv(closes))
    return Interpreter(bar, PersistentStore())


def test_function_def_registers_in_user_functions() -> None:
    interp = _interp([10.0, 11.0])
    tree = pyne_ast.parse("foo(x) => x + 1\n")
    interp.bar.advance()
    interp.execute(tree)
    assert "foo" in interp._user_functions
    fn = interp._user_functions["foo"]
    assert isinstance(fn, pyne_ast.FunctionDef)
    assert [p.name for p in fn.args] == ["x"]


# ---------------------------------------------------------------------------
# Task 2 — scope stack + _exec_reassign 로컬 frame (eng-review critical gap 보완)
# ---------------------------------------------------------------------------


def test_scope_stack_resolves_local_before_transient() -> None:
    interp = _interp([10.0])
    interp.bar.advance()
    # 외부 transient에 x = 1 세팅
    interp._transient["x"] = 1
    # 로컬 frame에 x = 99
    interp._scope_stack.append({"x": 99})
    assert interp._resolve_name("x") == 99
    # 로컬 frame pop 후 다시 1로 복원
    interp._scope_stack.pop()
    assert interp._resolve_name("x") == 1


def test_reassign_writes_to_local_frame_when_name_is_local() -> None:
    """Eng-review critical gap 보완 — supertrend body의 `lowerBand := ...` 패턴."""
    interp = _interp([10.0])
    interp.bar.advance()
    # top-level에도 같은 이름이 있지만 로컬 frame에 존재하는 변수면 frame에 써야 함.
    interp.store.declare_if_new("main::v", lambda: 1, varip=False)
    interp._scope_stack.append({"v": 10})
    # := 에 대응하는 ReAssign을 직접 생성
    tree = pyne_ast.parse("v := 99\n")
    interp._exec_stmt(tree.body[0])
    assert interp._scope_stack[-1]["v"] == 99
    # 상위 PersistentStore는 변경되지 않아야 함
    assert interp.store.get("main::v") == 1


def test_reassign_falls_through_to_persistent_when_not_local() -> None:
    interp = _interp([10.0])
    interp.bar.advance()
    interp.store.declare_if_new("main::p", lambda: 7, varip=False)
    # 로컬 frame이 열려 있어도 해당 이름이 없으면 persistent로 떨어짐.
    interp._scope_stack.append({"otherName": 1})
    tree = pyne_ast.parse("p := 42\n")
    interp._exec_stmt(tree.body[0])
    assert interp.store.get("main::p") == 42
    assert "p" not in interp._scope_stack[-1]


# ---------------------------------------------------------------------------
# Task 3 — user function Call dispatch + parameter binding + single return
# ---------------------------------------------------------------------------


def test_user_function_single_arg_single_expr() -> None:
    tree = pyne_ast.parse("foo(x) => x * 2\n")
    interp = _interp([10.0])
    interp.bar.advance()
    interp.execute(tree)
    # 직접 Call 평가
    call_node = pyne_ast.parse("foo(5)").body[0].value  # Expr.value = Call
    assert interp._eval_expr(call_node) == 10


def test_user_function_multi_arg_multi_stmt_body() -> None:
    src = """foo(x, y) =>
    a = x + y
    a * 2
"""
    tree = pyne_ast.parse(src)
    interp = _interp([10.0])
    interp.bar.advance()
    interp.execute(tree)
    call_node = pyne_ast.parse("foo(3, 4)").body[0].value
    assert interp._eval_expr(call_node) == 14


def test_user_function_local_does_not_leak() -> None:
    src = """foo(x) =>
    tmp = x + 1
    tmp
"""
    tree = pyne_ast.parse(src)
    interp = _interp([10.0])
    interp.bar.advance()
    interp.execute(tree)
    call_node = pyne_ast.parse("foo(5)").body[0].value
    _ = interp._eval_expr(call_node)
    assert "tmp" not in interp._transient


# ---------------------------------------------------------------------------
# Task 5 — na 전파 / arity / depth guard 엣지
# ---------------------------------------------------------------------------


def test_user_function_na_arg_propagates_to_body() -> None:
    src = "dbl(x) => x * 2\n"
    interp = _interp([10.0])
    interp.bar.advance()
    interp.execute(pyne_ast.parse(src))
    call_node = pyne_ast.parse("dbl(na)").body[0].value
    result = interp._eval_expr(call_node)
    assert math.isnan(result)


def test_user_function_arity_mismatch_raises() -> None:
    src = "pair(x, y) => x + y\n"
    interp = _interp([10.0])
    interp.bar.advance()
    interp.execute(pyne_ast.parse(src))
    call_node = pyne_ast.parse("pair(1)").body[0].value
    with pytest.raises(PineRuntimeError, match="expected 2 args, got 1"):
        interp._eval_expr(call_node)


def test_user_function_depth_guard_blocks_infinite_recursion() -> None:
    src = "rec(x) => rec(x - 1)\n"
    interp = _interp([10.0])
    interp.bar.advance()
    interp._max_call_depth = 5  # 테스트 단축
    interp.execute(pyne_ast.parse(src))
    call_node = pyne_ast.parse("rec(10)").body[0].value
    with pytest.raises(PineRuntimeError, match="depth exceeded"):
        interp._eval_expr(call_node)
