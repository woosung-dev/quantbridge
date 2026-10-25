"""JZXkmCi2의 typed label = if ... else na를 축소한 조건식 반환 회귀.

근거: https://www.tradingview.com/pine-script-docs/language/conditional-structures/
원본 source/생성 Python은 실행하지 않으며 명시 else와 지원하는 scope만 확인한다.
"""

import math

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError
from src.strategy.pine_v2.rendering import LabelObject


def run(body):
    frame = pd.DataFrame(
        {field: [100.0, 101.0, 102.0] for field in ("open", "high", "low", "close", "volume")}
    )
    return run_historical(
        '//@version=5\nindicator("if expression")\n' + body + "\n", frame, strict=True
    )


def test_typed_label_if_returns_selected_object_or_na_and_keeps_history():
    result = run(
        'label mark = if bar_index % 2 == 0\n    label.new(bar_index,na,"stop")\nelse\n    na\nlabel.delete(mark[1])'
    )
    marks = result.var_series["mark"]
    assert isinstance(marks[0], LabelObject)
    assert marks[0].deleted is True
    assert math.isnan(marks[1])
    assert isinstance(marks[2], LabelObject)
    assert marks[2].deleted is False
    assert marks[2].x == 2


def test_selected_if_branch_side_effects_execute_exactly_once():
    result = run(
        "a=array.new_int()\nx=if true\n    array.push(a,7)\n    99\nelse\n    array.push(a,9)\n    0\nsize=array.size(a)\nfirst=array.get(a,0)"
    )
    assert result.final_state["x"] == 99
    assert result.final_state["size"] == 1
    assert result.final_state["first"] == 7


def test_else_if_and_tuple_return_preserve_selected_values():
    result = run(
        "[a,b]=if bar_index == 0\n    [1,2]\nelse if bar_index == 1\n    [3,4]\nelse\n    [5,6]"
    )
    assert result.var_series["a"] == [1, 3, 5]
    assert result.var_series["b"] == [2, 4, 6]


def test_udf_final_if_returns_branch_result_without_changing_nonfinal_if():
    result = run(
        "f(x) =>\n    if x > 0\n        x+1\n    else\n        -x\ng(x) =>\n    total=0\n    if x > 0\n        total := x\n    total\na=f(3)\nb=f(-2)\nc=g(7)"
    )
    assert [result.final_state[k] for k in ("a", "b", "c")] == [4, 2, 7]


def test_if_expression_can_reassign_an_existing_global_once():
    result = run("total=1\nx=if true\n    total += 2\n    total\nelse\n    0")
    assert result.final_state["x"] == result.final_state["total"] == 3


@pytest.mark.parametrize(
    "body",
    [
        "x=if true\n    local=1\n    local\nelse\n    0",
        "x=if true\n    for i=0 to 1\n        1\n    7\nelse\n    0",
        "x=if true\n    1",
    ],
)
def test_unimplemented_lexical_or_implicit_return_types_fail_closed(body):
    with pytest.raises(PineRuntimeError, match="if expression"):
        run(body)


@pytest.mark.parametrize(
    "body",
    [
        "f(x) =>\n    if true\n        x := 7\n        x\n    else\n        0\na=f(1)",
        "total=0\nf(x) =>\n    if true\n        total := x\n        total\n    else\n        0\na=f(1)",
    ],
)
def test_udf_final_if_still_rejects_parameter_and_nonlocal_writes(body):
    with pytest.raises(PineRuntimeError, match="parameter or nonlocal"):
        run(body)
