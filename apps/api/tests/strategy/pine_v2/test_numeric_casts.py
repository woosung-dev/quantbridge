"""Pine v4+의 숫자/NA 캐스트와 버전·인자 경계를 확인한다."""

import math

import pandas as pd
import pytest
from pynescript import ast as pyne_ast

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter, PineRuntimeError
from src.strategy.pine_v2.runtime import PersistentStore


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [12.0, 13.0, 14.0],
            "low": [8.0, 9.0, 10.0],
            "close": [10.0, 11.0, 12.0],
            "volume": [1.0, 1.0, 1.0],
        }
    )


def _run(body: str, version: int = 5):
    header = 'study("cast")' if version < 5 else 'indicator("cast")'
    return run_historical(f"//@version={version}\n{header}\n{body}", _frame())


@pytest.mark.parametrize("version", [4, 5, 6])
def test_numeric_casts_truncate_and_preserve_float(version: int) -> None:
    result = _run("a = int(4.9)\nb = int(-4.9)\nc = float(3)\n", version)
    assert result.var_series["a"] == [4, 4, 4]
    assert result.var_series["b"] == [-4, -4, -4]
    assert result.var_series["c"] == [3.0, 3.0, 3.0]


@pytest.mark.parametrize("version", [4, 5, 6])
def test_int_and_float_cast_na_to_runtime_nan(version: int) -> None:
    result = _run("a = int(na)\nb = float(na)\n", version)
    assert all(math.isnan(value) for value in result.var_series["a"])
    assert all(math.isnan(value) for value in result.var_series["b"])


@pytest.mark.parametrize("version", [5, 6])
def test_bool_cast_numeric_and_na_contract(version: int) -> None:
    result = _run("a = bool(0)\nb = bool(-2.5)\nc = bool(na)\n", version)
    assert result.var_series["a"] == [False] * 3
    assert result.var_series["b"] == [True] * 3
    assert result.var_series["c"] == [False] * 3


def test_v4_bool_na_is_rejected_as_unverified() -> None:
    with pytest.raises(PineRuntimeError, match=r"bool\(na\).*unverified"):
        _run("x = bool(na)\n", version=4)


def test_v3_cast_call_remains_unsupported() -> None:
    with pytest.raises(PineRuntimeError, match="not supported in Pine v3"):
        _run("x = float(1)\n", version=3)


@pytest.mark.parametrize(
    "body, message",
    [
        ("a = int(1e309)\n", "infinite"),
        ("a = float(1e309)\n", "infinite"),
        ("a = bool(1e309)\n", "infinite"),
        ("a = int(true)\n", "numeric or na"),
        ('a = float("2")\n', "numeric or na"),
        ("a = bool(array.new_int(1))\n", r"bool\(\) supports only"),
    ],
)
def test_casts_reject_unverified_bounds_and_types(body: str, message: str) -> None:
    with pytest.raises(PineRuntimeError, match=message):
        _run(body)


@pytest.mark.parametrize("body", ["x = float()\n", "x = int(1, 2)\n", "x = bool(value=1)\n"])
def test_casts_reject_wrong_arity_and_named_arguments(body: str) -> None:
    with pytest.raises(PineRuntimeError, match=r"exactly one positional argument|named arguments"):
        _run(body)


def test_cast_argument_is_evaluated_once(monkeypatch: pytest.MonkeyPatch) -> None:
    tree = pyne_ast.parse('//@version=5\nindicator("cast")\nx = float(1)')
    call = next(
        node
        for node in pyne_ast.walk(tree)
        if isinstance(node, pyne_ast.Call)
        and isinstance(node.func, pyne_ast.Name)
        and node.func.id == "float"
    )
    interpreter = Interpreter(BarContext(_frame(), bar_index=0, pine_version=5), PersistentStore())
    evaluated = 0

    def evaluate(_node):
        nonlocal evaluated
        evaluated += 1
        return 4

    monkeypatch.setattr(interpreter, "_eval_expr", evaluate)
    assert interpreter._eval_call(call) == 4.0
    assert evaluated == 1


def test_user_function_keeps_priority_over_cast_dispatch() -> None:
    result = _run("int(x) => x + 100\ny = int(2.5)\n", version=5)
    assert result.var_series["y"] == [102.5, 102.5, 102.5]


def test_coverage_version_gates_cast_calls_without_confusing_input_type() -> None:
    assert not analyze_coverage('//@version=3\nstudy("x")\ny = float(1)\n').is_runnable
    assert analyze_coverage('//@version=4\nstudy("x")\ny = float(1)\n').is_runnable
    assert analyze_coverage('//@version=4\nstudy("x")\ny = input(1.0, type=float)\n').is_runnable


def test_version_text_in_multiline_string_does_not_enable_modern_casts() -> None:
    source = 'study("x")\ntext = "before\n//@version=6\nafter"\ny = float(1)\n'
    assert not analyze_coverage(source).is_runnable
