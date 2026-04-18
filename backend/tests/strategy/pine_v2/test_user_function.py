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
