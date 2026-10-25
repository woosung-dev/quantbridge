"""UI에서 수집한 원본 Pine의 컴파일·study·OHLCV 캡처를 검증한다.

출처가 부족하거나 플롯과 원문 호출의 대응이 모호하면 사건을 반환하지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Any

import pandas as pd
from pynescript import ast as A

from scripts.pine_validation.models import SignalEvent, utc_time
from src.strategy.pine_v2.interpreter import _ATTR_CONSTANTS, pine_version_from_ast
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.rendering import PineColor, color_call, color_literal, color_named

_STEPS = {"1h": timedelta(hours=1), "4h": timedelta(hours=4), "1d": timedelta(days=1)}
_SIGNAL_CALLS = {"plotshape", "plotchar", "alertcondition"}
_PLOT_CALLS = _SIGNAL_CALLS | {"plot", "barcolor", "bgcolor", "plotcandle", "plotarrow"}
_SOURCE_NAMES = {"open", "high", "low", "close", "volume", "hl2", "hlc3", "ohlc4"}
_INPUT_CALLS = {
    "input",
    "input.int",
    "input.float",
    "input.bool",
    "input.source",
    "input.string",
    "input.color",
}
_INPUT_ENUMS = {name: value for name, value in _ATTR_CONSTANTS.items() if name.startswith("size.")}
_PLOT_TYPES = {
    "alertcondition": "alertcondition",
    "plot": "line",
    "plotshape": "shapes",
    "plotchar": "chars",
    "barcolor": "bar_colorer",
    "bgcolor": "bg_colorer",
    "plotcandle": "ohlc_open",
    "plotarrow": "arrows",
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
        if any(
            start <= utc_time(item["bar_time"]) < end
            for item in self.metadata.get("missing_alertconditions", [])
        ):
            raise ValueError("비교창에 미관측 alertcondition 값이 있습니다")
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


def _input_default(node: Any, label: str) -> Any:
    """입력 슬롯의 부호 리터럴·공식 size 상수만 읽으며 일반 식은 계산하지 않는다."""
    if (
        isinstance(node, A.UnaryOp)
        and isinstance(node.op, (A.UAdd, A.USub))
        and isinstance(node.operand, A.Constant)
        and _numeric(node.operand.value)
    ):
        return -node.operand.value if isinstance(node.op, A.USub) else node.operand.value
    if _name(node) in _INPUT_ENUMS:
        return _INPUT_ENUMS[_name(node)]
    return _literal(node, label)


def _raw_input_call(node: Any) -> A.Call | None:
    """관측한 wrapper의 input 슬롯만 찾고 wrapper의 계산 결과는 만들지 않는다."""
    if isinstance(node, A.Call) and _name(node.func) in _INPUT_CALLS:
        return node
    if (
        isinstance(node, A.Call)
        and len(node.args) == 1
        and node.args[0].name is None
        and isinstance(node.args[0].value, A.Call)
    ):
        inner = node.args[0].value
        if (_name(node.func), _name(inner.func)) in {
            ("nz", "input.source"),
            ("str.tonumber", "input.string"),
        }:
            return inner

    def numeric_input(candidate: Any) -> bool:
        if not isinstance(candidate, A.Call) or _name(candidate.func) not in {
            "input",
            "input.int",
            "input.float",
        }:
            return False
        if _name(_arg(candidate, "type", 2)) == "input.source":
            return False
        default = _arg(candidate, "defval", 0)
        if isinstance(default, A.Constant):
            return _numeric(default.value)
        return (
            isinstance(default, A.UnaryOp)
            and isinstance(default.op, (A.UAdd, A.USub))
            and isinstance(default.operand, A.Constant)
            and _numeric(default.operand.value)
        )

    if isinstance(node, A.BinOp):
        if (
            isinstance(node.op, A.Div)
            and numeric_input(node.left)
            and isinstance(node.right, A.Constant)
            and type(node.right.value) is int
            and node.right.value in {10, 100}
        ):
            return node.left
        if (
            isinstance(node.op, A.Sub)
            and numeric_input(node.right)
            and isinstance(node.left, A.Constant)
            and _numeric(node.left.value)
        ):
            return node.right
    if any(
        isinstance(child, A.Call)
        and (_name(child.func) == "input" or _name(child.func).startswith("input."))
        for child in A.walk(node)
    ):
        raise ValueError("관측하지 않은 input wrapper는 슬롯을 추측해 추출하지 않습니다")
    return None


def _color_default(node: Any, version: int = 6) -> str:
    """관측한 compiler 색 표기만 만들며 채널·버전 의미는 PineColor SSOT를 쓴다."""
    if (
        isinstance(node, A.Constant)
        and node.kind == "#"
        and isinstance(node.value, str)
        and re.fullmatch(r"#[0-9a-fA-F]{8}", node.value)
    ):
        red, green, blue, alpha = [int(node.value[i : i + 2], 16) for i in (1, 3, 5, 7)]
        opacity = str(alpha / 255).removesuffix(".0")
        return f"rgba({red},{green},{blue},{opacity})"
    if (
        isinstance(node, A.Constant)
        and node.kind == "#"
        and isinstance(node.value, str)
        and re.fullmatch(r"#[0-9a-fA-F]{6}", node.value)
    ):
        return node.value
    if isinstance(node, A.Attribute) and _name(node) == f"color.{node.attr}":
        color = color_named(node.attr, version)
        return f"#{color.red:02X}{color.green:02X}{color.blue:02X}"
    if (
        isinstance(node, A.Call)
        and _name(node.func) == "color.new"
        and len(node.args) == 2
        and all(arg.name is None for arg in node.args)
    ):
        base, transparency = [arg.value for arg in node.args]
        if (
            isinstance(base, A.Constant)
            and base.kind == "#"
            and isinstance(base.value, str)
            and re.fullmatch(r"#[0-9a-fA-F]{6}", base.value)
            and isinstance(transparency, A.Constant)
            and type(transparency.value) in (int, float)
            and transparency.value == 0
        ):
            red, green, blue = [int(base.value[i : i + 2], 16) for i in (1, 3, 5)]
            return f"rgba({red},{green},{blue},1)"
        if (
            isinstance(base, A.Attribute)
            and _name(base) == f"color.{base.attr}"
            and isinstance(transparency, A.Constant)
            and type(transparency.value) is int
            and 0 <= transparency.value <= 100
        ):
            color = color_call(
                "color.new",
                {"color": color_named(base.attr, version), "transp": transparency.value},
                version,
            )
            opacity = str(color.alpha).removesuffix(".0")
            return f"rgba({color.red},{color.green},{color.blue},{opacity})"
    raise ValueError("input.color: 관측하지 않은 색 또는 동적 기본값입니다")


def _wire_color(value: Any) -> int:
    if not isinstance(value, str):
        raise ValueError("color 입력은 검증한 색 문자열이어야 합니다")
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        red, green, blue = [int(value[i : i + 2], 16) for i in (1, 3, 5)]
        alpha = 255
    else:
        match = re.fullmatch(r"rgba\((\d+),(\d+),(\d+),(0(?:\.\d+)?|1(?:\.0+)?)\)", value)
        if match is None:
            raise ValueError("color 입력의 wire 변환 근거가 없습니다")
        red, green, blue = map(int, match.groups()[:3])
        alpha = round(float(match[4]) * 255)
        if max(red, green, blue) > 255:
            raise ValueError("color 채널이 범위 밖입니다")
    # 실제 create_study의 color는 alpha byte를 포함한 unsigned ABGR이다.
    return (alpha << 24) | (blue << 16) | (green << 8) | red


def _source_calls(
    source: str,
    *,
    input_types: dict[str, str] | None = None,
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
    version = pine_version_from_ast(tree)
    constants = _readonly_globals(source)
    for statement in tree.body:
        if not isinstance(statement, A.Assign) or not isinstance(statement.target, A.Name):
            continue
        call = _raw_input_call(statement.value)
        if call is None:
            continue
        default_node = _arg(call, "defval", 0)
        source_input = _name(call.func) == "input.source" or (
            _name(call.func) == "input"
            and (_arg(call, "type", 2) is None or _name(_arg(call, "type", 2)) == "input.source")
        )
        generic_color = (
            constants.get(default_node.id)
            if isinstance(default_node, A.Name)
            and _name(call.func) == "input"
            and (_arg(call, "type", 2) is None or _name(_arg(call, "type", 2)) == "input.color")
            else None
        )
        if (
            isinstance(generic_color, A.Constant) and generic_color.kind == "#"
        ) or (
            isinstance(generic_color, A.Attribute)
            and _name(generic_color) == f"color.{generic_color.attr}"
        ):
            default = _color_default(generic_color, version)
            if input_types is not None:
                input_types[statement.target.id] = "color"
        elif _name(call.func) == "input.color":
            default = _color_default(default_node, version)
        elif _name(call.func) == "input.string":
            default = _input_default(default_node, "input.string defval")
            if type(default) is not str:
                raise ValueError("input.string 기본값은 문자열이어야 합니다")
        elif source_input and isinstance(default_node, A.Name):
            if default_node.id not in _SOURCE_NAMES:
                raise ValueError("input.source 기본값은 확인한 OHLCV source만 허용합니다")
            default = default_node.id
        else:
            default = _input_default(default_node, "input defval")
        title_node = _arg(call, "title", 1)
        title = (
            _literal(title_node, "input title") if title_node is not None else statement.target.id
        )
        inputs.append((statement.target.id, title, default))
        if input_types is not None and _name(call.func) in {"input.string", "input.color"}:
            input_types[statement.target.id] = (
                "text" if _name(call.func) == "input.string" else "color"
            )
    return calls, inputs, fills


def _writes(tree: Any) -> Counter[str]:
    """전역 후보와 같은 이름의 모든 중첩 대입도 보수적으로 쓰기로 센다."""
    return Counter(
        name.id
        for node in A.walk(tree)
        if isinstance(node, (A.Assign, A.ReAssign, A.AugAssign))
        for name in A.walk(node.target)
        if isinstance(name, A.Name)
    )


def _readonly_globals(source: str) -> dict[str, Any]:
    tree = parse_to_ast(source)
    writes = _writes(tree)
    ambiguous = {
        node.name for node in A.walk(tree) if isinstance(node, (A.Param, A.FunctionDef))
    } | {
        name.id
        for node in A.walk(tree)
        if isinstance(node, (A.ForTo, A.ForIn))
        for name in A.walk(node.target)
        if isinstance(name, A.Name)
    }
    return {
        node.target.id: node.value
        for node in tree.body
        if isinstance(node, A.Assign)
        and isinstance(node.target, A.Name)
        and writes[node.target.id] == 1
        and node.target.id not in ambiguous
        and (
            isinstance(node.value, A.Constant)
            or (
                isinstance(node.value, A.Attribute)
                and _name(node.value) == f"color.{node.value.attr}"
            )
            or (
                isinstance(node.value, A.Call)
                and _name(node.value.func) in {"color.new", "color.rgb"}
            )
        )
    }


def _constant_color_base(node: Any, version: int, constants: Mapping[str, Any]) -> PineColor | None:
    """관측한 hex/named와 정수3개 RGB 생성만 읽는다. 입력·임의 호출은 계산하지 않는다."""
    if isinstance(node, A.Name):
        node = constants.get(node.id)
    if isinstance(node, A.Constant) and node.kind == "#" and isinstance(node.value, str):
        return color_literal(node.value, version)
    if isinstance(node, A.Attribute) and _name(node) == f"color.{node.attr}":
        return color_named(node.attr, version)
    if (
        isinstance(node, A.Call)
        and _name(node.func) == "color.rgb"
        and len(node.args) == 3
        and all(
            arg.name is None
            and isinstance(arg.value, A.Constant)
            and type(arg.value.value) is int
            and 0 <= arg.value.value <= 255
            for arg in node.args
        )
    ):
        return color_call(
            "color.rgb",
            dict(
                zip(("red", "green", "blue"), [arg.value.value for arg in node.args], strict=True)
            ),
            version,
        )
    return None


def _source_plot_variables(source: str) -> dict[str, tuple[int, int]]:
    """AST를 바꾸지 않고 단일 전역 대입의 plot handle 위치만 읽는다."""
    tree = parse_to_ast(source)
    positions, writes = {}, _writes(tree)
    for statement in tree.body:
        if not isinstance(statement, (A.Assign, A.ReAssign, A.AugAssign)) or not isinstance(
            statement.target, A.Name
        ):
            continue
        name = statement.target.id
        call = statement.value
        if (
            isinstance(statement, A.Assign)
            and isinstance(call, A.Call)
            and _name(call.func) == "plot"
        ):
            positions[name] = (call.lineno, call.col_offset)
    return {name: position for name, position in positions.items() if writes[name] == 1}


def _source_static_colors(source: str) -> dict[str, tuple[str, int]]:
    """관측한 v4 단일 전역 color.new(named, int) 상수만 읽는다."""
    tree = parse_to_ast(source)
    if pine_version_from_ast(tree) != 4:
        return {}
    colors, writes = {}, _writes(tree)
    for statement in tree.body:
        if not isinstance(statement, (A.Assign, A.ReAssign, A.AugAssign)) or not isinstance(
            statement.target, A.Name
        ):
            continue
        name, value = statement.target.id, statement.value
        if (
            not isinstance(statement, A.Assign)
            or not isinstance(value, A.Call)
            or _name(value.func) != "color.new"
            or len(value.args) != 2
            or any(arg.name is not None for arg in value.args)
        ):
            continue
        base, transparency = [arg.value for arg in value.args]
        if (
            isinstance(base, A.Attribute)
            and _name(base) == f"color.{base.attr}"
            and isinstance(transparency, A.Constant)
            and type(transparency.value) is int
            and 0 <= transparency.value <= 100
        ):
            colors[name] = (_color_default(value, 4), transparency.value)
    return {name: value for name, value in colors.items() if writes[name] == 1}


def _static_fill_color(
    call: A.Call, version: int | None = None, constants: Mapping[str, Any] | None = None
) -> str | None:
    """관측한 순수 color.new의 채널과 리터럴 투명도만 compiler CSS로 읽는다."""
    color = _arg(call, "color", 2)
    if not isinstance(color, A.Call) or _name(color.func) != "color.new":
        return None
    literal = _arg(color, "color", 0)
    base = _constant_color_base(literal, version or 6, constants or {})
    if base is None:
        return None
    transparency = _arg(color, "transp", 1)
    if isinstance(transparency, A.Name):
        transparency = (constants or {}).get(transparency.id)
    if not (
        len(color.args) == 2
        and all(arg.name is None for arg in color.args)
        and (
            not isinstance(literal, A.Constant)
            or (
                literal.kind == "#"
                and isinstance(literal.value, str)
                and re.fullmatch(r"#[0-9a-fA-F]{6}", literal.value)
            )
        )
        and isinstance(transparency, A.Constant)
        and _numeric(transparency.value)
        and 0 <= transparency.value <= 100
        and len([arg for arg in call.args if arg.name is None]) <= 3
        and all(arg.name is None or arg.name in {"color", "title", "display"} for arg in call.args)
    ):
        raise ValueError("관측하지 않은 정적 fill 색 형식입니다")
    red, green, blue = base.red, base.green, base.blue
    alpha = (
        format((Decimal(100) - Decimal(str(transparency.value))) / 100, "f").rstrip("0").rstrip(".")
        or "0"
    )
    return f"rgba({red},{green},{blue},{alpha})"


def _source_hlines(source: str) -> tuple[list[A.Call], dict[str, str]]:
    tree = parse_to_ast(source)
    writes, calls, names = _writes(tree), [], {}
    for statement in tree.body:
        if not isinstance(statement, (A.Assign, A.Expr)):
            continue
        call = statement.value
        if not isinstance(call, A.Call) or _name(call.func) != "hline":
            continue
        if (
            isinstance(statement, A.Assign)
            and isinstance(statement.target, A.Name)
            and writes[statement.target.id] == 1
        ):
            names[statement.target.id] = f"hline_{len(calls)}"
        calls.append(call)
    if {id(call) for call in calls} != {
        id(node)
        for node in A.walk(tree)
        if isinstance(node, A.Call) and _name(node.func) == "hline"
    }:
        raise ValueError("로컬 hline은 native band에 고정할 수 없습니다")
    return calls, names


def _check_bands(calls: Sequence[A.Call], bands: Any, defaults: Any, version: int | None) -> None:
    if (
        version != 6
        or not isinstance(bands, list)
        or not isinstance(defaults, list)
        or len(bands) != len(calls)
        or len(defaults) != len(calls)
    ):
        raise ValueError("관측한 hline band 목록과 다릅니다")
    for index, (call, band, style) in enumerate(zip(calls, bands, defaults, strict=True)):
        price, title = (
            _literal(_arg(call, "price", 0), "hline price"),
            _literal(_arg(call, "title", 1), "hline title"),
        )
        width_node = _arg(call, "linewidth", 4)
        width = _literal(width_node, "hline linewidth") if width_node is not None else 1
        color_node = _arg(call, "color", 2)
        if (
            not isinstance(color_node, A.Attribute)
            or _name(color_node) != f"color.{color_node.attr}"
            or _name(_arg(call, "linestyle", 3)) != "hline.style_dotted"
            or not _numeric(price)
            or type(width) is not int
            or width not in {1, 2}
        ):
            raise ValueError("관측하지 않은 hline 원문 형식입니다")
        expected = {
            "color": _color_default(color_node, 6),
            "linestyle": 1,
            "linewidth": width,
            "value": price,
            "visible": True,
        }
        if (
            band != {"id": f"hline_{index}", "isHidden": False, "name": title}
            or band.get("isHidden") is not False
            or style != expected
            or style.get("visible") is not True
            or type(style.get("linewidth")) is not int
            or type(style.get("linestyle")) is not int
            or not _numeric(style.get("value"))
        ):
            raise ValueError("hline band의 제목·가격·색·스타일이 원문과 다릅니다")


def _empty_chart_resolution(source: str) -> tuple[str | None, bool | None]:
    declarations = [
        statement.value
        for statement in parse_to_ast(source).body
        if isinstance(statement, A.Expr)
        and isinstance(statement.value, A.Call)
        and _name(statement.value.func) in {"study", "indicator", "strategy"}
    ]
    if len(declarations) != 1:
        return None, None
    kind = _name(declarations[0].func)
    if kind not in {"study", "indicator"}:
        return None, None
    value = _arg(declarations[0], "resolution" if kind == "study" else "timeframe")
    if not (isinstance(value, A.Constant) and type(value.value) is str and value.value == ""):
        return None, None
    gaps = _arg(declarations[0], "timeframe_gaps")
    if gaps is None:
        return kind, None
    if kind != "indicator" or not isinstance(gaps, A.Constant) or gaps.value is not False:
        raise ValueError("빈 주기의 timeframe_gaps는 관측한 명시 false만 지원합니다")
    return kind, False


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
    if kind == "integer":
        return type(actual) is int and type(expected) is int and actual == expected
    if kind == "bool":
        return type(actual) is bool and type(expected) is bool and actual == expected
    if kind == "color":
        if type(actual) is not str or type(expected) is not str:
            return False
        if re.fullmatch(r"#[0-9a-fA-F]{6}", actual) and re.fullmatch(r"#[0-9a-fA-F]{6}", expected):
            return int(actual[1:], 16) == int(expected[1:], 16)
        if actual != expected:
            return False
        try:
            _wire_color(actual)
        except ValueError:
            return False
        return True
    if kind == "text":
        return type(actual) is str and type(expected) is str and actual == expected
    return type(actual) is type(expected) and actual == expected


def _plot_bindings(
    calls: list[tuple[str, A.Call]],
    plots: Any,
    styles: Any,
    reviewed: Sequence[Mapping[str, Any]],
    fills: Sequence[A.Call],
    *,
    ohlc_plots: Any = None,
    source_plot_variables: Mapping[str, tuple[int, int]] | None = None,
    filled_areas: Any = None,
    filled_area_defaults: Any = None,
    source_static_colors: Mapping[str, tuple[str, int]] | None = None,
    source_version: int | None = None,
    ohlc_defaults: Any = None,
    constants: Mapping[str, Any] | None = None,
    hlines: tuple[Sequence[A.Call], Mapping[str, str]] | None = None,
    bands: Any = None,
    band_defaults: Any = None,
    palettes: Any = None,
    palette_defaults: Any = None,
) -> list[tuple[int, str, int]]:
    if (
        not isinstance(plots, list)
        or any(not isinstance(plot, dict) for plot in plots)
        or not isinstance(styles, dict)
    ):
        raise ValueError("컴파일 plot 메타데이터가 없습니다")
    if [plot.get("id") for plot in plots] != [f"plot_{i}" for i in range(len(plots))]:
        raise ValueError("컴파일 plot id 순서가 연속적이지 않습니다")
    expected_fill_columns = []
    static_fills = []
    series_gradients = []
    for index, call in enumerate(fills):
        target = f"fill_{index}"
        top_value, bottom_value = _arg(call, "top_value", 2), _arg(call, "bottom_value", 3)
        if len([arg for arg in call.args if arg.name is None]) <= 3 and not any(
            arg.name in {"top_value", "bottom_value", "top_color", "bottom_color"}
            for arg in call.args
        ):
            reference = _arg(call, "color", 2)
            constant = (
                source_static_colors.get(reference.id)
                if source_static_colors and isinstance(reference, A.Name)
                else None
            )
            if constant and (
                source_version != 4
                or len([arg for arg in call.args if arg.name is None]) > 3
                or any(
                    arg.name is not None and arg.name not in {"color", "title", "display"}
                    for arg in call.args
                )
            ):
                raise ValueError("관측하지 않은 v4 정적 fill 호출 형식입니다")
            extra_style = {"display": 15, "transparency": constant[1]} if constant else {}
            if (
                source_version == 4
                and isinstance(reference, A.Attribute)
                and _name(reference) == f"color.{reference.attr}"
            ):
                if len([arg for arg in call.args if arg.name is None]) > 3 or any(
                    arg.name is not None and arg.name not in {"color", "title", "transp"}
                    for arg in call.args
                ):
                    raise ValueError("관측하지 않은 legacy fill 호출 형식입니다")
                transparency_node = _arg(call, "transp")
                transparency = (
                    90 if transparency_node is None else _literal(transparency_node, "fill transp")
                )
                if transparency_node is not None and (
                    type(transparency) is not int or transparency != 70
                ):
                    raise ValueError("관측하지 않은 legacy fill 투명도입니다")
                static_color = _color_default(reference, 4)
                extra_style = {"display": 15, "transparency": transparency}
            else:
                static_color = (
                    constant[0] if constant else _static_fill_color(call, source_version, constants)
                )
                if (
                    static_color is not None
                    and source_version == 5
                    and isinstance(reference, A.Call)
                    and isinstance(_arg(reference, "color", 0), A.Name)
                ):
                    extra_style = {"transparency": 0}
            if static_color is not None:
                static_fills.append((target, call, static_color, extra_style))
                continue
            expected_fill_columns.append({"type": "colorer", "target": target})
            continue
        # rbeErVR5의 관측한 gradient 형식: series topValue / const bottomValue /
        # color.new(series, const) topColor / na bottomColor의 두 비신호 열이다.
        top_color, bottom_color = _arg(call, "top_color", 4), _arg(call, "bottom_color", 5)
        top_reference = (
            top_value.operand
            if isinstance(top_value, A.UnaryOp) and isinstance(top_value.op, A.USub)
            else top_value
        )
        bottom_constant = (
            bottom_value.operand
            if isinstance(bottom_value, A.UnaryOp) and isinstance(bottom_value.op, A.USub)
            else bottom_value
        )
        # d3 실제 형식은 두 series 값과 조건부 topColor의 세 비신호 열이다.
        conditional = (
            source_version == 6
            and len(call.args) == 6
            and all(arg.name is None for arg in call.args)
            and isinstance(top_value, A.Name)
            and isinstance(bottom_value, A.Name)
            and isinstance(top_color, A.Conditional)
            and isinstance(top_color.test, A.Name)
            and isinstance(top_color.orelse, A.Name)
            and top_color.orelse.id == "na"
        )
        top_color_call = top_color.body if conditional else top_color
        if not (
            isinstance(top_reference, A.Name)
            and (
                conditional
                or (isinstance(bottom_constant, A.Constant) and _numeric(bottom_constant.value))
            )
            and isinstance(top_color_call, A.Call)
            and _name(top_color_call.func) == "color.new"
            and len(top_color_call.args) == 2
            and all(arg.name is None for arg in top_color_call.args)
            and isinstance(top_color_call.args[0].value, A.Name)
            and isinstance(top_color_call.args[1].value, A.Constant)
            and _numeric(top_color_call.args[1].value.value)
            and 0 <= top_color_call.args[1].value.value <= 100
            and isinstance(bottom_color, A.Name)
            and bottom_color.id == "na"
        ):
            raise ValueError("관측하지 않은 gradient fill 형식입니다")
        if conditional:
            series_gradients.append((target, call))
        expected_fill_columns.extend(
            [
                {"type": "data", "target": target, "targetField": "topValue"},
                *(
                    [{"type": "data", "target": target, "targetField": "bottomValue"}]
                    if conditional
                    else []
                ),
                {"type": "colorer", "target": target, "targetField": "topColor"},
            ]
        )
    fill_columns = []
    for index, plot in enumerate(plots):
        if plot["type"] not in {"colorer", "data"}:
            continue
        target = plot.get("target")
        if isinstance(target, str) and target.startswith("fill_"):
            ignored = {"id"}
            # 기존 단색 fill의 palette 식별자는 비신호 부가 메타데이터다.
            if plot["type"] == "colorer" and "targetField" not in plot:
                ignored.add("palette")
            fill_columns.append({key: value for key, value in plot.items() if key not in ignored})
        elif (
            plot["type"] == "data"
            or index == 0
            or target != f"plot_{index - 1}"
            or plots[index - 1].get("type") not in {"line", "shapes", "chars"}
        ):
            raise ValueError("컴파일 colorer가 앞선 line/shapes/chars plot에 결합되지 않았습니다")
    if fill_columns != expected_fill_columns:
        raise ValueError("컴파일 fill data/colorer와 원문 전역 fill 호출이 다릅니다")
    visible = []
    candle_columns: set[int] = set()
    candle_count = 0
    candle_calls = [call for kind, call in calls if kind == "plotcandle"]
    arrow_columns: set[int] = set()
    for index, plot in enumerate(plots):
        if index in candle_columns or index in arrow_columns:
            continue
        if plot.get("type") == "arrows":
            group = plots[index : index + 3]
            if (
                len(group) != 3
                or group[0] != {"id": f"plot_{index}", "type": "arrows"}
                or group[1]
                != {"id": f"plot_{index + 1}", "type": "up_colorer", "target": f"plot_{index}"}
                or group[2]
                != {"id": f"plot_{index + 2}", "type": "down_colorer", "target": f"plot_{index}"}
            ):
                raise ValueError("관측한 plotarrow 3열 순서·대상이 다릅니다")
            arrow_columns.update((index + 1, index + 2))
        if plot.get("type") == "ohlc_open":
            target = f"plotcandle_{candle_count}"
            if candle_count >= len(candle_calls):
                raise ValueError("원문에 없는 plotcandle 그룹입니다")
            call = candle_calls[candle_count]
            types = (
                "ohlc_open",
                "ohlc_high",
                "ohlc_low",
                "ohlc_close",
                "ohlc_colorer",
                "wick_colorer",
                "border_colorer",
            )
            if (
                source_version == 4
                and _arg(call, "color", 5) is not None
                and _arg(call, "wickcolor", 6) is None
                and _arg(call, "bordercolor") is None
            ):
                types = types[:5]
                defaults = ohlc_defaults.get(target) if isinstance(ohlc_defaults, dict) else None
                expected = {
                    "borderColor": "#000000",
                    "color": "#2196F3",
                    "display": 15,
                    "drawBorder": True,
                    "drawWick": True,
                    "visible": True,
                    "wickColor": "#737375",
                }
                if (
                    defaults != expected
                    or any(
                        defaults.get(name) is not True
                        for name in ("drawBorder", "drawWick", "visible")
                    )
                    or type(defaults.get("display")) is not int
                ):
                    raise ValueError("관측한 v4 plotcandle 기본 wick/border 스타일과 다릅니다")
            group = plots[index : index + len(types)]
            if len(group) != len(types):
                raise ValueError("관측한 plotcandle OHLC·색상 열이 누락됐습니다")
            for column, kind in zip(group, types, strict=True):
                if (
                    column.get("type") != kind
                    or column.get("target") != target
                    or set(column) - {"id", "type", "target", "palette"}
                    or (
                        kind.endswith("colorer")
                        and not re.fullmatch(r"palette_\d+", str(column.get("palette", "")))
                    )
                    or (not kind.endswith("colorer") and "palette" in column)
                ):
                    raise ValueError("plotcandle OHLC·색상 열의 순서·대상이 다릅니다")
            candle_columns.update(range(index, index + len(types)))
            candle_count += 1
        if plot.get("type") not in {"colorer", "data"}:
            visible.append((index, plot))
    if candle_count and (
        not isinstance(ohlc_plots, dict)
        or set(ohlc_plots) != {f"plotcandle_{i}" for i in range(candle_count)}
    ):
        raise ValueError("plotcandle 스타일의 고유 대상이 다릅니다")
    if len(visible) != len(calls):
        raise ValueError("원문 전역 plot/alert 호출 수와 컴파일 plot 수가 다릅니다")
    for (kind, call), (index, plot) in zip(calls, visible, strict=True):
        if plot.get("type") != _PLOT_TYPES[kind]:
            raise ValueError("원문 호출 유형과 컴파일 plot 유형이 다릅니다")
        style = (
            ohlc_plots.get(plot["target"]) if kind == "plotcandle" else styles.get(f"plot_{index}")
        )
        if not isinstance(style, dict):
            raise ValueError("컴파일 plot 스타일이 없습니다")
        if kind == "plotcandle" and style.get("plottype") != "ohlc_candles":
            raise ValueError("plotcandle 스타일 유형이 다릅니다")
        title_node = _arg(
            call,
            "title",
            4 if kind == "plotcandle" else None if kind in {"barcolor", "bgcolor"} else 1,
        )
        title = (
            _literal(title_node, "plot title")
            if title_node is not None
            else "Shapes"
            if kind == "plotshape"
            else "Chars"
            if kind == "plotchar" and source_version == 4
            else "Plot"
            if kind == "plot"
            else "Bar Color"
            if kind == "barcolor"
            else "Background Color"
            if kind == "bgcolor"
            else "PlotCandle"
            if kind == "plotcandle" and source_version == 4
            else None
        )
        if title is None or style.get("title") != title:
            raise ValueError("원문 plot title과 컴파일 스타일 제목이 다릅니다")
        if kind == "plotarrow" and (
            style != {"isHidden": False, "maxHeight": 100, "minHeight": 5, "title": title}
            or style.get("isHidden") is not False
            or type(style.get("maxHeight")) is not int
            or type(style.get("minHeight")) is not int
            or _arg(call, "minheight", 5) is not None
            or _arg(call, "maxheight", 6) is not None
        ):
            raise ValueError("관측한 plotarrow 기본 스타일과 다릅니다")
        if kind == "bgcolor" and (
            style != {"title": title, "isHidden": False} or style.get("isHidden") is not False
        ):
            raise ValueError("관측한 bgcolor 기본 스타일과 다릅니다")
        text_node = _arg(call, "message" if kind == "alertcondition" else "text")
        if (
            kind in _SIGNAL_CALLS
            and text_node is not None
            and style.get("text") != _literal(text_node, "signal text")
        ):
            raise ValueError("원문 신호 text와 컴파일 스타일이 다릅니다")
    if static_fills or series_gradients:
        if (
            not isinstance(filled_areas, list)
            or len(filled_areas) != len(fills)
            or [area.get("id") if isinstance(area, dict) else None for area in filled_areas]
            != [f"fill_{i}" for i in range(len(fills))]
        ):
            raise ValueError("정적 fill의 전체 filledAreas 대상이 다릅니다")
        plot_ids = {
            (call.lineno, call.col_offset): plot["id"]
            for (kind, call), (_, plot) in zip(calls, visible, strict=True)
            if kind == "plot"
        }
        for target, call, color, extra_style in static_fills:
            endpoints = [_arg(call, name, index) for index, name in enumerate(("plot1", "plot2"))]
            is_band = hlines is not None and all(
                isinstance(node, A.Name) and node.id in hlines[1] for node in endpoints
            )
            if is_band:
                _check_bands(hlines[0], bands, band_defaults, source_version)
                object_ids = [hlines[1][node.id] for node in endpoints]
            elif not source_plot_variables or any(
                not isinstance(node, A.Name) or source_plot_variables.get(node.id) not in plot_ids
                for node in endpoints
            ):
                raise ValueError("정적 fill 끝점은 단일 전역 plot 변수여야 합니다")
            else:
                object_ids = [plot_ids[source_plot_variables[node.id]] for node in endpoints]
            expected_area = {
                "id": target,
                "objAId": object_ids[0],
                "objBId": object_ids[1],
                "title": _literal(_arg(call, "title", 3), "fill title")
                if _arg(call, "title", 3) is not None
                else "Plots Background",
                "type": "hline_hline" if is_band else "plot_plot",
                "fillgaps": False,
                "isHidden": False,
            }
            area = filled_areas[int(target.split("_")[1])]
            if (
                area != expected_area
                or area.get("fillgaps") is not False
                or area.get("isHidden") is not False
            ):
                raise ValueError("정적 fill의 제목·유형·plot 끝점이 원문과 다릅니다")
            style = (
                filled_area_defaults.get(target) if isinstance(filled_area_defaults, dict) else None
            )
            keys = {"color", "visible"} | set(extra_style)
            if (
                not isinstance(style, dict)
                or set(style) != keys
                or style["color"] != color
                or type(style["visible"]) is not bool
                or (
                    source_version == 4
                    and _arg(call, "transp") is None
                    and isinstance(_arg(call, "color", 2), A.Attribute)
                    and style["visible"] is not True
                )
            ):
                raise ValueError("정적 fill의 기본 색·투명도 스타일이 원문과 다릅니다")
            if any(
                type(style[key]) is not int or style[key] != value
                for key, value in extra_style.items()
            ):
                raise ValueError("관측한 v4 정적 fill의 display·투명도와 다릅니다")
    for target, call in series_gradients:
        endpoints = [_arg(call, name, index) for index, name in enumerate(("plot1", "plot2"))]
        if not source_plot_variables or any(
            not isinstance(node, A.Name) or source_plot_variables.get(node.id) not in plot_ids
            for node in endpoints
        ):
            raise ValueError("gradient fill 끝점이 원문 전역 plot과 다릅니다")
        expected_area = {
            "id": target,
            "objAId": plot_ids[source_plot_variables[endpoints[0].id]],
            "objBId": plot_ids[source_plot_variables[endpoints[1].id]],
            "title": "Plots Background",
            "type": "plot_plot",
            "fillgaps": False,
            "isHidden": False,
        }
        area = filled_areas[int(target.split("_")[1])]
        style = filled_area_defaults.get(target) if isinstance(filled_area_defaults, dict) else None
        if (
            area != expected_area
            or area.get("fillgaps") is not False
            or area.get("isHidden") is not False
            or style != {"bottomColor": "rgba(0,0,0,0)", "fillType": "gradient", "visible": True}
            or style.get("visible") is not True
            or palettes is not None
            or palette_defaults is not None
        ):
            raise ValueError("관측한 gradient fill 제목·끝점·기본색·palette가 다릅니다")
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
    max_total_bars: int | None = None,
    require_full_prefix: bool = False,
    include_price_prefix: bool = False,
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
    if max_total_bars is not None and (type(max_total_bars) is not int or max_total_bars <= 0):
        raise ValueError("native 총 봉 한도는 양의 정수여야 합니다")
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
    source_input_types: dict[str, str] = {}
    calls, source_inputs, fills = _source_calls(source_text, input_types=source_input_types)
    source_version = pine_version_from_ast(parse_to_ast(source_text))
    overrides = payload.get("inputs")
    resolved = payload.get("resolved_inputs")
    if (
        not isinstance(overrides, dict)
        or overrides != dict(expected_inputs)
        or not isinstance(resolved, dict)
    ):
        raise ValueError("원본 입력 override 계약 또는 resolved_inputs가 없습니다")
    defaults = {name: default for name, _, default in source_inputs}
    expected_values = {**defaults, **overrides}
    if (
        set(overrides) - set(defaults)
        or set(resolved) != set(expected_values)
        or any(
            not _input_equal(resolved[name], value, "color")
            if source_input_types.get(name) == "color"
            else resolved[name] != value
            for name, value in expected_values.items()
        )
    ):
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
    # 관측한 stats는 barcolor/bgcolor를 세지 않으므로 실제 plot 열 대응에서 별도로 검사한다.
    counts = {
        kind: sum(call_kind == kind for call_kind, _ in calls)
        for kind in _PLOT_CALLS - {"barcolor", "bgcolor"}
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
            or (name in source_input_types and item.get("type") != source_input_types[name])
            or not _input_equal(item.get("defval"), defaults[name], item.get("type", ""))
            or not _input_equal(resolved[name], expected_values[name], item.get("type", ""))
        ):
            raise ValueError("컴파일 입력 기본값·제목이 원문과 다릅니다")
    expected_slots = {f"in_{i}" for i in range(len(source_inputs))}
    resolution_kind, explicit_gaps = _empty_chart_resolution(source_text)
    resolution_slot = f"in_{len(source_inputs)}" if resolution_kind is not None else None
    gaps_slot = f"in_{len(source_inputs) + 1}" if explicit_gaps is not None else None
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
        if isinstance(slot, dict) and "active" in slot:
            expected_resolution["active"] = True
        if (
            slot != expected_resolution
            or ("active" in slot and slot["active"] is not True)
            or slot["isMTFResolution"] is not True
            or slot["isFake"] is not True
            or sum(
                isinstance(item, dict) and item.get("id") == resolution_slot
                for item in meta["inputs"]
            )
            != 1
        ):
            raise ValueError("빈 차트 resolution의 compiler 자동 입력 근거가 다릅니다")
    if gaps_slot is not None:
        expected_slots.add(gaps_slot)
        slot = compiled_inputs.get(gaps_slot)
        expected_gaps = {
            "defval": False,
            "group": "Calculation",
            "id": gaps_slot,
            "isFake": True,
            "isMTFGaps": True,
            "name": "Wait for timeframe closes",
            "type": "bool",
        }
        if isinstance(slot, dict) and "active" in slot:
            expected_gaps["active"] = True
        if (
            slot != expected_gaps
            or slot.get("defval") is not False
            or ("active" in slot and slot["active"] is not True)
            or slot.get("isFake") is not True
            or slot.get("isMTFGaps") is not True
        ):
            raise ValueError("명시 timeframe_gaps=false의 compiler 자동 입력 근거가 다릅니다")
    if {key for key in compiled_inputs if re.fullmatch(r"in_\d+", str(key))} != expected_slots:
        raise ValueError("컴파일 입력 개수가 원문과 다릅니다")
    bound = _plot_bindings(
        calls,
        meta.get("plots"),
        meta.get("styles"),
        signal_bindings,
        fills,
        ohlc_plots=meta.get("ohlcPlots"),
        source_plot_variables=_source_plot_variables(source_text),
        filled_areas=meta.get("filledAreas"),
        filled_area_defaults=meta.get("defaults", {}).get("filledAreasStyle")
        if isinstance(meta.get("defaults"), dict)
        else None,
        source_static_colors=_source_static_colors(source_text),
        source_version=source_version,
        ohlc_defaults=meta.get("defaults", {}).get("ohlcPlots")
        if isinstance(meta.get("defaults"), dict)
        else None,
        constants=_readonly_globals(source_text),
        hlines=_source_hlines(source_text),
        bands=meta.get("bands"),
        band_defaults=meta.get("defaults", {}).get("bands")
        if isinstance(meta.get("defaults"), dict)
        else None,
        palettes=meta.get("palettes"),
        palette_defaults=meta.get("defaults", {}).get("palettes")
        if isinstance(meta.get("defaults"), dict)
        else None,
    )
    wire = payload.get("wire")
    if not isinstance(wire, list) or not wire:
        raise ValueError("UI wire 관측이 없습니다")
    sent, received, ordered = [], [], []
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
            ordered.append((entry["direction"], message))
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
        kind = compiled_inputs[f"in_{index}"].get("type", "")
        if kind == "color":
            matches = (
                isinstance(wire_input, dict)
                and wire_input.get("t") == "color"
                and (
                    (
                        type(wire_input.get("v")) is int
                        and wire_input["v"] == _wire_color(resolved[name])
                    )
                    or (
                        source_version <= 5
                        and type(wire_input.get("v")) is str
                        and _input_equal(wire_input["v"], resolved[name], "color")
                    )
                )
            )
        else:
            matches = isinstance(wire_input, dict) and _input_equal(
                wire_input.get("v"), resolved[name], kind
            )
        if name in source_input_types and isinstance(wire_input, dict):
            matches &= wire_input.get("t") == source_input_types[name]
        if not matches:
            raise ValueError("create_study 실제 입력이 원본 기본값과 다릅니다")
    if {key for key in study_inputs if re.fullmatch(r"in_\d+", str(key))} != expected_slots:
        raise ValueError("create_study 입력 개수가 컴파일 결과와 다릅니다")
    if resolution_slot is not None:
        slot = study_inputs.get(resolution_slot)
        if slot != {"v": "", "f": True, "t": "resolution"} or slot["f"] is not True:
            raise ValueError("create_study resolution은 원문의 빈 차트 주기를 유지해야 합니다")
    if gaps_slot is not None:
        slot = study_inputs.get(gaps_slot)
        if (
            slot != {"v": False, "f": True, "t": "bool"}
            or slot.get("v") is not False
            or slot.get("f") is not True
        ):
            raise ValueError("create_study timeframe_gaps는 원문의 명시 false를 유지해야 합니다")
    completed = [
        m
        for m in received
        if m.get("m") == "study_completed" and m.get("p", [])[:2] == [session, study_id]
    ]
    if not completed:
        raise ValueError("해당 study cohort 완료 관측이 없습니다")
    loading_messages = [
        message
        for message in received
        if message.get("m") == "study_loading" and message.get("p", [])[:2] == [session, study_id]
    ]
    if len(completed) > 1 or loading_messages:
        # 같은 계산의 추가 이력은 처음과 같은 token의 행 집합을 확장한다.
        # 각 추가 lifecycle은 이전 완료 이후의 실제 같은 주기 UI 범위 요청에 결박한다.
        token = completed[-1]["p"][2] if len(completed[-1]["p"]) == 3 else None
        if not isinstance(token, str) or not token:
            raise ValueError("native 계산 token 근거가 없습니다")
        resolutions = {"1h": {"60", "1H"}, "4h": {"240", "4H"}, "1d": {"1D", "D"}}
        loading = False
        pairs = 0
        pending_range = None
        for direction, message in ordered:
            parameters = message.get("p", [])
            if direction == "sent":
                if message.get("m") == "modify_series" and parameters[:2] == [session, chart_id]:
                    pending_range = parameters
                continue
            if parameters[:2] != [session, study_id]:
                continue
            kind = message.get("m")
            if kind not in {"study_loading", "study_completed"}:
                continue
            if parameters != [session, study_id, token]:
                raise ValueError("복수 완료의 계산 token이 다릅니다")
            if kind == "study_loading":
                if loading:
                    raise ValueError("native 계산이 완료되기 전에 다시 시작됐습니다")
                if pairs and (
                    pending_range is None
                    or len(pending_range) != 6
                    or pending_range[4] not in resolutions[expected_timeframe]
                    or not isinstance(pending_range[5], str)
                    or re.fullmatch(r"r,\d+:\d+", pending_range[5]) is None
                    or f"{pending_range[2]}_{creates[0]['p'][2]}" != token
                ):
                    raise ValueError("추가 계산의 같은 차트 주기 UI 범위 요청 근거가 없습니다")
                loading = True
            else:
                if not loading:
                    raise ValueError("native 추가 완료의 loading 근거가 없습니다")
                loading = False
                pairs += 1
                pending_range = None
        if loading or pairs != len(completed):
            raise ValueError("native 추가 계산의 완료 관측이 부족합니다")
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
    total_bars = len(set(study_rows) | set(price_rows))
    if max_total_bars is not None and total_bars > max_total_bars:
        raise ValueError(
            "native 총 봉이 계정 한도를 초과합니다; 후미 절단으로 재사용할 수 없습니다"
        )
    closed_study = {at: row for at, row in study_rows.items() if at + step <= observed_at}
    closed_price = {at: row for at, row in price_rows.items() if at + step <= observed_at}
    full_prefix = bool(closed_study) and set(closed_study) <= set(closed_price)
    if require_full_prefix and not full_prefix:
        raise ValueError("native 지표 계산의 초기 가격 이력이 누락됐습니다")
    common = sorted(set(closed_study) & set(closed_price))
    if not common or any(current - previous != step for previous, current in pairwise(common)):
        raise ValueError("공통 확정 study/OHLCV 봉이 없거나 시간 격자가 불연속입니다")
    observations, prices, events, missing_alertconditions = [], [], [], []
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
            if (
                kind == "alertcondition"
                and source_version in {4, 5}
                and type(value) is float
                and value == _SENTINEL
            ):
                missing_alertconditions.append(
                    {
                        "bar_time": at.isoformat(),
                        "column": column,
                        "direction": direction,
                        "line": line,
                        "value": value,
                    }
                )
                continue
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
    input_times = sorted(closed_price) if include_price_prefix else common
    if include_price_prefix:
        if any(current - previous != step for previous, current in pairwise(input_times)):
            raise ValueError("초기 가격 입력 격자가 불연속입니다")
        prices = []
        for at in input_times:
            price = closed_price[at][1:]
            if not all(_numeric(value) for value in price):
                raise ValueError("초기 OHLCV에 비수치 값이 있습니다")
            open_, high, low, close, volume = price
            if (
                min(open_, high, low, close) <= 0
                or volume < 0
                or high < max(open_, close, low)
                or low > min(open_, close, high)
            ):
                raise ValueError("초기 OHLCV 가격 범위 또는 거래량이 잘못됐습니다")
            prices.append(price)
    index = pd.DatetimeIndex(common, name="time")
    observation_frame = pd.DataFrame(
        observations, columns=[plot["id"] for plot in plots], index=index
    )
    ohlcv = pd.DataFrame(
        prices,
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex(input_times, name="time"),
    )
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
            "total_received_bars": total_bars,
            "full_study_prefix_covered": full_prefix,
            "study_first_bar": min(study_rows).isoformat(),
            "price_first_bar": min(price_rows).isoformat(),
            "study_completed_epochs": len(completed),
            "full_price_history_used": input_times == sorted(closed_price),
            **(
                {"missing_alertconditions": missing_alertconditions}
                if missing_alertconditions
                else {}
            ),
        },
    )
