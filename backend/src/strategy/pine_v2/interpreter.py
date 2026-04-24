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
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pandas as pd
from pynescript import ast as pyne_ast

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

# ta.* / na / nz — stdlib 디스패치 대상 이름
# Path β P-2 Coverage SSOT Sync — `coverage._TA_FUNCTIONS | _UTILITY_FUNCTIONS` 와
# 완전 일치해야 함 (ADR-013 §4.2). 새 stdlib 함수 추가 시 **3 파일 동시 갱신**
# (stdlib.py + interpreter.STDLIB_NAMES + coverage.py).
STDLIB_NAMES: frozenset[str] = frozenset({
    "ta.sma",
    "ta.ema",
    "ta.atr",
    "ta.rsi",
    "ta.crossover",
    "ta.crossunder",
    "ta.highest",
    "ta.lowest",
    "ta.change",
    "ta.pivothigh",
    "ta.pivotlow",
    "ta.stdev",
    "ta.variance",
    "ta.sar",  # Sprint X1+X3 W2 (i3_drfx Parabolic SAR)
    "ta.rma",  # Sprint X1+X3 follow-up (i3_drfx Wilder Running MA)
    "ta.barssince",
    "ta.valuewhen",  # Sprint 8c
    "na",
    "nz",
})

# ------------------------------------------------------------
# Bar Context — OHLCV 시계열 접근 계층
# ------------------------------------------------------------


@dataclass
class BarContext:
    """현재 bar + 히스토리 접근 인터페이스.

    Pine의 `close`는 현재 bar의 종가. `close[n]`은 n bar 전 종가.
    na(not available): 히스토리가 없는 구간 → float('nan') 반환.
    """

    ohlcv: pd.DataFrame  # columns: open/high/low/close/volume (float)
    bar_index: int = -1

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
                return self._eval_expr(value_expr)

            self.store.declare_if_new(
                key,
                factory,
                varip=(var_kind == "varip"),
            )
        else:
            # 비영속: 매 bar 평가. 함수 호출 중이면 로컬 frame에 기록.
            value = (
                self._eval_expr(node.value) if getattr(node, "value", None) is not None else None
            )
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

        # Pine v4 legacy alias — prefix 없는 stdlib을 ta.* / math.* 로 재라우팅
        # (i1_utbot / 일부 RTB 전략이 v4 문법 사용)
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

        # request.security(sym, tf, expression, ...) — Sprint 8c MVP: expression 인자 그대로.
        # (실제 MTF fetch는 H2+; NOP으로 graceful degrade.)
        if name in ("request.security", "request.security_lower_tf"):
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
        if name in ("strategy.entry", "strategy.close", "strategy.close_all"):
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
                # Pine input 시그니처: v4는 input(title=, type=, defval=, ...) keyword 사용 빈번.
                # defval= kwarg 우선, 없으면 첫 positional arg를 defval로 간주.
                pos_args, kw_args = self._collect_args(node)
                if "defval" in kw_args:
                    return kw_args["defval"]
                if pos_args:
                    return pos_args[0]
                return None
            return None

        # User-defined function (Sprint 8c) — Script top-level `foo(x) => ...`.
        # Name 단일 식별자만 매칭 (chain name 아님). 네임스페이스 prefix 없음.
        if name and name in self._user_functions:
            return self._call_user_function(self._user_functions[name], node)

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
        _ATTR_CONSTANTS = {
            "strategy.long": "long",
            "strategy.short": "short",
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
        if chain in _ATTR_CONSTANTS:
            return _ATTR_CONSTANTS[chain]
        # strategy.position_size / strategy.position_avg_price
        if chain == "strategy.position_size":
            return self.strategy.position_size
        if chain == "strategy.position_avg_price":
            return self.strategy.position_avg_price
        # syminfo 상수 — 심볼 메타데이터. Day 7: s1_pbr 호환을 위해 mintick 실제 값 반환
        if chain == "syminfo.mintick":
            return 0.01  # 기본값 — 심볼별 설정 기능은 향후 추가
        if chain == "syminfo.tickerid":
            return "UNKNOWN"
        # ta.tr — built-in series: True Range = max(high-low, |high-prev_close|, |low-prev_close|)
        # 첫 bar 는 prev_close 가 nan → high-low 만 (Pine 동작과 동일)
        if chain == "ta.tr":
            high = self.bar.current("high")
            low = self.bar.current("low")
            prev_close = self.bar.history("close", 1)
            if math.isnan(prev_close):
                return high - low
            return max(high - low, abs(high - prev_close), abs(low - prev_close))
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

            qty = float(
                kwargs.get(
                    "qty",
                    positional[2] if len(positional) >= 3 else 1.0,
                )
            )
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
