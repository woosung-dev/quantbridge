"""Pine AST 인터프리터 (비지터 패턴).

스프린트 1: 표현식 평가 + 기본 문 처리. `:=` self-reference와 복잡한 var 상태
추적은 단순 전략 한정으로 최소 범위에서 지원.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.strategy.pine.ast_nodes import (
    Assign,
    BinOp,
    FnCall,
    ForLoop,
    HistoryRef,
    Ident,
    IfExpr,
    IfStmt,
    Literal,
    Node,
    Program,
    VarDecl,
)
from src.strategy.pine.errors import PineRuntimeError, PineUnsupportedError
from src.strategy.pine.stdlib import SUPPORTED, is_supported
from src.strategy.pine.types import SignalResult


@dataclass
class Environment:
    """이름 → 값 매핑. Pine의 series는 pandas.Series로, scalar는 원시 타입."""

    variables: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def with_ohlcv(
        cls,
        *,
        open_: pd.Series,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> Environment:
        env = cls()
        env.variables.update({
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "hl2": (high + low) / 2,
            "hlc3": (high + low + close) / 3,
            "ohlc4": (open_ + high + low + close) / 4,
            "bar_index": pd.Series(range(len(close)), index=close.index),
            # strategy.long / strategy.short 등은 단순 상수로 매핑
            "strategy.long": "long",
            "strategy.short": "short",
            # 자주 쓰이는 na
            "na": float("nan"),
        })
        return env

    def lookup(self, name: str) -> Any:
        if name not in self.variables:
            raise PineRuntimeError(f"undefined identifier: {name}")
        return self.variables[name]

    def bind(self, name: str, value: Any) -> None:
        self.variables[name] = value


def evaluate_expression(node: Node, env: Environment) -> Any:
    """표현식 노드 평가."""
    if isinstance(node, Literal):
        return node.value

    if isinstance(node, Ident):
        return env.lookup(node.name)

    if isinstance(node, BinOp):
        return _eval_binop(node, env)

    if isinstance(node, IfExpr):
        cond = evaluate_expression(node.cond, env)
        then_ = evaluate_expression(node.then, env)
        else_ = evaluate_expression(node.else_, env)
        if isinstance(cond, pd.Series):
            # 시리즈 삼항 → np.where
            return pd.Series(
                np.where(cond, then_, else_),
                index=cond.index,
            )
        return then_ if cond else else_

    if isinstance(node, HistoryRef):
        target = evaluate_expression(node.target, env)
        offset = evaluate_expression(node.offset, env)
        if not isinstance(target, pd.Series):
            raise PineRuntimeError("history reference on non-series value")
        return target.shift(int(offset))

    if isinstance(node, FnCall):
        return _eval_fncall(node, env)

    raise PineRuntimeError(f"cannot evaluate node type: {type(node).__name__}")


def _eval_binop(node: BinOp, env: Environment) -> Any:
    op = node.op
    left = evaluate_expression(node.left, env)
    right = evaluate_expression(node.right, env)
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        return left / right
    if op == "%":
        return left % right
    if op == "<":
        return left < right
    if op == ">":
        return left > right
    if op == "<=":
        return left <= right
    if op == ">=":
        return left >= right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op == "and":
        if isinstance(left, pd.Series) or isinstance(right, pd.Series):
            return (left) & (right)
        return bool(left) and bool(right)
    if op == "or":
        if isinstance(left, pd.Series) or isinstance(right, pd.Series):
            return (left) | (right)
        return bool(left) or bool(right)
    if op == "not":
        # not은 (True, operand) 로 정규화되어 있음 — right가 피연산자
        if isinstance(right, pd.Series):
            return ~right.astype(bool)
        return not bool(right)
    raise PineRuntimeError(f"unknown operator: {op}")


def _eval_fncall(node: FnCall, env: Environment) -> Any:
    # input.* → 첫 인자(defval) 반환 (스프린트 1 단순화: 실제 입력 UI 없음)
    if node.name.startswith("input") or node.name == "input":
        if node.args:
            return evaluate_expression(node.args[0], env)
        return None

    # timestamp(...) → 미래 확장 (스프린트 1에선 0 반환하여 시간 윈도우 비활성화)
    if node.name == "timestamp":
        return 0

    # color.* / strategy.long 등 (이미 env에 등록) — 식별자 경로지만 함수 호출로 파싱됐을 수 있음
    # 여기선 화이트리스트 stdlib만 실행 함수로 간주
    if is_supported(node.name):
        args = [evaluate_expression(a, env) for a in node.args]
        kwargs = {kw.name: evaluate_expression(kw.value, env) for kw in node.kwargs}
        try:
            return SUPPORTED[node.name](*args, **kwargs)
        except Exception as e:
            raise PineRuntimeError(
                f"runtime error in {node.name}: {e}",
                line=node.source_span.line,
                column=node.source_span.column,
            ) from e

    # 여기까지 왔으면 validate_functions에서 이미 구조적 호출로 분류됐거나
    # 인터프리터 자체에서 처리할 의미 있는 함수가 아님.
    # Task 16에서 strategy.entry/close 등의 부수효과 호출을 처리.
    return None


# ---------------------------------------------------------------------------
# Task 16: 문 실행 + 시그널 수집
# ---------------------------------------------------------------------------


@dataclass
class _SignalAccumulator:
    """if-문 조건을 시그널로 누적."""

    entries: pd.Series
    exits: pd.Series

    @classmethod
    def zero_like(cls, series: pd.Series) -> _SignalAccumulator:
        false_like = pd.Series(False, index=series.index)
        return cls(entries=false_like.copy(), exits=false_like.copy())


@dataclass
class _BracketState:
    """strategy.exit 호출 시 평가된 stop/limit 가격 Series."""

    stop_series: pd.Series | None = None
    limit_series: pd.Series | None = None


def execute_program(
    program: Program,
    *,
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> SignalResult:
    """AST 프로그램 실행 → SignalResult 반환."""
    env = Environment.with_ohlcv(
        open_=open_, high=high, low=low, close=close, volume=volume,
    )
    signals = _SignalAccumulator.zero_like(close)
    brackets = _BracketState()

    for stmt in program.statements:
        _execute_statement(stmt, env, signals, brackets=brackets, gate=None)

    return _assemble_signal_result(signals, brackets, env)


def _assemble_signal_result(
    signals: _SignalAccumulator,
    brackets: _BracketState,
    env: Environment,
) -> SignalResult:
    entries = signals.entries.astype(bool)
    exits = signals.exits.astype(bool)

    pos_change = entries.astype(int) - exits.astype(int)
    position = pos_change.cumsum().clip(lower=0, upper=1)

    sl_stop = _carry_bracket(brackets.stop_series, entries, position)
    tp_limit = _carry_bracket(brackets.limit_series, entries, position)

    direction = pd.Series("long", index=entries.index) if bool(entries.any()) else None

    # position_size는 Task 2에서 채움. 이 Task에선 None 유지.
    return SignalResult(
        entries=entries,
        exits=exits,
        direction=direction,
        sl_stop=sl_stop,
        tp_limit=tp_limit,
        position_size=None,
        metadata={"vars": dict(env.variables)},
    )


def _carry_bracket(
    value_at_call: pd.Series | None,
    entries: pd.Series,
    position: pd.Series,
) -> pd.Series | None:
    """진입 바에서 value를 샘플링, 포지션 기간 동안 carry forward, flat에선 NaN."""
    if value_at_call is None:
        return None
    sampled = value_at_call.where(entries)
    carried = sampled.ffill()
    masked = carried.where(position == 1)
    return masked.astype(float)


def _execute_statement(
    node: Node,
    env: Environment,
    signals: _SignalAccumulator,
    *,
    brackets: _BracketState,
    gate: pd.Series | bool | None,
) -> None:
    """문 실행. `gate`는 상위 if의 누적 조건 (시그널 Series와 AND 결합)."""
    if isinstance(node, VarDecl):
        env.bind(node.name, evaluate_expression(node.expr, env))
        return

    if isinstance(node, Assign):
        # := 는 기존 바인딩 갱신. 스프린트 1에선 벡터 단위 치환.
        assert isinstance(node.target, Ident)
        env.bind(node.target.name, evaluate_expression(node.value, env))
        return

    if isinstance(node, IfStmt):
        cond_value = evaluate_expression(node.cond, env)
        new_gate = _combine_gate(gate, cond_value)
        for s in node.body:
            _execute_statement(s, env, signals, brackets=brackets, gate=new_gate)
        if node.else_body:
            neg = ~cond_value if isinstance(cond_value, pd.Series) else (not cond_value)
            else_gate = _combine_gate(gate, neg)
            for s in node.else_body:
                _execute_statement(s, env, signals, brackets=brackets, gate=else_gate)
        return

    if isinstance(node, FnCall):
        _execute_fncall_stmt(node, env, signals, brackets=brackets, gate=gate)
        return

    if isinstance(node, ForLoop):
        raise PineUnsupportedError(
            "for loop execution is not supported in sprint 1",
            feature="for",
            category="syntax",
            line=node.source_span.line,
            column=node.source_span.column,
        )

    # 표현식 단독 statement (부수효과 없음) → 평가만 하고 버림
    evaluate_expression(node, env)


def _combine_gate(
    gate: pd.Series | bool | None,
    cond: pd.Series | bool,
) -> pd.Series | bool:
    if gate is None:
        return cond
    if isinstance(gate, pd.Series) or isinstance(cond, pd.Series):
        return (gate) & (cond)
    return bool(gate) and bool(cond)


def _execute_fncall_stmt(
    node: FnCall,
    env: Environment,
    signals: _SignalAccumulator,
    *,
    brackets: _BracketState,
    gate: pd.Series | bool | None,
) -> None:
    name = node.name

    if name == "strategy.exit":
        kwargs = {kw.name: kw.value for kw in node.kwargs}
        has_stop = "stop" in kwargs
        has_limit = "limit" in kwargs
        if "profit" in kwargs or "loss" in kwargs:
            raise PineUnsupportedError(
                "strategy.exit(profit=, loss=) offset-based brackets are deferred",
                feature="strategy.exit(profit/loss)",
                category="function",
                line=node.source_span.line,
                column=node.source_span.column,
            )
        if not has_stop and not has_limit:
            raise PineUnsupportedError(
                "strategy.exit requires stop= or limit= argument",
                feature="strategy.exit(no-args)",
                category="function",
                line=node.source_span.line,
                column=node.source_span.column,
            )
        if has_stop:
            brackets.stop_series = _ensure_series(
                evaluate_expression(kwargs["stop"], env), signals.entries.index
            )
        if has_limit:
            brackets.limit_series = _ensure_series(
                evaluate_expression(kwargs["limit"], env), signals.entries.index
            )
        return

    # 진입 시그널
    if name == "strategy.entry":
        signals.entries = signals.entries | _gate_as_bool_series(gate, signals.entries.index)
        return

    # 청산 시그널
    if name == "strategy.close":
        signals.exits = signals.exits | _gate_as_bool_series(gate, signals.exits.index)
        return

    # 시각화/알림/기타 부수효과 함수 — no-op
    if name in (
        "plot", "plotshape", "bgcolor", "barcolor", "fill",
        "alert", "alertcondition",
        "indicator", "strategy",
    ):
        return

    # 그 외는 표현식으로 평가 (값 폐기)
    evaluate_expression(node, env)


def _ensure_series(value: Any, index: pd.Index) -> pd.Series:
    """스칼라 → 동일 값 Series, Series → 그대로."""
    if isinstance(value, pd.Series):
        return value.astype(float)
    return pd.Series(float(value), index=index)


def _gate_as_bool_series(gate: pd.Series | bool | None, index: pd.Index) -> pd.Series:
    if gate is None or gate is True:
        return pd.Series(True, index=index)
    if gate is False:
        return pd.Series(False, index=index)
    if isinstance(gate, pd.Series):
        return gate.fillna(False).astype(bool)
    return pd.Series(bool(gate), index=index)
