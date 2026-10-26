"""원본 Pine UI 캡처의 plot 순서, 입력, 봉 사건 출처를 검증한다."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime

import pytest

from scripts.pine_validation.native_capture import (
    _plot_bindings,
    _source_calls,
    parse_native_capture,
)

SOURCE = """//@version=5
indicator("demo")
length = input.int(2, title="Length")
buy = close > open
alertcondition(buy, title="Buy", message="B")
plot(close, title="Line")
plotshape(buy ? close : na, title="Marks", text="BUY")
"""
BINDINGS = [
    {"function": "alertcondition", "line": 5, "column": 0, "direction": "long", "when": "truthy"}
]
T0 = 1_766_620_800  # 2025-12-24 00:00 UTC, 1h grid


def _frame(message: dict) -> str:
    encoded = json.dumps(message, separators=(",", ":"))
    return f"~m~{len(encoded)}~m~{encoded}"


def _payload(*, price_method: str = "du") -> dict:
    metadata = {
        "stats": {"alertcondition": 1, "plot": 1, "plotshape": 1},
        "inputs": [
            {"id": "text", "defval": "compiled-il"},
            {"id": "in_0", "name": "Length", "defval": 2},
        ],
        "plots": [
            {"id": "plot_0", "type": "alertcondition"},
            {"id": "plot_1", "type": "line"},
            {"id": "plot_2", "type": "shapes"},
        ],
        "styles": {
            "plot_0": {"title": "Buy", "text": "B"},
            "plot_1": {"title": "Line"},
            "plot_2": {"title": "Marks", "text": "BUY"},
        },
    }
    create = {
        "m": "create_study",
        "p": ["cs", "study", "st1", "chart", "script", {"text": "compiled-il", "in_0": {"v": 2}}],
    }
    complete = {"m": "study_completed", "p": ["cs", "study", "s2_st1"]}
    study = {
        "m": "du",
        "p": [
            "cs",
            {
                "study": {
                    "st": [
                        {"i": 0, "v": [T0, 1, 101, 100]},
                        {"i": 1, "v": [T0 + 3600, 0, 102, 1e100]},
                    ]
                }
            },
        ],
    }
    prices = {
        "m": price_method,
        "p": [
            "cs",
            {
                "chart": {
                    "s": [
                        {"i": 0, "v": [T0, 100, 102, 99, 101, 10]},
                        {"i": 1, "v": [T0 + 3600, 101, 103, 100, 102, 11]},
                    ]
                }
            },
        ],
    }
    return {
        "id": "example",
        "symbol": "BYBIT:BTCUSDT.P",
        "timeframe": "1h",
        "observed_at": datetime.fromtimestamp(T0 + 7200, UTC).isoformat(),
        "source_sha256": hashlib.sha256(SOURCE.encode()).hexdigest(),
        "compiled_source": SOURCE,
        "compile_request_source": SOURCE,
        "inputs": {},
        "resolved_inputs": {"length": 2},
        "compile_responses": [
            {
                "data": {
                    "success": True,
                    "result": {"ilTemplate": "compiled-il", "metaInfo": metadata},
                }
            }
        ],
        "wire": [
            {"direction": "sent", "data": _frame(create)},
            {"direction": "received", "data": _frame(complete) + _frame(study) + _frame(prices)},
        ],
    }


def _parse(payload: dict, *, source: str = SOURCE, bindings: list[dict] = BINDINGS):
    return parse_native_capture(
        payload,
        source=source.encode(),
        signal_bindings=bindings,
        expected_indicator_id="example",
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs={},
    )


def test_compiled_source_plot_order_and_common_confirmed_ohlcv_produce_one_event() -> None:
    result = _parse(_payload())
    assert len(result.events) == 1
    assert result.events[0].direction == "long"
    assert result.events[0].source_line == 5
    assert result.metadata["common_bars"] == 2
    assert result.ohlcv["close"].tolist() == [101, 102]
    assert (
        result.window_events(
            datetime.fromtimestamp(T0, UTC), datetime.fromtimestamp(T0 + 7200, UTC)
        )
        == result.events
    )


def test_chart_history_timescale_update_supplies_ohlcv() -> None:
    result = _parse(_payload(price_method="timescale_update"))
    assert len(result.events) == 1
    assert result.ohlcv["volume"].tolist() == [10, 11]


def test_explicit_chart_history_reset_discards_prior_timeframe_rows_only() -> None:
    payload = _payload(price_method="timescale_update")
    stale = {
        "m": "du",
        "p": ["cs", {"chart": {"s": [{"i": 0, "v": [T0 + 1800, 100, 101, 99, 100, 1]}]}}],
    }
    reset = {"m": "timescale_update", "p": ["cs", {"chart": {"s": []}}]}
    payload["wire"][1:1] = [
        {"direction": "received", "data": _frame(stale)},
        {"direction": "received", "data": _frame(reset)},
    ]
    assert len(_parse(payload).ohlcv) == 2

    payload["wire"][1], payload["wire"][2] = payload["wire"][2], payload["wire"][1]
    with pytest.raises(ValueError, match="격자"):
        _parse(payload)


def test_decoded_timescale_update_from_sanitized_chart_history_is_accepted() -> None:
    payload = _payload()
    payload["wire"][1]["data"] = "~m~".join(payload["wire"][1]["data"].split("~m~")[:5])
    payload["wire"].append(
        {
            "direction": "received",
            "m": "timescale_update",
            "p": [
                "cs",
                {
                    "chart": {
                        "s": [
                            {"i": 0, "v": [T0, 100, 102, 99, 101, 10]},
                            {"i": 1, "v": [T0 + 3600, 101, 103, 100, 102, 11]},
                        ]
                    }
                },
            ],
        }
    )
    assert len(_parse(payload).ohlcv) == 2


def test_assigned_plot_positional_title_and_builtin_source_default() -> None:
    source = SOURCE.replace(
        'length = input.int(2, title="Length")', 'src = input.source(hl2, "Source")'
    ).replace('plot(close, title="Line")', 'lineHandle = plot(close, "Line")')
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
        resolved_inputs={"src": "hl2"},
    )
    payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1].update(
        name="Source", defval="hl2", type="source"
    )
    create = {
        "m": "create_study",
        "p": [
            "cs",
            "study",
            "st1",
            "chart",
            "script",
            {"text": "compiled-il", "in_0": {"v": "hl2"}},
        ],
    }
    payload["wire"][0]["data"] = _frame(create)
    assert len(_parse(payload, source=source).events) == 1


def test_positional_scalar_input_title_and_implicit_truthy_binding() -> None:
    source = SOURCE.replace(
        'length = input.int(2, title="Length")', 'start = input.float(0.02, "Start")'
    )
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
        resolved_inputs={"start": 0.02},
    )
    payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1].update(
        name="Start", defval=0.02, type="float"
    )
    create = {
        "m": "create_study",
        "p": [
            "cs",
            "study",
            "st1",
            "chart",
            "script",
            {"text": "compiled-il", "in_0": {"v": 0.02}},
        ],
    }
    payload["wire"][0]["data"] = _frame(create)
    binding = [{"function": "alertcondition", "line": 5, "column": 0, "direction": "long"}]
    assert len(_parse(payload, source=source, bindings=binding).events) == 1


def test_psar_fill_colorer_requires_matching_global_fill_call() -> None:
    source = SOURCE.replace('plot(close, title="Line")', 'lineHandle = plot(close, title="Line")')
    source += 'fill(lineHandle, lineHandle, title="Trade State Filling", color=color.red)\n'
    calls, _, fills = _source_calls(source)
    payload = _payload()
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["plots"].append({"id": "plot_3", "type": "colorer", "target": "fill_0"})
    assert _plot_bindings(calls, meta["plots"], meta["styles"], BINDINGS, fills) == [(1, "long", 5)]
    with pytest.raises(ValueError, match="colorer"):
        _plot_bindings(*(_source_calls(SOURCE)[0], meta["plots"], meta["styles"], BINDINGS, []))


@pytest.mark.parametrize(
    "change,pattern",
    [
        (lambda p: p.update(source_sha256="wrong"), "hash"),
        (lambda p: p.update(compile_request_source=SOURCE + "\n"), "compile 소스"),
        (lambda p: p.update(resolved_inputs={"length": 3}), "입력"),
        (
            lambda p: p["compile_responses"][0]["data"]["result"]["metaInfo"]["styles"][
                "plot_0"
            ].update(title="Sell"),
            "title",
        ),
        (
            lambda p: p["compile_responses"][0]["data"]["result"]["metaInfo"]["plots"][0].update(
                type="line"
            ),
            "유형",
        ),
        (lambda p: p["wire"].pop(), "cohort 완료"),
    ],
)
def test_unverified_capture_does_not_produce_events(change, pattern: str) -> None:
    payload = copy.deepcopy(_payload())
    change(payload)
    with pytest.raises(ValueError, match=pattern):
        _parse(payload)


def test_conflicting_closed_study_duplicate_is_rejected() -> None:
    payload = _payload()
    conflict = {"m": "du", "p": ["cs", {"study": {"st": [{"i": 0, "v": [T0, 0, 101, 1e100]}]}}]}
    payload["wire"].append({"direction": "received", "data": _frame(conflict)})
    with pytest.raises(ValueError, match="충돌하는 중복"):
        _parse(payload)


def test_missing_ohlcv_does_not_allow_event_output() -> None:
    payload = _payload()
    payload["wire"][1]["data"] = "~m~".join(payload["wire"][1]["data"].split("~m~")[:5])
    with pytest.raises(ValueError, match="공통 확정"):
        _parse(payload)


def test_plotshape_sentinel_and_zero_do_not_fire() -> None:
    payload = _payload()
    result = parse_native_capture(
        payload,
        source=SOURCE.encode(),
        signal_bindings=[
            {"function": "plotshape", "line": 7, "column": 0, "direction": "long", "when": "truthy"}
        ],
        expected_indicator_id="example",
        expected_symbol="BYBIT:BTCUSDT.P",
        expected_timeframe="1h",
        expected_inputs={},
    )
    assert [event.bar_time.timestamp() for event in result.events] == [T0]


def _color_payload(name: str, hex_value: str, wire_value: int) -> tuple[str, dict]:
    source = SOURCE.replace("//@version=5", "//@version=6").replace(
        'length = input.int(2, title="Length")',
        f'col = input.color(color.{name}, title="Color")',
    )
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
        resolved_inputs={"col": hex_value},
    )
    payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1].update(
        name="Color", defval=hex_value, type="color"
    )
    payload["wire"][0]["data"] = _frame(
        {
            "m": "create_study",
            "p": [
                "cs",
                "study",
                "st1",
                "chart",
                "script",
                {
                    "text": "compiled-il",
                    "in_0": {"v": wire_value, "t": "color"},
                },
            ],
        }
    )
    return source, payload


@pytest.mark.parametrize(
    "name,hex_value,wire_value",
    [
        # so4mWdrN 무수정 v6 원문의 실제 compiler defval/create_study 관측.
        ("green", "#4CAF50", 4283477836),
        ("yellow", "#FDD835", 4281719037),
        ("red", "#F23645", 4282726130),
        ("aqua", "#00BCD4", 4292131840),
    ],
)
def test_observed_v6_color_input_binds_hex_compiler_default_to_unsigned_abgr(
    name: str, hex_value: str, wire_value: int
) -> None:
    source, payload = _color_payload(name, hex_value, wire_value)
    result = _parse(payload, source=source)
    assert len(result.events) == 1
    assert result.metadata["resolved_inputs"] == {"col": hex_value}


@pytest.mark.parametrize(
    "wire_value,wire_type",
    [
        (4283477837, "color"),
        (-16732340, "color"),
        (4283477836.0, "color"),
        ("#4CAF50", "color"),
        (4283477836, "integer"),
    ],
)
def test_color_input_wire_value_and_type_must_match_actual_observation(wire_value, wire_type):
    source, payload = _color_payload("green", "#4CAF50", 4283477836)
    message = json.loads(payload["wire"][0]["data"].split("~m~", 2)[2])
    message["p"][5]["in_0"].update(v=wire_value, t=wire_type)
    payload["wire"][0]["data"] = _frame(message)
    with pytest.raises(ValueError, match="create_study 실제 입력"):
        _parse(payload, source=source)


@pytest.mark.parametrize(
    "change", ["compiler_color", "compiler_type", "unobserved_version", "unobserved_color"]
)
def test_unverified_color_semantics_are_rejected(change: str):
    source, payload = _color_payload("green", "#4CAF50", 4283477836)
    slot = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["inputs"][1]
    if change == "compiler_color":
        slot["defval"] = "#F23645"
    elif change == "compiler_type":
        slot["type"] = "text"
    else:
        source = (
            source.replace("//@version=6", "//@version=5")
            if change == "unobserved_version"
            else source.replace("color.green", "color.black")
        )
        payload.update(
            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            compiled_source=source,
            compile_request_source=source,
        )
    with pytest.raises(ValueError, match=r"입력|input\.color"):
        _parse(payload, source=source)


def test_observed_dynamic_line_and_three_fill_columns_preserve_signal_column():
    source, payload = _color_payload("green", "#4CAF50", 4283477836)
    source = source.replace('plot(close, title="Line")', 'p = plot(close, title="Line", color=col)')
    source += "\n".join(f'fill(p, p, color=col, title="Fill {i}")' for i in range(3)) + "\n"
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["plots"] = [
        *meta["plots"][:2],
        {"id": "plot_2", "type": "colorer", "target": "plot_1"},
        *({"id": f"plot_{i + 3}", "type": "colorer", "target": f"fill_{i}"} for i in range(3)),
        {"id": "plot_6", "type": "shapes"},
    ]
    meta["styles"]["plot_6"] = meta["styles"].pop("plot_2")
    messages = []
    for message in payload["wire"][1]["data"].split("~m~"):
        if message.startswith("{"):
            decoded = json.loads(message)
            if decoded["m"] == "du" and "study" in decoded["p"][1]:
                for row in decoded["p"][1]["study"]["st"]:
                    row["v"][3:3] = [0] * 4
            messages.append(_frame(decoded))
    payload["wire"][1]["data"] = "".join(messages)
    result = _parse(payload, source=source)
    assert result.observations.columns.tolist() == [f"plot_{i}" for i in range(7)]
    assert [event.bar_time.timestamp() for event in result.events] == [T0]
