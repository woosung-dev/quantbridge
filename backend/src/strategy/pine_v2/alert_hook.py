"""Alert Hook 추출 + 메시지 분류기 v0 (ADR-011 §2.1 Tier-1 사전 조사).

`alert()` / `alertcondition()` 호출을 AST에서 수집하여 매매 신호로 분류한다.

분류 우선순위 (3단계):
1. JSON 파싱 — `alert('{"action":"buy","size":1}')` 구조화 메시지 (`action` 필드 사용)
2. 키워드 매칭 (word-boundary, case-insensitive)
3. Fallback — `unknown`

한계 (Day 3 v0):
- 조건식 역추적(ADR-011 §2.1.3) 미구현 — 감싸는 `if` 조건은 Tier-1에서 구현
- 메시지 concat(`"BUY at " + str.tostring(close)`)은 literal 부분만 추출
- alert은 자발적 매매 신호 선언 가정이지만 Pine 개발자가 정보성 메시지를 alert()로 쓰는 경우 많음 → `information` 분류 유지

공개 API:
- `collect_alerts(source) -> list[AlertHook]`
- `classify_message(text) -> SignalKind`
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pynescript import ast as pyne_ast


class SignalKind(StrEnum):
    LONG_ENTRY = "long_entry"
    SHORT_ENTRY = "short_entry"
    LONG_EXIT = "long_exit"
    SHORT_EXIT = "short_exit"
    INFORMATION = "information"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AlertHook:
    """단일 alert/alertcondition 호출의 추출 결과."""

    kind: str  # "alert" | "alertcondition"
    message: str  # 추출된 메시지 (literal 우선, concat은 부분 복원)
    condition_expr: str | None  # alertcondition의 arg0 조건식 텍스트 요약 (있을 때만)
    signal: SignalKind  # 메시지 기반 분류 결과
    index: int  # corpus 내 순서 (1-based)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kind": self.kind,
            "message": self.message,
            "condition_expr": self.condition_expr,
            "signal": self.signal.value,
        }


# 분류 규칙 — 순서가 우선순위. information을 먼저 (돌파 알림이 "buy/sell" 포함 가능하기 때문).
# word-boundary 매칭으로 오매칭 방지.
_KEYWORD_RULES: list[tuple[SignalKind, tuple[str, ...]]] = [
    (SignalKind.INFORMATION, (
        r"\bbreak\b", r"\btrendline\b", r"\bsession\b", r"\bpivot\b",
        r"돌파", r"세션",
    )),
    (SignalKind.LONG_EXIT, (
        r"\bclose\s+long\b", r"\bexit\s+long\b", r"롱\s*청산", r"매수\s*청산",
    )),
    (SignalKind.SHORT_EXIT, (
        r"\bclose\s+short\b", r"\bexit\s+short\b", r"숏\s*청산", r"매도\s*청산",
    )),
    (SignalKind.LONG_ENTRY, (
        r"\blong\b", r"\bbuy\b", r"\bbull\b", r"매수",
    )),
    (SignalKind.SHORT_ENTRY, (
        r"\bshort\b", r"\bsell\b", r"\bbear\b", r"매도",
    )),
]


def classify_message(text: str) -> SignalKind:
    """메시지 문자열을 신호 종류로 분류."""
    # 1. JSON 파싱 시도
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            action = str(data.get("action", "")).lower()
            if action in ("buy", "long"):
                return SignalKind.LONG_ENTRY
            if action in ("sell", "short"):
                return SignalKind.SHORT_ENTRY
            if action in ("close_long", "exit_long"):
                return SignalKind.LONG_EXIT
            if action in ("close_short", "exit_short"):
                return SignalKind.SHORT_EXIT
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. 키워드 매칭
    for signal, patterns in _KEYWORD_RULES:
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                return signal

    # 3. Fallback
    return SignalKind.UNKNOWN


def _stringify(node: Any) -> str:
    """AST 노드를 사람이 읽을 수 있는 문자열로 근사 복원 (메시지/조건식 요약용)."""
    if isinstance(node, pyne_ast.Constant):
        return str(node.value)
    if isinstance(node, pyne_ast.Name):
        return node.id
    if isinstance(node, pyne_ast.Attribute):
        return f"{_stringify(node.value)}.{node.attr}"
    if isinstance(node, pyne_ast.BinOp):
        return f"{_stringify(node.left)} + {_stringify(node.right)}"
    if isinstance(node, pyne_ast.Compare):
        left = _stringify(node.left)
        # Compare는 comparators / ops 쌍으로 되어 있으나 v0는 첫 관계만 표시
        comps = getattr(node, "comparators", [])
        if comps:
            return f"{left} <cmp> {_stringify(comps[0])}"
        return left
    if isinstance(node, pyne_ast.Call):
        func = _stringify(node.func)
        args = ", ".join(_stringify(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args[:2])
        if len(node.args) > 2:
            args += ", ..."
        return f"{func}({args})"
    return f"<{type(node).__name__}>"


def _walk(node: Any) -> Iterator[Any]:
    yield node
    for child in pyne_ast.iter_child_nodes(node):
        yield from _walk(child)


def _is_call_named(node: Any, names: tuple[str, ...]) -> bool:
    """Call 노드의 함수명이 names에 포함되는지."""
    if not isinstance(node, pyne_ast.Call):
        return False
    f = node.func
    if isinstance(f, pyne_ast.Name):
        return f.id in names
    return False


def _arg_value(arg: Any) -> Any:
    """Arg 래퍼가 있으면 value를 벗기고, 없으면 원본."""
    return arg.value if isinstance(arg, pyne_ast.Arg) else arg


def _extract_literal_message(arg_node: Any) -> str:
    """메시지 인자에서 literal 문자열 우선 추출, concat은 literal 부분만."""
    val = _arg_value(arg_node)
    if isinstance(val, pyne_ast.Constant) and isinstance(val.value, str):
        return val.value
    if isinstance(val, pyne_ast.BinOp):
        left = _extract_literal_message(val.left)
        right = _extract_literal_message(val.right)
        return left + right
    return ""


def collect_alerts(source: str) -> list[AlertHook]:
    """Pine 소스에서 alert() / alertcondition() 호출을 순서대로 추출·분류."""
    tree = pyne_ast.parse(source)
    hooks: list[AlertHook] = []
    idx = 0

    for node in _walk(tree):
        # alert(message, freq, ...) — message는 arg0
        if _is_call_named(node, ("alert",)):
            idx += 1
            if not node.args:
                continue
            message = _extract_literal_message(node.args[0])
            hooks.append(AlertHook(
                kind="alert",
                message=message,
                condition_expr=None,
                signal=classify_message(message),
                index=idx,
            ))
            continue

        # alertcondition(condition, title, message) — condition=arg0, message=arg2
        if _is_call_named(node, ("alertcondition",)):
            idx += 1
            if not node.args:
                continue
            condition_expr = _stringify(_arg_value(node.args[0]))
            # message는 3번째 positional 또는 name='message' keyword
            message = ""
            if len(node.args) >= 3:
                message = _extract_literal_message(node.args[2])
            # Pine에서 kwarg 스타일도 지원 — Arg.name 체크
            if not message:
                for a in node.args:
                    if isinstance(a, pyne_ast.Arg) and getattr(a, "name", None) == "message":
                        message = _extract_literal_message(a)
                        break
            hooks.append(AlertHook(
                kind="alertcondition",
                message=message,
                condition_expr=condition_expr,
                signal=classify_message(message),
                index=idx,
            ))

    return hooks
