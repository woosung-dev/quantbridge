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
from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd
from pynescript import ast as pyne_ast

from src.strategy.pine_v2._names import STDLIB_NAMES
from src.strategy.pine_v2.rendering import (
    BoxObject,
    LabelObject,
    LineObject,
    RenderingRegistry,
    TableObject,
)
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.stdlib import StdlibDispatcher
from src.strategy.pine_v2.strategy_state import StrategyState

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
    "rsi": "ta.rsi",
    "crossover": "ta.crossover",
    "crossunder": "ta.crossunder",
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
}

# Pine enum constants — value 매핑 (location.absolute, extend.right, shape.*, etc.)
# Sprint 29 Slice C: function-local dict 에서 module-level dict 으로 export.
# coverage._ENUM_PREFIXES 와 parity invariant 검증 대상 (test_ssot_invariants.py).
_ATTR_CONSTANTS: dict[str, str] = {
    "strategy.long": "long",
    "strategy.short": "short",
    # Sprint 37 BL-185: Pine strategy(default_qty_type=...) 3종 — interpreter 가
    # `t = strategy.percent_of_equity` 같은 attribute access 를 evaluate 가능하도록 등록.
    # coverage._STRATEGY_CONSTANTS_EXTRA 와 SSOT invariant audit 자동 검증.
    "strategy.fixed": "strategy.fixed",
    "strategy.cash": "strategy.cash",
    "strategy.percent_of_equity": "strategy.percent_of_equity",
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
        return self.timestamps[self.bar_index]


# ------------------------------------------------------------
# Interpreter — Pine AST visit + 표현식 평가 + 문장 실행
# ------------------------------------------------------------


_BUILTIN_SERIES = frozenset({"open", "high", "low", "close", "volume"})

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
    ) -> None:
        self.bar = bar_context
        self.store = store
        # 비영속(transient) 변수 — 매 bar 재초기화
        self._transient: dict[str, Any] = {}
        # 사용자 정의 함수 (=>) — Script.body의 FunctionDef 노드 보관. 호출은 _eval_call에서 dispatch.
        self._user_functions: dict[str, Any] = {}
        # 함수 호출 중 로컬 스코프 스택. 최상단 = 현재 frame. 빈 리스트 = 최상위.
        self._scope_stack: list[dict[str, Any]] = []
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

    def reset_transient(self) -> None:
        self._transient = {}

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
            short = full_key.split("::", 1)[1] if "::" in full_key else full_key
            if short not in self._var_series:
                self._var_series[short] = deque(maxlen=self._max_bars_back)
            self._var_series[short].append(value)

    # ---- 실행 엔트리 --------------------------------------------------

    def execute(self, tree: Any) -> None:
        """pynescript Script 노드의 body를 순차 실행 (한 bar 분량)."""
        for stmt in getattr(tree, "body", []):
            self._exec_stmt(stmt)

    # ---- 문장 디스패치 -------------------------------------------------

    def _exec_stmt(self, node: Any) -> None:
        if isinstance(node, pyne_ast.Assign):
            self._exec_assign(node)
        elif isinstance(node, pyne_ast.ReAssign):
            self._exec_reassign(node)
        elif isinstance(node, pyne_ast.If):
            self._exec_if(node)
        elif isinstance(node, pyne_ast.Expr):
            # pynescript는 top-level `if`를 Expr(value=If(...))로 래핑함
            inner = node.value
            if isinstance(inner, pyne_ast.If):
                self._exec_if(inner)
            else:
                # 표현식 문장: 호출 등 side-effect만 있는 것 (e.g., alert)
                self._eval_expr(inner)
        elif isinstance(node, pyne_ast.FunctionDef):
            # Pine user function 정의: top-level에서만 등록. 호출은 _eval_call에서 dispatch.
            # (함수 내부 중첩 함수 정의는 H2+ — Pine 공식 범위 밖.)
            if not self._scope_stack:
                self._user_functions[node.name] = node
        else:
            # Return, for/while 등 Day 1-2 범위 밖 — 조용히 skip
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
            key = f"main::{target_name}"
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

            self.store.declare_if_new(
                key,
                factory,
                varip=(var_kind == "varip"),
            )
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
        value = self._eval_expr(node.value)
        # 로컬 scope 활성 & 해당 이름이 현재 frame에 존재 → frame에 재할당.
        if self._scope_stack and target_name in self._scope_stack[-1]:
            self._scope_stack[-1][target_name] = value
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
        """And/Or — Python 단축평가 채택 (Pine도 동일)."""
        op_name = type(node.op).__name__
        values = node.values
        if op_name == "And":
            result: Any = True
            for v in values:
                cur = self._eval_expr(v)
                if not self._truthy(cur):
                    return cur  # 첫 falsy 반환
                result = cur
            return result
        if op_name == "Or":
            if not values:
                return False
            last: Any = False
            for v in values:
                last = self._eval_expr(v)
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
                # Pine의 na 전파 — 비교 결과도 na. Python bool로 표현 불가하므로 False 처리
                return False
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
        # 음수 offset → Pine na (잘못된 인덱스 silently degrade)
        if isinstance(offset, float) and not math.isnan(offset):
            offset = int(offset)
        if not isinstance(offset, int) or offset < 0:
            return float("nan")

        # built-in series: 직접 DataFrame 조회
        if isinstance(value_node, pyne_ast.Name) and value_node.id in _BUILTIN_SERIES:
            return self.bar.history(value_node.id, offset)

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

        # Pine v4 legacy alias — prefix 없는 stdlib을 ta.* / math.* 로 재라우팅
        # (i1_utbot / 일부 RTB 전략이 v4 문법 사용)
        # Sprint 29 Slice C: function-local → module-level export. parity invariant 검증 대상.
        if name in _V4_ALIASES:
            name = _V4_ALIASES[name]

        # math.* — 순수 함수, caller state 없음. na 전파.
        if name and name.startswith("math."):
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
                return math.floor(args[0])
            if name == "math.ceil":
                return math.ceil(args[0])
            if name == "math.round":
                return round(args[0])
            if name == "math.sqrt":
                return math.sqrt(args[0])
            if name == "math.log":
                return math.log(args[0]) if len(args) == 1 else math.log(args[0], args[1])
            if name == "math.pow":
                return args[0] ** args[1]
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
                return math.exp(args[0])
            if name == "math.sum":
                # Pine math.sum(source, length) — 단순 cumulative sum stub
                # 정밀 구현은 ta.sum (stdlib); math.sum 은 거의 쓰이지 않으므로 단순 합산.
                return sum(args) if len(args) > 1 else args[0]
            raise PineRuntimeError(f"math function not supported: {name}")

        # timestamp(y, mo, d, h, mi[, s]) — v4/v5 built-in. 실제 datetime은 불필요
        # (time_cond 같은 기간 필터에서만 사용). year/month/day/hour/minute을 반영한
        # approx epoch ms 반환. time(=bar_index 기반 stub)과 같은 scale로 비교됨.
        if name == "timestamp":
            if not node.args:
                return 0
            parts: list[int] = []
            for a in node.args[:5]:
                val = self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a)
                try:
                    parts.append(int(val))
                except (TypeError, ValueError):
                    parts.append(0)
            while len(parts) < 5:
                parts.append(0)
            year, month, day, hour, minute = parts[:5]
            if year <= 1970:
                return 0
            # approx: (year-1970)*365일 + (month-1)*30일 + (day-1)*1일 → 초/ms 변환
            # 월·일 정보 보존이 목적 (정확한 calendar math는 H2+).
            days = (year - 1970) * 365 + (month - 1) * 30 + (day - 1)
            return days * 86_400 * 1000 + hour * 3_600_000 + minute * 60_000

        # tostring(x[, format]) — Pine v4/v5 numeric→str 변환. format은 무시(H2+).
        if name == "tostring":
            if not node.args:
                return ""
            val = self._eval_expr(
                node.args[0].value if isinstance(node.args[0], pyne_ast.Arg) else node.args[0]
            )
            if isinstance(val, float) and math.isnan(val):
                return "NaN"
            return str(val)

        # Sprint 29 Slice A (a): heikinashi NOP — 일반 OHLC 그대로 반환 (Trust Layer 위반, dogfood-only).
        # Heikin-Ashi 캔들 정확 변환은 Sprint 30+ ADR-009 Candle transformation layer.
        if name == "heikinashi":
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
            if len(node.args) < 3:
                return float("nan")
            expr_arg = node.args[2]
            return self._eval_expr(
                expr_arg.value if isinstance(expr_arg, pyne_ast.Arg) else expr_arg
            )

        # iff(cond, then, else) — v4 built-in (v5는 ternary로 대체). 단축평가.
        if name == "iff":
            if len(node.args) != 3:
                raise PineRuntimeError(f"iff expects 3 args, got {len(node.args)}")
            cond_arg, then_arg, else_arg = (
                a.value if isinstance(a, pyne_ast.Arg) else a for a in node.args
            )
            cond_val = self._eval_expr(cond_arg)
            return (
                self._eval_expr(then_arg) if self._truthy(cond_val) else self._eval_expr(else_arg)
            )

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
            )

        # strategy.* 실행 핸들러
        if name in ("strategy.entry", "strategy.close", "strategy.close_all", "strategy.exit"):
            return self._exec_strategy_call(name, node)

        # 렌더링 scope A — line/box/label/table. 좌표 저장 + getter만, 렌더링 NOP.
        if name in _RENDERING_FACTORIES:
            return self._exec_rendering_call(name, node)

        # handle.method() 형태 — line/box/label/table 객체의 메서드 호출
        if name and "." in name:
            head, _, tail = name.rpartition(".")
            handle = self._resolve_name_if_declared(head)
            if isinstance(handle, (LineObject, BoxObject, LabelObject, TableObject)):
                return self._exec_rendering_method(handle, tail, node)

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
            return None

        # NOTE (Sprint 21 P1 #1 + #4): user-defined function dispatch 는 _eval_call
        # 시작 직후 (v4 alias 전) 처리됨 — 본 위치는 unreachable. 의도적으로 제거하여
        # 단일 source of truth 유지 (plain identifier user_function 은 위 prior dispatch).

        raise PineRuntimeError(f"Call to {name!r} not supported in current scope")

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
        self._scope_stack.append(frame)
        # ta.* 상태 격리: call-site별 고유 prefix push → 동일 함수의 서로 다른 호출 위치가
        # 각자 독립 상태를 가지게 됨. call_node의 node_id/lineno/id 중 가용한 값 사용.
        call_prefix = str(
            getattr(call_node, "node_id", None)
            or getattr(call_node, "lineno", None)
            or id(call_node)
        )
        self.stdlib.push_call_prefix(call_prefix)
        try:
            last_expr_val: Any = None
            for stmt in fn_def.body:
                if isinstance(stmt, pyne_ast.Expr):
                    inner = stmt.value
                    # pynescript는 top-level if를 Expr(value=If)로 래핑. 이건 statement
                    # 실행이지 return expr이 아니므로 _exec_if로 우회.
                    if isinstance(inner, pyne_ast.If):
                        self._exec_if(inner)
                        continue
                    # 마지막 Expr(Tuple literal)은 Python tuple로 반환 — multi-return.
                    if isinstance(inner, pyne_ast.Tuple):
                        last_expr_val = tuple(self._eval_expr(e) for e in inner.elts)
                    else:
                        last_expr_val = self._eval_expr(inner)
                else:
                    self._exec_stmt(stmt)
            return last_expr_val
        finally:
            self._scope_stack.pop()
            self.stdlib.pop_call_prefix()

    # ---- Name 해석 (built-in + var + transient) ------------------------

    def _resolve_name(self, name: str) -> Any:
        # 로컬 frame 우선 — user function 호출 중 매개변수/로컬 변수 lookup.
        if self._scope_stack and name in self._scope_stack[-1]:
            return self._scope_stack[-1][name]
        if name in _BUILTIN_SERIES:
            return self.bar.current(name)
        if name == "bar_index":
            return self.bar.bar_index
        if name == "time":
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
        # Sprint 58 BL-242b: timeframe 속성 — 단일 타임프레임 백테스트 가정
        if chain in ("timeframe.isdaily", "timeframe.isminutes", "timeframe.ismonthly",
                     "timeframe.isseconds", "timeframe.isweekly"):
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
            )
        # ta.tr — built-in series: True Range = max(high-low, |high-prev_close|, |low-prev_close|)
        # 첫 bar 는 prev_close 가 nan → high-low 만 (Pine 동작과 동일)
        if chain == "ta.tr":
            high = self.bar.current("high")
            low = self.bar.current("low")
            prev_close = self.bar.history("close", 1)
            if math.isnan(prev_close):
                return high - low
            return max(high - low, abs(high - prev_close), abs(low - prev_close))
        # timeframe.period — Sprint 29 Slice A: BarContext 에 timeframe 미구현,
        # 기본값 "1D" 반환 (backtest 단일 timeframe 가정).
        if chain == "timeframe.period":
            return "1D"
        # color.* 는 렌더링 맥락에서만 쓰이므로 na 반환
        if chain.startswith("color."):
            return float("nan")
        # alert.freq_* / display.* 등 추가 Pine enum은 문자열 stub 반환
        if chain.startswith(("alert.freq_", "display.", "xloc.", "yloc.", "text.", "font.")):
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
            # BL-188 v3 entry placement gate (Track S) — disallowed session 이면
            # silent skip → equity/state 영향 0. 단일 reference =
            # `src.strategy.trading_sessions.is_allowed`. timestamps 미주입 시 skip 하지 않음
            # (회귀 0). v2_adapter 가 tz-naive sessions-only 활성 시 422 reject.
            if self.strategy.sessions_allowed:
                bar_ts = self.bar.current_timestamp()
                if bar_ts is not None:
                    from src.strategy.trading_sessions import is_allowed

                    if not is_allowed(list(self.strategy.sessions_allowed), bar_ts.to_pydatetime()):
                        return None

            trade_id = str(positional[0]) if positional else str(kwargs.get("id", "default"))
            # when= kwarg: False면 entry skip (Pine v4 backtest range 필터)
            when_val = kwargs.get("when")
            if when_val is not None and not self._truthy(when_val):
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
            # stop= 는 지원 (Week 3 Day 1부터). limit/trail은 여전히 미지원.
            stop_raw = kwargs.get("stop")
            stop: float | None = None
            if stop_raw is not None and not _is_na(stop_raw):
                stop = float(stop_raw)
            unsupported = [
                k for k in kwargs if k in ("limit", "trail_points", "trail_offset", "qty_percent")
            ]
            self.strategy.entry(
                trade_id,
                direction,  # type: ignore[arg-type]
                qty=qty,
                bar=bar_idx,
                fill_price=current_close,
                comment=comment,
                stop=stop,
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
            self.strategy.close_all(bar=bar_idx, fill_price=current_close)
            return None

        if name == "strategy.exit":
            # Sprint 23 BL-098 — 보수적 NOP (codex G.0 P1 #1+#2 회피).
            # Pine `strategy.exit(id, from_entry, profit/limit/loss/stop/trail_*)`
            # 는 exit order 예약 (target price 도달 시 trigger) — 즉시 close 아님.
            # close-fallback 시 (a) 거짓 양성 (entry 직후 즉시 close) + (b) wrong-id
            # close (Pine 첫 인자 id ≠ close target, from_entry 가 진짜 target).
            # H2 동안 silent NOP + warnings 기록. 후속 BL-104 에서 PendingExitOrder
            # 본격 구현으로 교체.
            #
            # when= kwarg: False면 skip (entry/close 패턴 일치).
            when_val = kwargs.get("when")
            if when_val is not None and not self._truthy(when_val):
                return None
            exit_id = str(positional[0]) if positional else str(kwargs.get("id", "default"))
            from_entry = (
                str(positional[1])
                if len(positional) >= 2
                else str(kwargs.get("from_entry", ""))
                if kwargs.get("from_entry")
                else None
            )
            # 모든 kwargs (when 제외) 를 unsupported 로 기록 — close 안 함을 사용자에게 알림
            unsupported = sorted(k for k in kwargs if k not in ("id", "from_entry", "when"))
            self.strategy.warnings.append(
                f"strategy.exit({exit_id!r}, from_entry={from_entry!r}): "
                f"NOP — H2 partial support (BL-098/BL-104). "
                f"ignored kwargs={unsupported}"
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
