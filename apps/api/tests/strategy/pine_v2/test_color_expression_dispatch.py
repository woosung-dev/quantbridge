"""실측 색 helper의 interpreter 결박·키워드 순서·입력 override를 검증한다."""

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError
from src.strategy.pine_v2.rendering import PineColor, color_literal


def run(body, *, version=6, params=None):
    data = pd.DataFrame({k: [100.0] * 3 for k in ("open", "high", "low", "close", "volume")})
    return run_historical(
        f'//@version={version}\nindicator("colour dispatch")\n{body}\n',
        data,
        strict=True,
        input_overrides=params,
    )


@pytest.mark.parametrize("version", [5, 6])
def test_literal_and_named_colours_are_typed_and_keep_version_identity(version):
    result = run(
        "c=#ffffff\nn=color.white\nred=color.r(c)\ngreen=color.g(c)\nblue=color.b(c)\nt=color.t(c)",
        version=version,
    )
    assert isinstance(result.final_state["c"], PineColor)
    assert result.final_state["c"] == color_literal("#ffffff", version)
    assert result.final_state["n"] == color_literal("#FFFFFF", version)
    assert [result.final_state[k] for k in ("red", "green", "blue", "t")] == [255, 255, 255, 0]


def test_reordered_keywords_and_optional_transparency_use_public_signature():
    result = run(
        "a=color.rgb(10,20,30)\nb=color.rgb(blue=30,red=10,green=20)\nc=color.new(transp=50,color=a)\nd=color.from_gradient(top_color=color.white,bottom_value=0,value=5,bottom_color=#000000,top_value=10)\nx=color.r(d)\ny=color.t(c)"
    )
    assert result.final_state["a"] == result.final_state["b"]
    assert result.final_state["x"] == 127
    assert result.final_state["y"] == 50


@pytest.mark.parametrize(
    "expression",
    [
        "color.rgb(red=1,red=2,green=3,blue=4)",
        "color.new(#ffffff)",
        "color.r(value=#ffffff)",
        "color.rgb(1,green=2,3)",
        "color(#ffffff,#ffffff)",
        "color.new(color=#ffffff,transparency=2)",
    ],
)
def test_invalid_colour_signatures_are_rejected_before_execution(expression):
    with pytest.raises(PineRuntimeError):
        run("c=" + expression)


def test_colour_keyword_side_effects_run_once_in_source_order():
    result = run(
        "a=array.new_int()\nf(values,tag,value) =>\n    array.push(values,tag)\n    value\nc=color.rgb(blue=f(a,1,30),red=f(a,2,10),green=f(a,3,20))\nfirst=array.get(a,0)\nsecond=array.get(a,1)\nthird=array.get(a,2)\nsize=array.size(a)"
    )
    assert [result.final_state[k] for k in ("first", "second", "third", "size")] == [1, 2, 3, 3]
    assert result.final_state["c"].red == 10
    assert result.final_state["c"].blue == 30
    with pytest.raises(PineRuntimeError, match="unknown or duplicate"):
        run("a=array.new_int()\nc=color.rgb(unknown=array.get(a,99))")


def test_input_colour_hex_override_is_normalized_without_altering_other_input_types():
    result = run(
        'c=input.color(#FFFFFF,"Color")\ns=input.string("default","Text")\nr=color.r(c)',
        params={"c": "#102030", "s": "#ffffff"},
    )
    assert result.final_state["c"] == color_literal("#102030", 6)
    assert result.final_state["r"] == 16
    assert result.final_state["s"] == "#ffffff"
    with pytest.raises(PineRuntimeError, match=r"input\.color"):
        run('c=input.color(#FFFFFF,"Color")', params={"c": True})


def test_colour_scalar_udf_history_is_staged_without_reference_coercion():
    result = run("f(x) =>\n    x[1]\nc=bar_index==0?#010203:#040506\np=f(c)")
    assert result.var_series["p"][1] == color_literal("#010203", 6)
    assert result.var_series["p"][2] == color_literal("#040506", 6)


def test_unknown_colour_attribute_keeps_explicit_runtime_error():
    with pytest.raises(PineRuntimeError, match=r"Attribute access not supported: color\.unknown"):
        run("x=color.unknown")
