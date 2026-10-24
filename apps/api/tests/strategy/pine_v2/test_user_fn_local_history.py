"""UDF 호출별 scalar 상태와 확정 봉 이력: 독립 수기 반례 및 제한 경계."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter, PineRuntimeError
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def _frame(values: list[float] | None = None) -> pd.DataFrame:
    values = values or [2, 5, 9]
    return pd.DataFrame(
        {
            "open": values,
            "high": [v + 1 for v in values],
            "low": [v - 1 for v in values],
            "close": values,
            "volume": 1,
        }
    )


def _source(body: str) -> str:
    return '//@version=5\nindicator("UDF contract")\n' + body


def _assert_series(actual: list, expected: list) -> None:
    assert len(actual) == len(expected)
    for value, wanted in zip(actual, expected, strict=True):
        if wanted is None:
            assert math.isnan(value)
        else:
            assert value == pytest.approx(wanted, rel=1e-12, abs=1e-12)


_ACC = "f(x) =>\n    var float acc = 0.0\n    acc := acc + x\n    acc\n"


@pytest.mark.parametrize("kind", ["var", "varip"])
def test_persistent_calls_are_independent(kind: str) -> None:
    result = run_historical(
        _source(_ACC.replace("var float", f"{kind} float") + "a=f(1)\nb=f(10)\n"),
        _frame(),
        strict=True,
    )
    _assert_series(result.var_series["a"], [1, 2, 3])
    _assert_series(result.var_series["b"], [10, 20, 30])
    assert set(result.var_series) == {"a", "b"}
    assert set(result.final_state) == {"a", "b"}


def test_normal_local_recursive_history_and_tuple_binding() -> None:
    body = (
        "f(x) =>\n    [y, z] = [x, x*2]\n"
        "    y := nz(y[1]) + x\n    z := nz(z[1]) + x*2\n    [y,z]\n"
        "[a,b]=f(1)\n[c,d]=f(10)\n"
    )
    result = run_historical(_source(body), _frame(), strict=True)
    for name, values in {
        "a": [1, 2, 3],
        "b": [2, 4, 6],
        "c": [10, 20, 30],
        "d": [20, 40, 60],
    }.items():
        _assert_series(result.var_series[name], values)


def test_parameter_history_and_current_value() -> None:
    result = run_historical(
        _source("f(x) =>\n    [x[0],x[1]]\n[a,b]=f(close)\n"), _frame(), strict=True
    )
    _assert_series(result.var_series["a"], [2, 5, 9])
    _assert_series(result.var_series["b"], [None, 2, 5])


def test_same_line_and_nested_paths_are_independent() -> None:
    body = _ACC + "g(x) =>\n    f(x)\nz=g(1)+g(10)\n"
    result = run_historical(_source(body), _frame(), strict=True)
    _assert_series(result.var_series["z"], [11, 22, 33])


def test_local_shadow_does_not_change_global_values_or_history() -> None:
    body = "var float acc=100\n" + _ACC + "a=f(1)\nb=acc\nc=acc[1]\n"
    result = run_historical(_source(body), _frame(), strict=True)
    _assert_series(result.var_series["a"], [1, 2, 3])
    _assert_series(result.var_series["b"], [100, 100, 100])
    _assert_series(result.var_series["c"], [None, 100, 100])
    assert result.final_state["main::acc"] == 100
    assert set(result.final_state) == {"main::acc", "a", "b", "c"}


def test_conditional_call_lag_one_uses_last_committed_call_bar() -> None:
    body = "f(x) =>\n    x[1]\na=bar_index%2==0 ? f(close) : -1\n"
    result = run_historical(_source(body), _frame([2, 5, 9, 4, 8]), strict=True)
    _assert_series(result.var_series["a"], [None, -1, 2, -1, 9])


def test_consecutive_local_history_supports_larger_offset() -> None:
    result = run_historical(_source("f(x) =>\n    x[2]\na=f(close)\n"), _frame(), strict=True)
    _assert_series(result.var_series["a"], [None, None, 2])


@pytest.mark.parametrize(
    "body",
    [
        "f(x) =>\n    x[2]\na=bar_index%3==0 ? f(close) : -1\n",
        "f(x) =>\n    x[1]\na=0.0\nfor i=1 to 2\n    a := f(i)\n",
    ],
)
def test_unverified_sparse_or_loop_history_is_rejected(body: str) -> None:
    with pytest.raises(PineRuntimeError, match=r"UDF.*history.*not supported"):
        run_historical(_source(body), _frame([2, 5, 9, 4]), strict=True)


def test_loop_reuses_persistence_without_creating_iteration_scopes() -> None:
    result = run_historical(
        _source(_ACC + "a=0.0\nfor i=1 to 2\n    a := f(i)\n"), _frame(), strict=True
    )
    _assert_series(result.var_series["a"], [3, 6, 9])


@pytest.mark.parametrize(
    "body",
    [
        "f(x) =>\n    x := x+1\n    x\na=f(1)\n",
        "var float total=0\nf(x) =>\n    total := total+x\n    total\na=f(1)\n",
        "f(x) =>\n    y=0\n    if x>0\n        y=10\n    y\na=f(1)\n",
    ],
)
def test_illegal_reassignment_or_lexical_block_declaration_is_rejected(body: str) -> None:
    with pytest.raises(PineRuntimeError, match="UDF"):
        run_historical(_source(body), _frame(), strict=True)


def test_if_can_reassign_existing_function_local() -> None:
    body = "f(x) =>\n    y=0.0\n    if x>0\n        y := nz(y[1])+x\n    y\na=f(1)\n"
    result = run_historical(_source(body), _frame(), strict=True)
    _assert_series(result.var_series["a"], [1, 2, 3])


def test_global_only_values_and_snapshots_are_preserved() -> None:
    body = (
        "var float total=0\ntotal := total+close\nlag=close[1]\n"
        "smooth=close\nsmooth := nz(smooth[1])+close\n"
    )
    result = run_historical(_source(body), _frame(), capture_history=True, strict=True)
    _assert_series(result.var_series["total"], [2, 7, 16])
    _assert_series(result.var_series["smooth"], [2, 7, 16])
    _assert_series(result.var_series["lag"], [None, 2, 5])
    assert result.final_state == {"main::total": 16, "lag": 5, "smooth": 16}
    assert len(result.state_history) == 3


def test_failed_nested_call_unwinds_and_does_not_commit_partial_local_history() -> None:
    bar = BarContext(_frame())
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(
        _source(
            "f(x) =>\n    y=x\n    y[1]\ng(x) =>\n"
            "    y=f(x)\n    z=array.new_float(0)\n"
            "    array.get(z,0)\na=g(close)\n"
        )
    )
    assert bar.advance()
    store.begin_bar()
    with pytest.raises(PineRuntimeError, match="out of bounds"):
        interp.execute(tree)
    assert interp._scope_stack == []
    assert interp.stdlib._prefix_stack == []
    assert interp._assignment_target_stack == []
    interp.append_var_series()
    # 실패한 부모 호출에서 성공했던 자식도 정상 확정 이력으로 승격하지 않는다.
    assert not interp._local_history


def test_recursive_smoothing_has_memory_after_first_bar() -> None:
    # 원문 _iT3의 첫 재귀단과 같은 수식. 독립 기대: 0.5*x + 0.5*직전 상태.
    body = (
        "f(x) =>\n    y=x\n    y := nz(y[1])+0.5*(x-nz(y[1]))\n    y\na=f(close)\nb=f(close*10)\n"
    )
    result = run_historical(_source(body), _frame([2, 5, 9, 4]), strict=True)
    _assert_series(result.var_series["a"], [1, 3, 6, 5])
    _assert_series(result.var_series["b"], [10, 30, 60, 50])


def test_parameter_shadowing_builtin_uses_local_history() -> None:
    result = run_historical(
        _source("f(close) =>\n    close[1]\na=f(close*10)\n"), _frame(), strict=True
    )
    _assert_series(result.var_series["a"], [None, 20, 50])


def test_var_factory_runs_once_at_first_actual_call() -> None:
    body = "f(x) =>\n    var float first=x\n    [first,first[1]]\n[a,b]=f(close)\n"
    result = run_historical(_source(body), _frame(), strict=True)
    _assert_series(result.var_series["a"], [2, 2, 2])
    _assert_series(result.var_series["b"], [None, 2, 2])


def test_function_local_var_and_varip_keep_store_rollback_contract() -> None:
    body = (
        "f(x) =>\n    var float a=0\n    varip float b=0\n"
        "    a := a+x\n    b := b+x\n    [a,b]\n[a,b]=f(1)\n"
    )
    bar = BarContext(_frame())
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(_source(body))
    assert bar.advance()
    store.begin_bar()
    interp.execute(tree)
    store.commit_bar()
    interp.append_var_series()
    assert bar.advance()
    store.begin_bar()
    interp.reset_transient()
    interp.execute(tree)
    store.rollback_bar()
    interp.reset_transient()
    interp.execute(tree)
    # 현재 루프의 realtime 지원 주장이 아니라 저장소 var/varip 구분 회귀다.
    assert interp._transient["a"] == 2
    assert interp._transient["b"] == 3


def test_nested_function_does_not_read_callers_local_scope() -> None:
    body = "f() =>\n    callerOnly\ng(callerOnly) =>\n    f()\na=g(10)\n"
    with pytest.raises(PineRuntimeError, match="Undefined name: callerOnly"):
        run_historical(_source(body), _frame(), strict=True)


def test_function_reference_type_history_is_explicitly_rejected() -> None:
    body = "f(x) =>\n    a=array.new_float(1,x)\n    a[1]\nz=f(close)\n"
    with pytest.raises(PineRuntimeError, match="UDF reference-type history"):
        run_historical(_source(body), _frame(), strict=True)


def test_virtual_strategy_uses_function_history_commit() -> None:
    from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy

    body = (
        "f(x) =>\n    y=x\n    y := nz(y[1])+x\n    y\n"
        'v=f(1)\nalertcondition(v==3,"Long","UT Long")\n'
    )
    result = run_virtual_strategy(_source(body), _frame(), strict=True)
    assert result.strategy_state.open_trades["L"].entry_bar == 2


def test_live_replay_uses_same_corrected_history_as_historical() -> None:
    from src.strategy.pine_v2.event_loop import run_live

    source = (
        '//@version=5\nstrategy("UDF replay")\nf(x) =>\n'
        "    y=x\n    y := nz(y[1])+x\n    y\n"
        'v=f(1)\nif v==3\n    strategy.entry("L",strategy.long)\n'
    )
    frame = _frame()
    frame["timestamp"] = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
    historical = run_historical(source, frame, strict=True)
    live = run_live(source, frame)
    assert not live.errors
    assert historical.strategy_state.open_trades["L"].entry_bar == 2
    assert len(live.signals) == 1
    assert live.signals[0].action == "entry"


def test_named_arguments_are_rejected_instead_of_bound_by_position() -> None:
    body = "f(x,y) =>\n    x-y\nz=f(y=10,x=1)\n"
    with pytest.raises(PineRuntimeError, match="UDF named arguments"):
        run_historical(_source(body), _frame(), strict=True)


def test_function_loop_counter_scope_restores_outer_loop_and_global() -> None:
    body = (
        "i=100\nf(x) =>\n    total=0\n    for i=1 to 2\n"
        "        for i=3 to 4\n            total := total+i\n"
        "        total := total+i\n    total+i\na=f(0)\nb=i\n"
    )
    result = run_historical(_source(body), _frame(), strict=True)
    _assert_series(result.var_series["a"], [117, 117, 117])
    _assert_series(result.var_series["b"], [100, 100, 100])


@pytest.mark.parametrize(
    "body",
    [
        "f(x) =>\n    x += 1\n    x\na=f(1)\n",
        "var total=0\nf(x) =>\n    total += x\n    total\na=f(1)\n",
    ],
)
def test_udf_compound_assignment_cannot_write_parameter_or_global(body: str) -> None:
    with pytest.raises(PineRuntimeError, match="parameter or nonlocal"):
        run_historical(_source(body), _frame(), strict=True)


@pytest.mark.parametrize("operator,expected", [("+=", 3), ("-=", -1)])
def test_global_compound_assignment_updates_declared_binding(operator: str, expected: int) -> None:
    result = run_historical(_source(f"v=1\nv {operator} 2\n"), _frame(), strict=True)
    _assert_series(result.var_series["v"], [expected] * 3)
