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
    BinOp,
    FnCall,
    HistoryRef,
    Ident,
    IfExpr,
    Literal,
    Node,
)
from src.strategy.pine.errors import PineRuntimeError
from src.strategy.pine.stdlib import SUPPORTED, is_supported


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
