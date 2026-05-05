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
from typing import Literal, TypedDict

# ---------------------------------------------------------------------
# SUPPORTED — interpreter._STDLIB_NAMES + stdlib._call() 분기 + _eval_attribute() 분기
# ---------------------------------------------------------------------

# stdlib functions (interpreter.py:684 _STDLIB_NAMES)
_TA_FUNCTIONS: frozenset[str] = frozenset(
    {
        "ta.sma",
        "ta.ema",
        "ta.rma",
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
        "ta.sar",
        "ta.barssince",
        "ta.valuewhen",
    }
)

# Math / utility (na, nz + math.* 일부)
_UTILITY_FUNCTIONS: frozenset[str] = frozenset(
    {
        "na",
        "nz",
    }
)

# strategy.* — interpreter._exec_strategy_call (entry/close/close_all/exit)
_STRATEGY_FUNCTIONS: frozenset[str] = frozenset(
    {
        "strategy.entry",
        "strategy.close",
        "strategy.close_all",
        "strategy.exit",
    }
)

# Indicator declarations (script header — NOP)
_DECLARATION_FUNCTIONS: frozenset[str] = frozenset(
    {
        "indicator",
        "strategy",
        "library",
        "study",  # Sprint 21 — v2/v3 declaration alias (interpreter NOP via _NOP_NAMES)
    }
)

# Pine plot/visual — backtest 영향 없음 (interpreter NOP)
_PLOT_FUNCTIONS: frozenset[str] = frozenset(
    {
        "plot",
        "plotshape",
        "plotchar",
        "plotarrow",
        "plotcandle",
        "plotbar",
        "bgcolor",
        "barcolor",  # Sprint 29 Slice A: 시각 효과만, 백테스트 무관 (interpreter NOP)
        "fill",
        "hline",
        "vline",
        "alertcondition",
        "alert",
        "label.new",
        "line.new",
        "box.new",
        "table.new",
        "color.new",
        "color.rgb",
    }
)

# Sprint 29 Slice C: Rendering object methods (box/line/label/table) — _RENDERING_FACTORIES parity
_RENDERING_METHODS: frozenset[str] = frozenset(
    {
        "box.delete",
        "box.get_bottom",
        "box.get_top",
        "box.set_right",
        "label.delete",
        "label.set_xy",
        "line.delete",
        "line.get_price",
        "line.set_xy1",
        "line.set_xy2",
        "table.cell",
        "table.delete",
    }
)

# Input / config (interpreter NOP — default value 만 사용)
_INPUT_FUNCTIONS: frozenset[str] = frozenset(
    {
        "input",
        "input.int",
        "input.float",
        "input.bool",
        "input.string",
        "input.color",
        "input.source",
        "input.timeframe",
        "input.symbol",
        "input.session",
        "input.price",
        "input.time",
    }
)

# String / format (NOP — display only)
_STRING_FUNCTIONS: frozenset[str] = frozenset(
    {
        "str.tostring",
        "str.tonumber",
        "str.format",
        "str.length",
        "tostring",
        "tonumber",
    }
)

# Known-unsupported functions — 정적 분석에서 명시적으로 unsupported_functions에 포함.
# interpreter는 런타임 NOP/graceful degrade로 처리하지만,
# coverage analyzer는 사용자에게 "지원되지 않는 함수" 로 명시해야 함.
# (ADR-013 §4 Trust Layer 철학: partial silentfail → 명시적 unsupported 선언)
_KNOWN_UNSUPPORTED_FUNCTIONS: frozenset[str] = frozenset(
    {
        # "request.security",  # Sprint 29 Slice A: graceful (단일 timeframe 가정) → SUPPORTED
        "request.security_lower_tf",  # 본 sprint 미처리
        "request.dividends",
        "request.earnings",
        "request.quandl",
        "request.financial",
        "ticker.new",
    }
)

# Sprint 31 A (BL-159 + BL-161): Pine v5/v6 collection types 미지원 — 명시적 namespace.
# Pine v6 array<type> / matrix<type> / map<K,V> 신규 syntax 는 transpiler 미지원.
# Coverage analyzer pre-flight 에서 422 reject 의무 (interpreter._eval_call 880 line
# `Call to '...' not supported in current scope` runtime fail 차단).
#
# `_KNOWN_NAMESPACES` 에 등록하면 (`_is_pine_namespace` True 반환) `analyze_coverage`
# 가 SUPPORTED_FUNCTIONS 에 없는 모든 호출을 unsupported_functions 에 자동 등록.
# 추가 enumeration 불필요 — namespace 차원에서 catch.
_PINE_V6_COLLECTION_NAMESPACES: frozenset[str] = frozenset(
    {
        "array",  # array.new_float / array.push / array.pop / array.size 등 모두 catch
        "matrix",  # matrix.new / matrix.set / matrix.get 등
        "map",  # map.new / map.put / map.get 등
    }
)

# Sprint 29 Slice A: graceful security functions (단일 timeframe 가정으로 expression 인자 반환)
_SECURITY_FUNCTIONS: frozenset[str] = frozenset(
    {
        "request.security",  # Sprint 29 Slice A: graceful (interpreter.py:766-774)
        "security",  # Sprint 29 Slice A: v4 alias (no-namespace) — same graceful treatment
    }
)

# Sprint 29 Slice A: heikinashi Trust Layer 위반 + dogfood-only (ADR)
_HEIKINASHI_FUNCTIONS: frozenset[str] = frozenset(
    {
        "heikinashi",  # Sprint 29 Slice A (a): Trust Layer 위반 + dogfood-only flag
    }
)

# Sprint 29 Slice B: unsupported 발견 시 사용자에게 우회 패턴 안내.
# 80% coverage 임계 = DrFXGOD ~28 항목 중 23+ 등록.
_UNSUPPORTED_WORKAROUNDS: dict[str, str] = {
    # Data layer (request.* / syminfo.* / timeframe.*)
    "request.security_lower_tf": "다른 timeframe lower 데이터 미지원. 단일 timeframe 으로 전략 재구성 필요.",
    "request.dividends": "배당 데이터 미지원. 외부 source 연동 필요.",
    "request.earnings": "실적 데이터 미지원. 외부 source 연동 필요.",
    "ticker.new": "단일 ticker 사용 권장 (현재 backtest symbol).",
    "syminfo.prefix": "exchange prefix 는 backtest 에서 의미 없음. 변수 추출 권장.",
    "syminfo.ticker": "현재 backtest symbol 변수로 직접 사용.",
    "syminfo.timezone": "단일 timezone 가정 (UTC). timezone 분기 로직 제거 권장.",
    "timeframe.isdaily": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.isminutes": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.ismonthly": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.isseconds": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.isweekly": "단일 timeframe 가정. 분기 로직 제거.",
    "timeframe.multiplier": "현재 timeframe 의 numeric multiplier 가 필요하면 변수 추출.",
    "timeframe.period": "현재 timeframe string. backtest 는 단일 timeframe 가정 — 변수 추출 권장.",
    "barstate.isrealtime": "backtest 는 항상 historical. 분기 로직 제거.",
    # Math layer (ta.*/math.*)
    "ta.alma": "Arnaud Legoux MA 미지원. ta.sma 또는 ta.ema 로 근사 (정확도 차이 < 1%).",
    "ta.bb": "Bollinger Bands = ta.sma + ta.stdev 조합으로 직접 구현.",
    "ta.cross": "ta.crossover + ta.crossunder 조합으로 대체.",
    "ta.dmi": "Directional Movement Index = ta.atr + 직접 +DI/-DI 계산.",
    "ta.mom": "Momentum = close - close[length] 단순 계산.",
    "ta.wma": "Weighted MA = ta.sma 또는 ta.ema 로 근사.",
    "ta.obv": "On-Balance Volume = volume 누적 sum 으로 직접 구현.",
    # Drawing layer (시각 NOP — backtest 영향 없음)
    "table.cell_set_bgcolor": "Drawing layer 는 시각 NOP. 시각 표시 외 로직에 의존하면 안전.",
    "label.style_label_down": "label style 은 시각 NOP. 변수 추출 후 backtest 와 무관.",
    "label.style_label_left": "label style 은 시각 NOP.",
    "label.style_label_up": "label style 은 시각 NOP.",
    "label.get_x": "label 좌표 읽기는 시각 NOP. backtest 로직에서 제거 가능.",
    "label.set_x": "label 좌표 설정은 시각 NOP. backtest 로직에서 제거 가능.",
    "label.set_y": "label 좌표 설정은 시각 NOP. backtest 로직에서 제거 가능.",
    # Misc
    "fixnan": "nz() + 직전 값 캐싱 조합으로 대체 가능.",
    "time": "시간 기반 로직은 가격 기반 (close/open 변화) 권장. 필요 시 변수 추출.",
    "request.security": "단일 timeframe 전략으로 재구성 권장. Slice A graceful 가정 시 current bar 값 반환.",
    # Sprint 31 A (BL-159+161): Pine v5/v6 collection types 미지원 안내.
    # 공통 워크어라운드: 단일 series 변수 또는 ta.highest/lowest 등 stateful 지표.
    "array.new_float": "Pine array<float> 미지원. 단일 series 변수 또는 ta.highest/lowest 등 stateful 지표로 대체.",
    "array.new_int": "Pine array<int> 미지원. 단일 series 변수 사용.",
    "array.new_bool": "Pine array<bool> 미지원. 단일 boolean series 변수 사용.",
    "array.new_string": "Pine array<string> 미지원. 단일 string 변수 사용.",
    "array.new_color": "Pine array<color> 미지원. 시각 NOP 영역 — 제거 권장.",
    "array.new_line": "Pine array<line> 미지원. 시각 NOP 영역 — 단일 line 변수 사용.",
    "array.new_label": "Pine array<label> 미지원. 시각 NOP 영역 — 단일 label 변수 사용.",
    "array.new_box": "Pine array<box> 미지원. 시각 NOP 영역 — 단일 box 변수 사용.",
    "array.new_table": "Pine array<table> 미지원. 시각 NOP 영역 — 단일 table 변수 사용.",
    "array.push": "array.* 자체 미지원 → 호출 불필요. 단일 series 변수로 재구성.",
    "array.pop": "array.* 자체 미지원 → 호출 불필요.",
    "array.get": "array.* 자체 미지원 → 호출 불필요.",
    "array.set": "array.* 자체 미지원 → 호출 불필요.",
    "array.size": "array.* 자체 미지원 → 호출 불필요.",
    "array.shift": "array.* 자체 미지원 → 호출 불필요.",
    "array.unshift": "array.* 자체 미지원 → 호출 불필요.",
    "array.clear": "array.* 자체 미지원 → 호출 불필요.",
    "matrix.new": "Pine matrix<T> 미지원. 2D 데이터는 외부 source 또는 다중 series 로 재구성.",
    "map.new": "Pine map<K,V> 미지원. dict-like 데이터는 외부 source 또는 lookup 변수로 재구성.",
}

# Math built-ins (사용자 호출)
_MATH_FUNCTIONS: frozenset[str] = frozenset(
    {
        "math.max",
        "math.min",
        "math.abs",
        "math.sign",
        "math.sqrt",
        "math.exp",
        "math.log",
        "math.log10",
        "math.pow",
        "math.round",
        "math.floor",
        "math.ceil",
        "math.sum",
        "math.avg",
    }
)

# Pine v4→v5 호환 별칭 (interpreter alias map)
_V4_ALIASES: frozenset[str] = frozenset(
    {
        "rma",
        "sma",
        "ema",
        "rsi",
        "atr",
        "highest",
        "lowest",
        "crossover",
        "crossunder",
        "change",
        "stdev",
        "variance",
        "iff",
        "switch",
        # Sprint 21 (codex G.0 P1 #1) — RsiD/UtBot 의 v4 no-namespace builtin.
        # interpreter.py:597 의 `_V4_ALIASES` runtime map 과 동기 (3-파일 SSOT 의무).
        "abs",
        "max",
        "min",
        "pivothigh",
        "pivotlow",
        "barssince",
        "valuewhen",
        "timestamp",
    }
)

SUPPORTED_FUNCTIONS: frozenset[str] = (
    _TA_FUNCTIONS
    | _UTILITY_FUNCTIONS
    | _STRATEGY_FUNCTIONS
    | _DECLARATION_FUNCTIONS
    | _PLOT_FUNCTIONS
    | _RENDERING_METHODS
    | _INPUT_FUNCTIONS
    | _STRING_FUNCTIONS
    | _MATH_FUNCTIONS
    | _V4_ALIASES
    | _SECURITY_FUNCTIONS  # Sprint 29 Slice A: graceful request.security + v4 security
    | _HEIKINASHI_FUNCTIONS  # Sprint 29 Slice A (a): dogfood-only flag
)

# Built-in series variables (close/high/low/open/volume + ta.tr 등)
_SERIES_ATTRS: frozenset[str] = frozenset(
    {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "hl2",
        "hlc3",
        "ohlc4",
        "time",
        "bar_index",
        "barstate.isfirst",
        "barstate.islast",
        "barstate.ishistory",
        "barstate.isconfirmed",
        "ta.tr",  # Sprint X1+X3 follow-up
    }
)

# Strategy state attrs
_STRATEGY_ATTRS: frozenset[str] = frozenset(
    {
        "strategy.long",
        "strategy.short",
        "strategy.position_size",
        "strategy.position_avg_price",
    }
)

# Symbol info attrs
_SYMINFO_ATTRS: frozenset[str] = frozenset(
    {
        "syminfo.mintick",
        "syminfo.tickerid",
    }
)

# Sprint 21 (codex G.0 P1 #3) — explicit constant sets. _ENUM_PREFIXES 에
# `currency.` / `strategy.` / `timeframe.` 를 prefix 추가하면 nonexistent constant
# (e.g. `currency.USDXYZ123`) 까지 false-pass 됨. explicit set 만 허용.
_CURRENCY_CONSTANTS: frozenset[str] = frozenset(
    {
        "currency.USD",
        "currency.EUR",
        "currency.JPY",
        "currency.GBP",
        "currency.AUD",
        "currency.CAD",
        "currency.CHF",
        "currency.NZD",
        "currency.HKD",
        "currency.SGD",
        "currency.KRW",
        "currency.NONE",
    }
)

# strategy.fixed / cash / percent_of_equity 는 default_qty_type / commission_type
# 인자에 사용되는 enum constant. _STRATEGY_ATTRS (long/short/position_size/...)
# 와 분리해 운영 (둘 다 `strategy.` prefix 라 단일 set 도 가능하지만 의미 분리).
_STRATEGY_CONSTANTS_EXTRA: frozenset[str] = frozenset(
    {
        "strategy.fixed",
        "strategy.cash",
        "strategy.percent_of_equity",
        "strategy.commission_percent",
        "strategy.commission_cash_per_contract",
        "strategy.commission_cash_per_order",
    }
)

# Sprint 21 codex G.2 P1 #1 — _TIMEFRAME_CONSTANTS 제거.
# 이유: coverage supported 였지만 interpreter._eval_attribute 가 `timeframe.*` 미구현
# → preflight 통과 후 runtime fail (silent corruption). interpreter 추가는 scope 폭발
# (사용자 비교 logic 정확성 trade-off) → Sprint 22+ BL 로 이관.
# Sprint 29 Slice A: timeframe.period 를 명시적으로 추가 (interpreter._eval_attribute 구현 완료).
_TIMEFRAME_CONSTANTS: frozenset[str] = frozenset(
    {
        "timeframe.period",  # Sprint 29 Slice A: BarContext.timeframe string return (interpreter)
    }
)

# Pine enum constants (interpreter._ATTR_CONSTANTS — render scope A)
_ENUM_PREFIXES: tuple[str, ...] = (
    "line.style_",
    "extend.",
    "shape.",
    "location.",
    "size.",
    "position.",
    "color.",  # color.* → nan (NOP)
    "alert.freq_",
    "display.",
    "xloc.",
    "yloc.",
    "text.",
    "font.",
)

SUPPORTED_ATTRIBUTES: frozenset[str] = (
    _SERIES_ATTRS
    | _STRATEGY_ATTRS
    | _SYMINFO_ATTRS
    # Sprint 21 (codex G.0 P1 #3) — explicit constant sets (prefix 미허용, false-pass 차단)
    | _CURRENCY_CONSTANTS
    | _STRATEGY_CONSTANTS_EXTRA
    | _TIMEFRAME_CONSTANTS
)


def is_supported_attribute(chain: str) -> bool:
    """attribute access 가 지원되는지. enum prefix 도 처리."""
    if chain in SUPPORTED_ATTRIBUTES:
        return True
    return any(chain.startswith(p) for p in _ENUM_PREFIXES)


# Pine v5 의 알려진 namespace prefix. 이 외의 prefix (예: 사용자 변수 dntl.set_xy1)는
# coverage analyzer 의 검사 대상이 아님 — false positive 방지.
_KNOWN_NAMESPACES: frozenset[str] = frozenset(
    {
        "ta",
        "math",
        "str",
        "strategy",
        "syminfo",
        "input",
        "request",
        "color",
        "line",
        "box",
        "label",
        "table",
        "polyline",
        "linefill",
        "shape",
        "location",
        "size",
        "position",
        "extend",
        "alert",
        "display",
        "xloc",
        "yloc",
        "text",
        "font",
        "barstate",
        "session",
        "currency",
        "dayofweek",
        "earnings",
        "splits",
        "dividends",
        "chart",
        "timeframe",
        "time",
        "ticker",  # ticker.new 등 (H2+ 미지원)
        # Sprint 31 A (BL-159+161): Pine v5/v6 collection namespace 명시 catch.
        # `_PINE_V6_COLLECTION_NAMESPACES` 와 일관 — SUPPORTED 0건 → analyze_coverage
        # 가 자동으로 unsupported_functions/attributes 에 분류 (false negative 차단).
        "array",
        "matrix",
        "map",
    }
)


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
_DOTTED_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\b"
)
_COMMENT_RE = re.compile(r"//[^\n]*")
_STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')


# Sprint 29 Slice B: TypedDict for each unsupported call with line/category/workaround.
class UnsupportedCall(TypedDict):
    """미지원 호출 정보 — line 번호 + workaround 안내 포함."""

    name: str
    line: int
    col: int | None
    workaround: str | None
    category: Literal["drawing", "data", "syntax", "math", "other"]


# Sprint 29 Slice B: category 분류 helper
_CATEGORY_PREFIXES: dict[str, str] = {
    "line.": "drawing",
    "box.": "drawing",
    "label.": "drawing",
    "table.": "drawing",
    "plot": "drawing",
    "barcolor": "drawing",
    "fill": "drawing",
    "hline": "drawing",
    "ta.": "math",
    "math.": "math",
    "request.": "data",
    "syminfo.": "data",
    "timeframe.": "data",
    "ticker.": "data",
    "barstate.": "data",
    # Sprint 31 A (BL-159+161): Pine v5/v6 collection types — syntax category.
    # array/matrix/map 은 v6 신규 type system 으로, 본 transpiler 의 단일 series
    # 모델과 paradigm mismatch (data 가 아닌 syntax 차원의 갭).
    "array.": "syntax",
    "matrix.": "syntax",
    "map.": "syntax",
}


def _categorize(name: str) -> Literal["drawing", "data", "syntax", "math", "other"]:
    """미지원 이름의 category 반환."""
    for prefix, cat in _CATEGORY_PREFIXES.items():
        if name.startswith(prefix) or name == prefix.rstrip("."):
            return cat  # type: ignore[return-value]
    return "other"


def _find_line(source: str, pattern: str) -> int | None:
    """source 에서 pattern 첫 등장 line 번호 (1-indexed). 미발견 시 None."""
    escaped = re.escape(pattern)
    for i, line in enumerate(source.splitlines(), start=1):
        if re.search(rf"\b{escaped}\b", line):
            return i
    return None


# Sprint 29 codex G2 P0 fix: Trust Layer 의도적 위반 함수.
# coverage 가 supported 로 분류 (graceful execution) 하지만 backtest semantic 측면에서는
# Pine 원본과 결과 차이 가능 — 사용자 명시 동의 (`allow_degraded_pine=true`) 없이 backtest
# 실행 차단 의무. backtest/service.py 의 submit gate 가 본 set 검사.
_DEGRADED_FUNCTIONS: frozenset[str] = frozenset(
    {
        "request.security",  # Slice A: 단일 timeframe 가정 graceful — 다른 TF 의도 시 거짓 양성
        "heikinashi",  # Slice A (a) ADR: 일반 OHLC 그대로 반환 — Heikin-Ashi 결과 차이 가능
    }
)
_DEGRADED_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "timeframe.period",  # Slice A: BarContext.timeframe 미구현, "1D" 기본값 — 분기 잘못 실행
    }
)


@dataclass(frozen=True)
class CoverageReport:
    """Pine 소스의 함수/변수 사용 vs SUPPORTED 매트릭스.

    - `unsupported_functions`: 호출 형태로 사용된 미지원 함수 (예: `fixnan()`)
    - `unsupported_attributes`: 변수 접근 형태로 사용된 미지원 chain (예: `ta.supertrend`)
    - `is_runnable`: 둘 다 비어있으면 True (backtest 실행 가능)
    - `dogfood_only_warning`: heikinashi 등 Trust Layer 위반 함수 사용 시 경고 문자열
    - `degraded_calls`: Sprint 29 codex G2 P0 — Trust Layer 의도적 위반 (graceful 이지만 결과 차이).
      backtest submit 시 `allow_degraded_pine=true` 명시 동의 없으면 422 reject.
    """

    used_functions: tuple[str, ...]
    used_attributes: tuple[str, ...]
    unsupported_functions: tuple[str, ...]  # 기존, backward-compat
    unsupported_attributes: tuple[str, ...]  # 기존, backward-compat
    unsupported_calls: tuple[UnsupportedCall, ...] = ()  # Sprint 29 Slice B 신규
    # Sprint 29 Slice A: heikinashi Trust Layer 위반 transparency
    dogfood_only_warning: str | None = None
    # Sprint 29 codex G2 P0 fix: Trust Layer 의도적 위반 함수/속성 (degraded execution).
    # supported 로 graceful 실행되지만 사용자 명시 동의 없이는 backtest 차단.
    degraded_calls: tuple[str, ...] = ()

    @property
    def is_runnable(self) -> bool:
        return not self.unsupported_functions and not self.unsupported_attributes

    @property
    def has_degraded(self) -> bool:
        """Trust Layer 의도적 위반 함수 사용 여부. backtest submit 시 명시 동의 검사."""
        return bool(self.degraded_calls)

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
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*=>", clean):
        user_defs.add(m.group(1))

    skip_keywords = {
        "if",
        "for",
        "while",
        "and",
        "or",
        "not",
        "in",
        "true",
        "false",
        "switch",
    }

    # functions — namespace prefix 가 알려진 Pine namespace 일 때만 검사
    # (사용자 변수 method 호출 예: `dntl.set_xy1(...)` 는 false positive 방지로 skip)
    used_funcs_all = sorted(
        {
            m.group(1)
            for m in _CALL_RE.finditer(clean)
            if m.group(1).lower() not in skip_keywords and m.group(1) not in user_defs
        }
    )
    used_funcs = [f for f in used_funcs_all if "." not in f or _is_pine_namespace(f)]
    # known-unsupported를 먼저 분리: SUPPORTED_FUNCTIONS에서 제거 후 명시적 unsupported 처리
    # (interpreter는 NOP으로 graceful degrade하지만 coverage analyzer는 명시적 노출)
    unsupp_funcs_raw = [f for f in used_funcs if f not in SUPPORTED_FUNCTIONS]
    # known-unsupported는 used_funcs에 감지되면 항상 unsupported로 분류
    known_found = [f for f in used_funcs if f in _KNOWN_UNSUPPORTED_FUNCTIONS]
    # 중복 없이 합산 (known_found는 이미 SUPPORTED_FUNCTIONS에서 제외됐으므로 union)
    unsupp_funcs_set = set(unsupp_funcs_raw) | set(known_found)
    unsupp_funcs = tuple(sorted(unsupp_funcs_set))

    # attributes (call site 제외 — `(` 직후 위치는 함수로 이미 잡힘)
    used_attrs_set: set[str] = set()
    for m in _DOTTED_RE.finditer(clean):
        chain = m.group(1)
        # 호출 형태 ((직후 `(`) 인 경우 함수로 이미 잡힘 → skip
        end_idx = m.end()
        # check next non-space char is `(`
        rest = clean[end_idx : end_idx + 4].lstrip()
        if rest.startswith("("):
            continue
        used_attrs_set.add(chain)

    used_attrs = sorted(used_attrs_set)
    # 알려진 Pine namespace prefix 만 검사 — 사용자 변수 attribute (예: `dntl.x1`) skip
    unsupp_attrs = tuple(
        a for a in used_attrs if _is_pine_namespace(a) and not is_supported_attribute(a)
    )

    # Sprint 29 Slice A: dogfood_only_warning — heikinashi Trust Layer 위반 감지
    warning: str | None = None
    if "heikinashi" in used_funcs_all:
        warning = (
            "heikinashi() 사용 — Trust Layer 위반 (Sprint 29 ADR). "
            "Heikin-Ashi 캔들은 일반 OHLC 와 다른 변환이라 backtest 결과가 "
            "Pine 원본과 다를 수 있음 (거짓 양성 risk). dogfood-only 사용 권장. "
            "참고: docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md"
        )

    # Sprint 29 Slice B: unsupported_calls — line 번호 + workaround + category 포함
    # P1 fix (codex G0): comment/string noise 차단 위해 clean (stripped) source 에서 line 검색.
    # _strip_noise 는 // 주석 + 문자열 리터럴을 제거하므로 첫 등장 line 이 실제 코드 위치.
    unsupported_calls_list: list[UnsupportedCall] = []
    for fn in unsupp_funcs:
        line_no = _find_line(clean, fn) or 0
        unsupported_calls_list.append(
            UnsupportedCall(
                name=fn,
                line=line_no,
                col=None,
                workaround=_UNSUPPORTED_WORKAROUNDS.get(fn),
                category=_categorize(fn),
            )
        )
    for attr in unsupp_attrs:
        line_no = _find_line(clean, attr) or 0
        unsupported_calls_list.append(
            UnsupportedCall(
                name=attr,
                line=line_no,
                col=None,
                workaround=_UNSUPPORTED_WORKAROUNDS.get(attr),
                category=_categorize(attr),
            )
        )

    # Sprint 29 codex G2 P0 fix: degraded_calls — Trust Layer 의도적 위반 함수/속성.
    # supported 로 분류되어 is_runnable=True 이지만 production backtest 차단 의무.
    degraded_set: set[str] = set()
    for fn in used_funcs_all:
        if fn in _DEGRADED_FUNCTIONS:
            degraded_set.add(fn)
    for attr in used_attrs:
        if attr in _DEGRADED_ATTRIBUTES:
            degraded_set.add(attr)
    degraded_calls = tuple(sorted(degraded_set))

    return CoverageReport(
        used_functions=tuple(used_funcs),
        used_attributes=tuple(used_attrs),
        unsupported_functions=unsupp_funcs,
        unsupported_attributes=unsupp_attrs,
        unsupported_calls=tuple(unsupported_calls_list),
        dogfood_only_warning=warning,
        degraded_calls=degraded_calls,
    )
