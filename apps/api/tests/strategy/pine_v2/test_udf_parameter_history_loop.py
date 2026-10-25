"""루프 밖에서 매봉 호출한 UDF의 불변 수치 매개변수 이력만 확장한다."""

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def run(body):
    frame = pd.DataFrame(
        {field: [2.0, 5.0, 9.0, 4.0] for field in ("open", "high", "low", "close", "volume")}
    )
    return run_historical(
        '//@version=5\nindicator("parameter history")\n' + body + "\n", frame, strict=True
    )


FUNCTION = "f(x) =>\n    total=0.0\n    for j=0 to 2\n        total += nz(x[j],0)\n    total\n"


def test_readonly_numeric_parameter_history_inside_own_loop():
    result = run(FUNCTION + "a=f(close)\nb=f(close*10)")
    assert result.var_series["a"] == [2, 7, 16, 18]
    assert result.var_series["b"] == [20, 70, 160, 180]


@pytest.mark.parametrize(
    "body",
    [
        FUNCTION + "a=0.0\nfor i=0 to 1\n    a := f(close+i)",
        "f(x) =>\n    y=x\n    total=0.0\n    for j=0 to 1\n        total += nz(y[j],0)\n    total\na=f(close)",
        "f(x) =>\n    total=0.0\n    for j=0 to 1\n        total += nz(j[1],0)\n    total\na=f(close)",
        "f(x) =>\n    for j=0 to 1\n        array.size(x[1])\n    0\na=f(array.new_float())",
        FUNCTION + "g(x) =>\n    f(x)\na=0.0\nfor i=0 to 1\n    a := g(close+i)",
    ],
)
def test_unsupported_call_or_reference_or_mutable_local_history_remains_rejected(body):
    with pytest.raises(PineRuntimeError, match=r"UDF.*history.*not supported"):
        run(body)


def test_parameter_mutation_is_still_rejected_before_loop_execution():
    with pytest.raises(PineRuntimeError, match="parameter or nonlocal"):
        run("f(x) =>\n    for j=0 to 1\n        x += 1\n    x\na=f(close)")


def test_sparse_larger_parameter_offset_is_still_rejected():
    with pytest.raises(PineRuntimeError, match=r"UDF sparse history.*not supported"):
        run(
            "f(x) =>\n    total=0.0\n    for j=0 to 2\n        total += nz(x[j],0)\n    total\na=bar_index%2==0?f(close):-1"
        )
