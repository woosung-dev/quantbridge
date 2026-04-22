"""Alert Hook 추출 + 메시지/조건 분류기 v1 (ADR-011 §2.1 Tier-1 사전 조사).

`alert()` / `alertcondition()` 호출을 AST에서 수집하여 매매 신호로 분류한다.

v1 개선 (Day 6 — ADR-011 §2.1.3 condition-trace 구현):
- 감싸는 `if` 문의 test 조건 ancestor tracking
- 조건 변수명을 AST의 대응 Assign으로 역추적하여 정의 문자열 확보
- 메시지 기반 분류 vs 조건 기반 분류 독립 수행 → `discrepancy` 플래그
- i3_drfx alert #6(`message='BUY'` + `condition=bear`) 같은 소스 불일치를 **자동 감지**

분류 우선순위 (3단계, 메시지·조건 공통):
1. JSON 파싱 — `alert('{"action":"buy","size":1}')` 구조화 메시지 (`action` 필드 사용)
2. 키워드 매칭 (word-boundary, case-insensitive)
3. Fallback — `unknown`

v1 한계 (Sprint 8b Tier-1에서 완성 예정):
- ancestor 탐색은 직계 If에 한정; 중첩 if + and/or 복합 조건은 얕은 stringify만
- 변수 해석은 top-level Assign 1회 look-up (체인은 미지원)
- else 분기 alert의 의미 반전은 자동화하지 않음(branch 메타만 기록)
- 메시지 concat(`"BUY at " + str.tostring(close)`)은 literal 부분만 추출

공개 API:
- `collect_alerts(source) -> list[AlertHook]`
- `classify_message(text) -> SignalKind`
"""

from __future__ import annotations

import json
import os
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
    """단일 alert/alertcondition 호출의 v1 추출 결과.

    분류 필드:
    - `message_signal`: 메시지 문자열 기반 분류 (항상 수행)
    - `condition_signal`: 조건식 기반 분류 (조건 확보 가능 시)
    - `signal`: 최종 권고 값 (condition 우선, 없으면 message)
    - `discrepancy`: message vs condition 불일치 (둘 다 UNKNOWN 아닐 때만 True)

    조건 소스 필드:
    - `condition_expr`: alertcondition arg0 직접 stringify
    - `enclosing_if_condition`: 감싸는 if 의 test 조건 stringify
    - `enclosing_if_branch`: "then" | "else" | None (alert의 위치)
    - `resolved_condition`: 변수 해석 적용한 최종 조건 텍스트
    """

    kind: str  # "alert" | "alertcondition"
    message: str
    condition_expr: str | None
    enclosing_if_condition: str | None
    enclosing_if_branch: str | None  # "then" | "else" | None
    resolved_condition: str | None
    message_signal: SignalKind
    condition_signal: SignalKind | None
    signal: SignalKind  # 최종 권고 (condition 우선)
    discrepancy: bool
    index: int
    # Tier-1 bar 단위 조건 재평가용 — alertcondition arg0 또는 enclosing if.test의 AST 노드.
    # JSON 직렬화 대상 아님 (to_dict에서 제외). pyne_ast.Expression 하위 노드 허용.
    condition_ast: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kind": self.kind,
            "message": self.message,
            "condition_expr": self.condition_expr,
            "enclosing_if_condition": self.enclosing_if_condition,
            "enclosing_if_branch": self.enclosing_if_branch,
            "resolved_condition": self.resolved_condition,
            "message_signal": self.message_signal.value,
            "condition_signal": (
                self.condition_signal.value if self.condition_signal is not None else None
            ),
            "signal": self.signal.value,
            "discrepancy": self.discrepancy,
        }


_KEYWORD_RULES: list[tuple[SignalKind, tuple[str, ...]]] = [
    (
        SignalKind.INFORMATION,
        (
            r"\bbreak\b",
            r"\btrendline\b",
            r"\bsession\b",
            r"\bpivot\b",
            r"돌파",
            r"세션",
        ),
    ),
    (
        SignalKind.LONG_EXIT,
        (
            r"\bclose\s+long\b",
            r"\bexit\s+long\b",
            r"롱\s*청산",
            r"매수\s*청산",
        ),
    ),
    (
        SignalKind.SHORT_EXIT,
        (
            r"\bclose\s+short\b",
            r"\bexit\s+short\b",
            r"숏\s*청산",
            r"매도\s*청산",
        ),
    ),
    (
        SignalKind.LONG_ENTRY,
        (
            r"\blong\b",
            r"\bbuy\b",
            r"\bbull\b",
            r"매수",
        ),
    ),
    (
        SignalKind.SHORT_ENTRY,
        (
            r"\bshort\b",
            r"\bsell\b",
            r"\bbear\b",
            r"매도",
        ),
    ),
]

# loose 모드: INFORMATION을 마지막 우선순위로 이동 + bull/bear는 prefix 매칭(bullish/bearish)
# (Sprint X1 — i2_luxalgo 류 LuxAlgo indicator alert을 매매 신호로 분류 가능하게 함)
_KEYWORD_RULES_LOOSE: list[tuple[SignalKind, tuple[str, ...]]] = [
    (
        SignalKind.LONG_EXIT,
        (
            r"\bclose\s+long\b",
            r"\bexit\s+long\b",
            r"롱\s*청산",
            r"매수\s*청산",
        ),
    ),
    (
        SignalKind.SHORT_EXIT,
        (
            r"\bclose\s+short\b",
            r"\bexit\s+short\b",
            r"숏\s*청산",
            r"매도\s*청산",
        ),
    ),
    (
        SignalKind.LONG_ENTRY,
        (
            r"\blong\b",
            r"\bbuy\b",
            r"\bbull",
            r"매수",
        ),
    ),
    (
        SignalKind.SHORT_ENTRY,
        (
            r"\bshort\b",
            r"\bsell\b",
            r"\bbear",
            r"매도",
        ),
    ),
    (
        SignalKind.INFORMATION,
        (
            r"\bbreak\b",
            r"\btrendline\b",
            r"\bsession\b",
            r"\bpivot\b",
            r"돌파",
            r"세션",
        ),
    ),
]


def _get_heuristic_mode() -> str:
    """환경변수 `PINE_ALERT_HEURISTIC_MODE` 를 읽어 'strict' 또는 'loose' 반환.

    - 미설정·잘못된 값 → 'strict' (후방호환).
    - 대소문자 무관(`LOOSE`/`Loose`/`loose` 모두 동일).
    - **lazy read** — `os.environ.get` 호출이 매번 일어나므로 pytest monkeypatch가
      안전하게 동작한다 (모듈 import 시점 캐싱 없음).

    loose 모드는 break/trendline/session/pivot 같은 context 키워드보다
    방향 키워드(long/short/bull/bear/매수/매도)를 우선 매칭하여 LuxAlgo류
    indicator alert을 매매 신호로 분류할 수 있게 한다.
    """
    raw = os.environ.get("PINE_ALERT_HEURISTIC_MODE", "strict")
    mode = raw.lower().strip() if isinstance(raw, str) else "strict"
    return "loose" if mode == "loose" else "strict"


def classify_message(text: str) -> SignalKind:
    """문자열(메시지 또는 조건식 stringify)을 신호 종류로 분류.

    모드 (환경변수 `PINE_ALERT_HEURISTIC_MODE`):
    - **strict** (default): INFORMATION(break/trendline/session/pivot) > 방향 > UNKNOWN
    - **loose**: 방향(long/short/bull*/bear*/매수/매도) > INFORMATION > UNKNOWN
      (loose는 bull/bear에 한해 prefix 매칭으로 'bullish'/'bearish'도 잡음)
    """
    if not text:
        return SignalKind.UNKNOWN

    stripped = text.strip()
    # 1. JSON 파싱 시도 (모드 무관)
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

    # 2. 키워드 매칭 (모드별 rule set 선택)
    rules = _KEYWORD_RULES_LOOSE if _get_heuristic_mode() == "loose" else _KEYWORD_RULES
    for signal, patterns in rules:
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                return signal

    # 3. Fallback
    return SignalKind.UNKNOWN


def _stringify(node: Any) -> str:
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
        comps = getattr(node, "comparators", [])
        if comps:
            return f"{left} <cmp> {_stringify(comps[0])}"
        return left
    if isinstance(node, pyne_ast.BoolOp):
        op = type(node.op).__name__.lower()  # And | Or
        values = getattr(node, "values", [])
        return f" {op} ".join(_stringify(v) for v in values)
    if isinstance(node, pyne_ast.UnaryOp):
        return f"not {_stringify(node.operand)}"
    if isinstance(node, pyne_ast.Call):
        func = _stringify(node.func)
        args = ", ".join(
            _stringify(a.value if isinstance(a, pyne_ast.Arg) else a) for a in node.args[:2]
        )
        if len(node.args) > 2:
            args += ", ..."
        return f"{func}({args})"
    return f"<{type(node).__name__}>"


def _is_call_named(node: Any, names: tuple[str, ...]) -> bool:
    if not isinstance(node, pyne_ast.Call):
        return False
    f = node.func
    if isinstance(f, pyne_ast.Name):
        return f.id in names
    return False


def _arg_value(arg: Any) -> Any:
    return arg.value if isinstance(arg, pyne_ast.Arg) else arg


def _extract_literal_message(arg_node: Any) -> str:
    val = _arg_value(arg_node)
    if isinstance(val, pyne_ast.Constant) and isinstance(val.value, str):
        return val.value
    if isinstance(val, pyne_ast.BinOp):
        left = _extract_literal_message(val.left)
        right = _extract_literal_message(val.right)
        return left + right
    return ""


def _build_symbol_table(tree: Any) -> dict[str, str]:
    """top-level `Assign`에서 `Name = expr` 매핑 수집 (ADR-011 §2.1.3 look-up 테이블).

    중복 정의 시 마지막 것 유지(Pine은 재할당 허용; 보수적으로 마지막 정의 채택).
    """
    table: dict[str, str] = {}
    for stmt in getattr(tree, "body", []):
        if isinstance(stmt, pyne_ast.Assign):
            # pynescript는 targets(list) 또는 target(single) 중 하나 사용 — 양쪽 지원
            targets_attr = getattr(stmt, "targets", None)
            if targets_attr:
                targets = targets_attr
            else:
                single = getattr(stmt, "target", None)
                targets = [single] if single is not None else []
            value = getattr(stmt, "value", None)
            if value is None:
                continue
            for tgt in targets:
                if isinstance(tgt, pyne_ast.Name):
                    table[tgt.id] = _stringify(value)
    return table


def _resolve_condition(
    expr: str | None,
    *,
    symbol_table: dict[str, str],
    depth: int = 2,
) -> str | None:
    """조건 텍스트를 symbol_table로 해석. 단순 Name 한 개면 1회 look-up.

    재귀 체인은 피함 (v1 단순성) — depth 2까지.
    """
    if expr is None:
        return None
    cur = expr.strip()
    for _ in range(depth):
        if cur in symbol_table:
            cur = symbol_table[cur]
        else:
            break
    return cur


def _walk_with_if_context(node: Any) -> Iterator[tuple[Any, Any | None, str | None]]:
    """AST 순회: (node, enclosing_if, branch) 튜플. branch="then"|"else"|None."""

    def recurse(
        n: Any,
        enclosing_if: Any | None,
        branch: str | None,
    ) -> Iterator[tuple[Any, Any | None, str | None]]:
        yield n, enclosing_if, branch
        # If 노드에 들어갈 땐 test/body/orelse 자식들의 컨텍스트를 분기
        if isinstance(n, pyne_ast.If):
            # test 자식들: 아직 bodies 밖. enclosing_if는 한 단계 위 그대로
            yield from recurse(n.test, enclosing_if, branch)
            for stmt in n.body:
                yield from recurse(stmt, n, "then")
            for stmt in n.orelse or []:
                yield from recurse(stmt, n, "else")
            return
        # 일반 노드: 자식들 상속
        for child in pyne_ast.iter_child_nodes(n):
            yield from recurse(child, enclosing_if, branch)

    yield from recurse(node, None, None)


def collect_alerts(source: str) -> list[AlertHook]:
    """Pine 소스에서 alert/alertcondition을 추출·분류 (v1: condition-trace 포함)."""
    tree = pyne_ast.parse(source)
    symbol_table = _build_symbol_table(tree)
    hooks: list[AlertHook] = []
    idx = 0

    for node, enclosing_if, branch in _walk_with_if_context(tree):
        is_alert = _is_call_named(node, ("alert",))
        is_alertcondition = _is_call_named(node, ("alertcondition",))
        if not (is_alert or is_alertcondition):
            continue

        idx += 1
        if not node.args:
            continue

        # 메시지 추출 + 조건 AST 보존 (Tier-1 bar 재평가용)
        message = ""
        condition_expr: str | None = None
        condition_ast_node: Any | None = None

        if is_alert:
            message = _extract_literal_message(node.args[0])
            # alert()는 조건을 enclosing if에서 가져옴 (아래에서 설정)
        else:  # alertcondition
            condition_ast_node = _arg_value(node.args[0])
            condition_expr = _stringify(condition_ast_node)
            if len(node.args) >= 3:
                message = _extract_literal_message(node.args[2])
            if not message:
                for a in node.args:
                    if isinstance(a, pyne_ast.Arg) and getattr(a, "name", None) == "message":
                        message = _extract_literal_message(a)
                        break

        # 감싸는 if 정보
        enclosing_if_condition: str | None = None
        if enclosing_if is not None:
            enclosing_if_condition = _stringify(enclosing_if.test)
            # alert()는 조건 AST를 enclosing if.test에서 상속
            if is_alert and condition_ast_node is None:
                condition_ast_node = enclosing_if.test

        # 조건 소스 우선순위: alertcondition arg0 > enclosing if test
        condition_source = condition_expr or enclosing_if_condition
        resolved_condition = _resolve_condition(condition_source, symbol_table=symbol_table)

        # 분류
        message_signal = classify_message(message)

        # 조건 기반 분류: 원본 condition_expr(변수명) → enclosing_if → resolved 순으로 시도
        # 'bear' 같은 의미 있는 변수명을 해석 결과(ta.crossunder...)보다 우선 반영.
        condition_signal: SignalKind | None = None
        for candidate in (condition_expr, enclosing_if_condition, resolved_condition):
            if candidate:
                cs = classify_message(candidate)
                if cs != SignalKind.UNKNOWN:
                    condition_signal = cs
                    break

        # 최종 signal: condition 우선, 없으면 message
        final = condition_signal if condition_signal is not None else message_signal

        # discrepancy: 둘 다 확정적인데 다를 때
        discrepancy = (
            condition_signal is not None
            and message_signal != SignalKind.UNKNOWN
            and message_signal != condition_signal
        )

        hooks.append(
            AlertHook(
                kind="alert" if is_alert else "alertcondition",
                message=message,
                condition_expr=condition_expr,
                enclosing_if_condition=enclosing_if_condition,
                enclosing_if_branch=branch if enclosing_if is not None else None,
                resolved_condition=resolved_condition,
                message_signal=message_signal,
                condition_signal=condition_signal,
                signal=final,
                discrepancy=discrepancy,
                index=idx,
                condition_ast=condition_ast_node,
            )
        )

    return hooks
