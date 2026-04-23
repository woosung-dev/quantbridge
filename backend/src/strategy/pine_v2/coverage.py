"""Pine Script v5 coverage analyzer — pre-flight unsupported builtin detection.

Sprint Y1 (B+D) — TradingView Trust Layer 철학 정합:
- backtest 실행 *전* 에 미지원 함수/변수 식별 → 사용자에게 명시
- whack-a-mole 패턴 (실행 → 다음 미지원 노출 → 추가 → 반복) 종식
- 지원 set 은 interpreter / stdlib 와 SSOT — 추가 시 본 모듈만 갱신

분류:
- functions (call-style): `ta.sma(...)`, `strategy.entry(...)`, `math.max(...)` 등
- attributes (variable-style): `ta.tr`, `strategy.position_size`, `syminfo.mintick`,
  `close`, `high`, etc.
- enum constants: `line.style_dashed`, `shape.labelup` 등
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------
# SUPPORTED — interpreter._STDLIB_NAMES + stdlib._call() 분기 + _eval_attribute() 분기
# ---------------------------------------------------------------------

# stdlib functions (interpreter.py:684 _STDLIB_NAMES)
_TA_FUNCTIONS: frozenset[str] = frozenset({
    "ta.sma", "ta.ema", "ta.rma", "ta.atr", "ta.rsi",
    "ta.crossover", "ta.crossunder",
    "ta.highest", "ta.lowest",
    "ta.change", "ta.pivothigh", "ta.pivotlow",
    "ta.stdev", "ta.variance",
    "ta.sar", "ta.barssince", "ta.valuewhen",
})

# Math / utility (na, nz + math.* 일부)
_UTILITY_FUNCTIONS: frozenset[str] = frozenset({
    "na", "nz",
})

# strategy.* — interpreter._exec_strategy_call (entry/close/close_all/exit)
_STRATEGY_FUNCTIONS: frozenset[str] = frozenset({
    "strategy.entry", "strategy.close", "strategy.close_all", "strategy.exit",
})

# Indicator declarations (script header — NOP)
_DECLARATION_FUNCTIONS: frozenset[str] = frozenset({
    "indicator", "strategy", "library",
})

# Pine plot/visual — backtest 영향 없음 (interpreter NOP)
_PLOT_FUNCTIONS: frozenset[str] = frozenset({
    "plot", "plotshape", "plotchar", "plotarrow", "plotcandle", "plotbar",
    "bgcolor", "fill", "hline", "vline",
    "alertcondition", "alert",
    "label.new", "line.new", "box.new", "table.new",
    "color.new", "color.rgb",
})

# Input / config (interpreter NOP — default value 만 사용)
_INPUT_FUNCTIONS: frozenset[str] = frozenset({
    "input", "input.int", "input.float", "input.bool", "input.string",
    "input.color", "input.source", "input.timeframe", "input.symbol",
    "input.session", "input.price", "input.time",
})

# String / format (NOP — display only)
_STRING_FUNCTIONS: frozenset[str] = frozenset({
    "str.tostring", "str.tonumber", "str.format", "str.length",
    "tostring", "tonumber",
    "request.security",  # NOP placeholder (Sprint 8c — MTF는 H2+)
})

# Math built-ins (사용자 호출)
_MATH_FUNCTIONS: frozenset[str] = frozenset({
    "math.max", "math.min", "math.abs", "math.sign",
    "math.sqrt", "math.exp", "math.log", "math.log10",
    "math.pow", "math.round", "math.floor", "math.ceil",
    "math.sum", "math.avg",
})

# Pine v4→v5 호환 별칭 (interpreter alias map)
_V4_ALIASES: frozenset[str] = frozenset({
    "rma", "sma", "ema", "rsi", "atr", "highest", "lowest",
    "crossover", "crossunder", "change", "stdev", "variance",
    "iff", "switch",
})

SUPPORTED_FUNCTIONS: frozenset[str] = (
    _TA_FUNCTIONS
    | _UTILITY_FUNCTIONS
    | _STRATEGY_FUNCTIONS
    | _DECLARATION_FUNCTIONS
    | _PLOT_FUNCTIONS
    | _INPUT_FUNCTIONS
    | _STRING_FUNCTIONS
    | _MATH_FUNCTIONS
    | _V4_ALIASES
)

# Built-in series variables (close/high/low/open/volume + ta.tr 등)
_SERIES_ATTRS: frozenset[str] = frozenset({
    "open", "high", "low", "close", "volume",
    "hl2", "hlc3", "ohlc4",
    "time", "bar_index", "barstate.isfirst", "barstate.islast",
    "barstate.ishistory", "barstate.isconfirmed",
    "ta.tr",  # Sprint X1+X3 follow-up
})

# Strategy state attrs
_STRATEGY_ATTRS: frozenset[str] = frozenset({
    "strategy.long", "strategy.short",
    "strategy.position_size", "strategy.position_avg_price",
})

# Symbol info attrs
_SYMINFO_ATTRS: frozenset[str] = frozenset({
    "syminfo.mintick", "syminfo.tickerid",
})

# Pine enum constants (interpreter._ATTR_CONSTANTS — render scope A)
_ENUM_PREFIXES: tuple[str, ...] = (
    "line.style_", "extend.", "shape.", "location.", "size.",
    "position.", "color.",  # color.* → nan (NOP)
    "alert.freq_", "display.", "xloc.", "yloc.", "text.", "font.",
)

SUPPORTED_ATTRIBUTES: frozenset[str] = (
    _SERIES_ATTRS | _STRATEGY_ATTRS | _SYMINFO_ATTRS
)


def is_supported_attribute(chain: str) -> bool:
    """attribute access 가 지원되는지. enum prefix 도 처리."""
    if chain in SUPPORTED_ATTRIBUTES:
        return True
    return any(chain.startswith(p) for p in _ENUM_PREFIXES)


# Pine v5 의 알려진 namespace prefix. 이 외의 prefix (예: 사용자 변수 dntl.set_xy1)는
# coverage analyzer 의 검사 대상이 아님 — false positive 방지.
_KNOWN_NAMESPACES: frozenset[str] = frozenset({
    "ta", "math", "str", "strategy", "syminfo", "input", "request",
    "color", "line", "box", "label", "table", "polyline", "linefill",
    "shape", "location", "size", "position", "extend",
    "alert", "display", "xloc", "yloc", "text", "font", "barstate",
    "session", "currency", "dayofweek", "earnings", "splits",
    "dividends", "chart", "timeframe", "time",
})


def _is_pine_namespace(chain: str) -> bool:
    """chain 의 첫 token 이 알려진 Pine namespace 인가."""
    head = chain.split(".", 1)[0]
    return head in _KNOWN_NAMESPACES


# ---------------------------------------------------------------------
# Coverage analyzer
# ---------------------------------------------------------------------

# call: `name(` — `_collect_functions` 와 동일 패턴 + dotted chain
_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(")
# attribute: `chain` 단독 (call 직전 X). Pine 식별자 chain.
# 단순화: "xxx.yyy" 형태 모두 추출 후 함수 호출 위치 빼기.
_DOTTED_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\b")
_COMMENT_RE = re.compile(r"//[^\n]*")
_STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')


@dataclass(frozen=True)
class CoverageReport:
    """Pine 소스의 함수/변수 사용 vs SUPPORTED 매트릭스.

    - `unsupported_functions`: 호출 형태로 사용된 미지원 함수 (예: `fixnan()`)
    - `unsupported_attributes`: 변수 접근 형태로 사용된 미지원 chain (예: `ta.supertrend`)
    - `is_runnable`: 둘 다 비어있으면 True (backtest 실행 가능)
    """

    used_functions: tuple[str, ...]
    used_attributes: tuple[str, ...]
    unsupported_functions: tuple[str, ...]
    unsupported_attributes: tuple[str, ...]

    @property
    def is_runnable(self) -> bool:
        return not self.unsupported_functions and not self.unsupported_attributes

    @property
    def all_unsupported(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.unsupported_functions + self.unsupported_attributes)))


def _strip_noise(source: str) -> str:
    """주석 + 문자열 리터럴 제거."""
    no_comments = _COMMENT_RE.sub("", source)
    return _STRING_RE.sub('""', no_comments)


def analyze_coverage(source: str) -> CoverageReport:
    """Pine 소스를 정적 분석해 미지원 built-in 식별.

    한계:
    - regex 기반 — `aa.bb.cc` 형태 chain 의 prefix 매칭만 봄
    - 사용자 정의 함수 호출도 unsupported_functions 후보로 잡힐 수 있음 (top-level def 검출 보강 가능)
    - call 후 attribute access (`f().x`) 는 attribute 로 분류 안 함

    Pine Script 미지원 함수 1개라도 포함 시 backtest 실행 차단 (CLAUDE.md Golden Rule).
    """
    clean = _strip_noise(source)

    # 사용자 정의 함수: `myFunc(...) =>` 패턴
    user_defs = set()
    for m in re.finditer(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*=>", clean
    ):
        user_defs.add(m.group(1))

    skip_keywords = {
        "if", "for", "while", "and", "or", "not", "in", "true", "false", "switch",
    }

    # functions — namespace prefix 가 알려진 Pine namespace 일 때만 검사
    # (사용자 변수 method 호출 예: `dntl.set_xy1(...)` 는 false positive 방지로 skip)
    used_funcs_all = sorted({
        m.group(1)
        for m in _CALL_RE.finditer(clean)
        if m.group(1).lower() not in skip_keywords and m.group(1) not in user_defs
    })
    used_funcs = [
        f for f in used_funcs_all
        if "." not in f or _is_pine_namespace(f)
    ]
    unsupp_funcs = tuple(
        f for f in used_funcs if f not in SUPPORTED_FUNCTIONS
    )

    # attributes (call site 제외 — `(` 직후 위치는 함수로 이미 잡힘)
    used_attrs_set: set[str] = set()
    for m in _DOTTED_RE.finditer(clean):
        chain = m.group(1)
        # 호출 형태 ((직후 `(`) 인 경우 함수로 이미 잡힘 → skip
        end_idx = m.end()
        # check next non-space char is `(`
        rest = clean[end_idx:end_idx + 4].lstrip()
        if rest.startswith("("):
            continue
        used_attrs_set.add(chain)

    used_attrs = sorted(used_attrs_set)
    # 알려진 Pine namespace prefix 만 검사 — 사용자 변수 attribute (예: `dntl.x1`) skip
    unsupp_attrs = tuple(
        a for a in used_attrs
        if _is_pine_namespace(a) and not is_supported_attribute(a)
    )

    return CoverageReport(
        used_functions=tuple(used_funcs),
        used_attributes=tuple(used_attrs),
        unsupported_functions=unsupp_funcs,
        unsupported_attributes=unsupp_attrs,
    )
