"""첫 조건 keyword·원문 span·1회 평가와 제한된 선언 옵션을 반증한다."""

import pandas as pd
import pytest

from scripts.pine_validation.strategy_adapter import StrategyAdapterError, adapt_strategy
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.parser_adapter import parse_to_ast


def binding(function, line=3):
    return [{"function": function, "line": line, "direction": "long", "column": 0}]


@pytest.mark.parametrize(
    "function,keyword",
    [("plotshape", "series"), ("plotchar", "series"), ("alertcondition", "condition")],
)
@pytest.mark.parametrize("condition_first", [True, False])
def test_named_condition_preserves_keyword_span_and_single_stateful_evaluation(
    function, keyword, condition_first
):
    value = f"{keyword} = (ta.change(close) > 0)"
    args = f'{value}, title="한글"' if condition_first else f'title="한글", {value}'
    source = f'//@version=5\r\nindicator("Named")\r\n{function}({args}) // 원문\r\n'
    out = adapt_strategy(source, binding(function))
    temp = out.bindings[0]["condition_variable"]
    assert f"{keyword} = ({temp})" in out.strategy_source
    assert 'title="한글"' in out.strategy_source and "// 원문\r\n" in out.strategy_source
    assert out.strategy_source.count("ta.change(close)") == 1
    assert "\n" not in out.strategy_source.replace("\r\n", "")
    frame = pd.DataFrame(
        {
            "open": [10, 12, 11, 13],
            "high": [11, 13, 12, 14],
            "low": [9, 11, 10, 12],
            "close": [10, 12, 11, 13],
            "volume": 1,
        }
    )
    original = run_historical(source, frame, capture_signals=True)
    adapted = run_historical(out.strategy_source, frame, capture_signals=True)
    assert not original.errors and not adapted.errors
    assert [x.value for x in original.signal_trace] == [x.value for x in adapted.signal_trace]
    assert any(x.value for x in original.signal_trace)


@pytest.mark.parametrize(
    "args,code",
    [
        ("true, series=false", "ambiguous_signal_condition"),
        ("series=true, series=false", "ambiguous_signal_condition"),
        ("condition=true", "named_first_condition"),
        ("title=str.tostring(ta.change(close)), series=true", "dynamic_signal_arguments"),
        ("series=true, title=str.tostring(ta.change(close))", "dynamic_signal_arguments"),
        ("series=input.bool(true)", "unsupported_condition_call"),
    ],
)
def test_invalid_or_side_effectful_named_arguments_are_rejected(args, code):
    with pytest.raises(StrategyAdapterError) as error:
        adapt_strategy(f'indicator("X")\nplotshape({args})\n', binding("plotshape", 2))
    assert error.value.code == code


@pytest.mark.parametrize("flag", ["true", "false"])
def test_third_positional_overlay_becomes_explicit_without_changing_body(flag):
    source = f'indicator("X", "Short", {flag})\nplotshape(true)\n'
    out = adapt_strategy(source, binding("plotshape", 2))
    header = parse_to_ast(out.strategy_source).body[0].value
    assert next(a.value.value for a in header.args if a.name == "overlay") == (flag == "true")
    assert sum(a.name == "overlay" for a in header.args) == 1


@pytest.mark.parametrize("suffix", ["close > 0", "true, overlay=false", "true, format.price"])
def test_positional_overlay_does_not_enable_other_positional_declarations(suffix):
    with pytest.raises(StrategyAdapterError):
        adapt_strategy(f'indicator("X", "S", {suffix})\nplotshape(true)\n', binding("plotshape", 2))


@pytest.mark.parametrize("flag", ["true", "false"])
def test_gaps_only_with_explicit_chart_timeframe_warns_about_lost_settings(flag):
    source = f'indicator("X", timeframe_gaps={flag}, timeframe="")\nplotshape(true)\n'
    out = adapt_strategy(source, binding("plotshape", 2))
    header = parse_to_ast(out.strategy_source).body[0].value
    assert not {a.name for a in header.args} & {"timeframe", "timeframe_gaps"}
    assert any("설정 UI" in warning for warning in out.warnings)


@pytest.mark.parametrize(
    "args",
    [
        "timeframe_gaps=true",
        'timeframe="D", timeframe_gaps=true',
        'timeframe="", timeframe_gaps=close > 0',
        'timeframe="", timeframe_gaps=1',
        "timeframe=close, timeframe_gaps=false",
    ],
)
def test_non_chart_or_dynamic_gap_declarations_remain_rejected(args):
    with pytest.raises(StrategyAdapterError):
        adapt_strategy(f'indicator("X", {args})\nplotshape(true)\n', binding("plotshape", 2))
