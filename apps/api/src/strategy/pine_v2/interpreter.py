"""Pine AST interpreter (Week 2 Day 1-2) — ADR-011 Tier-0 핵심.

pynescript AST 위에서 bar-by-bar 실행되는 tree-walking 인터프리터.
Day 8 통합 POC의 "수작업 해석"을 체계적 visitor로 확장.

Day 1-2 범위:
- 표현식: Constant / Name / BinOp / UnaryOp / BoolOp / Compare / Conditional(ternary) / Subscript / Attribute / Call(stdlib pass-through)
- 문장: Assign (regular / var / varip) / ReAssign / If(+orelse) / Expr (호출 포함)
- built-in 변수: open / high / low / close / volume / bar_index / na / true / false
- Pine history `close[n]` = n bar 전 값 (DataFrame look-back)

범위 밖 (2단계 이상):
- 함수 정의 / 호출 (=>, builtins ta.* 등 stdlib 미지원 — Call은 에러 발생)
- for / while 루프
- 배열 / Matrix / Map / UDT
- strategy.* 실행 핸들러 (포지션 상태)
- 렌더링 호출 (plot/box/label/line/table) — 조용히 NOP 처리

공개 API:
- `Interpreter(bar_context, store)` — 생성
- `interp.execute(tree)` — 한 bar 분량 실행 (이벤트 루프가 반복 호출)

Key 네이밍 관례:
- 영속(var/varip): `main::{name}` — PersistentStore에 저장
- 비영속(transient): `{name}` — dict에 저장 (매 bar 초기화)
"""

from __future__ import annotations

import math
import operator
import re
from collections import deque
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pandas as pd
from pynescript import ast as pyne_ast

from src.strategy.pine_v2._names import CAST_FUNCTIONS, STDLIB_NAMES
from src.strategy.pine_v2.rendering import (
    BoxObject,
    LabelObject,
    LineObject,
    RenderingRegistry,
    TableObject,
)
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.signal_trace import SignalFunction, SignalObservation
from src.strategy.pine_v2.stdlib import StdlibDispatcher
from src.strategy.pine_v2.strategy_state import PendingMarketExitError, StrategyState

# BL-200 (Sprint 47): STDLIB_NAMES 는 `_names.py` 에서 re-export.
# 이전 inline frozenset 정의는 coverage.py 와 Triple SSOT 였음 (interpreter /
# coverage / stdlib dispatch). 본 import 로 단일 소스 + object identity 동일
# (`STDLIB_NAMES is _names.STDLIB_NAMES` True). 새 stdlib 추가 시 `_names.py`
# 한 곳만 갱신 + stdlib.py dispatch 분기 추가 + tests/strategy/pine_v2/
# test_ssot_invariants.py 가 자동 검증.

# Pine v4 legacy alias — prefix 없는 stdlib (atr/ema/sma/rsi/crossover/...) 을
# ta.* / math.* 로 재라우팅. (i1_utbot 및 일부 RTB 전략이 v4 문법 사용)
# Sprint 29 Slice C: function-local dict 에서 module-level export.
# parity invariant: `_V4_ALIASES.values() ⊆ STDLIB_NAMES` (test_ssot_invariants.py).
_V4_ALIASES: dict[str, str] = {
    "atr": "ta.atr",
    "ema": "ta.ema",
    "sma": "ta.sma",
    "wma": "ta.wma",
    "rsi": "ta.rsi",
    "crossover": "ta.crossover",
    "crossunder": "ta.crossunder",
    "cross": "ta.cross",
    "highest": "ta.highest",
    "lowest": "ta.lowest",
    "change": "ta.change",
    "pivothigh": "ta.pivothigh",
    "pivotlow": "ta.pivotlow",
    "barssince": "ta.barssince",  # Sprint 8c
    "valuewhen": "ta.valuewhen",  # Sprint 8c
    "max": "math.max",
    "min": "math.min",
    "abs": "math.abs",
    "floor": "math.floor",
    "round": "math.round",
    "sqrt": "math.sqrt",
    "avg": "math.avg",
    "stdev": "ta.stdev",
}

# Pine enum constants — value 매핑 (location.absolute, extend.right, shape.*, etc.)
# Sprint 29 Slice C: function-local dict 에서 module-level dict 으로 export.
# coverage._ENUM_PREFIXES 와 parity invariant 검증 대상 (test_ssot_invariants.py).
_ATTR_CONSTANTS: dict[str, str] = {
    # v4 input(..., type=input.integer) 등의 타입 상수다. input.*() 함수와 별개다.
    "input.integer": "integer",
    "input.float": "float",
    "input.bool": "bool",
    "input.source": "source",
    # 수집 원본의 표시 전용 상수다. 미지의 format/plot 속성은 계속 오류로 둔다.
    "format.price": "price",
    "plot.style_line": "line",
    "plot.style_linebr": "linebr",
    "plot.style_circles": "circles",
    "plot.style_cross": "cross",
    "plot.style_columns": "columns",
    "hline.style_dotted": "dotted",
    "hline.style_solid": "solid",
    "hline.style_dashed": "dashed",
    "strategy.long": "long",
    "strategy.short": "short",
    # Sprint 37 BL-185: Pine strategy(default_qty_type=...) 3종 — interpreter 가
    # `t = strategy.percent_of_equity` 같은 attribute access 를 evaluate 가능하도록 등록.
    # coverage._STRATEGY_CONSTANTS_EXTRA 와 SSOT invariant audit 자동 검증.
    "strategy.fixed": "strategy.fixed",
    "strategy.cash": "strategy.cash",
    "strategy.percent_of_equity": "strategy.percent_of_equity",
    # S2 (전체 정검 P1-10/13): commission_type 3종 — coverage._STRATEGY_CONSTANTS_EXTRA
    # 가 SUPPORTED 표기하나 _ATTR_CONSTANTS 누락이던 누출 (strategy.fixed 패턴 동일).
    "strategy.commission_percent": "strategy.commission_percent",
    "strategy.commission_cash_per_contract": "strategy.commission_cash_per_contract",
    "strategy.commission_cash_per_order": "strategy.commission_cash_per_order",
    # 렌더링 scope A — enum 상수 (string identity 유지)
    "line.style_dashed": "dashed",
    "line.style_dotted": "dotted",
    "line.style_solid": "solid",
    "line.style_arrow_left": "arrow_left",
    "line.style_arrow_right": "arrow_right",
    "line.style_arrow_both": "arrow_both",
    "extend.none": "none",
    "extend.left": "left",
    "extend.right": "right",
    "extend.both": "both",
    "shape.labelup": "labelup",
    "shape.labeldown": "labeldown",
    "shape.triangleup": "triangleup",
    "shape.triangledown": "triangledown",
    "shape.arrowup": "arrowup",
    "shape.arrowdown": "arrowdown",
    "shape.circle": "circle",
    "shape.cross": "cross",
    "shape.xcross": "xcross",
    "shape.flag": "flag",
    "shape.square": "square",
    "shape.diamond": "diamond",
    "location.absolute": "absolute",
    "location.abovebar": "abovebar",
    "location.belowbar": "belowbar",
    "location.top": "top",
    "location.bottom": "bottom",
    "size.auto": "auto",
    "size.tiny": "tiny",
    "size.small": "small",
    "size.normal": "normal",
    "size.large": "large",
    "size.huge": "huge",
    "position.top_left": "top_left",
    "position.top_center": "top_center",
    "position.top_right": "top_right",
    "position.middle_left": "middle_left",
    "position.middle_center": "middle_center",
    "position.middle_right": "middle_right",
    "position.bottom_left": "bottom_left",
    "position.bottom_center": "bottom_center",
    "position.bottom_right": "bottom_right",
}

# ------------------------------------------------------------
# Bar Context — OHLCV 시계열 접근 계층
# ------------------------------------------------------------


def pine_version_from_ast(tree: Any) -> int:
    """문자열 리터럴이 아닌 파서의 compiler annotation에서 버전을 읽는다."""
    for annotation in getattr(tree, "annotations", []):
        match = re.fullmatch(r"//\s*@version\s*=\s*(\d+)\s*", annotation)
        if match is not None:
            return int(match[1])
    return 1


@dataclass
class BarContext:
    """현재 bar + 히스토리 접근 인터페이스.

    Pine의 `close`는 현재 bar의 종가. `close[n]`은 n bar 전 종가.
    na(not available): 히스토리가 없는 구간 → float('nan') 반환.

    BL-188 v3: timestamps (Optional DatetimeIndex) — entry placement gate 가
    `current_timestamp()` 로 tz-aware bar timestamp 를 얻어 `is_allowed` 평가.
    None 이면 session gate skip (회귀 호환 — 기존 BarContext(ohlcv) 호출).
    """

    ohlcv: pd.DataFrame  # columns: open/high/low/close/volume (float)
    bar_index: int = -1
    timestamps: pd.DatetimeIndex | None = None
    timeframe: str | None = None
    pine_version: int = 6
    _timeframe_attributes: dict[str, str | int | bool] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        if self.timeframe is None:
            return
        match = re.fullmatch(r"([1-9]\d*)([smhdwM])", self.timeframe)
        if match is None:
            raise ValueError(f"Unsupported timeframe context: {self.timeframe!r}")
        count, unit = int(match[1]), match[2]
        multiplier = count * 60 if unit == "h" else count
        suffix = {"s": "S", "m": "", "h": "", "d": "D", "w": "W", "M": "M"}[unit]
        prefix = (
            ""
            if self.pine_version < 6 and count == 1 and unit in {"d", "w", "M"}
            else str(multiplier)
        )
        self._timeframe_attributes = {
            "timeframe.period": f"{prefix}{suffix}",
            "timeframe.multiplier": multiplier,
            "timeframe.isseconds": unit == "s",
            "timeframe.isminutes": unit in {"m", "h"},
            "timeframe.isdaily": unit == "d",
            "timeframe.isweekly": unit == "w",
            "timeframe.ismonthly": unit == "M",
        }

    def advance(self) -> bool:
        """다음 bar로 이동. 데이터가 남아있으면 True, 끝났으면 False."""
        self.bar_index += 1
        return self.bar_index < len(self.ohlcv)

    def current(self, field: str) -> float:
        return float(self.ohlcv.iloc[self.bar_index][field])

    def history(self, field: str, offset: int) -> float:
        """offset bar 이전 값. 음수/범위 밖 → nan (Pine의 na)."""
        if offset < 0:
            raise ValueError(f"history offset must be >= 0, got {offset}")
        idx = self.bar_index - offset
        if idx < 0:
            return float("nan")
        return float(self.ohlcv.iloc[idx][field])

    def current_timestamp(self) -> pd.Timestamp | None:
        """현재 bar 의 tz-aware timestamp. timestamps 미주입 시 None.

        v2_adapter 가 tz-naive sessions-only 활성 시 422 reject 하므로, 본 메서드가
        is_allowed 에 전달하는 ts 는 tz-aware 만 도달.
        """
        if self.timestamps is None:
            return None
        if self.bar_index < 0 or self.bar_index >= len(self.timestamps):
            return None
        stamp = self.timestamps[self.bar_index]
        return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")

    def timeframe_attribute(self, name: str) -> str | int | bool | None:
        return self._timeframe_attributes.get(name)


# ------------------------------------------------------------
# Interpreter — Pine AST visit + 표현식 평가 + 문장 실행
# ------------------------------------------------------------


_BUILTIN_SERIES = frozenset({"open", "high", "low", "close", "volume"})

# S2 (전체 정검 P1-10/13): 합성 source — OHLC 로부터 계산되는 built-in series.
# _BUILTIN_SERIES 와 달리 DataFrame 컬럼이 없어 _synthetic_source 로 계산.
_SYNTHETIC_SERIES = frozenset({"hl2", "hlc3", "ohlc4"})

# 렌더링 scope A (ADR-011 §2.0.4) — factory/getter는 name 기반 직접 dispatch.
# handle.method() 형식은 _exec_rendering_method에서 타입별 접두어로 라우팅.
_RENDERING_FACTORIES: dict[str, str] = {
    "line.new": "line_new",
    "box.new": "box_new",
    "label.new": "label_new",
    "table.new": "table_new",
    "line.get_price": "line_get_price",
    "box.get_top": "box_get_top",
    "box.get_bottom": "box_get_bottom",
    "line.set_xy1": "line_set_xy1",
    "line.set_xy2": "line_set_xy2",
    "line.delete": "line_delete",
    "box.set_right": "box_set_right",
    "box.delete": "box_delete",
    "label.set_xy": "label_set_xy",
    "label.set_x": "label_set_x",
    "label.delete": "label_delete",
    "table.cell": "table_cell",
    "table.delete": "table_delete",
}

# 연산자 매핑
_BINOP: dict[str, Any] = {
    "Add": operator.add,
    "Sub": operator.sub,
    "Mult": operator.mul,
    "Div": operator.truediv,
    "Mod": operator.mod,
    "Pow": operator.pow,
}
_CMPOP: dict[str, Any] = {
    "Eq": operator.eq,
    "NotEq": operator.ne,
    "Lt": operator.lt,
    "LtE": operator.le,
    "Gt": operator.gt,
    "GtE": operator.ge,
}
# BoolOp 단축평가는 _eval_boolop에서 직접 처리 (And/Or)


class PineRuntimeError(RuntimeError):
    """Pine 실행 중 발생한 오류 (미지원 노드, 미정의 변수 등)."""


# G1 (2026-07-12 pine-batch QA) — 루프 제어 흐름. PineRuntimeError 서브클래스라
# 루프 밖 stray break/continue 는 strict 모드에서 그대로 loud 하게 전파된다.
class LoopBreak(PineRuntimeError):
    """`break` — 가장 안쪽 루프 핸들러가 catch."""


class LoopContinue(PineRuntimeError):
    """`continue` — 가장 안쪽 루프 핸들러가 catch."""


# TV 는 loop 당 500ms 시간 제한 → 본 엔진은 결정적 iteration 상한 채택.
_LOOP_ITERATION_CAP = 100_000

# Expr 로 래핑되어 오는 문장형 노드 (pynescript 는 top-level 문장을 Expr(value=...) 로 감쌈)
_STATEMENT_EXPR_NODES = (
    pyne_ast.If,
    pyne_ast.ForTo,
    pyne_ast.ForIn,
    pyne_ast.While,
    pyne_ast.Break,
    pyne_ast.Continue,
)


@dataclass
class _FunctionFrame:
    """호출 경로별 binding과 아직 확정되지 않은 scalar 이력."""

    path: tuple[str, ...]
    params: frozenset[str]
    declarations: dict[str, str | None]
    staged: dict[tuple[tuple[str, ...], str], Any] = field(default_factory=dict)
    loop_names: set[str] = field(default_factory=set)


class Interpreter:
    """Pine AST interpreter — per-bar 실행.

    Usage:
        bar = BarContext(ohlcv)
        store = PersistentStore()
        interp = Interpreter(bar, store)
        while bar.advance():
            store.begin_bar()
            interp.reset_transient()
            interp.execute(tree)
            store.commit_bar()
    """

    def __init__(
        self,
        bar_context: BarContext,
        store: PersistentStore,
        *,
        rendering: RenderingRegistry | None = None,
        input_overrides: Mapping[str, Any] | None = None,
        capture_signals: bool = False,
    ) -> None:
        self.bar = bar_context
        self.store = store
        # 비영속(transient) 변수 — 매 bar 재초기화
        self._transient: dict[str, Any] = {}
        # 사용자 정의 함수 (=>) — Script.body의 FunctionDef 노드 보관. 호출은 _eval_call에서 dispatch.
        self._user_functions: dict[str, Any] = {}
        # 함수 호출 중 로컬 스코프 스택. 최상단 = 현재 frame. 빈 리스트 = 최상위.
        self._scope_stack: list[dict[str, Any]] = []
        self._function_frames: list[_FunctionFrame] = []
        self._function_declarations: dict[str, dict[str, str | None]] = {}
        self._local_history: dict[tuple[tuple[str, ...], str], deque[tuple[int, Any]]] = {}
        self._local_pending: dict[tuple[tuple[str, ...], str], Any] = {}
        self._loop_depth = 0
        # 재귀 depth guard (Pine은 공식 재귀 미지원; 무한 재귀 방지).
        self._max_call_depth: int = 32
        # ta.* stdlib 디스패처 (bar 교차 상태 유지)
        self.stdlib = StdlibDispatcher()
        # strategy.* 실행 상태 (포지션/체결 기록)
        self.strategy = StrategyState()
        # 사용자 변수 시리즈 — 각 변수명 → deque[bar별 값...]. `myvar[n]` 지원용.
        # max_bars_back=500: Pine v5 기본값과 동일. 메모리 한계 방지.
        self._max_bars_back: int = 500
        self._var_series: dict[str, deque[Any]] = {}
        # 이전 close (ta.atr 등 prev close 필요 시 사용)
        self._prev_close: float = float("nan")
        # 렌더링 scope A — line/box/label/table 객체 handle 관리
        self.rendering = rendering or RenderingRegistry()
        # Sprint 51 BL-220 — pine_v2 input override (Param Stability grid sweep).
        # key = pine InputDecl.var_name, value = Decimal/int/bool/str.
        # _eval_call() input.* handler 가 _assignment_target_stack[-1] 으로 lookup.
        # codex G.0 P1#2: _exec_assign 에서 RHS eval 전 push, 후 pop (try/finally).
        self.input_overrides: Mapping[str, Any] | None = input_overrides
        self._assignment_target_stack: list[str] = []
        self.capture_signals = capture_signals
        # 변수 history ring과 달리 전체 평가 구간의 관찰값을 보존한다.
        self.signal_trace: list[SignalObservation] = []
        self.degraded_calls_seen: list[str] = []

    def reset_transient(self) -> None:
        self._transient = {}
        self._local_pending.clear()

    def begin_bar_snapshot(self) -> None:
        """Bar 시작 시 호출 — ta.atr 등 prev-close 참조용.

        이벤트 루프 정책: bar.advance() 후 begin_bar → begin_bar_snapshot → execute → commit_bar → 시리즈 append
        """
        # 첫 bar는 prev_close == nan; 그 이후엔 직전 bar_index의 close
        idx = self.bar.bar_index
        self._prev_close = float(self.bar.ohlcv.iloc[idx - 1]["close"]) if idx > 0 else float("nan")

    def append_var_series(self) -> None:
        """Bar 종료 시 호출 — 현재 bar의 모든 user 변수 값을 시리즈에 append.

        transient + persistent 양쪽 수집. `myvar[n]` subscript는 과거 bar 값을 찾을 때 이 시리즈 조회.
        deque(maxlen=_max_bars_back) 사용으로 메모리 상한 보장.
        """
        # transient: bare name
        for name, value in self._transient.items():
            if name not in self._var_series:
                self._var_series[name] = deque(maxlen=self._max_bars_back)
            self._var_series[name].append(value)
        # persistent: "main::name" 접두어 제거
        for full_key, value in self.store.snapshot_dict().items():
            if full_key.startswith("udf:"):
                continue
            short = full_key.split("::", 1)[1] if "::" in full_key else full_key
            if short not in self._var_series:
                self._var_series[short] = deque(maxlen=self._max_bars_back)
            self._var_series[short].append(value)
        for key, value in self._local_pending.items():
            history = self._local_history.setdefault(key, deque(maxlen=self._max_bars_back))
            history.append((self.bar.bar_index, value))
        self._local_pending.clear()

    def global_state_snapshot(self) -> dict[str, Any]:
        """함수 내부 슬롯은 기존 전역 진단 snapshot으로 유출하지 않는다."""
        return {
            key: value
            for key, value in self.store.snapshot_dict().items()
            if not key.startswith("udf:")
        } | self._transient

    # ---- 실행 엔트리 --------------------------------------------------

    def execute(self, tree: Any) -> None:
        """pynescript Script 노드의 body를 순차 실행 (한 bar 분량)."""
        for stmt in getattr(tree, "body", []):
            self._exec_stmt(stmt)

    # ---- 문장 디스패치 -------------------------------------------------

    def _exec_stmt(self, node: Any) -> None:
        if isinstance(node, pyne_ast.Expr):
            # pynescript는 top-level 문장(if/for/while/break/continue)을
            # Expr(value=...)로 래핑함 — 문장형이면 unwrap 후 아래 디스패치로.
            inner = node.value
            if isinstance(inner, _STATEMENT_EXPR_NODES):
                node = inner
            else:
                # 표현식 문장: 호출 등 side-effect만 있는 것 (e.g., alert)
                self._eval_expr(inner)
                return
        if isinstance(node, pyne_ast.Assign):
            self._exec_assign(node)
        elif isinstance(node, pyne_ast.ReAssign):
            self._exec_reassign(node)
        elif isinstance(node, pyne_ast.AugAssign):
            raise PineRuntimeError("compound assignment is not supported")
        elif isinstance(node, pyne_ast.If):
            self._exec_if(node)
        elif isinstance(node, pyne_ast.ForTo):
            self._exec_scoped_loop(node, self._exec_for_to)
        elif isinstance(node, pyne_ast.ForIn):
            self._exec_scoped_loop(node, self._exec_for_in)
        elif isinstance(node, pyne_ast.While):
            self._exec_while(node)
        elif isinstance(node, pyne_ast.Break):
            raise LoopBreak("break outside loop")
        elif isinstance(node, pyne_ast.Continue):
            raise LoopContinue("continue outside loop")
        elif isinstance(node, pyne_ast.FunctionDef):
            # Pine user function 정의: top-level에서만 등록. 호출은 _eval_call에서 dispatch.
            # (함수 내부 중첩 함수 정의는 H2+ — Pine 공식 범위 밖.)
            if not self._scope_stack:
                self._user_functions[node.name] = node
        else:
            # Return 등 잔여 범위 밖 노드 — 조용히 skip
            pass

    def _exec_assign(self, node: Any) -> None:
        """`x = expr`, `var x = expr`, `varip x = expr`, `[a, b] = expr` 처리.

        Var/VarIp marker 자식 노드로 유형 구분. 대상 Name이 없는 destructure는 Tuple/List
        unpack으로 처리.
        """
        var_kind = self._detect_var_kind(node)
        targets_attr = getattr(node, "targets", None)
        target_list = targets_attr if targets_attr else [getattr(node, "target", None)]
        primary = target_list[0] if target_list else None

        # Tuple / List 좌변 — multi-return unpack. var/varip 미지원(H2+).
        if isinstance(primary, pyne_ast.Tuple):
            if var_kind is not None:
                raise PineRuntimeError("var/varip with tuple destructuring is not supported")
            value = (
                self._eval_expr(node.value) if getattr(node, "value", None) is not None else None
            )
            elts = primary.elts
            if not isinstance(value, (tuple, list)) or len(value) != len(elts):
                expected = len(elts)
                got = len(value) if isinstance(value, (tuple, list)) else "scalar"
                raise PineRuntimeError(f"tuple unpack: expected {expected} values, got {got}")
            for name_node, item in zip(elts, value, strict=True):
                if not isinstance(name_node, pyne_ast.Name):
                    raise PineRuntimeError("tuple unpack target must be identifier")
                if self._scope_stack:
                    self._scope_stack[-1][name_node.id] = item
                else:
                    self._transient[name_node.id] = item
            return

        # 단일 Name target (기존 경로)
        target_name = next(
            (t.id for t in target_list if isinstance(t, pyne_ast.Name)),
            None,
        )
        if target_name is None:
            return

        if var_kind is not None:
            # 영속: 첫 bar에서만 RHS 평가. PersistentStore.declare_if_new가 lazy 처리.
            key = (
                self._local_persistent_key(target_name)
                if self._function_frames
                else f"main::{target_name}"
            )
            value_expr = node.value

            def factory() -> Any:
                # Sprint 51 BL-220 (codex Slice 2 review P1) — `var x = input.int(...)`
                # 또는 `varip` 패턴에서 deferred factory 평가 시점에도 input override
                # hook 활성. push/pop 누락 시 stack empty → _eval_call() 가 override
                # 무시 → silent failure (Param Stability grid 가 default 만 사용).
                self._assignment_target_stack.append(target_name)
                try:
                    return self._eval_expr(value_expr)
                finally:
                    self._assignment_target_stack.pop()

            value = self.store.declare_if_new(
                key,
                factory,
                varip=(var_kind == "varip"),
            )
            if self._scope_stack:
                self._scope_stack[-1][target_name] = value
        else:
            # 비영속: 매 bar 평가. 함수 호출 중이면 로컬 frame에 기록.
            # Sprint 51 BL-220 (codex G.0 P1#2): input.* override 를 위해 RHS eval
            # 전에 assignment target name 을 stack 에 push. eval 후 try/finally 로 pop.
            # _eval_call() input.* handler 가 stack[-1] 로 var_name lookup.
            self._assignment_target_stack.append(target_name)
            try:
                value = (
                    self._eval_expr(node.value)
                    if getattr(node, "value", None) is not None
                    else None
                )
            finally:
                self._assignment_target_stack.pop()
            if self._scope_stack:
                self._scope_stack[-1][target_name] = value
            else:
                self._transient[target_name] = value

    def _exec_reassign(self, node: Any) -> None:
        """`x := expr` — 재할당. 로컬 frame > PersistentStore > transient 순."""
        targets_attr = getattr(node, "targets", None)
        target_list = targets_attr if targets_attr else [getattr(node, "target", None)]
        target_name = next(
            (t.id for t in target_list if isinstance(t, pyne_ast.Name)),
            None,
        )
        if target_name is None:
            return
        if self._function_frames:
            frame = self._function_frames[-1]
            if target_name in frame.params or target_name not in self._scope_stack[-1]:
                raise PineRuntimeError(f"UDF cannot reassign parameter or nonlocal: {target_name}")
        value = self._eval_expr(node.value)
        # 로컬 scope 활성 & 해당 이름이 현재 frame에 존재 → frame에 재할당.
        if self._scope_stack and target_name in self._scope_stack[-1]:
            self._scope_stack[-1][target_name] = value
            if self._function_frames and self._function_frames[-1].declarations.get(
                target_name
            ) in ("var", "varip"):
                self.store.set(self._local_persistent_key(target_name), value)
            return
        key = f"main::{target_name}"
        if self.store.is_declared(key):
            self.store.set(key, value)
        elif target_name in self._transient:
            self._transient[target_name] = value
        else:
            # 인터프리터는 관대하게 transient 생성. 함수 내부면 로컬 frame에.
            if self._scope_stack:
                self._scope_stack[-1][target_name] = value
            else:
                self._transient[target_name] = value

    def _exec_if(self, node: Any) -> None:
        """if-else 분기."""
        if self._truthy(self._eval_expr(node.test)):
            for stmt in node.body:
                self._exec_stmt(stmt)
        else:
            for stmt in node.orelse or []:
                self._exec_stmt(stmt)

    # ---- 루프 (G1, 2026-07-12 pine-batch QA) ---------------------------

    def _exec_scoped_loop(self, node: Any, execute: Callable[[Any], None]) -> None:
        """UDF loop counter는 block 종료 시 복원한다. 전역 루프 경로는 그대로 둔다."""
        if not self._function_frames:
            execute(node)
            return
        target = node.target
        targets = target.elts if isinstance(target, pyne_ast.Tuple) else [target]
        names = {item.id for item in targets if isinstance(item, pyne_ast.Name)}
        values = self._scope_stack[-1]
        previous = {name: values[name] for name in names if name in values}
        frame = self._function_frames[-1]
        previous_names = frame.loop_names.copy()
        frame.loop_names.update(names)
        try:
            execute(node)
        finally:
            for name in names:
                values.pop(name, None)
            values.update(previous)
            frame.loop_names = previous_names

    def _set_loop_var(self, name: str, value: Any) -> None:
        """루프 카운터를 현재 스코프(함수 frame 또는 transient)에 기록."""
        if self._scope_stack:
            self._scope_stack[-1][name] = value
        else:
            self._transient[name] = value

    def _run_loop_body(self, body: list[Any]) -> bool:
        """루프 body 1회 실행. break 발생 시 True 반환 (루프 종료 신호)."""
        self._loop_depth += 1
        try:
            for stmt in body:
                self._exec_stmt(stmt)
        except LoopContinue:
            return False
        except LoopBreak:
            return True
        finally:
            self._loop_depth -= 1
        return False

    def _exec_for_to(self, node: Any) -> None:
        """`for i = from to to [by step]` — TV 시멘틱.

        - 양 끝 **inclusive**.
        - 방향 자동: to > from 상향, to < from 하향 (`for i = 1 to 0` 은 1, 0 두 번).
        - `by step` 은 양수 크기 — 방향은 여전히 from/to 비교가 결정.
        """
        target = getattr(node, "target", None)
        if not isinstance(target, pyne_ast.Name):
            raise PineRuntimeError("for loop counter must be an identifier")
        start = self._eval_expr(node.start)
        end = self._eval_expr(node.end)
        for bound, label in ((start, "from"), (end, "to")):
            if bound is None or (isinstance(bound, float) and math.isnan(bound)):
                raise PineRuntimeError(f"for loop '{label}' bound is na")
        step_mag: Any = 1
        if getattr(node, "step", None) is not None:
            raw_step = self._eval_expr(node.step)
            if raw_step is None or (isinstance(raw_step, float) and math.isnan(raw_step)):
                raise PineRuntimeError("for loop 'by' step is na")
            step_mag = abs(raw_step)
            if step_mag == 0:
                raise PineRuntimeError("for loop 'by' step must be non-zero")
        direction = 1 if end >= start else -1
        step = step_mag * direction

        counter = start
        iterations = 0
        while (direction > 0 and counter <= end) or (direction < 0 and counter >= end):
            iterations += 1
            if iterations > _LOOP_ITERATION_CAP:
                raise PineRuntimeError(
                    f"for loop exceeded {_LOOP_ITERATION_CAP} iterations (runaway guard)"
                )
            self._set_loop_var(target.id, counter)
            if self._run_loop_body(node.body):
                break
            counter = counter + step

    def _exec_for_in(self, node: Any) -> None:
        """`for x in collection` — array 등 시퀀스 순회 (G2 array.* 와 조합)."""
        target = getattr(node, "target", None)
        iterable = self._eval_expr(node.iter)
        items: Iterator[Any]
        if isinstance(iterable, (list, tuple)):
            items = iter(list(iterable))
        else:
            raise PineRuntimeError(f"for-in expects an array/tuple, got {type(iterable).__name__}")
        names: list[str] = []
        if isinstance(target, pyne_ast.Name):
            names = [target.id]
        elif isinstance(target, pyne_ast.Tuple):
            # `for [i, x] in arr` — index + 원소 동시 바인딩
            for elt in target.elts:
                if not isinstance(elt, pyne_ast.Name):
                    raise PineRuntimeError("for-in target must be identifier or [index, value]")
                names.append(elt.id)
            if len(names) != 2:
                raise PineRuntimeError("for-in tuple target must be [index, value]")
        else:
            raise PineRuntimeError("for-in target must be identifier or [index, value]")

        for index, item in enumerate(items):
            if index >= _LOOP_ITERATION_CAP:
                raise PineRuntimeError(
                    f"for-in loop exceeded {_LOOP_ITERATION_CAP} iterations (runaway guard)"
                )
            if len(names) == 1:
                self._set_loop_var(names[0], item)
            else:
                self._set_loop_var(names[0], index)
                self._set_loop_var(names[1], item)
            if self._run_loop_body(node.body):
                break

    def _exec_while(self, node: Any) -> None:
        """`while cond` — 매 iteration 전 조건 평가 (TV 시멘틱)."""
        iterations = 0
        while self._truthy(self._eval_expr(node.test)):
            iterations += 1
            if iterations > _LOOP_ITERATION_CAP:
                raise PineRuntimeError(
                    f"while loop exceeded {_LOOP_ITERATION_CAP} iterations (runaway guard)"
                )
            if self._run_loop_body(node.body):
                break

    # ---- array.* (G2, 2026-07-12 pine-batch QA) -------------------------

    def _eval_array_call(self, name: str, node: Any) -> Any:
        """`array.*` 최소 서브셋 — `_names.ARRAY_FUNCTIONS` 와 1:1.

        - Pine array 는 참조 타입 → Python list. TV 와 동일하게 범위 밖 index 는
          runtime error (loud PineRuntimeError).
        - 미등재 array 함수는 coverage preflight 가 차단하지만, 방어적으로 runtime
          에서도 raise (부분 실행 금지).
        - `new_<type>` 의 initial_value 기본값은 TV 와 동일하게 na.
        """
        args = [self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args]
        op = name.removeprefix("array.")

        if op.startswith("new_"):
            if op not in (
                "new_float",
                "new_int",
                "new_bool",
                "new_string",
                "new_line",
                "new_label",
                "new_box",
            ):
                raise PineRuntimeError(f"array function not supported: {name}")
            size_raw = args[0] if args else 0
            try:
                size = int(size_raw)
            except (TypeError, ValueError, OverflowError):
                size = 0
            if size < 0:
                raise PineRuntimeError(f"{name}: negative size {size}")
            initial = args[1] if len(args) > 1 else float("nan")  # TV 기본 = na
            return [initial] * size

        if not args or not isinstance(args[0], list):
            got = type(args[0]).__name__ if args else "no argument"
            raise PineRuntimeError(f"{name}: first argument must be an array, got {got}")
        arr: list[Any] = args[0]

        if op == "push":
            arr.append(args[1] if len(args) > 1 else float("nan"))
            return None
        if op == "pop":
            if not arr:
                raise PineRuntimeError("array.pop: index out of bounds (array is empty)")
            return arr.pop()
        if op == "shift":
            if not arr:
                raise PineRuntimeError("array.shift: index out of bounds (array is empty)")
            return arr.pop(0)
        if op == "unshift":
            arr.insert(0, args[1] if len(args) > 1 else float("nan"))
            return None
        if op in ("get", "set"):
            try:
                index = int(args[1])
            except (TypeError, ValueError, OverflowError):
                raise PineRuntimeError(f"{name}: index is not an integer") from None
            if index < 0 or index >= len(arr):
                raise PineRuntimeError(f"{name}: index {index} out of bounds (size {len(arr)})")
            if op == "get":
                return arr[index]
            arr[index] = args[2] if len(args) > 2 else float("nan")
            return None
        if op == "clear":
            arr.clear()
            return None
        if op == "size":
            return len(arr)
        if op == "avg":
            values = [value for value in arr if not _is_na(value)]
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float)) for value in values
            ):
                raise PineRuntimeError("array.avg: elements must be int or float")
            return sum(values) / len(values) if values else float("nan")

        raise PineRuntimeError(f"array function not supported: {name}")

    # ---- 표현식 평가 --------------------------------------------------

    def _eval_expr(self, node: Any) -> Any:
        if node is None:
            return None
        if isinstance(node, pyne_ast.Constant):
            return node.value
        if isinstance(node, pyne_ast.Name):
            return self._resolve_name(node.id)
        if isinstance(node, pyne_ast.BinOp):
            return self._eval_binop(node)
        if isinstance(node, pyne_ast.UnaryOp):
            return self._eval_unaryop(node)
        if isinstance(node, pyne_ast.BoolOp):
            return self._eval_boolop(node)
        if isinstance(node, pyne_ast.Compare):
            return self._eval_compare(node)
        if isinstance(node, pyne_ast.Conditional):
            # Pine의 ternary a ? b : c
            return (
                self._eval_expr(node.body)
                if self._truthy(self._eval_expr(node.test))
                else self._eval_expr(node.orelse)
            )
        if isinstance(node, pyne_ast.Subscript):
            return self._eval_subscript(node)
        if isinstance(node, pyne_ast.Attribute):
            return self._eval_attribute(node)
        if isinstance(node, pyne_ast.Call):
            return self._eval_call(node)
        if isinstance(node, pyne_ast.Switch):
            return self._eval_switch(node)
        if isinstance(node, pyne_ast.Tuple):
            # Tuple literal (예: input(options=['A','B'])의 options 값). Python tuple 반환.
            return tuple(self._eval_expr(e) for e in node.elts)
        # 기타: Day 1-2 범위 밖
        raise PineRuntimeError(f"Unsupported expression node: {type(node).__name__}")

    def _eval_switch(self, node: Any) -> Any:
        """Pine switch expression: subject 값과 각 Case.pattern 비교.

        - subject가 있으면: cases 순회하며 pattern == subject이면 그 body 실행
        - subject가 None(pattern-only switch)이면: 각 pattern을 truthy 조건으로 평가
        - pattern이 None인 Case는 default (마지막 배치 권장; 순회 순서 그대로 처리)
        - Case.body는 statements 리스트. 마지막 Expr(value=...)의 값이 반환값.
        """
        subject = self._eval_expr(node.subject) if getattr(node, "subject", None) else None
        default_body: Any | None = None
        for case in getattr(node, "cases", []):
            pattern = getattr(case, "pattern", None)
            body = getattr(case, "body", [])
            if pattern is None:
                default_body = body
                continue
            pat_val = self._eval_expr(pattern)
            matched = (pat_val == subject) if subject is not None else self._truthy(pat_val)
            if matched:
                return self._exec_case_body(body)
        if default_body is not None:
            return self._exec_case_body(default_body)
        return None

    def _exec_case_body(self, body: list[Any]) -> Any:
        """switch Case body 실행: 마지막 Expr(value=...) 의 값 반환.

        body는 일반 statement도 허용하지만 최종 평가되는 것은 마지막 expression.
        """
        last_value: Any = None
        for stmt in body:
            if isinstance(stmt, pyne_ast.Expr):
                last_value = self._eval_expr(stmt.value)
            else:
                self._exec_stmt(stmt)
        return last_value

    def _eval_binop(self, node: Any) -> Any:
        op_name = type(node.op).__name__
        fn = _BINOP.get(op_name)
        if fn is None:
            raise PineRuntimeError(f"Unsupported BinOp: {op_name}")
        left = self._eval_expr(node.left)
        right = self._eval_expr(node.right)
        # Pine na 전파: 피연산자가 nan이면 결과도 nan
        if _is_na(left) or _is_na(right):
            return float("nan")
        # BL-374: na 정규화(ZeroDivision/overflow → na)는 숫자 산술에만. 문자열 등
        # 타입 오용(예: 잘못된 포맷 "%" % x → ValueError)은 fail-closed 로 전파 유지.
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return _na_safe(lambda: fn(left, right))
        return fn(left, right)

    def _eval_unaryop(self, node: Any) -> Any:
        op_name = type(node.op).__name__
        val = self._eval_expr(node.operand)
        if op_name == "USub":
            return float("nan") if _is_na(val) else -val
        if op_name == "UAdd":
            return val
        if op_name == "Not":
            return not self._truthy(val)
        raise PineRuntimeError(f"Unsupported UnaryOp: {op_name}")

    def _eval_boolop(self, node: Any) -> Any:
        """Pine v5 이하는 모든 항을 평가하고, v6부터 단축 평가한다."""
        op_name = type(node.op).__name__
        values: Iterator[Any] = (self._eval_expr(value) for value in node.values)
        if self.bar.pine_version < 6:
            # legacy 논리는 NA를 false로 소비하되, 모든 항의 평가 이력은 보존한다.
            values = iter([self._truthy(value) for value in values])
        if op_name == "And":
            result: Any = True
            for cur in values:
                if not self._truthy(cur):
                    return cur  # 첫 falsy 반환
                result = cur
            return result
        if op_name == "Or":
            last: Any = False
            for last in values:
                if self._truthy(last):
                    return last  # 첫 truthy 반환
            return last  # 모두 falsy면 마지막 값 반환 (Pine 단축평가 관례)
        raise PineRuntimeError(f"Unsupported BoolOp: {op_name}")

    def _eval_compare(self, node: Any) -> Any:
        """a < b < c 같은 chained compare 지원."""
        left = self._eval_expr(node.left)
        for op_node, cmp_node in zip(node.ops, node.comparators, strict=True):
            right = self._eval_expr(cmp_node)
            op_name = type(op_node).__name__
            fn = _CMPOP.get(op_name)
            if fn is None:
                raise PineRuntimeError(f"Unsupported compare: {op_name}")
            if _is_na(left) or _is_na(right):
                # v4/v5 native의 비교 결과는 NA를 보존한다. bool 2값은 v6 계약이다.
                return float("nan") if self.bar.pine_version < 6 else False
            if not fn(left, right):
                return False
            left = right
        return True

    def _eval_subscript(self, node: Any) -> Any:
        """Pine `x[n]` — 시계열 히스토리. built-in + 사용자 변수 시리즈 지원.

        의미:
        - `x[0]` = 현재 bar의 현재 값 (이번 bar 내 재할당 반영). 즉 `x`와 동일.
        - `x[1]` = 직전 bar 종료 시점의 값.
        - `x[n]` (n≥1) = n bar 전 종료 시점의 값.

        Event loop는 bar 종료 시 append_var_series()를 호출해 시리즈에 값을 쌓는다.
        따라서 bar N 실행 중: `_var_series['x']` = [bar 0의 값, ..., bar N-1의 값].
        `x[1]`은 series[-1] (방금 전 bar), `x[n]`은 series[-n].
        """
        value_node = node.value
        slice_node = node.slice
        offset = self._eval_expr(slice_node)
        # 음수/비유한 offset → Pine na (잘못된 인덱스 degrade). BL-376: inf 도 int() 안 함 → na.
        if isinstance(offset, float) and math.isfinite(offset):
            offset = int(offset)
        if not isinstance(offset, int) or offset < 0:
            return float("nan")

        if isinstance(value_node, pyne_ast.Name) and self._function_frames:
            frame = self._function_frames[-1]
            name = value_node.id
            if name in frame.params or name in frame.declarations or name in frame.loop_names:
                if offset == 0:
                    return self._resolve_name(name)
                if self._loop_depth:
                    raise PineRuntimeError("UDF local history in loops is not supported")
                current = self._scope_stack[-1].get(name)
                if current is not None and not isinstance(current, (bool, int, float, str)):
                    raise PineRuntimeError("UDF reference-type history is not supported")
                history = self._local_history.get((frame.path, name), ())
                if offset > 1 and history:
                    recent = list(history)[-offset:]
                    if any(
                        bar != self.bar.bar_index - i
                        for i, (bar, _) in enumerate(reversed(recent), 1)
                    ):
                        raise PineRuntimeError(
                            "UDF sparse history with offset > 1 is not supported"
                        )
                if len(history) < offset:
                    return float("nan")
                return history[-offset][1]

        # built-in series: 직접 DataFrame 조회
        if isinstance(value_node, pyne_ast.Name) and value_node.id in _BUILTIN_SERIES:
            return self.bar.history(value_node.id, offset)

        # S2 (전체 정검 P1-10/13): 합성 series (hl2/hlc3/ohlc4) history.
        # _var_series 에 없어 na 를 반환하던 silent 오값 차단 — OHLC history 로 직접 계산.
        if isinstance(value_node, pyne_ast.Name) and value_node.id in _SYNTHETIC_SERIES:
            return self._synthetic_source(value_node.id, offset)

        # 사용자 변수 series
        if isinstance(value_node, pyne_ast.Name):
            name = value_node.id
            if offset == 0:
                # 현재 값 — 통상 _resolve_name 경유 (transient/persistent/built-in)
                return self._resolve_name(name)
            series = self._var_series.get(name)
            if series is None or len(series) < offset:
                return float("nan")  # 이력 부족 → na
            return series[-offset]

        raise PineRuntimeError(
            f"Subscript on non-Name expression not supported: {_describe(value_node)}"
        )

    def _synthetic_source(self, name: str, offset: int) -> float:
        """hl2/hlc3/ohlc4 합성 source 를 offset bar 의 OHLC 로 계산 (offset=0 → 현재 bar).

        S2: current (`hl2`) 와 history (`hl2[1]`) 가 동일 helper 사용 — Pine 정의 1:1.
        bar.history 가 범위 밖에서 nan 반환 → 합성식도 nan 전파 (Pine na 동작).
        """

        def get(field: str) -> float:
            return self.bar.current(field) if offset == 0 else self.bar.history(field, offset)

        if name == "hl2":
            return (get("high") + get("low")) / 2
        if name == "hlc3":
            return (get("high") + get("low") + get("close")) / 3
        # ohlc4
        return (get("open") + get("high") + get("low") + get("close")) / 4

    def _resolve_name_if_declared(self, name: str) -> Any:
        """_resolve_name의 안전 버전 — 미정의면 None 반환 (렌더링 handle 검사용)."""
        key = f"main::{name}"
        if self.store.is_declared(key):
            return self.store.get(key)
        return self._transient.get(name)

    def _collect_args(self, node: Any) -> tuple[list[Any], dict[str, Any]]:
        """Call.args에서 positional/keyword 분리 + 각 argument evaluate."""
        positional: list[Any] = []
        kwargs: dict[str, Any] = {}
        for a in node.args:
            val = self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a)
            arg_name = getattr(a, "name", None) if isinstance(a, pyne_ast.Arg) else None
            if arg_name:
                kwargs[arg_name] = val
            else:
                positional.append(val)
        return positional, kwargs

    def _exec_rendering_call(self, name: str, node: Any) -> Any:
        """line.new/box.new/label.new/table.new + getter 호출."""
        method_name = _RENDERING_FACTORIES[name]
        args, kwargs = self._collect_args(node)
        bound = getattr(self.rendering, method_name)
        return bound(*args, **kwargs)

    def _exec_rendering_method(self, handle: Any, method_name: str, node: Any) -> Any:
        """handle.method(...) 형식 호출.

        handle 타입에 따라 registry 메서드 이름 prefix 결정:
        LineObject → line_*, BoxObject → box_*, 등.
        """
        prefix = {
            LineObject: "line",
            BoxObject: "box",
            LabelObject: "label",
            TableObject: "table",
        }[type(handle)]
        full = f"{prefix}_{method_name}"
        args, kwargs = self._collect_args(node)
        bound = getattr(self.rendering, full, None)
        if bound is None:
            raise PineRuntimeError(f"rendering method not supported: {prefix}.{method_name}")
        return bound(handle, *args, **kwargs)

    def _eval_call(self, node: Any) -> Any:
        """Call 해석: stdlib(ta.*/na/nz) → strategy.* → 선언/렌더링 NOP → 에러."""
        name = _call_chain_name(node.func)

        # Sprint 21 (codex G.0 P1 #1 + #4) — user-defined function 우선 dispatch.
        # plain identifier (no dot) 만 — dotted method/strategy/request call 은
        # 후 단계 dispatch path 가 처리. 이 ordering 없으면 사용자가 `abs(x) =>`,
        # `max(a,b) =>` 같은 함수 정의 시 v4 alias (`abs → math.abs`) 에 압도되어
        # silent correctness bug 발생 (Sprint 8c corpus i3_drfx/s3_rsid 가 통과한 건
        # 우연히 alias 와 충돌하는 함수명을 사용 안 했기 때문).
        if name and "." not in name and name in self._user_functions:
            return self._call_user_function(self._user_functions[name], node)

        # v4+ scalar 캐스트는 단항 순수 함수이며, 미지원 인자는 평가 전에 거부한다.
        if name in CAST_FUNCTIONS:
            if self.bar.pine_version < 4:
                raise PineRuntimeError(
                    f"{name}() is not supported in Pine v{self.bar.pine_version}; explicit casts require v4+"
                )
            if len(node.args) != 1:
                raise PineRuntimeError(f"{name}() expects exactly one positional argument")
            arg = node.args[0]
            if isinstance(arg, pyne_ast.Arg) and arg.name is not None:
                raise PineRuntimeError(f"{name}() does not support named arguments")
            value = self._eval_expr(arg.value if isinstance(arg, pyne_ast.Arg) else arg)
            is_na = _is_na(value)
            if type(value) is float and not is_na and not math.isfinite(value):
                raise PineRuntimeError(f"{name}() does not support infinite numeric values")
            if name == "bool":
                if is_na and self.bar.pine_version == 4:
                    raise PineRuntimeError("bool(na) is unverified in Pine v4")
                if is_na:
                    return False
                if type(value) is bool:
                    return value
                if type(value) in (int, float):
                    return value != 0
                raise PineRuntimeError("bool() supports only bool, numeric, or na values")
            if is_na:
                return float("nan")
            if type(value) not in (int, float):
                raise PineRuntimeError(f"{name}() supports only numeric or na values")
            if name == "float":
                try:
                    return float(value)
                except OverflowError as exc:
                    raise PineRuntimeError("float() numeric value is out of range") from exc
            return int(value)

        # Pine v4 legacy alias — prefix 없는 stdlib을 ta.* / math.* 로 재라우팅
        # (i1_utbot / 일부 RTB 전략이 v4 문법 사용)
        # Sprint 29 Slice C: function-local → module-level export. parity invariant 검증 대상.
        if name in _V4_ALIASES:
            name = _V4_ALIASES[name]

        # math.sum은 호출 지점별 이력을 쓰며 나머지 산술 함수는 NA를 전파한다.
        if name and name.startswith("math."):
            if name == "math.sum":
                # 인자 binding을 먼저 검증하고 원래 순서대로 한 번씩 평가한다.
                argument_names: list[str] = []
                saw_keyword = False
                for index, arg in enumerate(node.args):
                    arg_name = getattr(arg, "name", None) if isinstance(arg, pyne_ast.Arg) else None
                    if arg_name is None:
                        if saw_keyword:
                            raise PineRuntimeError(
                                "math.sum positional argument follows keyword argument"
                            )
                        if index >= 2:
                            raise PineRuntimeError("math.sum expects source and length")
                        arg_name = ("source", "length")[index]
                    else:
                        saw_keyword = True
                    if arg_name in argument_names:
                        raise PineRuntimeError("math.sum duplicate argument")
                    argument_names.append(arg_name)
                if set(argument_names) != {"source", "length"}:
                    raise PineRuntimeError("math.sum expects source and length")
                sum_args = {
                    name: self._eval_expr(arg.value if isinstance(arg, pyne_ast.Arg) else arg)
                    for name, arg in zip(argument_names, node.args, strict=True)
                }
                source, length = sum_args["source"], sum_args["length"]
                if type(length) is not int or length < 1:
                    raise PineRuntimeError("math.sum length must be a positive int")
                if not _is_na(source) and (
                    type(source) not in (int, float) or not math.isfinite(source)
                ):
                    raise PineRuntimeError("math.sum source must be finite numeric or na")
                scoped_id = self.stdlib._scoped_node_id(id(node))
                slot = self.stdlib.state.buffers.setdefault(
                    scoped_id, {"values": [], "bar_index": None}
                )
                if slot["bar_index"] == self.bar.bar_index:
                    raise PineRuntimeError("math.sum repeated in one bar is unsupported")
                if slot["bar_index"] is not None and slot["bar_index"] != self.bar.bar_index - 1:
                    raise PineRuntimeError("math.sum nonconsecutive calls are unsupported")
                slot["bar_index"] = self.bar.bar_index
                if not _is_na(source):
                    slot["values"].append(source)
                history = slot["values"]
                result = float(sum(history[-length:])) if len(history) >= length else float("nan")
                if len(history) >= length and not math.isfinite(result):
                    raise PineRuntimeError("math.sum result must be finite")
                return result
            args = [
                self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args
            ]
            if any(_is_na(a) for a in args):
                return float("nan")
            if name == "math.abs":
                return abs(args[0])
            if name == "math.max":
                return max(args)
            if name == "math.min":
                return min(args)
            if name == "math.floor":
                # BL-376 (G1 P1#1): floor/ceil/round 만 inf → na (int 변환 OverflowError 차단).
                # 공유 na 가드(위 any(_is_na))를 inf 로 확장 금지 — abs/sign/max/min 은 inf 통과 유지.
                return float("nan") if not math.isfinite(args[0]) else math.floor(args[0])
            if name == "math.ceil":
                return float("nan") if not math.isfinite(args[0]) else math.ceil(args[0])
            if name == "math.round":
                return float("nan") if not math.isfinite(args[0]) else round(args[0])
            if name == "math.sqrt":
                # BL-374: math.sqrt(-1) → ValueError(domain) → na (TradingView 의미).
                return _na_safe(lambda: math.sqrt(args[0]))
            if name == "math.log":
                # BL-374: log(0)/log(음수)/base=1 도메인·0나눗셈 → na.
                return _na_safe(
                    lambda: math.log(args[0]) if len(args) == 1 else math.log(args[0], args[1])
                )
            if name == "math.log10":  # S2 (전체 정검 P1-10/13): coverage SUPPORTED 누락분
                # BL-374: math.log10(0)/log10(음수) domain error → na.
                return _na_safe(lambda: math.log10(args[0]))
            if name == "math.pow":
                # BL-374: math.pow 로 통일 — bigint(10**1000)/complex(음수^분수) 무음오염 차단.
                return _na_safe(lambda: math.pow(args[0], args[1]))
            if name == "math.avg":
                # Pine math.avg(x1, x2, ...) — 여러 값의 산술 평균. na 는 무시.
                clean = [a for a in args if not _is_na(a)]
                if not clean:
                    return float("nan")
                return sum(clean) / len(clean)
            if name == "math.sign":
                v = args[0]
                if _is_na(v):
                    return float("nan")
                return 1 if v > 0 else (-1 if v < 0 else 0)
            if name == "math.exp":
                # BL-374: math.exp(1000) → OverflowError → na (inf 무음오염 차단).
                return _na_safe(lambda: math.exp(args[0]))
            raise PineRuntimeError(f"math function not supported: {name}")

        # array.* — G2 (2026-07-12 pine-batch QA) 최소 서브셋. Pine array 는 참조
        # 타입 — Python list 로 표현, var 선언 시 PersistentStore 가 객체 identity
        # 를 보관하므로 in-place mutation 이 bar 간 영속.
        if name and name.startswith("array."):
            return self._eval_array_call(name, node)

        # Bybit의 기본 exchange timezone은 UTC다. 근사 달력이면 실제 time과 날짜
        # 필터를 비교할 때 윤년·월 길이만큼 경계가 어긋나므로 epoch ms를 정확히 계산한다.
        if name == "timestamp":
            return self._eval_timestamp(node)

        # str.* / bare tostring·tonumber — display NOP-safe (tostring/format) 또는
        # 정확 변환 (tonumber=parse|na, length=len). backtest math 에 무관하거나 정확.
        # S2 (전체 정검 P1-10/13): coverage._STRING_FUNCTIONS 가 SUPPORTED 표기하나
        # bare tostring 만 구현돼 있던 누출 — dotted str.* 는 handle.method 통과 후 raise.
        def _first_arg() -> Any:
            return self._eval_expr(
                node.args[0].value if isinstance(node.args[0], pyne_ast.Arg) else node.args[0]
            )

        # tostring(x[, format]) — Pine v4/v5 numeric→str 변환. format은 무시(H2+).
        if name in ("tostring", "str.tostring"):
            if not node.args:
                return ""
            # 표시 format을 무시해도 모든 인자는 원본 순서로 한 번씩 평가한다.
            values = [
                self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args
            ]
            val = values[0]
            if isinstance(val, float) and math.isnan(val):
                return "NaN"
            return str(val)
        # tonumber(s) — string→number parse, 실패 시 na (Pine 의미).
        if name in ("tonumber", "str.tonumber"):
            if not node.args:
                return float("nan")
            try:
                return float(_first_arg())
            except (TypeError, ValueError):
                return float("nan")
        # str.length(s) — 문자열 길이 (정확).
        if name == "str.length":
            return len(str(_first_arg())) if node.args else 0
        # str.format(fmt, ...) — display-only. {i} 위치 치환 best-effort (backtest math 무관).
        if name == "str.format":
            fmt_args = [
                self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args
            ]
            if not fmt_args:
                return ""
            out = str(fmt_args[0])
            for i, a in enumerate(fmt_args[1:]):
                out = out.replace("{" + str(i) + "}", str(a))
            return out

        # Sprint 29 Slice A (a): heikinashi NOP — 일반 OHLC 그대로 반환 (Trust Layer 위반, dogfood-only).
        # Heikin-Ashi 캔들 정확 변환은 Sprint 30+ ADR-009 Candle transformation layer.
        if name == "heikinashi":
            self._record_degraded_call(name)
            return (
                self.bar.current("open"),
                self.bar.current("high"),
                self.bar.current("low"),
                self.bar.current("close"),
            )

        # request.security(sym, tf, expression, ...) — Sprint 8c MVP: expression 인자 그대로.
        # Sprint 29 Slice A: `security` (v4 no-namespace alias) 도 동일 처리.
        # (실제 MTF fetch는 H2+; NOP으로 graceful degrade.)
        if name in ("request.security", "request.security_lower_tf", "security"):
            self._record_degraded_call(name)
            if len(node.args) < 3:
                return float("nan")
            expr_arg = node.args[2]
            return self._eval_expr(
                expr_arg.value if isinstance(expr_arg, pyne_ast.Arg) else expr_arg
            )

        # v4 iff는 반환하지 않는 쪽도 평가한다. lazy한 ternary와 구분한다.
        if name == "iff":
            if len(node.args) != 3:
                raise PineRuntimeError(f"iff expects 3 args, got {len(node.args)}")
            cond_val, then_val, else_val = (
                self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args
            )
            return then_val if self._truthy(cond_val) else else_val

        # ta.* / na / nz — stdlib 디스패치 (참조: STDLIB_NAMES 모듈-level frozenset)
        if name in STDLIB_NAMES:
            args = [
                self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args
            ]
            return self.stdlib.call(
                name,
                id(node),
                args,
                high=self.bar.current("high"),
                low=self.bar.current("low"),
                close_prev=self._prev_close,
                pine_version=self.bar.pine_version,
            )

        # strategy.* 실행 핸들러
        if name in (
            "strategy.entry",
            "strategy.close",
            "strategy.close_all",
            "strategy.exit",
            "strategy.cancel",
            "strategy.cancel_all",
        ):
            try:
                return self._exec_strategy_call(name, node)
            except PendingMarketExitError as exc:
                raise PineRuntimeError(str(exc)) from exc

        # 렌더링 scope A — line/box/label/table. 좌표 저장 + getter만, 렌더링 NOP.
        if name in _RENDERING_FACTORIES:
            return self._exec_rendering_call(name, node)

        # handle.method() 형태 — line/box/label/table 객체의 메서드 호출
        if name and "." in name:
            head, _, tail = name.rpartition(".")
            handle = self._resolve_name_if_declared(head)
            if isinstance(handle, (LineObject, BoxObject, LabelObject, TableObject)):
                return self._exec_rendering_method(handle, tail, node)

        if self.capture_signals and name in {
            "plotshape",
            "plotchar",
            "plotarrow",
            "alertcondition",
            "alert",
        }:
            self._capture_signal_call(cast(SignalFunction, name), node)
            return None

        # 선언/렌더링/alert NOP
        _NOP_NAMES = {
            "indicator",
            "study",
            "strategy",
            "library",
            "plot",
            "plotshape",
            "plotchar",
            "plotbar",
            "plotcandle",
            "plotarrow",
            "bgcolor",
            "barcolor",
            "fill",
            "hline",
            "vline",  # Sprint 23 BL-099 — coverage.py:88 supported 와 parity
            "alert",
            "alertcondition",
            "input",
            "input.int",
            "input.float",
            "input.bool",
            "input.string",
            "input.source",
            "input.color",
            "input.time",
            "input.timeframe",
            "input.price",
            "input.session",
            "input.symbol",
            # Sprint 8c — 렌더링 색상/스타일 관련 순수 함수(값은 렌더링 NOP과만 interact).
            "color.new",
            "color.rgb",
            "color.from_gradient",
        }
        if name in _NOP_NAMES:
            if name and name.startswith("input"):
                # Sprint 51 BL-220 (codex G.0 P1#2): input override hook.
                # _exec_assign 이 RHS eval 전에 target var_name 을 stack 에 push.
                # input_overrides[target] 가 있으면 defval 대신 override 값 반환.
                target = (
                    self._assignment_target_stack[-1] if self._assignment_target_stack else None
                )
                if (
                    target is not None
                    and self.input_overrides is not None
                    and target in self.input_overrides
                ):
                    override_value = self.input_overrides[target]
                    # input.int / input.float / input.bool 은 stdlib 이 numeric
                    # 타입 가정 (Decimal 입력 시 'float / Decimal' TypeError). Pine v5
                    # 도 input.int 는 정수 보장 → engine 단 Decimal 을 명시적 cast.
                    if name == "input.int":
                        return int(override_value)
                    if name == "input.float":
                        return float(override_value)
                    if name == "input.bool":
                        return bool(override_value)
                    return override_value
                # Pine input 시그니처: v4는 input(title=, type=, defval=, ...) keyword 사용 빈번.
                # defval= kwarg 우선, 없으면 첫 positional arg를 defval로 간주.
                pos_args, kw_args = self._collect_args(node)
                if "defval" in kw_args:
                    return kw_args["defval"]
                if pos_args:
                    return pos_args[0]
                return None
            # 렌더링을 생략해도 인자의 상태 변경은 실행 의미의 일부다.
            self._collect_args(node)
            return None

        # NOTE (Sprint 21 P1 #1 + #4): user-defined function dispatch 는 _eval_call
        # 시작 직후 (v4 alias 전) 처리됨 — 본 위치는 unreachable. 의도적으로 제거하여
        # 단일 source of truth 유지 (plain identifier user_function 은 위 prior dispatch).

        raise PineRuntimeError(f"Call to {name!r} not supported in current scope")

    def _record_degraded_call(self, name: str) -> None:
        """검증 모드만 실제로 진입한 근사 실행을 기록한다. 정적 coverage는 바꾸지 않는다."""
        if self.capture_signals and name not in self.degraded_calls_seen:
            self.degraded_calls_seen.append(name)

    def _eval_timestamp(self, node: Any) -> int | float:
        """숫자 calendar 인자와 UTC timezone만 지원하며 다른 overload는 명시 차단한다."""
        positional, named = self._collect_args(node)
        zone = named.pop("timezone", None)
        if positional and isinstance(positional[0], str):
            zone = positional.pop(0)
        if zone not in {None, "UTC", "UTC0", "UTC+0", "UTC+00:00", "GMT", "GMT0", "Etc/UTC"}:
            raise PineRuntimeError("timestamp: dateString 및 비UTC timezone은 지원하지 않습니다")
        fields = ("year", "month", "day", "hour", "minute", "second")
        if len(positional) > len(fields) or set(named) - set(fields):
            raise PineRuntimeError("timestamp: 지원하지 않는 인자입니다")
        values = dict(zip(fields, positional, strict=False))
        values.update(named)
        if any(name not in values for name in fields[:3]):
            raise PineRuntimeError("timestamp: year, month, day가 필요합니다")
        try:
            parts = [int(values.get(name, 0)) for name in fields]
        except (TypeError, ValueError, OverflowError):
            return float("nan")
        year, month, day, hour, minute, second = parts
        try:
            # Pine은 음수 월·월말 초과 일자도 달력 경계를 넘어 정규화한다.
            year, month_index = divmod(year * 12 + month - 1, 12)
            stamp = datetime(year, month_index + 1, 1, tzinfo=UTC) + timedelta(
                days=day - 1, hours=hour, minutes=minute, seconds=second
            )
        except (ValueError, OverflowError) as exc:
            raise PineRuntimeError("timestamp: 지원하는 UTC 달력 범위를 벗어났습니다") from exc
        delta = stamp - datetime(1970, 1, 1, tzinfo=UTC)
        return delta.days * 86_400_000 + delta.seconds * 1000

    def _capture_signal_call(self, name: SignalFunction, node: Any) -> None:
        """실행된 호출의 조건/offset만 한 번 평가한다. 방향·edge는 추론하지 않는다."""
        raw: Any = True if name == "alert" else None
        offset = 0
        positional_index = 0
        offset_index = 4 if name == "plotarrow" else 5
        for arg in node.args:
            arg_name = getattr(arg, "name", None)
            value_node = arg.value if isinstance(arg, pyne_ast.Arg) else arg
            is_first = (arg_name is None and positional_index == 0) or arg_name in {
                "series",
                "condition",
            }
            is_offset = arg_name == "offset" or (
                arg_name is None and positional_index == offset_index
            )
            if name != "alert" and is_first:
                raw = self._eval_expr(value_node)
            elif name in {"plotshape", "plotchar", "plotarrow"} and is_offset:
                offset = int(self._eval_expr(value_node))
            else:
                self._eval_expr(value_node)
            if arg_name is None:
                positional_index += 1
        value: bool | int | float | None = None
        if isinstance(raw, (bool, int)) or (isinstance(raw, float) and math.isfinite(raw)):
            value = raw
        stamp = self.bar.current_timestamp()
        self.signal_trace.append(
            SignalObservation(
                function=name,
                source_line=node.lineno,
                source_column=node.col_offset,
                bar_index=self.bar.bar_index,
                bar_open_time=stamp.to_pydatetime() if stamp is not None else None,
                value=value,
                marker_offset=offset,
            )
        )

    def _local_persistent_key(self, name: str) -> str:
        return f"udf:{'/'.join(self._function_frames[-1].path)}::{name}"

    def _udf_declarations(self, fn_def: Any) -> dict[str, str | None]:
        """함수 본문 scalar binding만 지원한다. block 선언은 scope를 흉내 내지 않는다."""
        if fn_def.name in self._function_declarations:
            return self._function_declarations[fn_def.name]
        params = {param.name for param in fn_def.args}
        declarations: dict[str, str | None] = {}
        reassignments: set[str] = set()
        loop_counters: set[str] = set()

        def visit(node: Any, in_block: bool = False) -> None:
            if isinstance(node, pyne_ast.AugAssign):
                raise PineRuntimeError("UDF compound assignment is not supported")
            if isinstance(node, pyne_ast.Assign):
                if in_block:
                    raise PineRuntimeError("UDF lexical block declarations are not supported")
                targets = getattr(node, "targets", None) or [getattr(node, "target", None)]
                for target in targets:
                    names = target.elts if isinstance(target, pyne_ast.Tuple) else [target]
                    for name in names:
                        if isinstance(name, pyne_ast.Name):
                            if name.id in params or name.id in declarations:
                                raise PineRuntimeError(f"UDF duplicate binding: {name.id}")
                            declarations[name.id] = self._detect_var_kind(node)
            if isinstance(node, pyne_ast.ReAssign):
                targets = getattr(node, "targets", None) or [getattr(node, "target", None)]
                reassignments.update(t.id for t in targets if isinstance(t, pyne_ast.Name))
            if isinstance(node, (pyne_ast.ForTo, pyne_ast.ForIn)):
                target = node.target
                targets = target.elts if isinstance(target, pyne_ast.Tuple) else [target]
                loop_counters.update(t.id for t in targets if isinstance(t, pyne_ast.Name))
            nested_block = in_block or isinstance(node, _STATEMENT_EXPR_NODES)
            for child in pyne_ast.iter_child_nodes(node):
                visit(child, nested_block)

        for stmt in fn_def.body:
            visit(stmt)
        if loop_counters & (params | declarations.keys()):
            raise PineRuntimeError("UDF loop-counter shadowing is not supported")
        forbidden = reassignments - declarations.keys()
        if forbidden:
            raise PineRuntimeError(
                f"UDF cannot reassign parameter or nonlocal: {sorted(forbidden)[0]}"
            )
        self._function_declarations[fn_def.name] = declarations
        return declarations

    def _call_user_function(self, fn_def: Any, call_node: Any) -> Any:
        """Pine user function 호출: 매개변수 바인딩 + body 실행 + 마지막 Expr 값 반환.

        Pine 규칙:
        - body는 statement 리스트. 마지막 Expr(value=X)의 X가 반환값.
        - Tuple/List literal을 마지막 Expr로 두면 Python tuple 반환 (multi-return) — Task 4.
        - 로컬 변수는 로컬 frame에만 존재. 외부 transient/persistent 영향 X.
        """
        if len(self._scope_stack) >= self._max_call_depth:
            raise PineRuntimeError(
                f"user function call depth exceeded: {fn_def.name} (max={self._max_call_depth})"
            )
        declarations = self._udf_declarations(fn_def)
        if any(isinstance(arg, pyne_ast.Arg) and arg.name is not None for arg in call_node.args):
            raise PineRuntimeError("UDF named arguments are not supported")
        # 실인자 평가 (positional only — named arg는 H2+).
        actual_args = [
            self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a) for a in call_node.args
        ]
        params = [p.name for p in fn_def.args]
        if len(actual_args) != len(params):
            raise PineRuntimeError(
                f"user function {fn_def.name}: expected {len(params)} args, got {len(actual_args)}"
            )
        frame: dict[str, Any] = dict(zip(params, actual_args, strict=True))
        # ta.* 상태 격리: call-site별 고유 prefix push → 동일 함수의 서로 다른 호출 위치가
        # 각자 독립 상태를 가지게 됨.
        # ★BL-846 — 줄만으로는 call-site 가 안 갈린다. `pynescript` 의 `Call` 은
        #   `_attributes = ['lineno','col_offset','end_lineno','end_col_offset']` 뿐이고
        #   `node_id` 가 **없다**(설치본 프로브 확인). `lineno` 는 1 이상이라 항상 truthy 라
        #   `id(call_node)` 폴백에는 영원히 도달하지 않았고, `z = f(close) + f(open)` 의 두
        #   호출이 같은 슬롯을 써 `ta.*` 버퍼가 뒤섞였다(예외도 경고도 없는 침묵 오류).
        #   회귀 = tests/strategy/pine_v2/test_user_fn_callsite_isolation.py
        lineno = getattr(call_node, "lineno", None)
        col_offset = getattr(call_node, "col_offset", None)
        call_prefix = str(
            getattr(call_node, "node_id", None)
            or (f"{lineno}:{col_offset}" if lineno is not None else None)
            or id(call_node)
        )
        parent_path = self._function_frames[-1].path if self._function_frames else ()
        local_frame = _FunctionFrame((*parent_path, call_prefix), frozenset(params), declarations)
        self._scope_stack.append(frame)
        self._function_frames.append(local_frame)
        self.stdlib.push_call_prefix(call_prefix)
        try:
            last_expr_val: Any = None
            for stmt in fn_def.body:
                if isinstance(stmt, pyne_ast.Expr):
                    inner = stmt.value
                    # pynescript는 top-level if/for/while 을 Expr(value=...)로 래핑.
                    # 이건 statement 실행이지 return expr이 아니므로 _exec_stmt로 우회.
                    # (Pine 의 loop/if-as-expression 반환값은 미지원 — 기존 If 한계 유지.)
                    if isinstance(inner, _STATEMENT_EXPR_NODES):
                        self._exec_stmt(stmt)
                        continue
                    # 마지막 Expr(Tuple literal)은 Python tuple로 반환 — multi-return.
                    if isinstance(inner, pyne_ast.Tuple):
                        last_expr_val = tuple(self._eval_expr(e) for e in inner.elts)
                    else:
                        last_expr_val = self._eval_expr(inner)
                else:
                    self._exec_stmt(stmt)
            local_frame.staged.update(
                {
                    (local_frame.path, name): value
                    for name, value in frame.items()
                    if value is None or isinstance(value, (bool, int, float, str))
                }
            )
            # 부모가 실패하면 자식의 성공 이력도 버린다. 최상위 성공만 봉 staging에 넣는다.
            destination = (
                self._function_frames[-2].staged
                if len(self._function_frames) > 1
                else self._local_pending
            )
            destination.update(local_frame.staged)
            return last_expr_val
        finally:
            self._function_frames.pop()
            self._scope_stack.pop()
            self.stdlib.pop_call_prefix()

    # ---- Name 해석 (built-in + var + transient) ------------------------

    def _true_range(self) -> float:
        """v4 tr와 v5 ta.tr 속성이 같은 현재·직전 봉 계산을 공유한다."""
        high = self.bar.current("high")
        low = self.bar.current("low")
        prev_close = self.bar.history("close", 1)
        if math.isnan(prev_close):
            return high - low
        return max(high - low, abs(high - prev_close), abs(low - prev_close))

    def _resolve_name(self, name: str) -> Any:
        # 로컬 frame 우선 — user function 호출 중 매개변수/로컬 변수 lookup.
        if self._scope_stack and name in self._scope_stack[-1]:
            return self._scope_stack[-1][name]
        if self._function_frames and name in self._function_frames[-1].declarations:
            raise PineRuntimeError(f"UDF local referenced before declaration: {name}")
        if name in _BUILTIN_SERIES:
            return self.bar.current(name)
        if name == "tr":
            return self._true_range()
        # S2 (전체 정검 P1-10/13): 합성 series source — Pine 정의와 1:1 (근사 없음).
        # coverage._SERIES_ATTRS 가 SUPPORTED 표기하나 interpreter 미구현이던 누출.
        if name in _SYNTHETIC_SERIES:
            return self._synthetic_source(name, 0)
        if name == "bar_index":
            return self.bar.bar_index
        if name == "time":
            stamp = self.bar.current_timestamp()
            if stamp is not None:
                return stamp.value // 1_000_000
            # Pine `time` = 현재 bar의 timestamp (epoch ms). OHLCV에 timestamp 없으면
            # 2020-01-01 기준(≈ 50년 * 365*86400*1000 ms)으로 bar_index 분봉 가정.
            # backtest range 필터(time >= startDate and time <= finishDate)가
            # fromYear=1970 / toYear=2100 범위에서 True가 되도록 맞춤.
            return 50 * 365 * 86_400 * 1000 + self.bar.bar_index * 60_000
        if name == "na":
            return float("nan")
        if name == "true":
            return True
        if name == "false":
            return False
        # strategy.* built-in constants + 상태
        if name == "strategy.long":
            return "long"
        if name == "strategy.short":
            return "short"
        if name == "strategy.position_size":
            return self.strategy.position_size
        if name == "strategy.position_avg_price":
            return self.strategy.position_avg_price
        if name == "strategy.equity":
            return (
                self.strategy.running_equity
                if self.strategy.running_equity is not None
                else float("nan")
            )
        key = f"main::{name}"
        if self.store.is_declared(key):
            return self.store.get(key)
        if name in self._transient:
            return self._transient[name]
        # 수집한 v2/v3 원본의 표시·입력 상수다. v4부터는 namespace를 사용한다.
        if self.bar.pine_version < 4:
            # Pine v3 공식 기본 색상 17종. 기존 color.*와 같은 표시 NOP만 제공한다.
            if name in {
                "black",
                "silver",
                "gray",
                "white",
                "maroon",
                "red",
                "purple",
                "fuchsia",
                "green",
                "lime",
                "olive",
                "yellow",
                "navy",
                "blue",
                "teal",
                "aqua",
                "orange",
            }:
                return float("nan")  # color.*와 같은 표시 전용 NOP다.
            legacy_constants = {
                "line": "line",
                "circles": "circles",
                "cross": "cross",
                "integer": "integer",
                "float": "float",
                "source": "source",
                "bool": "bool",
            }
            if name in legacy_constants:
                return legacy_constants[name]
        raise PineRuntimeError(f"Undefined name: {name}")

    # ---- Attribute 해석 (`strategy.long` 등 built-in 상수) -----------

    def _eval_attribute(self, node: Any) -> Any:
        """Attribute 체인을 'a.b.c' 로 합친 뒤 built-in 상수 룩업.

        렌더링 scope A 지원(ADR-011 §2.0.4)을 위해 Pine 그리기 enum 상수도 매핑.
        실제 차트에 영향 없지만 call arg로 전달될 수 있어 평가는 필요.
        """
        chain = _attr_chain(node)
        if chain in _ATTR_CONSTANTS:
            return _ATTR_CONSTANTS[chain]
        # strategy.position_size / strategy.position_avg_price
        if chain == "strategy.position_size":
            return self.strategy.position_size
        if chain == "strategy.position_avg_price":
            return self.strategy.position_avg_price
        if chain == "strategy.equity":
            return (
                self.strategy.running_equity
                if self.strategy.running_equity is not None
                else float("nan")
            )
        # syminfo 상수 — 심볼 메타데이터. Day 7: s1_pbr 호환을 위해 mintick 실제 값 반환
        if chain == "syminfo.mintick":
            return 0.01  # 기본값 — 심볼별 설정 기능은 향후 추가
        if chain == "syminfo.tickerid":
            return "UNKNOWN"
        # Sprint 58 BL-242b: syminfo 추가 상수
        if chain == "syminfo.prefix":
            return ""
        if chain == "syminfo.ticker":
            return ""
        if chain == "syminfo.timezone":
            return "UTC"
        # Sprint 58 BL-242b: barstate.isrealtime — backtest 는 항상 historical
        if chain == "barstate.isrealtime":
            return False
        # S2 (전체 정검 P1-10/13): 나머지 barstate.* — backtest 의미상 정확.
        # coverage._SERIES_ATTRS 가 SUPPORTED 표기하나 isrealtime 만 구현돼 있던 누출.
        if chain == "barstate.isfirst":
            return self.bar.bar_index == 0
        if chain == "barstate.islast":
            return self.bar.bar_index == len(self.bar.ohlcv) - 1
        if chain == "barstate.ishistory":
            return True  # backtest 는 전 bar historical (isrealtime=False 의 보완)
        if chain == "barstate.isconfirmed":
            return True  # backtest bar 는 전부 closed/confirmed
        if chain.startswith("timeframe."):
            context_value = self.bar.timeframe_attribute(chain)
            if context_value is not None:
                return context_value
        # 명시 context가 없는 기존 호출은 종전 기본값을 유지한다.
        if chain in (
            "timeframe.isdaily",
            "timeframe.isminutes",
            "timeframe.ismonthly",
            "timeframe.isseconds",
            "timeframe.isweekly",
        ):
            return False
        if chain == "timeframe.multiplier":
            return 0
        # Sprint 58 BL-241: ta.obv — 누적 OBV series attribute
        if chain == "ta.obv":
            close_val = self.bar.current("close")
            vol_val = self.bar.current("volume")
            return self.stdlib.call(
                "ta.obv",
                id(node),
                [close_val, vol_val, self._prev_close],
                pine_version=self.bar.pine_version,
            )
        # ta.tr — built-in series: True Range = max(high-low, |high-prev_close|, |low-prev_close|)
        # 첫 bar 는 prev_close 가 nan → high-low 만 (Pine 동작과 동일)
        if chain == "ta.tr":
            return self._true_range()
        # timeframe.period — Sprint 29 Slice A: BarContext 에 timeframe 미구현,
        # 기본값 "1D" 반환 (backtest 단일 timeframe 가정).
        if chain == "timeframe.period":
            self._record_degraded_call(chain)
            return "1D"
        # color.* 는 렌더링 맥락에서만 쓰이므로 na 반환
        if chain.startswith("color."):
            return float("nan")
        # alert.freq_* / display.* 등 추가 Pine enum은 문자열 stub 반환.
        # G5 (2026-07-12 QA): label.style_* / line.style_* prefix fallback 추가 —
        # coverage._ENUM_PREFIXES 는 prefix 로 허용하는데 runtime 은 dict 열거만
        # 하던 drift 봉합 (bs `label.style_label_down` 케이스). 명시 dict 우선.
        if chain.startswith(
            (
                "alert.freq_",
                "display.",
                "xloc.",
                "yloc.",
                "text.",
                "font.",
                "label.style_",
                "line.style_",
            )
        ):
            return chain.split(".", 1)[1]
        # S2 (전체 정검 P1-10/13): currency.* enum — coverage._CURRENCY_CONSTANTS explicit
        # set 이 preflight 에서 invalid 차단. runtime 은 통화 코드 suffix 반환 (currency.USD == "USD").
        if chain.startswith("currency."):
            return chain.split(".", 1)[1]
        raise PineRuntimeError(f"Attribute access not supported: {chain}")

    # ---- strategy.* 핸들러 --------------------------------------------

    def _exec_strategy_call(self, name: str, node: Any) -> None:
        """strategy.entry/close/close_all 실행 — 시장가, 현재 bar close 체결."""
        current_close = self.bar.current("close")
        bar_idx = self.bar.bar_index

        # 인자 평가: positional + kwarg
        positional: list[Any] = []
        kwargs: dict[str, Any] = {}
        for a in node.args:
            val = self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a)
            arg_name = getattr(a, "name", None) if isinstance(a, pyne_ast.Arg) else None
            if arg_name:
                kwargs[arg_name] = val
            else:
                positional.append(val)

        if name == "strategy.entry":
            trade_id = str(positional[0]) if positional else str(kwargs.get("id", "default"))

            # when= kwarg: False면 entry skip (Pine v4 backtest range 필터)
            # ★세션 게이트보다 **먼저** 판정한다. `when=false` 는 애초에 진입 의도가
            # 없다는 뜻이라, 세션을 먼저 보면 "거래 시간대 밖에서 막혔다" 는 skip 이
            # 기록되고 화면·메트릭에 유령 1건이 뜬다. 두 분기 모두 `return None` 이라
            # 실행 결과는 동일하고 **기록되는 사유만** 정확해진다.
            when_val = kwargs.get("when")
            if when_val is not None and not self._truthy(when_val):
                return None

            # BL-188 v3 entry placement gate (Track S) — disallowed session 이면
            # silent skip → equity/state 영향 0. 단일 reference =
            # `src.strategy.trading_sessions.is_allowed`. timestamps 미주입 시 skip 하지 않음
            # (회귀 0). v2_adapter 가 tz-naive sessions-only 활성 시 422 reject.
            if self.strategy.sessions_allowed:
                bar_ts = self.bar.current_timestamp()
                if bar_ts is not None:
                    from src.strategy.trading_sessions import is_allowed

                    if not is_allowed(list(self.strategy.sessions_allowed), bar_ts.to_pydatetime()):
                        self.strategy._record_entry_skip(
                            bar=bar_idx,
                            reason="session_closed",
                            trade_id=trade_id,
                        )
                        return None

            # direction 결정 — v4는 2번째 positional이 boolean(true=long, false=short),
            # v5는 strategy.long/short 상수 문자열. direction= kwarg도 가능.
            raw_dir: Any
            if len(positional) >= 2:
                raw_dir = positional[1]
            elif "direction" in kwargs:
                raw_dir = kwargs["direction"]
            else:
                raw_dir = "long"
            if isinstance(raw_dir, bool):
                direction: str = "long" if raw_dir else "short"
            elif raw_dir == "long":
                direction = "long"
            elif raw_dir == "short":
                direction = "short"
            else:
                # 알 수 없는 값은 long 기본 (보수적)
                direction = "long"

            # BL-185 spot-equivalent: qty 미지정 시 default_qty_type/value 기반 계산.
            # configure_sizing 미호출 또는 default_qty_type=None → compute_qty=1.0 (호환).
            if "qty" in kwargs:
                qty = float(kwargs["qty"])
            elif len(positional) >= 3:
                qty = float(positional[2])
            else:
                qty = self.strategy.compute_qty(fill_price=current_close)
            comment = str(kwargs.get("comment", ""))

            # stop= 는 지원 (Week 3 Day 1부터).
            # ★limit= 도 지원 (2026-08-15 surface-truth · U8). 종전에는 `unsupported` 목록에
            #   들어가 **조용히 시장가로 치환**됐고, 화면은 그 전략을 「지원됨」 초록 칩으로
            #   표시했다(Coverage 는 함수 이름만 보므로 kwarg 를 못 본다). 백테스트는 시장가
            #   결과를 냈고 경고는 네 지점에서 폐기됐다. trail_*/qty_percent 는 여전히 미지원.
            #
            # ★★**위치 인자도 읽는다** (2026-08-15 적대 리뷰 P1). Pine v5 시그니처는
            #   `strategy.entry(id, direction, qty, limit, stop, oca_name, ...)` 이라
            #   `limit` 은 **4번째**, `stop` 은 **5번째** 위치 인자다. `kwargs` 만 보면
            #   `strategy.entry("L", strategy.long, 8, 10)` 의 `limit=10` 이 **통째로
            #   사라지고 시장가 진입으로 샌다** — 실측으로 `run_live` 가 `entry/L/long/8`
            #   signal 을 냈다(pending·skip 둘 다 빈 채로). 이 회차가 닫으려던 바로 그 구멍이
            #   위치 인자 축에 그대로 남아 있었고, 회귀 테스트는 named 형태만 쓰고 있었다.
            #   ★`stop` 의 위치 인자 누락은 **이 회차 이전부터** 있던 것이다.
            def _price_arg(name: str, index: int) -> float | None:
                raw = kwargs.get(name)
                if raw is None and len(positional) > index:
                    raw = positional[index]
                if raw is None or _is_na(raw):
                    return None
                return float(raw)

            stop: float | None = _price_arg("stop", 4)
            limit: float | None = _price_arg("limit", 3)
            unsupported = [
                k for k in kwargs if k in ("trail_points", "trail_offset", "qty_percent")
            ]
            # TV parity — fill_timing=next_bar_open: 시장가(stop·limit 없음) entry 는 인텐트
            # 큐 등록 → 다음 bar 시가 체결. qty 미지정 시 체결 시가 기준 sizing 위해
            # None 전달 (compute_qty deferred). stop=/limit= 은 pending 경로 유지.
            # ★★`and limit is None` 이 빠지면 지정가 진입이 **여기서 계속 시장가로 샌다** —
            #   `unsupported` 목록에서 "limit" 을 빼는 것만으로는 아무것도 고쳐지지 않는다.
            #   ★엔진 기본값은 `bar_close`(`strategy_state.py:399`)라 이 분기는 사용자가
            #   TV parity 를 켰을 때(`fill_timing="next_bar_open"`)만 지난다. 그래서 이 가드는
            #   **기본 경로 테스트로는 잡히지 않는다** — 2026-08-15 에 이 가드를 지우는 변이가
            #   전건 초록으로 빠져나갔고, 전용 회귀
            #   (`test_limit_entry_order.py::test_limit_entry_is_not_converted_to_market_under_next_bar_open`)
            #   를 세우고서야 red 가 됐다.
            if self.strategy.fill_timing == "next_bar_open" and stop is None and limit is None:
                from src.strategy.pine_v2.strategy_state import MarketIntent

                explicit_qty: float | None
                if "qty" in kwargs:
                    explicit_qty = float(kwargs["qty"])
                elif len(positional) >= 3:
                    explicit_qty = float(positional[2])
                else:
                    explicit_qty = None
                if unsupported:
                    self.strategy.warnings.append(
                        f"strategy.entry({trade_id!r}): ignored unsupported kwargs: {unsupported}"
                    )
                self.strategy.queue_market_intent(
                    MarketIntent(
                        kind="entry",
                        trade_id=trade_id,
                        direction=direction,  # type: ignore[arg-type]
                        qty=explicit_qty,
                        comment=comment,
                        placed_bar=bar_idx,
                    )
                )
                return None
            self.strategy.entry(
                trade_id,
                direction,  # type: ignore[arg-type]
                qty=qty,
                bar=bar_idx,
                fill_price=current_close,
                comment=comment,
                stop=stop,
                limit=limit,
                unsupported_kwargs=unsupported,
            )
            return None

        if name == "strategy.close":
            trade_id = str(positional[0]) if positional else str(kwargs.get("id", "default"))
            # when= kwarg: False면 close skip (strategy.entry 와 동일 정책).
            # Pine의 `strategy.close(id=..., when=cond, ...)` 호출이 cond 가 거짓일 때
            # 무조건 close 되던 버그 (dogfood 2026-04-22) 수정.
            when_val = kwargs.get("when")
            if when_val is not None and not self._truthy(when_val):
                return None
            comment = str(kwargs.get("comment", ""))
            # TV parity — next_bar_open: close 인텐트 큐 등록 → 다음 bar 시가 체결.
            if self.strategy.fill_timing == "next_bar_open":
                from src.strategy.pine_v2.strategy_state import MarketIntent

                self.strategy.queue_market_intent(
                    MarketIntent(
                        kind="close",
                        trade_id=trade_id,
                        comment=comment,
                        placed_bar=bar_idx,
                    )
                )
                return None
            self.strategy.close(
                trade_id,
                bar=bar_idx,
                fill_price=current_close,
                comment=comment,
            )
            return None

        if name == "strategy.close_all":
            # when= kwarg: False면 close_all skip.
            when_val = kwargs.get("when")
            if when_val is not None and not self._truthy(when_val):
                return None
            # TV parity — next_bar_open: close_all 인텐트 큐 등록.
            if self.strategy.fill_timing == "next_bar_open":
                from src.strategy.pine_v2.strategy_state import MarketIntent

                self.strategy.queue_market_intent(
                    MarketIntent(kind="close_all", trade_id="", placed_bar=bar_idx)
                )
                return None
            self.strategy.close_all(bar=bar_idx, fill_price=current_close)
            return None

        if name in ("strategy.cancel", "strategy.cancel_all"):
            allowed = {"id"} if name == "strategy.cancel" else set()
            if set(kwargs) - allowed or len(positional) > (1 if allowed else 0):
                raise PineRuntimeError(f"{name}: unsupported arguments")
            if name == "strategy.cancel":
                if not positional and "id" not in kwargs:
                    raise PineRuntimeError("strategy.cancel requires id")
                self.strategy.cancel(str(positional[0] if positional else kwargs["id"]))
            else:
                self.strategy.cancel_all()
            return None

        if name == "strategy.exit":
            supported = {
                "id",
                "from_entry",
                "when",
                "comment",
                "stop",
                "limit",
                "profit",
                "loss",
                "trail_offset",
                "trail_points",
                "trail_price",
                "qty",
                "qty_percent",
            }
            unknown = sorted(set(kwargs) - supported)
            if unknown or len(positional) > 2:
                raise PineRuntimeError(
                    f"strategy.exit unsupported arguments: {unknown or 'positional>2'}"
                )
            # BL-104 — strategy.exit 본격 구현 (NOP 교체). Pine
            # `strategy.exit(id, from_entry, profit/limit/loss/stop/trail_*)` =
            # exit order 예약 (target price 도달 시 trigger). 매 bar 재호출 시 같은
            # (from_entry, id) 브래킷을 갱신 (Pine re-issue). from_entry="" → 전체 open.
            #
            # when= kwarg: False면 skip (entry/close 패턴 일치).
            when_val = kwargs.get("when")
            if when_val is not None and not self._truthy(when_val):
                return None
            exit_id = str(positional[0]) if positional else str(kwargs.get("id", "default"))
            if len(positional) >= 2:
                from_entry = str(positional[1])
            elif kwargs.get("from_entry"):
                from_entry = str(kwargs.get("from_entry", ""))
            else:
                from_entry = ""  # 전체 open 포지션

            def _num(key: str) -> float | None:
                raw = kwargs.get(key)
                if raw is None or _is_na(raw):
                    return None
                return float(raw)

            # 절대가: limit(TP)/stop(SL). 상대오프셋: profit/loss/trail_*.
            # pine_v2 는 mintick 모델이 없어 profit/loss/trail 을 price-distance 로
            # 근사 (mintick=1). entry 가 기준 → place_exit 가 target 별로 환산.
            limit_price = _num("limit")
            stop_price = _num("stop")
            profit_offset = _num("profit")
            loss_offset = _num("loss")
            trail_offset = _num("trail_offset")
            trail_points = _num("trail_points")
            trail_price = _num("trail_price")
            if trail_points is not None and trail_price is not None:
                raise PineRuntimeError(
                    "strategy.exit: trail_points activation 조합은 미지원; 절대 trail_price와 trail_offset 사용"
                )
            if trail_price is not None and trail_offset is None:
                raise PineRuntimeError("strategy.exit: trail_price requires trail_offset")
            if trail_points is not None:
                self.strategy.warnings.append(
                    "strategy.exit: trail_points는 legacy 가격거리 근사입니다; trail_offset이 있으면 우선 사용하며 tick/activation 의미는 미지원입니다"
                )
            trail = trail_offset if trail_offset is not None else trail_points
            self.strategy.place_exit(
                from_entry=from_entry,
                exit_id=exit_id,
                bar=bar_idx,
                limit=limit_price,
                stop=stop_price,
                profit_offset=profit_offset,
                loss_offset=loss_offset,
                trail_offset=trail,
                trail_price=trail_price,
                qty=_num("qty"),
                qty_percent=_num("qty_percent"),
                comment=str(kwargs.get("comment", "")),
            )
            return None

        raise PineRuntimeError(f"Unexpected strategy call: {name}")

    # ---- 보조 ----------------------------------------------------------

    @staticmethod
    def _detect_var_kind(assign_node: Any) -> str | None:
        for child in pyne_ast.iter_child_nodes(assign_node):
            cls = type(child).__name__
            if cls == "Var":
                return "var"
            if cls == "VarIp":
                return "varip"
        return None

    @staticmethod
    def _truthy(value: Any) -> bool:
        """Pine 진리값 — na는 False 취급."""
        if _is_na(value):
            return False
        return bool(value)


# ------------------------------------------------------------
# 헬퍼
# ------------------------------------------------------------


def _is_na(value: Any) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _na_safe(compute: Callable[[], Any]) -> Any:
    # Pine 산술/math: ZeroDivision / domain error / overflow → na. 음수밑 분수승 complex → na.
    # PineRuntimeError(RuntimeError)·TypeError 는 안 잡음 (BL-362 fail-closed 유지).
    try:
        result = compute()
    except (ArithmeticError, ValueError):
        return float("nan")
    if isinstance(result, complex):
        return float("nan")
    return result


def _attr_chain(node: Any) -> str:
    """Attribute 체인을 `a.b.c` 문자열로."""
    parts: list[str] = []
    cur: Any = node
    while isinstance(cur, pyne_ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, pyne_ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _call_chain_name(func_node: Any) -> str | None:
    """Call.func이 Name이면 id, Attribute면 chain."""
    if isinstance(func_node, pyne_ast.Name):
        return func_node.id
    if isinstance(func_node, pyne_ast.Attribute):
        return _attr_chain(func_node)
    return None


def _describe(node: Any) -> str:
    if isinstance(node, pyne_ast.Name):
        return node.id
    if isinstance(node, pyne_ast.Attribute):
        return _attr_chain(node)
    return type(node).__name__


def iter_statements(tree: Any) -> Iterator[Any]:
    """편의: top-level body를 반복."""
    yield from getattr(tree, "body", [])
