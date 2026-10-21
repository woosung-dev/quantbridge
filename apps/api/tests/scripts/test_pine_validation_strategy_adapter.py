"""검토한 원본 신호의 1회 평가와 실제 앱 선물 체결 연결을 검증한다."""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from scripts.pine_validation.strategy_adapter import (
    StrategyAdapterError,
    adapt_strategy,
    compare_app_backtest,
)
from scripts.validate_pine_signals import bind_events, execute_pine


def _frame(bars: int = 8) -> pd.DataFrame:
    closes = [100.0 + (index % 3) / 10 for index in range(bars)]
    return pd.DataFrame(
        {"open": closes, "high": 102, "low": 99, "close": closes, "volume": 1},
        index=pd.date_range("2026-01-01", periods=bars, freq="h", tz="UTC"),
    )


def _bindings(*pairs: tuple[int, str], function: str = "plotshape") -> list[dict]:
    return [
        {"function": function, "line": line, "column": 0, "direction": direction}
        for line, direction in pairs
    ]


def _compare(source: str, bindings: list[dict], frame: pd.DataFrame, **kwargs) -> dict:
    original = execute_pine(source, frame, {}, "1h")
    events = bind_events(original.signal_trace, bindings, "1h")
    converted = adapt_strategy(source, bindings)
    return compare_app_backtest(converted.strategy_source, frame, {}, "1h", events, **kwargs)


def test_multiline_unicode_crlf_body_and_exact_source_mapping_are_preserved() -> None:
    source = (
        '//@version=5\r\nindicator(\r\n    "한글 지표", overlay=true) // 선언 보존\r\n'
        "buy = bar_index == 0\r\n// 원문 주석\r\nplotshape(\r\n    buy,\r\n"
        '    title="↑ 매수", text="매수") // 표식 보존\r\nbuy := false\r\n'
    )
    result = adapt_strategy(source, _bindings((6, "long")))
    assert "// 선언 보존\r\n" in result.strategy_source
    assert "// 원문 주석\r\n" in result.strategy_source
    assert '    title="↑ 매수", text="매수") // 표식 보존\r\n' in result.strategy_source
    assert result.strategy_source.endswith("buy := false\r\n")
    assert "\n" not in result.strategy_source.replace("\r\n", "")
    binding = result.bindings[0]
    converted_line = binding["converted_line"]
    assert result.strategy_source.splitlines()[converted_line - 1] == "plotshape("
    assert result.source_line_map[9] == len(result.strategy_source.splitlines())
    assert result.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    assert result.converted_sha256 == hashlib.sha256(result.strategy_source.encode()).hexdigest()
    json.dumps(result.to_dict())


def test_inline_stateful_condition_is_evaluated_once_and_keeps_original_markers() -> None:
    source = """//@version=5
indicator("Inline")
plotshape(ta.change(close) > 0, "Buy")
plotshape(ta.change(close) < 0, "Sell")
"""
    frame = _frame()
    bindings = _bindings((3, "long"), (4, "short"))
    result = adapt_strategy(source, bindings)
    assert result.strategy_source.count("ta.change(close)") == 2
    original = execute_pine(source, frame, {}, "1h")
    adapted = execute_pine(result.strategy_source, frame, {}, "1h")
    assert [item.value for item in adapted.signal_trace] == [
        item.value for item in original.signal_trace
    ]
    comparison = _compare(source, bindings, frame)
    assert comparison["status"] == "exact_match", comparison
    assert comparison["app_trades"] == comparison["ledger_trades"]
    json.dumps(comparison)


def test_temporaries_capture_value_before_original_reassignment() -> None:
    source = """//@version=5
indicator("Snapshot")
buy = bar_index == 0
sell = bar_index == 3
plotshape(buy, "B")
buy := false
plotshape(sell, "S")
sell := false
"""
    result = _compare(source, _bindings((5, "long"), (7, "short")), _frame())
    assert result["status"] == "exact_match", result
    assert result["app_trades"][0]["pnl"] == "0"


def test_reversed_bindings_and_duplicate_direction_markers_do_not_duplicate_fills() -> None:
    source = """//@version=4
study("Several markers", resolution="")
plotshape(bar_index == 0, "Buy")
plotshape(bar_index <= 1, "Also buy")
plotshape(bar_index == 3, "Sell")
"""
    bindings = _bindings((5, "short"), (4, "long"), (3, "long"))
    adapted = adapt_strategy(source, bindings)
    assert "resolution" not in adapted.strategy_source
    assert any("resolution" in warning for warning in adapted.warnings)
    result = _compare(source, bindings, _frame())
    assert result["status"] == "exact_match", result
    assert len(result["app_trades"]) == 2
    assert all(trade["qty"] == "1" for trade in result["app_trades"])


@pytest.mark.parametrize("version", [2, 3, 4, 5, 6])
def test_original_version_direction_and_timeframe_contract(version: int) -> None:
    declaration = "study" if version < 5 else "indicator"
    source = f"""//@version={version}
{declaration}("Versions")
plotchar(bar_index == 0, "B", "↑")
plotchar(bar_index == 2, "S", "↓")
"""
    result = _compare(source, _bindings((3, "long"), (4, "short"), function="plotchar"), _frame())
    assert result["status"] == "exact_match", result


@pytest.mark.parametrize(
    ("source", "bindings", "code"),
    [
        (
            'indicator("X")\nplotshape(true)\n',
            [{"function": "plotshape", "line": 2}],
            "unsupported_signal_binding",
        ),
        (
            'indicator("X")\nplotshape(series=true)\n',
            _bindings((2, "long")),
            "named_first_condition",
        ),
        (
            'indicator("X")\nif true\n    plotshape(true)\n',
            _bindings((3, "long")),
            "signal_scope_or_position",
        ),
        (
            'indicator("X")\nplotshape(input.bool(true))\n',
            _bindings((2, "long")),
            "unsupported_condition_call",
        ),
        (
            'indicator("X")\nf(x) => x\nplotshape(f(close))\n',
            _bindings((3, "long")),
            "unsupported_condition_call",
        ),
        (
            'indicator("X")\nplotshape(true, text=str.tostring(ta.change(close)))\n',
            _bindings((2, "long")),
            "dynamic_signal_arguments",
        ),
        (
            'study("X", resolution="D")\nplotshape(true)\n',
            _bindings((2, "long")),
            "non_chart_timeframe",
        ),
        ('strategy("X")\nplotshape(true)\n', _bindings((2, "long")), "unsupported_declaration"),
    ],
)
def test_unsupported_paths_fail_explicitly(source: str, bindings: list[dict], code: str) -> None:
    with pytest.raises(StrategyAdapterError) as raised:
        adapt_strategy(source, bindings)
    assert raised.value.code == code


def test_both_paths_keep_warmup_positions_before_report_window() -> None:
    source = """//@version=5
indicator("Warmup")
alertcondition(bar_index == 0, "B")
alertcondition(bar_index == 5, "S")
"""
    frame = _frame()
    result = _compare(
        source,
        _bindings((3, "long"), (4, "short"), function="alertcondition"),
        frame,
        window_start=frame.index[3],
        window_end=frame.index[-1] + pd.Timedelta(hours=1),
    )
    assert result["status"] == "exact_match", result
    assert result["execution_policy"] == "whole_frame_both_paths"
    assert result["app_trades"][0]["entry_time"] == frame.index[1].isoformat()
    assert result["app_trades"][0]["entry_time"] < result["report_window"]["start"]
    assert result["pending_queue_compared"] is False


@pytest.mark.parametrize(
    ("condition", "status"), [("false", "no_signal"), ("bar_index == 7", "no_fills")]
)
def test_no_fills_cannot_be_reported_as_exact(condition: str, status: str) -> None:
    source = f'indicator("No fills")\nplotshape({condition})\n'
    result = _compare(source, _bindings((2, "long")), _frame())
    assert result["status"] == status, result


def test_conflicting_oracle_events_do_not_prevent_real_app_execution() -> None:
    source = 'indicator("Conflict")\nplotshape(true)\nplotshape(true)\n'
    result = _compare(source, _bindings((2, "long"), (3, "short")), _frame())
    assert result["status"] == "invalid_signal_ledger"
    assert "충돌" in result["detail"]
    assert result["executed"] is True
    assert result["app_status"] == "ok"
    assert result["app_trades"]


def test_missing_oracle_still_runs_app_without_claiming_parity() -> None:
    converted = adapt_strategy(
        'indicator("X")\nplotshape(bar_index == 0)\n', _bindings((2, "long"))
    )
    result = compare_app_backtest(converted.strategy_source, _frame(), {}, "1h", None)
    assert result["status"] == "missing_signal_ledger"
    assert result["executed"] is True
    assert result["app_status"] == "ok"
    assert len(result["app_trades"]) == 1


def test_wrong_signal_events_are_reported_as_real_app_mismatch() -> None:
    converted = adapt_strategy(
        'indicator("X")\nplotshape(bar_index == 0)\n', _bindings((2, "long"))
    )
    result = compare_app_backtest(converted.strategy_source, _frame(), {}, "1h", [])
    assert result["status"] == "mismatch", result
    assert result["differences"][0]["field"] == "trade_count"


@pytest.mark.parametrize(
    "header",
    [
        'indicator("Display", "Short", overlay=true, linktoseries=true, max_labels_count=500)',
        'indicator("Display", max_lines_count=1)',
        'indicator("Display", shorttitle="Short", max_lines_count=500, max_labels_count=500)',
    ],
)
def test_display_only_declaration_options_allow_actual_app_execution(header: str) -> None:
    source = f"//@version=5\n{header}\nplotshape(bar_index == 0)\nplotshape(bar_index == 3)\n"
    result = _compare(source, _bindings((3, "long"), (4, "short")), _frame())
    assert result["status"] == "exact_match", result


@pytest.mark.parametrize(
    "option", ['timeframe="D"', "timeframe_gaps=true", "resolution_gaps=false"]
)
def test_execution_declaration_options_remain_explicitly_unsupported(option: str) -> None:
    with pytest.raises(StrategyAdapterError):
        adapt_strategy(f'indicator("X", {option})\nplotshape(true)\n', _bindings((2, "long")))


def test_explicit_exits_precede_entries_and_preserve_captured_conditions() -> None:
    source = """//@version=5
indicator("Exits")
buy = bar_index == 0 or bar_index == 2 or bar_index == 5
plotshape(buy)
buy := false
plotshape(bar_index == 2 or bar_index == 3)
plotshape(bar_index == 3)
plotshape(bar_index == 5 or bar_index == 6)
"""
    bindings = _bindings((4, "long"), (6, "long_exit"), (7, "short"), (8, "short_exit"))
    result = _compare(source, bindings, _frame())
    assert result["status"] == "exact_match", result
    assert [trade["direction"] for trade in result["app_trades"]] == [
        "long",
        "long",
        "short",
        "long",
    ]
    assert len(result["app_trades"]) == 4


def test_exit_while_flat_does_not_close_new_entry_and_warmup_is_guarded() -> None:
    source = """//@version=5
indicator("Exit first")
plotshape(bar_index == 0 or bar_index == 3)
plotshape(bar_index == 0 or bar_index == 5)
"""
    bindings = _bindings((3, "long"), (4, "long_exit"))
    result = _compare(source, bindings, _frame())
    assert result["status"] == "exact_match", result
    converted = adapt_strategy(source, bindings, trade_start=_frame().index[2])
    guarded = compare_app_backtest(converted.strategy_source, _frame(), {}, "1h", None)
    assert len(guarded["app_trades"]) == 1
    assert guarded["app_trades"][0]["entry_time"] == _frame().index[4].isoformat()
