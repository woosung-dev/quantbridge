"""실제 에디터 픽 실패를 축소한 Pine 의미 회귀. Python 생성 원문은 실행하지 않는다.

근거: TV language/operators, user-defined-functions, v5/language/arrays.
"""

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def run(body, version=5, bars=3):
    values = [100.0 + i for i in range(bars)]
    frame = pd.DataFrame(dict.fromkeys(("open", "high", "low", "close", "volume"), values))
    return run_historical(
        f'//@version={version}\nindicator("regression")\n{body}\n', frame, strict=True
    )


@pytest.mark.parametrize(
    "operator,expected", [("+=", 9), ("-=", 3), ("*=", 18), ("/=", 2), ("%=", 0)]
)
def test_global_compound_uses_previous_value(operator, expected):
    result = run(f"x=6.0\nx {operator} 3\n")
    assert result.final_state["x"] == expected


def test_compound_preserves_var_across_bars_and_string_concatenation():
    result = run('var count=0\nif close > 100\n    count += 1\ntext="a"\ntext += "b"')
    assert result.var_series["count"] == [0, 1, 2]
    assert result.final_state["text"] == "ab"


def test_udf_compound_local_and_final_assignment_are_returned():
    result = run("f(x) =>\n    total=2.0\n    total += x\n    total *= 3\na=f(4)\nb=f(2)")
    assert result.final_state["a"] == 18
    assert result.final_state["b"] == 12


def test_automatic_trendlines_final_declaration_returns_numeric_or_na():
    result = run(
        "get_y(m,b,ts) =>\n    Y=m*ts+b\ny=get_y(2,3,bar_index)\nmissing=get_y(na,3,bar_index)"
    )
    assert result.var_series["y"] == [3, 5, 7]
    assert math.isnan(result.final_state["missing"])


@pytest.mark.parametrize(
    "body",
    [
        "x += 1",
        "f(x) =>\n    x += 1\n    x\na=f(1)",
        "var total=0\nf(x) =>\n    total += x\n    total\na=f(1)",
    ],
)
def test_compound_rejects_undeclared_parameter_or_nonlocal_binding(body):
    with pytest.raises(PineRuntimeError):
        run(body)


@pytest.mark.parametrize("version", [4, 5, 6])
def test_na_to_bound_skips_body_without_changing_prior_value(version):
    result = run("count=7\nfor i=0 to int(na)\n    count := count + 1", version=version)
    assert result.final_state["count"] == 7


def test_last_declaration_does_not_repeat_side_effects():
    result = run(
        "a=array.new_int(0)\nf(values) =>\n    array.push(values, 7)\n    n=array.size(values)\nx=f(a)\nsize=array.size(a)"
    )
    assert result.final_state["x"] == result.final_state["size"] == 1


def test_array_constructor_statistics_copy_and_search():
    result = run(
        "a=array.from(3.0,na,1.0,3.0)\nb=array.copy(a)\narray.set(b,0,99)\ntotal=array.sum(a)\nmaximum=array.max(a,1)\nminimum=array.min(a)\nfound=array.indexof(a,3.0)\nmissing=array.indexof(a,8.0)\noriginal=array.get(a,0)"
    )
    assert [
        result.final_state[k]
        for k in ["total", "maximum", "minimum", "found", "missing", "original"]
    ] == [7, 3, 1, 0, -1, 3]


@pytest.mark.parametrize("op", ["sum", "max", "min"])
def test_empty_or_all_na_array_statistics_are_na(op):
    result = run(f"a=array.new_float(0)\nb=array.new_float(2,na)\nx=array.{op}(a)\ny=array.{op}(b)")
    assert math.isnan(result.final_state["x"]) and math.isnan(result.final_state["y"])


def test_compound_rhs_and_local_array_method_evaluate_once():
    result = run(
        "a=array.from(1,2)\nx=1\nx += array.pop(a)\nf(values) =>\n    values.push(7)\n    values.size()\nn=f(a)\nremaining=array.size(a)"
    )
    assert [result.final_state[k] for k in ("x", "n", "remaining")] == [3, 2, 2]


def test_compound_local_var_preserves_separate_callsite_state():
    result = run("f(x) =>\n    var total=0\n    total += x\n    total\na=f(1)\nb=f(2)")
    assert result.var_series["a"] == [1, 2, 3]
    assert result.var_series["b"] == [2, 4, 6]


def test_import_alias_is_not_treated_as_array_instance():
    with pytest.raises(PineRuntimeError, match=r"pa\.push"):
        run(
            "import HeWhoMustNotBeNamed/arrayutils/10 as pa\na=array.new_float()\npa.push(a,1.0,7)",
            version=6,
        )


def test_trigonometry_and_v4_scalar_aliases():
    result = run(
        "a=sin(0)+cos(0)+tan(0)+acos(1)\nb=asin(1)\nc=atan(1)\nd=pow(2,3)+exp(0)+log(1)\ne=sum(close,2)",
        version=4,
    )
    assert result.final_state["a"] == 1
    assert result.final_state["b"] == pytest.approx(math.pi / 2)
    assert result.final_state["c"] == pytest.approx(math.pi / 4)
    assert result.final_state["d"] == 9
    assert result.final_state["e"] == 203


def test_vwma_receives_actual_bar_volume():
    result = run("weighted=ta.vwma(close,2)")
    assert result.final_state["weighted"] == pytest.approx((101 * 101 + 102 * 102) / 203)


def test_rendering_coordinate_getter_dispatches_to_actual_object():
    result = run("level=line.new(0,2,1,3)\nline.set_y1(level,7)\ny=line.get_y1(level)")
    assert result.final_state["y"] == 7


@pytest.mark.parametrize(
    "positional,keyword",
    [
        ("ta.cum(close)", "ta.cum(source=close)"),
        (
            "ta.stoch(close,high+2,low-2,2)",
            "ta.stoch(length=2,low=low-2,high=high+2,source=close)",
        ),
        ("ta.linreg(close,2,0)", "ta.linreg(offset=0,length=2,source=close)"),
        ("ta.vwma(close,2)", "ta.vwma(length=2,source=close)"),
        ("ta.roc(close,2)", "ta.roc(length=2,source=close)"),
        ("ta.cci(close,2)", "ta.cci(length=2,source=close)"),
    ],
)
def test_new_ta_keywords_use_public_signature(positional, keyword):
    result = run(f"a={positional}\nb={keyword}", bars=5)
    for a, b in zip(result.var_series["a"], result.var_series["b"], strict=True):
        assert (math.isnan(a) and math.isnan(b)) or a == b


@pytest.mark.parametrize(
    "expression",
    [
        "ta.stoch(close,high,low,period=2)",
        "ta.cum(src=close)",
        "ta.vwma(close,source=close)",
        "ta.roc(length=2,close)",
        "ta.linreg(close,2)",
        "ta.cci(close,2,3)",
    ],
)
def test_new_ta_rejects_invalid_binding_before_dispatch(expression):
    with pytest.raises(PineRuntimeError):
        run(f"a={expression}")


def test_new_ta_keyword_expressions_evaluate_once_in_source_order():
    result = run(
        "a=array.new_int()\nf(values,x) =>\n    array.push(values,x)\n    x\n"
        "value=ta.linreg(offset=f(a,0),length=f(a,2),source=f(a,7))\n"
        "first=array.get(a,0)\nsecond=array.get(a,1)\nthird=array.get(a,2)\nsize=array.size(a)"
    )
    assert [result.final_state[k] for k in ("first", "second", "third", "size")] == [0, 2, 7, 3]
