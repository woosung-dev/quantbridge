"""닫힌 전략 명세. 명세는 실행되지 않고 언어별 소스로만 컴파일한다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

IndicatorKind = Literal[
    "ema",
    "sma",
    "rsi",
    "atr",
    "highest",
    "lowest",
    "stdev",
    "obv",
    "donchian",
    "keltner",
    "atr_breakout",
    "macd",
    "bollinger",
    "roc",
    "stochastic",
    "cci",
    "williams_r",
    "vwap",
    "anchored_vwap",
    "cmf",
    "mfi",
    "aroon",
    "regression",
    "heikin_ashi",
    "chandelier",
    "supertrend",
    "dmi",
    "ichimoku",
    "stoch_rsi",
    "tsi",
    "confirmed_divergence",
    "mtf_ema",
    "squeeze",
]


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class IndicatorSpec(ClosedModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    kind: IndicatorKind
    source: Literal["open", "high", "low", "close", "volume", "hlc3"] = "close"
    length: int = Field(default=20, ge=1, le=1000)
    slow: int = Field(default=26, ge=1, le=1000)
    signal: int = Field(default=9, ge=1, le=1000)
    multiplier: float = Field(default=2, gt=0, le=100, allow_inf_nan=False)
    anchor_ms: int | None = Field(default=None, ge=0)


class ValueRef(ClosedModel):
    series: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,39}$")
    output: Literal["value", "upper", "lower", "signal", "slope", "up", "down", "open"] = "value"
    offset: int = Field(default=0, ge=0, le=1000)
    constant: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def exactly_one_value(self) -> ValueRef:
        if (self.series is None) == (self.constant is None):
            raise ValueError("series와 constant 중 정확히 하나가 필요합니다")
        if self.constant is not None and (self.offset or self.output != "value"):
            raise ValueError("상수에 offset/output을 적용할 수 없습니다")
        return self


class Condition(ClosedModel):
    op: Literal[
        "gt", "gte", "lt", "lte", "cross_up", "cross_down", "all", "any", "not", "true", "false"
    ]
    left: ValueRef | None = None
    right: ValueRef | None = None
    children: tuple[Condition, ...] = ()

    @model_validator(mode="after")
    def shape(self) -> Condition:
        if self.op in ("gt", "gte", "lt", "lte", "cross_up", "cross_down"):
            if self.left is None or self.right is None or self.children:
                raise ValueError("비교 조건에는 left/right만 필요합니다")
        elif self.op in ("all", "any", "not"):
            if self.left or self.right or not self.children:
                raise ValueError("논리 조건에는 children만 필요합니다")
            if self.op == "not" and len(self.children) != 1:
                raise ValueError("not에는 자식 하나만 필요합니다")
        elif self.left or self.right or self.children:
            raise ValueError("상수 조건에는 피연산자가 없습니다")
        return self


_OUTPUTS: dict[str, set[str]] = {
    "macd": {"value", "signal"},
    "obv": {"value", "signal"},
    "donchian": {"value", "upper", "lower"},
    "keltner": {"value", "upper", "lower"},
    "atr_breakout": {"upper", "lower"},
    "bollinger": {"value", "upper", "lower"},
    "stochastic": {"value", "signal"},
    "aroon": {"up", "down"},
    "regression": {"value", "upper", "lower", "slope"},
    "heikin_ashi": {"value", "open"},
    "chandelier": {"upper", "lower"},
    "dmi": {"value", "up", "down"},
    "ichimoku": {"value", "signal", "upper", "lower"},
    "stoch_rsi": {"value", "signal"},
    "tsi": {"value", "signal"},
}
PRICES = frozenset({"open", "high", "low", "close", "volume", "hlc3"})


class StrategySpec(ClosedModel):
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=120)
    indicators: tuple[IndicatorSpec, ...] = Field(default=(), max_length=40)
    long_entry: Condition
    short_entry: Condition
    long_invalidation: Condition = Condition(op="false")
    short_invalidation: Condition = Condition(op="false")
    warmup_bars: int = Field(default=200, ge=1, le=10000)
    risk_policy: Literal["swing_two_bar_v1"] = "swing_two_bar_v1"
    fill_timing: Literal["next_bar_open"] = "next_bar_open"

    @model_validator(mode="after")
    def references(self) -> StrategySpec:
        names = {item.id: item for item in self.indicators}
        if len(names) != len(self.indicators) or PRICES.intersection(names):
            raise ValueError("지표 ID가 중복되거나 가격 이름과 충돌합니다")
        count = 0

        def visit(node: Condition, depth: int) -> None:
            nonlocal count
            count += 1
            if depth > 12 or count > 200:
                raise ValueError("조건 크기 또는 깊이 한도를 초과했습니다")
            for ref in (node.left, node.right):
                if ref is None or ref.series is None:
                    continue
                if ref.series in PRICES:
                    if ref.output != "value":
                        raise ValueError("가격에는 value 출력만 있습니다")
                elif ref.series not in names:
                    raise ValueError(f"존재하지 않는 지표: {ref.series}")
                elif ref.output not in _OUTPUTS.get(names[ref.series].kind, {"value"}):
                    raise ValueError(f"지표 출력이 없습니다: {ref.series}.{ref.output}")
            for child in node.children:
                visit(child, depth + 1)

        for condition in (
            self.long_entry,
            self.short_entry,
            self.long_invalidation,
            self.short_invalidation,
        ):
            visit(condition, 0)
        for item in self.indicators:
            if item.kind == "anchored_vwap" and item.anchor_ms is None:
                raise ValueError("anchored_vwap에는 사전에 고정한 anchor_ms가 필요합니다")
        return self


class UnsupportedStrategySpec(ValueError):
    """현재 compiler가 의미를 보존할 수 없는 명세를 명시적으로 거부한다."""
