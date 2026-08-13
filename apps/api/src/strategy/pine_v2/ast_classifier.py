"""Pine AST 구조 분류기 — Track S/A/M 판정 + 호출 분포 프로파일.

ADR-011 §3 3-Track Coverage 구현의 사전 조사 도구.
- Track S: `strategy()` 선언 있음 → Tier-3 네이티브 실행
- Track A: `indicator()`/v4 `study()` + `alert()`/`alertcondition()` 있음 → Tier-1 Alert Hook Parser
- Track M: `indicator()`/v4 `study()` + alert 없음 → Tier-4 Variable Explorer

Execution-First 원칙(P1) 검증용 카운트:
- `strategy.*` 체결 호출 (entry/exit/close/close_all/cancel)
- `alert()`/`alertcondition()` — 자발적 매매 신호 선언
- `request.security`/`request.security_lower_tf` — MTF
- 렌더링 객체 범위 A 대상: `box.*`/`label.*`/`line.*`/`table.*`
- 렌더링 NOP 대상: `plot`/`plotshape`/`bgcolor`/`fill`/`barcolor`/`hline`

공개 API:
- `classify_script(source: str) -> ScriptProfile`
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

from pynescript import ast as pyne_ast

Declaration = Literal["strategy", "indicator", "library", "unknown"]
Track = Literal["S", "A", "M", "unknown"]

_INDICATOR_ALIASES: frozenset[str] = frozenset({"indicator", "study"})
_RENDER_SCOPE_A_PREFIXES: frozenset[str] = frozenset({"box", "label", "line", "table"})
_RENDER_NOP_NAMES: frozenset[str] = frozenset({
    "plot", "plotshape", "plotchar", "plotbar", "plotcandle", "plotarrow",
    "bgcolor", "barcolor", "fill", "hline",
})
_ALERT_NAMES: frozenset[str] = frozenset({"alert", "alertcondition"})
_SECURITY_NAMES: frozenset[str] = frozenset({
    "request.security", "request.security_lower_tf",
})


@dataclass(frozen=True)
class ScriptProfile:
    """Pine 스크립트의 구조적 프로파일."""

    declaration: Declaration
    track: Track
    alert_count: int
    security_count: int
    strategy_calls: dict[str, int] = field(default_factory=dict)
    render_scope_a: dict[str, int] = field(default_factory=dict)
    render_nop: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화용 dict — fixture report 작성 시 사용."""
        return {
            "declaration": self.declaration,
            "track": self.track,
            "alert_count": self.alert_count,
            "security_count": self.security_count,
            "strategy_calls": dict(sorted(self.strategy_calls.items())),
            "render_scope_a": dict(sorted(self.render_scope_a.items())),
            "render_nop": dict(sorted(self.render_nop.items())),
        }


def _walk(node: Any) -> Iterator[Any]:
    yield node
    for child in pyne_ast.iter_child_nodes(node):
        yield from _walk(child)


def _call_name(node: Any) -> str | None:
    """Call 노드에서 함수명 추출: 'strategy' / 'ta.sma' / 'line.new' / 'request.security'."""
    if not isinstance(node, pyne_ast.Call):
        return None
    func = node.func
    if isinstance(func, pyne_ast.Name):
        return func.id
    if isinstance(func, pyne_ast.Attribute):
        parts: list[str] = []
        cur: Any = func
        while isinstance(cur, pyne_ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, pyne_ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _detect_declaration(tree: Any) -> Declaration:
    """top-level body에서 선언 호출 탐색 (strategy/indicator/study/library)."""
    for stmt in getattr(tree, "body", []):
        # 선언은 거의 항상 top-level 표현식 문
        expr = getattr(stmt, "value", stmt)
        name = _call_name(expr)
        if name is None:
            continue
        if name == "strategy":
            return "strategy"
        if name in _INDICATOR_ALIASES:
            return "indicator"
        if name == "library":
            return "library"
    return "unknown"


def _classify_track(decl: Declaration, alert_count: int) -> Track:
    if decl == "strategy":
        return "S"
    if decl in ("indicator", "library"):
        return "A" if alert_count > 0 else "M"
    return "unknown"


def classify_script(source: str) -> ScriptProfile:
    """Pine 소스를 pynescript로 파싱하여 구조 프로파일 반환."""
    tree = pyne_ast.parse(source)

    declaration = _detect_declaration(tree)

    alert = 0
    security = 0
    strategy_calls: Counter[str] = Counter()
    render_a: Counter[str] = Counter()
    render_nop: Counter[str] = Counter()

    for node in _walk(tree):
        name = _call_name(node)
        if name is None:
            continue
        if name in _ALERT_NAMES:
            alert += 1
            continue
        if name in _SECURITY_NAMES:
            security += 1
            continue
        if name.startswith("strategy."):
            strategy_calls[name] += 1
            continue
        if name in _RENDER_NOP_NAMES:
            render_nop[name] += 1
            continue
        prefix = name.split(".", 1)[0] if "." in name else None
        if prefix in _RENDER_SCOPE_A_PREFIXES:
            render_a[name] += 1
            continue

    track = _classify_track(declaration, alert)

    return ScriptProfile(
        declaration=declaration,
        track=track,
        alert_count=alert,
        security_count=security,
        strategy_calls=dict(strategy_calls),
        render_scope_a=dict(render_a),
        render_nop=dict(render_nop),
    )
