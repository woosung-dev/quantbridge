"""UI에서 수집한 원본 Pine의 컴파일·study·OHLCV 캡처를 검증한다.

출처가 부족하거나 플롯과 원문 호출의 대응이 모호하면 사건을 반환하지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from typing import Any

import pandas as pd
from pynescript import ast as A

from scripts.pine_validation.models import SignalEvent, utc_time
from src.strategy.pine_v2.parser_adapter import parse_to_ast

_STEPS = {"1h": timedelta(hours=1), "4h": timedelta(hours=4), "1d": timedelta(days=1)}
_SIGNAL_CALLS = {"plotshape", "plotchar", "alertcondition"}
_PLOT_CALLS = _SIGNAL_CALLS | {"plot", "barcolor"}
_SOURCE_NAMES = {"open", "high", "low", "close", "hl2", "hlc3", "ohlc4"}
_PLOT_TYPES = {
    "alertcondition": "alertcondition",
    "plot": "line",
    "plotshape": "shapes",
    "plotchar": "chars",
    "barcolor": "bar_colorer",
}
_FRAME = re.compile(r"~m~(\d+)~m~")
_SENTINEL = 1e100


@dataclass(frozen=True)
class NativeCapture:
    observations: pd.DataFrame
    ohlcv: pd.DataFrame
    events: list[SignalEvent]
    metadata: dict[str, Any]

    def window_events(self, start: str | datetime, end: str | datetime) -> list[SignalEvent]:
        start, end = utc_time(start), utc_time(end)
        step = _STEPS[self.metadata["timeframe"]]
        if (
            start >= end
            or start.timestamp() % step.total_seconds()
            or end.timestamp() % step.total_seconds()
        ):
            raise ValueError("비교창은 타임프레임 격자에 맞는 [시작, 종료)여야 합니다")
        if end > utc_time(self.metadata["observed_at"]):
            raise ValueError("미확정 봉은 비교할 수 없습니다")
        expected = pd.date_range(start, end, freq=step, inclusive="left")
        if (
            not expected.difference(self.observations.index).empty
            or not expected.difference(self.ohlcv.index).empty
        ):
            raise ValueError("비교창에 native study 또는 OHLCV 확정 봉이 누락됐습니다")
        return [event for event in self.events if start <= event.bar_time < end]


def _name(node: Any) -> str:
    if isinstance(node, A.Name):
        return node.id
    if isinstance(node, A.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    return ""


def _arg(call: A.Call, name: str, position: int | None = None) -> Any:
    for argument in call.args:
        if argument.name == name:
            return argument.value
    if position is not None:
        positional = [argument.value for argument in call.args if argument.name is None]
        if len(positional) > position:
            return positional[position]
    return None


def _literal(node: Any, label: str) -> Any:
    if not isinstance(node, A.Constant) or type(node.value) not in (str, int, float, bool):
        raise ValueError(f"{label}: 원문의 정적 리터럴만 검증할 수 있습니다")
    return node.value


def _source_calls(
    source: str,
) -> tuple[list[tuple[str, A.Call]], list[tuple[str, str, Any]], list[A.Call]]:
    try:
        tree = parse_to_ast(source)
    except Exception as exc:
        raise ValueError("원본 Pine AST를 해석할 수 없습니다") from exc
    top = []
    fills = []
    for statement in tree.body:
        if isinstance(statement, A.Expr) or (
            isinstance(statement, A.Assign) and isinstance(statement.target, A.Name)
        ):
            call = statement.value
        else:
            continue
        if isinstance(call, A.Call) and _name(call.func) in _PLOT_CALLS:
            top.append(call)
        elif isinstance(call, A.Call) and _name(call.func) == "fill":
            fills.append(call)
    all_calls = [
        node
        for node in A.walk(tree)
        if isinstance(node, A.Call) and _name(node.func) in _PLOT_CALLS
    ]
    if len(top) != len(all_calls) or {id(node) for node in top} != {id(node) for node in all_calls}:
        raise ValueError("로컬·동적 plot/alert 호출은 native 열에 고정할 수 없습니다")
    all_fills = [
        node for node in A.walk(tree) if isinstance(node, A.Call) and _name(node.func) == "fill"
    ]
    if {id(node) for node in fills} != {id(node) for node in all_fills}:
        raise ValueError("로컬·동적 fill 호출은 native 열에 고정할 수 없습니다")
    calls = [(_name(call.func), call) for call in top]
    inputs: list[tuple[str, str, Any]] = []
    for statement in tree.body:
        if not isinstance(statement, A.Assign) or not isinstance(statement.target, A.Name):
            continue
        call = statement.value
        # 관측한 퍼센트 입력은 slot의 원시 기본값을 비교하며 /100 결과를 평가하지 않는다.
        if (
            isinstance(call, A.BinOp)
            and isinstance(call.op, A.Div)
            and isinstance(call.right, A.Constant)
            and type(call.right.value) is int
            and call.right.value == 100
            and isinstance(call.left, A.Call)
            and _name(call.left.func) in {"input", "input.float"}
            and isinstance(_arg(call.left, "defval", 0), A.Constant)
            and type(_arg(call.left, "defval", 0).value) in (int, float)
        ):
            call = call.left
        if not isinstance(call, A.Call) or _name(call.func) not in {
            "input",
            "input.int",
            "input.float",
            "input.bool",
            "input.source",
        }:
            continue
        default_node = _arg(call, "defval", 0)
        source_input = _name(call.func) == "input.source" or (
            _name(call.func) == "input"
            and (_arg(call, "type", 2) is None or _name(_arg(call, "type", 2)) == "input.source")
        )
        if source_input and isinstance(default_node, A.Name):
            if default_node.id not in _SOURCE_NAMES:
                raise ValueError("input.source 기본값은 확인한 OHLCV source만 허용합니다")
            default = default_node.id
        else:
            default = _literal(default_node, "input defval")
        title_node = _arg(call, "title", 1)
        title = (
            _literal(title_node, "input title") if title_node is not None else statement.target.id
        )
        inputs.append((statement.target.id, title, default))
    return calls, inputs, fills


def _empty_chart_resolution(source: str) -> str | None:
    declarations = [
        statement.value
        for statement in parse_to_ast(source).body
        if isinstance(statement, A.Expr)
        and isinstance(statement.value, A.Call)
        and _name(statement.value.func) in {"study", "indicator", "strategy"}
    ]
    if len(declarations) != 1:
        return None
    kind = _name(declarations[0].func)
    if kind not in {"study", "indicator"}:
        return None
    value = _arg(declarations[0], "resolution" if kind == "study" else "timeframe")
    return (
        kind
        if isinstance(value, A.Constant) and type(value.value) is str and value.value == ""
        else None
    )


def _frames(data: str) -> list[dict[str, Any]]:
    if not isinstance(data, str):
        raise ValueError("wire data 형식이 잘못됐습니다")
    messages = []
    position = 0
    while position < len(data):
        match = _FRAME.match(data, position)
        if match is None:
            if data.startswith("~h~", position):
                break  # TradingView heartbeat에는 study 값이 없다.
            raise ValueError("wire frame 길이 또는 경계가 잘못됐습니다")
        length = int(match.group(1))
        end = match.end() + length
        if end > len(data):
            raise ValueError("wire frame이 잘렸습니다")
        raw = data[match.end() : end]
        if raw.startswith("~h~"):
            position = end
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("wire JSON이 잘못됐습니다") from exc
        if not isinstance(message, dict):
            raise ValueError("wire message는 객체여야 합니다")
        messages.append(message)
        position = end
    return messages


def _epoch(value: Any, step: timedelta) -> datetime:
    if type(value) not in (int, float) or not math.isfinite(value) or int(value) != value:
        raise ValueError("봉 시각은 정수 epoch 초여야 합니다")
    if value % step.total_seconds():
        raise ValueError("봉 시각이 타임프레임 격자와 다릅니다")
    try:
        return datetime.fromtimestamp(value, UTC)
    except (OSError, OverflowError, ValueError) as exc:
        raise ValueError("봉 시각이 날짜 범위를 벗어났습니다") from exc


def _numeric(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _input_equal(actual: Any, expected: Any, kind: str) -> bool:
    if kind == "float":
        return _numeric(actual) and _numeric(expected) and actual == expected
    return type(actual) is type(expected) and actual == expected


def _plot_bindings(
    calls: list[tuple[str, A.Call]],
    plots: Any,
    styles: Any,
    reviewed: Sequence[Mapping[str, Any]],
    fills: Sequence[A.Call],
) -> list[tuple[int, str, int]]:
    if (
        not isinstance(plots, list)
        or any(not isinstance(plot, dict) for plot in plots)
        or not isinstance(styles, dict)
    ):
        raise ValueError("컴파일 plot 메타데이터가 없습니다")
    if [plot.get("id") for plot in plots] != [f"plot_{i}" for i in range(len(plots))]:
        raise ValueError("컴파일 plot id 순서가 연속적이지 않습니다")
    visible = [(index, plot) for index, plot in enumerate(plots) if plot.get("type") != "colorer"]
    if len(visible) != len(calls):
        raise ValueError("원문 전역 plot/alert 호출 수와 컴파일 plot 수가 다릅니다")
    fill_colorer_targets = []
    for index, plot in enumerate(plots):
        if plot["type"] != "colorer":
            continue
        target = plot.get("target")
        if isinstance(target, str) and target.startswith("fill_"):
            fill_colorer_targets.append(target)
        elif (
            index == 0
            or target != f"plot_{index - 1}"
            or plots[index - 1].get("type") not in {"line", "shapes"}
        ):
            raise ValueError("컴파일 colorer가 앞선 line/shapes plot에 결합되지 않았습니다")
    if fill_colorer_targets != [f"fill_{index}" for index in range(len(fills))]:
        raise ValueError("컴파일 fill colorer와 원문 전역 fill 호출이 다릅니다")
    for (kind, call), (index, plot) in zip(calls, visible, strict=True):
        if plot.get("type") != _PLOT_TYPES[kind]:
            raise ValueError("원문 호출 유형과 컴파일 plot 유형이 다릅니다")
        style = styles.get(f"plot_{index}")
        if not isinstance(style, dict):
            raise ValueError("컴파일 plot 스타일이 없습니다")
        title_node = _arg(call, "title", None if kind == "barcolor" else 1)
        if kind == "barcolor" and title_node is not None:
            raise ValueError("barcolor는 관측한 기본 제목 Bar Color만 허용합니다")
        title = (
            _literal(title_node, "plot title")
            if title_node is not None
            else "Shapes"
            if kind == "plotshape"
            else "Plot"
            if kind == "plot"
            else "Bar Color"
            if kind == "barcolor"
            else None
        )
        if title is None or style.get("title") != title:
            raise ValueError("원문 plot title과 컴파일 스타일 제목이 다릅니다")
        text_node = _arg(call, "message" if kind == "alertcondition" else "text")
        if (
            kind in _SIGNAL_CALLS
            and text_node is not None
            and style.get("text") != _literal(text_node, "signal text")
        ):
            raise ValueError("원문 신호 text와 컴파일 스타일이 다릅니다")
    bound: list[tuple[int, str, int]] = []
    used: set[int] = set()
    directions: set[str] = set()
    for binding in reviewed:
        matches = [
            (index, kind, call)
            for (kind, call), (index, _) in zip(calls, visible, strict=True)
            if kind == binding.get("function")
            and call.lineno == binding.get("line")
            and call.col_offset == binding.get("column")
        ]
        if (
            len(matches) != 1
            or binding.get("direction") not in {"long", "short", "long_exit", "short_exit"}
            or binding.get("when", "truthy") != "truthy"
        ):
            raise ValueError("검토 신호 위치·방향·조건이 원문과 맞지 않습니다")
        index, kind, call = matches[0]
        if index in used or kind not in _SIGNAL_CALLS or binding["direction"] in directions:
            raise ValueError("검토 신호 plot이 중복됐거나 방향 신호가 아닙니다")
        if kind in {"plotshape", "plotchar"}:
            offset = _arg(call, "offset")
            if offset is not None and _literal(offset, "signal offset") != 0:
                raise ValueError("표시 위치가 사건 봉과 다른 신호는 지원하지 않습니다")
        used.add(index)
        directions.add(binding["direction"])
        bound.append((index + 1, binding["direction"], call.lineno))
    if not bound:
        raise ValueError("검토한 방향별 신호 바인딩이 없습니다")
    return bound


def parse_native_capture(
    payload: Mapping[str, Any],
    *,
    source: bytes,
    signal_bindings: Sequence[Mapping[str, Any]],
    expected_indicator_id: str,
    expected_symbol: str,
    expected_timeframe: str,
    expected_inputs: Mapping[str, Any],
) -> NativeCapture:
    """원본과 교차 확인한 확정 common cohort에서만 native 사건을 만든다."""
    if (
        not isinstance(payload, Mapping)
        or payload.get("id") != expected_indicator_id
        or payload.get("symbol") != expected_symbol
        or payload.get("timeframe") != expected_timeframe
    ):
        raise ValueError("native 지표·심볼·타임프레임이 기대값과 다릅니다")
    if expected_timeframe not in _STEPS:
        raise ValueError("지원하지 않는 타임프레임입니다")
    step = _STEPS[expected_timeframe]
    observed_at = utc_time(payload.get("observed_at"))
    digest = hashlib.sha256(source).hexdigest()
    if payload.get("source_sha256") != digest:
        raise ValueError("원본 source hash가 다릅니다")
    try:
        source_text = source.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("원본 소스는 UTF-8이어야 합니다") from exc
    compiled_source, request_source = (
        payload.get("compiled_source"),
        payload.get("compile_request_source"),
    )
    if not isinstance(compiled_source, str) or not isinstance(request_source, str):
        raise ValueError("실제 compiled/editor 소스와 compile request 소스가 필요합니다")

    def normalize(value: str) -> str:
        return value.replace("\r\n", "\n")

    if normalize(source_text) != normalize(compiled_source) or normalize(source_text) != normalize(
        request_source
    ):
        raise ValueError("compile 소스가 무수정 원본과 다릅니다")
    calls, source_inputs, fills = _source_calls(source_text)
    overrides = payload.get("inputs")
    resolved = payload.get("resolved_inputs")
    if (
        not isinstance(overrides, dict)
        or overrides != dict(expected_inputs)
        or not isinstance(resolved, dict)
    ):
        raise ValueError("원본 입력 override 계약 또는 resolved_inputs가 없습니다")
    defaults = {name: default for name, _, default in source_inputs}
    if set(overrides) - set(defaults) or resolved != {**defaults, **overrides}:
        raise ValueError("실제 입력 값이 원본 기본값·override와 다릅니다")
    responses = payload.get("compile_responses")
    if (
        not isinstance(responses, list)
        or len(responses) != 1
        or responses[0].get("data", {}).get("success") is not True
    ):
        raise ValueError("성공한 컴파일 응답 하나가 필요합니다")
    meta = responses[0]["data"].get("result", {}).get("metaInfo")
    if not isinstance(meta, dict) or not isinstance(meta.get("inputs"), list):
        raise ValueError("컴파일 metaInfo가 없습니다")
    # 관측한 compiler stats는 barcolor를 세지 않으므로 실제 plot 열 대응에서 별도로 검사한다.
    counts = {
        kind: sum(call_kind == kind for call_kind, _ in calls)
        for kind in _PLOT_CALLS - {"barcolor"}
    }
    stats = meta.get("stats")
    if not isinstance(stats, dict) or any(
        stats.get(kind, 0) != count for kind, count in counts.items()
    ):
        raise ValueError("컴파일 신호·plot 호출 통계가 원문과 다릅니다")
    compiled_inputs = {item.get("id"): item for item in meta["inputs"] if isinstance(item, dict)}
    for index, (name, title, _) in enumerate(source_inputs):
        item = compiled_inputs.get(f"in_{index}")
        if (
            not isinstance(item, dict)
            or item.get("name") != title
            or not _input_equal(item.get("defval"), resolved[name], item.get("type", ""))
        ):
            raise ValueError("컴파일 입력 기본값·제목이 원문과 다릅니다")
    expected_slots = {f"in_{i}" for i in range(len(source_inputs))}
    resolution_kind = _empty_chart_resolution(source_text)
    resolution_slot = f"in_{len(source_inputs)}" if resolution_kind is not None else None
    if resolution_slot is not None:
        expected_slots.add(resolution_slot)
        slot = compiled_inputs.get(resolution_slot)
        expected_resolution = {
            "id": resolution_slot,
            "name": "Indicator Timeframe" if resolution_kind == "study" else "Timeframe",
            "type": "resolution",
            "isMTFResolution": True,
            "isFake": True,
            "defval": "",
        }
        if resolution_kind == "study":
            expected_resolution["inline"] = "study_mtf"
        else:
            expected_resolution.update(group="Calculation", solutionId=43000591555)
        if (
            slot != expected_resolution
            or slot["isMTFResolution"] is not True
            or slot["isFake"] is not True
            or sum(
                isinstance(item, dict) and item.get("id") == resolution_slot
                for item in meta["inputs"]
            )
            != 1
        ):
            raise ValueError("빈 차트 resolution의 compiler 자동 입력 근거가 다릅니다")
    if {key for key in compiled_inputs if re.fullmatch(r"in_\d+", str(key))} != expected_slots:
        raise ValueError("컴파일 입력 개수가 원문과 다릅니다")
    bound = _plot_bindings(calls, meta.get("plots"), meta.get("styles"), signal_bindings, fills)
    wire = payload.get("wire")
    if not isinstance(wire, list) or not wire:
        raise ValueError("UI wire 관측이 없습니다")
    sent, received = [], []
    for entry in wire:
        if not isinstance(entry, dict) or entry.get("direction") not in {"sent", "received"}:
            raise ValueError("wire 방향이 잘못됐습니다")
        if "data" in entry:
            messages = _frames(entry["data"])
        elif isinstance(entry.get("m"), str) and isinstance(entry.get("p"), list):
            messages = [{"m": entry["m"], "p": entry["p"]}]
        else:
            raise ValueError("wire 메시지 내용이 없습니다")
        for message in messages:
            (sent if entry["direction"] == "sent" else received).append(message)
    creates = [message for message in sent if message.get("m") == "create_study"]
    if len(creates) != 1 or len(creates[0].get("p", [])) < 6:
        raise ValueError("create_study 관측 하나가 필요합니다")
    session, study_id, _, chart_id, _, study_inputs = creates[0]["p"][:6]
    if not all(
        isinstance(value, str) and value for value in (session, study_id, chart_id)
    ) or not isinstance(study_inputs, dict):
        raise ValueError("study cohort가 잘못됐습니다")
    if study_inputs.get("text") != meta["inputs"][0].get("defval") or study_inputs.get(
        "text"
    ) != responses[0]["data"]["result"].get("ilTemplate"):
        raise ValueError("create_study IL과 컴파일 결과가 다릅니다")
    for index, (name, _, _) in enumerate(source_inputs):
        wire_input = study_inputs.get(f"in_{index}")
        if not isinstance(wire_input, dict) or not _input_equal(
            wire_input.get("v"), resolved[name], compiled_inputs[f"in_{index}"].get("type", "")
        ):
            raise ValueError("create_study 실제 입력이 원본 기본값과 다릅니다")
    if {key for key in study_inputs if re.fullmatch(r"in_\d+", str(key))} != expected_slots:
        raise ValueError("create_study 입력 개수가 컴파일 결과와 다릅니다")
    if resolution_slot is not None:
        slot = study_inputs.get(resolution_slot)
        if slot != {"v": "", "f": True, "t": "resolution"} or slot["f"] is not True:
            raise ValueError("create_study resolution은 원문의 빈 차트 주기를 유지해야 합니다")
    completed = [
        m
        for m in received
        if m.get("m") == "study_completed" and m.get("p", [])[:2] == [session, study_id]
    ]
    if len(completed) != 1:
        raise ValueError("해당 study cohort 완료 관측이 없습니다")
    plots = meta["plots"]
    study_rows: dict[datetime, list[Any]] = {}
    price_rows: dict[datetime, list[Any]] = {}
    price_reset_at = max(
        (
            index
            for index, message in enumerate(received)
            if message.get("m") == "timescale_update"
            and len(message.get("p", [])) >= 2
            and message["p"][0] == session
            and isinstance(message["p"][1], dict)
            and isinstance(message["p"][1].get(chart_id), dict)
            and message["p"][1][chart_id].get("s") == []
        ),
        default=-1,
    )
    for index, message in enumerate(received):
        if (
            message.get("m") not in {"du", "timescale_update"}
            or len(message.get("p", [])) < 2
            or message["p"][0] != session
        ):
            continue
        packet = message["p"][1]
        if not isinstance(packet, dict):
            raise ValueError("du cohort 형식이 잘못됐습니다")
        for key, field, target, width in (
            (study_id, "st", study_rows, len(plots) + 1),
            (chart_id, "s", price_rows, 6),
        ):
            if key == chart_id and index < price_reset_at:
                continue
            if key not in packet:
                continue
            rows = packet[key].get(field)
            if not isinstance(rows, list):
                raise ValueError("du 행 배열이 없습니다")
            for row in rows:
                values = row.get("v") if isinstance(row, dict) else None
                if not isinstance(values, list) or len(values) != width:
                    raise ValueError("du 행의 plot/OHLCV 열 수가 다릅니다")
                at = _epoch(values[0], step)
                if at > observed_at:
                    raise ValueError("관측 시각보다 미래인 봉이 있습니다")
                if at in target and target[at] != values and at + step <= observed_at:
                    raise ValueError("확정 봉에 충돌하는 중복 응답이 있습니다")
                target[at] = values
    closed_study = {at: row for at, row in study_rows.items() if at + step <= observed_at}
    closed_price = {at: row for at, row in price_rows.items() if at + step <= observed_at}
    common = sorted(set(closed_study) & set(closed_price))
    if not common or any(current - previous != step for previous, current in pairwise(common)):
        raise ValueError("공통 확정 study/OHLCV 봉이 없거나 시간 격자가 불연속입니다")
    observations, prices, events = [], [], []
    for at in common:
        row = closed_study[at]
        if any(value is not None and not _numeric(value) for value in row[1:]):
            raise ValueError("study plot에 비수치 값이 있습니다")
        price = closed_price[at][1:]
        if not all(_numeric(value) for value in price):
            raise ValueError("OHLCV에 비수치 값이 있습니다")
        open_, high, low, close, volume = price
        if (
            min(open_, high, low, close) <= 0
            or volume < 0
            or high < max(open_, close, low)
            or low > min(open_, close, high)
        ):
            raise ValueError("OHLCV 가격 범위 또는 거래량이 잘못됐습니다")
        active_directions = []
        for column, direction, line in bound:
            value = row[column]
            kind = plots[column - 1]["type"]
            active = (
                value in (1, 1.0)
                if kind == "alertcondition"
                else value is not None and value != 0 and abs(value) < _SENTINEL
            )
            if kind == "alertcondition" and value not in (0, 1):
                raise ValueError("alertcondition은 0/1이어야 합니다")
            if active:
                active_directions.append(direction)
                events.append(SignalEvent(at, direction, at + step, at, line))
        if "long" in active_directions and "short" in active_directions:
            raise ValueError("동일 봉 매수·매도 신호가 충돌합니다")
        observations.append(row[1:])
        prices.append(price)
    index = pd.DatetimeIndex(common, name="time")
    observation_frame = pd.DataFrame(
        observations, columns=[plot["id"] for plot in plots], index=index
    )
    ohlcv = pd.DataFrame(prices, columns=["open", "high", "low", "close", "volume"], index=index)
    return NativeCapture(
        observation_frame,
        ohlcv,
        events,
        {
            "reference_kind": "native_original_partial_window",
            "indicator_id": expected_indicator_id,
            "source_sha256": digest,
            "study_id": study_id,
            "chart_id": chart_id,
            "symbol": expected_symbol,
            "timeframe": expected_timeframe,
            "inputs": overrides,
            "resolved_inputs": resolved,
            "observed_at": observed_at.isoformat(),
            "first_bar": common[0].isoformat(),
            "last_bar": common[-1].isoformat(),
            "common_bars": len(common),
            "study_bars": len(closed_study),
            "ohlcv_bars": len(closed_price),
        },
    )
