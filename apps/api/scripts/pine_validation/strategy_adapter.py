"""검토한 신호 위치에만 진입문을 붙이는 로컬 Pine 전략 어댑터."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
from pynescript import ast as A

from scripts.pine_validation.futures import simulate_futures
from scripts.pine_validation.models import EventInput, coerce_events, utc_time
from src.strategy.pine_v2.interpreter import _V4_ALIASES, STDLIB_NAMES, pine_version_from_ast
from src.strategy.pine_v2.parser_adapter import parse_to_ast

_SIGNALS = {"plotshape", "plotchar", "alertcondition"}
_DISPLAY_CALLS = {"color.new", "color.rgb", "color.from_gradient"}
_HEADER_ARGS = {
    "title",
    "shorttitle",
    "overlay",
    "format",
    "precision",
    "max_lines_count",
    "max_labels_count",
    "max_boxes_count",
    "max_bars_back",
    "explicit_plot_zorder",
}
_SECONDS = {"1h": 3600, "4h": 14400, "1d": 86400}


class StrategyAdapterError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


@dataclass(frozen=True)
class StrategyAdaptation:
    strategy_source: str
    source_sha256: str
    converted_sha256: str
    bindings: list[dict[str, Any]]
    warnings: list[str]
    source_line_map: dict[int, int | None]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _name(node: Any) -> str:
    if isinstance(node, A.Name):
        return node.id
    if isinstance(node, A.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    return ""


def _span(node: Any, lines: list[str], offsets: list[int]) -> tuple[int, int]:
    positions = [
        getattr(node, key, None) for key in ("lineno", "col_offset", "end_lineno", "end_col_offset")
    ]
    if any(type(value) is not int for value in positions):
        raise StrategyAdapterError("missing_source_span", "AST에 정확한 원본 종료 위치가 없습니다")
    first, column, last, end_column = positions
    if (
        not (1 <= first <= last <= len(lines))
        or not (0 <= column <= len(lines[first - 1]))
        or not (0 <= end_column <= len(lines[last - 1]))
    ):
        raise StrategyAdapterError("invalid_source_span", "AST 원본 범위가 소스와 맞지 않습니다")
    return offsets[first - 1] + column, offsets[last - 1] + end_column


def _safe_calls(node: Any, *, display: bool) -> bool:
    for child in A.walk(node):
        if not isinstance(child, A.Call):
            continue
        name = _name(child.func)
        if display:
            if name not in _DISPLAY_CALLS:
                return False
        elif name not in STDLIB_NAMES and name not in _V4_ALIASES and not name.startswith("math."):
            return False
    return True


def adapt_strategy(
    source: str,
    signal_bindings: Sequence[Mapping[str, Any]],
    *,
    trade_start: Any = None,
    fixed_quantity: Decimal | None = Decimal("1"),
) -> StrategyAdaptation:
    """전체 body를 보존하며 첫 조건을 한 번 계산한다. 범위를 추측해서 확장하지 않는다."""
    try:
        tree = parse_to_ast(source)
    except Exception as exc:
        raise StrategyAdapterError("invalid_pine", "원본 Pine을 해석할 수 없습니다") from exc
    declarations = [
        statement.value
        for statement in tree.body
        if isinstance(statement, A.Expr)
        and isinstance(statement.value, A.Call)
        and _name(statement.value.func) in {"indicator", "study", "strategy"}
    ]
    if len(declarations) != 1 or _name(declarations[0].func) == "strategy":
        raise StrategyAdapterError(
            "unsupported_declaration", "indicator/study 선언 한 개만 변환합니다"
        )
    if not signal_bindings:
        raise StrategyAdapterError(
            "missing_signal_bindings", "검토한 방향별 신호 위치가 필요합니다"
        )
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    newline = "\r\n" if "\r\n" in source else "\n"
    used = {node.id for node in A.walk(tree) if isinstance(node, A.Name)}

    def unique(name: str) -> str:
        while name in used:
            name += "_"
        used.add(name)
        return name

    long_flag, short_flag = unique("qb_adapt_long_submitted"), unique("qb_adapt_short_submitted")
    header = declarations[0]
    header_args = []
    warnings = ["검토한 위치만 연결하며 원본의 다른 plot/alert 및 계산 body는 보존합니다"]
    for index, argument in enumerate(header.args):
        if argument.name in {"resolution", "timeframe"}:
            if not isinstance(argument.value, A.Constant) or argument.value.value != "":
                raise StrategyAdapterError(
                    "non_chart_timeframe", "별도 resolution/timeframe 선언은 변환하지 않습니다"
                )
            warnings.append(f"빈 {argument.name} 선언 인자만 제거했습니다")
        elif argument.name == "timeframe_gaps":
            chart_timeframes = [arg for arg in header.args if arg.name == "timeframe"]
            if (
                _name(header.func) != "indicator"
                or len(chart_timeframes) != 1
                or not isinstance(chart_timeframes[0].value, A.Constant)
                or chart_timeframes[0].value.value != ""
                or not isinstance(argument.value, A.Constant)
                or type(argument.value.value) is not bool
            ):
                raise StrategyAdapterError(
                    "unsupported_timeframe_gaps",
                    "timeframe_gaps는 명시 timeframe=빈문자열의 bool 상수만 허용합니다",
                )
            warnings.append(
                "차트 주기 기본값에서 timeframe_gaps 선언을 제거했습니다; "
                "Timeframe/Wait for timeframe closes 설정 UI는 보존하지 않습니다"
            )
        elif argument.name == "linktoseries":
            if not isinstance(argument.value, A.Constant) or type(argument.value.value) is not bool:
                raise StrategyAdapterError(
                    "dynamic_declaration", "linktoseries는 상수만 허용합니다"
                )
            warnings.append("화면 축 연결 전용 linktoseries 선언 인자만 제거했습니다")
        elif (
            argument.name is None
            and _name(header.func) == "study"
            and pine_version_from_ast(tree) == 4
            and 2 <= index <= 4
        ):
            parameter = ("overlay", "format", "precision")[index - 2]
            value = argument.value
            if parameter == "overlay":
                valid = isinstance(value, A.Constant) and type(value.value) is bool
            elif parameter == "format":
                valid = _name(value) in {"format.inherit", "format.price", "format.volume"}
            else:
                valid = (
                    isinstance(value, A.Constant)
                    and type(value.value) is int
                    and 0 <= value.value <= 16
                )
            if (
                not valid
                or any(arg.name == parameter for arg in header.args)
                or any(arg.name is not None for arg in header.args[:index])
            ):
                raise StrategyAdapterError(
                    "dynamic_declaration",
                    "v4 study 위치 인자는 중복 없는 bool·format 상수·0~16 정수만 허용합니다",
                )
            header_args.append(A.Arg(name=parameter, value=value))
        elif argument.name is None and index == 2 and _name(header.func) == "indicator":
            if (
                not isinstance(argument.value, A.Constant)
                or type(argument.value.value) is not bool
                or any(arg.name == "overlay" for arg in header.args)
            ):
                raise StrategyAdapterError(
                    "dynamic_declaration",
                    "세 번째 positional overlay는 중복 없는 bool 상수만 허용합니다",
                )
            header_args.append(A.Arg(name="overlay", value=argument.value))
        elif argument.name in _HEADER_ARGS or (argument.name is None and index <= 1):
            if not _safe_calls(argument.value, display=True):
                raise StrategyAdapterError(
                    "dynamic_declaration", "동적 선언 인자는 변환하지 않습니다"
                )
            header_args.append(argument)
        else:
            raise StrategyAdapterError(
                "unsupported_declaration_option", f"선언 인자를 지원하지 않습니다: {argument.name}"
            )
    replacement = A.unparse(A.Call(func=A.Name(id="strategy", ctx=A.Load()), args=header_args))
    start, end = _span(header, lines, offsets)
    edits: list[tuple[int, int, str]] = [(start, end, replacement)]
    after_header = offsets[header.end_lineno]
    separator = "" if after_header and source[after_header - 1] == "\n" else newline
    edits.append(
        (
            after_header,
            after_header,
            f"{separator}{long_flag} = false{newline}{short_flag} = false{newline}",
        )
    )
    top_calls = [
        statement.value
        for statement in tree.body
        if isinstance(statement, A.Expr) and isinstance(statement.value, A.Call)
    ]
    ordered_bindings = list(signal_bindings)
    if any(
        type(binding.get("line")) is not int or binding["line"] < 1 for binding in ordered_bindings
    ):
        raise StrategyAdapterError("invalid_signal_position", "신호 줄은 양의 정수여야 합니다")
    # 인접 호출의 경계에서 이전 진입문이 다음 조건 선계산보다 먼저 온다.
    ordered_bindings.sort(key=lambda binding: binding["line"])
    udf_names = {node.name for node in A.walk(tree) if isinstance(node, A.FunctionDef)}
    seen = set()
    reviewed = []
    has_exits = any(
        binding.get("direction") in {"long_exit", "short_exit"} for binding in ordered_bindings
    )
    deferred_entries = []
    for binding in ordered_bindings:
        function, line, direction = (
            binding.get("function"),
            binding.get("line"),
            binding.get("direction"),
        )
        if (
            function not in _SIGNALS
            or direction not in {"long", "short", "long_exit", "short_exit"}
            or binding.get("when", "truthy") != "truthy"
        ):
            raise StrategyAdapterError(
                "unsupported_signal_binding", "함수·명시 방향·truthy 조건을 확인하세요"
            )
        matches = [
            call
            for call in top_calls
            if _name(call.func) == function
            and call.lineno == line
            and ("column" not in binding or call.col_offset == binding["column"])
        ]
        if len(matches) != 1 or matches[0].col_offset != 0:
            raise StrategyAdapterError(
                "signal_scope_or_position", "선택한 신호는 단독 최상위 호출이어야 합니다"
            )
        call = matches[0]
        if call.lineno <= header.end_lineno:
            raise StrategyAdapterError(
                "signal_before_declaration", "신호 호출은 선언 뒤에 있어야 합니다"
            )
        key = (call.lineno, call.col_offset)
        if key in seen:
            raise StrategyAdapterError(
                "duplicate_signal_binding", "같은 호출을 중복 방향에 연결할 수 없습니다"
            )
        seen.add(key)
        condition_name = "condition" if function == "alertcondition" else "series"
        conditions = [arg for arg in call.args if arg.name == condition_name]
        if call.args and call.args[0].name is None:
            conditions.insert(0, call.args[0])
        if not conditions:
            raise StrategyAdapterError(
                "named_first_condition", "첫 positional 또는 함수의 주조건 keyword가 필요합니다"
            )
        if len(conditions) != 1:
            raise StrategyAdapterError(
                "ambiguous_signal_condition", "주조건 인자를 중복 지정할 수 없습니다"
            )
        argument = conditions[0]
        if not _safe_calls(argument.value, display=False) or any(
            isinstance(node, A.Call) and _name(node.func) in udf_names
            for node in A.walk(argument.value)
        ):
            raise StrategyAdapterError(
                "unsupported_condition_call", "조건의 UDF/input/외부 호출은 변환하지 않습니다"
            )
        if any(
            not _safe_calls(arg.value, display=True) for arg in call.args if arg is not argument
        ):
            raise StrategyAdapterError(
                "dynamic_signal_arguments", "다른 인자에 실행 부작용이 있는 호출이 있습니다"
            )
        call_start, _ = _span(call, lines, offsets)
        tail = lines[call.end_lineno - 1][call.end_col_offset :].strip()
        if tail and not tail.startswith("//"):
            raise StrategyAdapterError(
                "shared_statement_line", "호출 뒤 같은 줄의 다른 문장은 지원하지 않습니다"
            )
        condition = A.unparse(argument.value)
        temp = unique(f"qb_condition_{line}_{call.col_offset}")
        # 작은 expression만 unparse하며 AST 구조가 같은지 다시 확인한다.
        check = parse_to_ast(f"{temp} = {condition}\n").body[0]
        if A.dump(check.value) != A.dump(argument.value):
            raise StrategyAdapterError(
                "condition_render_mismatch", "조건 표현식 구조가 달라졌습니다"
            )
        arg_start, arg_end = _span(argument.value, lines, offsets)
        edits.append((call_start, call_start, f"{temp} = {condition}{newline}"))
        edits.append((arg_start, arg_end, temp))
        reviewed.append(
            {
                **dict(binding),
                "column": call.col_offset,
                "condition_variable": temp,
                "condition": condition,
            }
        )
        if direction.endswith("_exit"):
            continue
        flag = long_flag if direction == "long" else short_flag
        guard = (
            "strategy.position_size <= 0" if direction == "long" else "strategy.position_size >= 0"
        )
        if trade_start is not None:
            guard += f" and time >= {int(pd.Timestamp(utc_time(trade_start)).value // 1_000_000)}"
        pine_direction = (
            ("true" if direction == "long" else "false")
            if pine_version_from_ast(tree) < 4
            else f"strategy.{direction}"
        )
        trade_id = "L" if direction == "long" else "S"
        quantity_arg = "" if fixed_quantity is None else f", qty={fixed_quantity}"
        if has_exits:
            deferred_entries.append(
                (direction, temp, flag, guard, trade_id, pine_direction, quantity_arg)
            )
        else:
            after_call = offsets[call.end_lineno]
            separator = "" if after_call and source[after_call - 1] == "\n" else newline
            edits.append(
                (
                    after_call,
                    after_call,
                    f"{separator}if {temp} and {guard} and not {flag}{newline}"
                    f'    strategy.entry("{trade_id}", {pine_direction}{quantity_arg}){newline}'
                    f"    {flag} := true{newline}",
                )
            )
    if has_exits:
        # 원래 위치의 캡처값을 사용하고, 다음 봉 주문 큐에는 명시 청산을 먼저 넣는다.
        block = "" if source.endswith("\n") else newline
        exits = {}
        for direction, trade_id in (("long", "L"), ("short", "S")):
            conditions = [
                item["condition_variable"]
                for item in reviewed
                if item["direction"] == f"{direction}_exit"
            ]
            exits[direction] = " or ".join(conditions) or "false"
            if conditions:
                block += f'if {exits[direction]}{newline}    strategy.close("{trade_id}"){newline}'
        for (
            direction,
            temp,
            flag,
            guard,
            trade_id,
            pine_direction,
            quantity_arg,
        ) in deferred_entries:
            position_guard = (
                "strategy.position_size <= 0"
                if direction == "long"
                else "strategy.position_size >= 0"
            )
            guard = guard.replace(position_guard, f"({position_guard} or ({exits[direction]}))")
            block += (
                f"if {temp} and {guard} and not {flag}{newline}"
                f'    strategy.entry("{trade_id}", {pine_direction}{quantity_arg}){newline}'
                f"    {flag} := true{newline}"
            )
        edits.append((len(source), len(source), block))
        warnings.append(
            "명시 청산은 원문 조건을 캡처한 뒤 진입보다 먼저 다음 봉 주문 큐에 제출합니다"
        )
    edits.sort(key=lambda item: (item[0], item[1]))
    chunks, cursor = [], 0
    for first, last, text in edits:
        if first < cursor:
            raise StrategyAdapterError("overlapping_source_edits", "원본 편집 범위가 겹칩니다")
        chunks.extend((source[cursor:first], text))
        cursor = last
    converted = "".join((*chunks, source[cursor:]))

    def mapped_line(position: int) -> int | None:
        delta = 0
        for first, last, text in edits:
            if first == last and first <= position:
                delta += len(text)
            elif last <= position:
                delta += len(text) - (last - first)
            elif first < position < last:
                return None
            elif first == position:
                break
        return converted.count("\n", 0, position + delta) + 1

    line_map = {number: mapped_line(position) for number, position in enumerate(offsets[:-1], 1)}
    for binding in reviewed:
        binding["converted_line"] = line_map[binding["line"]]
    try:
        parse_to_ast(converted)
    except Exception as exc:
        raise StrategyAdapterError(
            "invalid_generated_strategy", "생성 전략의 Pine 문법을 검증하지 못했습니다"
        ) from exc
    return StrategyAdaptation(
        converted,
        hashlib.sha256(source.encode()).hexdigest(),
        hashlib.sha256(converted.encode()).hexdigest(),
        reviewed,
        warnings,
        line_map,
    )


def compare_app_backtest(
    source: str,
    frame: pd.DataFrame,
    inputs: Mapping[str, Any],
    timeframe: str,
    events: EventInput | None,
    *,
    window_start: Any = None,
    window_end: Any = None,
) -> dict[str, Any]:
    """원장과 앱을 같은 전체 history로 실행한다. 보고창 때문에 초기 포지션을 버리지 않는다."""
    from src.backtest.engine.types import BacktestConfig
    from src.backtest.engine.v2_adapter import run_backtest_v2

    if timeframe not in _SECONDS:
        return {"status": "unsupported_timeframe", "timeframe": timeframe, "executed": False}
    outcome = run_backtest_v2(
        source,
        frame,
        BacktestConfig(
            fees=0,
            slippage=0,
            maker_fee=0,
            leverage=1,
            include_funding=False,
            default_qty_type="strategy.fixed",
            default_qty_value=1,
            input_overrides=dict(inputs),
            freq="1D" if timeframe == "1d" else timeframe,
            fill_timing="next_bar_open",
        ),
    )
    if outcome.status != "ok" or outcome.result is None:
        return {
            "status": "app_backtest_failed",
            "executed": True,
            "app_status": outcome.status,
            "detail": str(outcome.error),
        }
    actual = []
    for trade in outcome.result.trades:
        actual.append(
            {
                "direction": trade.direction,
                "entry_time": utc_time(frame.index[trade.entry_bar_index]),
                "entry_price": trade.entry_price,
                "qty": trade.size,
                "exit_time": utc_time(frame.index[trade.exit_bar_index])
                if trade.exit_bar_index is not None
                else None,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl if trade.status == "closed" else None,
            }
        )

    def json_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: json_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [json_value(item) for item in value]
        if isinstance(value, Decimal):
            return format(value.normalize(), "f") if value else "0"
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    execution = {"executed": True, "app_status": "ok", "app_trades": json_value(actual)}
    if events is None:
        return {**execution, "status": "missing_signal_ledger"}
    try:
        signals = coerce_events(events)
        ledger = simulate_futures(frame, signals)
    except (ValueError, TypeError, KeyError) as exc:
        return {**execution, "status": "invalid_signal_ledger", "detail": str(exc)}
    expected = [
        {
            "direction": trade.direction,
            "entry_time": trade.entry_time,
            "entry_price": trade.entry_price,
            "qty": trade.qty,
            "exit_time": trade.exit_time,
            "exit_price": trade.exit_price,
            "pnl": trade.pnl,
        }
        for trade in [*ledger.trades, *([ledger.open_position] if ledger.open_position else [])]
    ]
    differences = []
    if len(actual) != len(expected):
        differences.append({"field": "trade_count", "app": len(actual), "ledger": len(expected)})
    for index, (left, right) in enumerate(zip(actual, expected, strict=False)):
        for field, value in left.items():
            if value != right[field]:
                differences.append(
                    {"trade_index": index, "field": field, "app": value, "ledger": right[field]}
                )

    status = (
        "mismatch"
        if differences
        else "exact_match"
        if actual
        else "no_fills"
        if signals
        else "no_signal"
    )
    return json_value(
        {
            **execution,
            "status": status,
            "execution_policy": "whole_frame_both_paths",
            "execution_window": {
                "start": utc_time(frame.index[0]),
                "end": utc_time(frame.index[-1]) + timedelta(seconds=_SECONDS[timeframe]),
                "bars": len(frame),
            },
            "report_window": {
                "start": utc_time(window_start) if window_start is not None else None,
                "end": utc_time(window_end) if window_end is not None else None,
            },
            "assumptions": {
                "fill_timing": "next_bar_open",
                "qty": "1",
                "fees": "0",
                "slippage": "0",
                "funding": "0",
                "leverage": 1,
            },
            "app_trades": actual,
            "ledger_trades": expected,
            "differences": differences,
            "pending_signal_events": [event.to_dict() for event in ledger.pending_events],
            "pending_queue_compared": False,
        }
    )
