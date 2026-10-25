"""Pine은 지표·진입 의도만 계산하고 체결은 외부 공통 원장이 결정한다."""

from __future__ import annotations

import math
import re
from itertools import pairwise
from typing import Any, cast

import pandas as pd

from src.strategy.code_runtime.models import PROTOCOL_VERSION, CodeRuntimeError
from src.strategy.pine_v2.ast_classifier import _call_name, _detect_declaration, _walk
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.interpreter import BarContext, Interpreter, pine_version_from_ast
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.strategy_state import Trade
from src.strategy.python_runtime.sandbox import DockerPythonTransport

_ALLOWED_ORDERS = {"strategy.entry", "strategy.close", "strategy.close_all"}

_CONTEXT_TIMEFRAME_ATTRIBUTES = frozenset(
    {
        "timeframe.period",
        "timeframe.multiplier",
        "timeframe.isseconds",
        "timeframe.isminutes",
        "timeframe.isintraday",
        "timeframe.isdaily",
        "timeframe.isweekly",
        "timeframe.ismonthly",
    }
)


def validated_timeframe(ohlcv: pd.DataFrame) -> str | None:
    """명시한 source 봉 주기를 실제 UTC index 격자와 대조한다. 주기를 추론하지 않는다."""
    if "timeframe" not in ohlcv.attrs:
        return None
    value = ohlcv.attrs["timeframe"]
    match = re.fullmatch(r"([1-9]\d*)([smhdw])", value) if isinstance(value, str) else None
    if match is None:
        raise CodeRuntimeError("Pine timeframe context 형식이 다릅니다")
    count, unit = int(match[1]), match[2]
    if (
        (unit == "s" and count not in {1, 5, 10, 15, 30, 45})
        or (unit == "m" and count > 1440)
        or (unit == "h" and count > 24)
        or (unit in {"d", "w"} and count != 1)
    ):
        raise CodeRuntimeError("검증하지 않은 Pine timeframe context입니다")
    seconds = count * {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
    if unit in {"s", "m", "h"} and 86400 % seconds:
        raise CodeRuntimeError("검증하지 않은 Pine intraday 주기 anchor입니다")
    index = ohlcv.index
    if (
        not isinstance(index, pd.DatetimeIndex)
        or index.tz is None
        or index.hasnans
        or len(index) < 2
        or not index.is_unique
        or not index.is_monotonic_increasing
    ):
        raise CodeRuntimeError(
            "Pine timeframe context에는 정렬된 timezone-aware 2봉 이상이 필요합니다"
        )
    step = pd.Timedelta(seconds=seconds)
    if not all(right - left == step for left, right in pairwise(index)):
        raise CodeRuntimeError("Pine timeframe context와 실제 봉 간격이 다릅니다")
    period_ns = seconds * 1000000000
    anchor_ns = -3 * 86400 * 1000000000 if unit == "w" else 0
    if any(
        (stamp.value - anchor_ns) % period_ns for stamp in index.tz_convert("UTC").as_unit("ns")
    ):
        raise CodeRuntimeError("Pine timeframe context의 UTC 봉 격자가 다릅니다")
    return cast(str, value)


DEFAULT_PINE_IMAGE = "quantbridge-pine-runner:local"


class PineSignalTransport(DockerPythonTransport):
    """기존 Pine 해석기를 동일한 gVisor·900초·1GiB 경계에서 실행한다."""

    def __init__(self, ohlcv: pd.DataFrame, timeout: float = 900) -> None:
        from src.strategy.python_runtime.serialization import bars_payload

        if not math.isfinite(timeout) or timeout <= 0:
            raise CodeRuntimeError("Pine 실행 제한은 유한한 양수여야 합니다")
        timeframe = validated_timeframe(ohlcv)
        super().__init__(image=DEFAULT_PINE_IMAGE, timeout=timeout)
        try:
            message: dict[str, Any] = {"type": "load", "bars": bars_payload(ohlcv)}
            if timeframe is not None:
                message["timeframe"] = timeframe
            expected: dict[str, Any] = {"loaded": True}
            if timeframe is not None:
                expected["timeframe"] = timeframe
            if self.exchange(message) != expected:
                raise CodeRuntimeError("Pine worker 데이터·timeframe 초기화 확인 실패")
        except BaseException as error:
            try:
                self.close()
            except BaseException as cleanup_error:
                error.add_note(f"격리 실행기 회수 실패: {type(cleanup_error).__name__}")
            raise

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        try:
            return super().exchange(message)
        except Exception:
            self.close()
            raise


class _PineInterpreterTransport:
    """외부에서 확정한 포지션을 주입한다. Pine 내부 체결 루프는 호출하지 않는다."""

    def __init__(self, ohlcv: pd.DataFrame) -> None:
        self._ohlcv = ohlcv
        self._timeframe = validated_timeframe(ohlcv)
        self._interpreter: Interpreter | None = None
        self._tree: Any = None
        self._entry_id = "code"
        self._entry_bar = 0
        self._previous_direction = "flat"

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        if message.get("type") == "init":
            if self._interpreter is not None or message.get("protocol") != PROTOCOL_VERSION:
                raise CodeRuntimeError("Pine 실행기 초기화 순서 또는 버전이 다릅니다")
            source = message["source"]
            coverage = analyze_coverage(source)
            degraded = set(coverage.degraded_calls)
            if self._timeframe is not None:
                degraded -= _CONTEXT_TIMEFRAME_ATTRIBUTES
            elif set(coverage.used_attributes) & _CONTEXT_TIMEFRAME_ATTRIBUTES:
                raise CodeRuntimeError("Pine 주기 속성에는 검증한 timeframe context가 필요합니다")
            if not coverage.is_runnable or degraded:
                raise CodeRuntimeError("Pine 공통 실행기는 미지원·근사 기능을 허용하지 않습니다")
            self._tree = parse_to_ast(source)
            if _detect_declaration(self._tree) != "strategy":
                raise CodeRuntimeError("Pine 코드는 strategy 선언이 필요합니다")
            for node in _walk(self._tree):
                name = _call_name(node)
                if name and name.startswith("strategy."):
                    if name not in _ALLOWED_ORDERS:
                        raise CodeRuntimeError(
                            "Pine 공통 실행기는 시장가 entry/close 의도만 지원합니다"
                        )
                    names = {getattr(arg, "name", None) for arg in node.args}
                    allowed = {"when", "comment", None}
                    if name != "strategy.close_all":
                        allowed.add("id")
                    if name == "strategy.entry":
                        allowed.add("direction")
                    positional = sum(getattr(arg, "name", None) is None for arg in node.args)
                    maximum = (
                        2 if name == "strategy.entry" else 1 if name == "strategy.close" else 0
                    )
                    if names - allowed or positional > maximum:
                        raise CodeRuntimeError(
                            "Pine 수량·가격·부분 주문은 공통 리스크 원장이 결정합니다"
                        )
                    if name == "strategy.entry":
                        args = [arg for arg in node.args if getattr(arg, "name", None) is None]
                        direction_node = next(
                            (
                                arg.value
                                for arg in node.args
                                if getattr(arg, "name", None) == "direction"
                            ),
                            args[1].value if len(args) > 1 else None,
                        )
                        if (
                            getattr(direction_node, "attr", None) not in ("long", "short")
                            or getattr(getattr(direction_node, "value", None), "id", None)
                            != "strategy"
                        ):
                            raise CodeRuntimeError(
                                "Pine 진입 방향은 strategy.long/short를 명시해야 합니다"
                            )
            bar = BarContext(
                self._ohlcv.reset_index(drop=True),
                timestamps=cast(pd.DatetimeIndex, self._ohlcv.index),
                pine_version=pine_version_from_ast(self._tree),
                timeframe=self._timeframe,
            )
            self._interpreter = Interpreter(
                bar, PersistentStore(), input_overrides=message["params"]
            )
            self._interpreter.strategy.fill_timing = "next_bar_open"
            return {"ready": PROTOCOL_VERSION}
        interp = self._interpreter
        if message.get("type") != "bar" or interp is None:
            raise CodeRuntimeError("Pine 실행기가 초기화되지 않았습니다")
        if not interp.bar.advance() or interp.bar.bar_index != message["bar"]["index"]:
            raise CodeRuntimeError("Pine 봉 전달 순서가 다릅니다")
        position = message["position"]
        direction = position["direction"]
        state = interp.strategy
        state.open_trades.clear()
        state.pending_market_intents.clear()
        if direction != "flat":
            if direction != self._previous_direction:
                self._entry_bar = interp.bar.bar_index
            state.open_trades[self._entry_id] = Trade(
                id=self._entry_id,
                direction=direction,
                qty=float(position["size"]),
                entry_bar=self._entry_bar,
                entry_price=float(position["average_price"]),
                entry_phase="bar_open",
            )
        self._previous_direction = direction
        interp.store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(self._tree)
        interp.store.commit_bar()
        interp.append_var_series()
        orders = state.pending_market_intents
        entries = [order for order in orders if order.kind == "entry"]
        directions = {order.direction for order in entries}
        if len(directions) > 1:
            raise CodeRuntimeError("같은 봉의 양방향 진입 의도는 지원하지 않습니다")
        action = "hold"
        if entries and str(entries[-1].direction) != direction:
            chosen = entries[-1]
            action = str(chosen.direction)
            self._entry_id = chosen.trade_id
        elif any(
            order.kind == "close_all"
            or (order.kind == "close" and order.trade_id == self._entry_id)
            for order in orders
        ):
            action = "close"
        elif entries:
            action = str(entries[-1].direction)
        state.pending_market_intents.clear()
        if state.closed_trades or state.events or state.pending_orders or state.pending_exits:
            raise CodeRuntimeError("Pine 내부 체결이 발생해 공통 원장과 분리할 수 없습니다")
        return {"intent": {"action": action}}

    def close(self) -> None:
        self._interpreter = None
        self._tree = None
