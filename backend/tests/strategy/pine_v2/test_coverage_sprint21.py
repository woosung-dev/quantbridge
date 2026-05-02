"""Sprint 21 Phase A.2 — coverage.py supported list expansion.

codex G.0 round 1+2 P1 #2 / #3 / free-3 반영:
- v4 no-namespace alias 8개 (abs/max/min/pivothigh/pivotlow/barssince/valuewhen/timestamp)
- explicit constant set 3종 (currency / strategy / timeframe — prefix 금지, false-pass 차단)
- study NOP (declaration alias)
- heikinashi / security 는 _KNOWN_UNSUPPORTED 유지 (Trust Layer)

목표: RsiD strategy hard 의 8 unsupported (abs/barssince/currency.USD/max/pivothigh/
pivotlow/strategy.fixed/valuewhen) 가 모두 supported 로 분류되어 통과.
"""

from __future__ import annotations

import pytest

from src.strategy.pine_v2.coverage import analyze_coverage

# --------------------------------------------------------------------
# A.2.1 v4 no-namespace alias (8개) — 사용자가 alias 정의 안 했을 때 supported
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "func_call,desc",
    [
        ("abs(-5)", "math.abs alias"),
        ("max(2, 3)", "math.max alias"),
        ("min(2, 3)", "math.min alias"),
        ("pivothigh(close, 5, 5)", "ta.pivothigh alias"),
        ("pivotlow(close, 5, 5)", "ta.pivotlow alias"),
        ("barssince(close > open)", "ta.barssince alias"),
        ("valuewhen(close > open, close, 0)", "ta.valuewhen alias"),
        ("timestamp(2024, 1, 1, 0, 0)", "v4/v5 builtin"),
    ],
)
def test_v4_alias_supported(func_call: str, desc: str) -> None:
    """v4 no-namespace alias 가 coverage.py 의 supported set 에 포함."""
    src = f"""
//@version=5
strategy("V4Alias", overlay=true)
result = {func_call}
"""
    r = analyze_coverage(src)
    assert r.is_runnable, (
        f"{desc} ({func_call}) should be supported. "
        f"unsupported_functions={r.unsupported_functions}, "
        f"unsupported_attributes={r.unsupported_attributes}"
    )


# --------------------------------------------------------------------
# A.2.2 explicit constant sets — prefix 미허용 + false-pass 차단
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "constant",
    [
        "currency.USD",
        "currency.EUR",
        "currency.JPY",
        "currency.NONE",
    ],
)
def test_currency_constants_supported(constant: str) -> None:
    """_CURRENCY_CONSTANTS 의 명시 항목은 supported (RsiD currency.USD 통과 의무)."""
    src = f"""
//@version=5
strategy("CurrencyTest", overlay=true, currency={constant})
"""
    r = analyze_coverage(src)
    assert constant not in r.unsupported_attributes, (
        f"{constant} should be supported (explicit constant set). "
        f"unsupported_attributes={r.unsupported_attributes}"
    )


def test_currency_unknown_constant_rejected() -> None:
    """currency.* prefix 가 _ENUM_PREFIXES 에 추가되지 않아야 false-pass 차단."""
    src = """
//@version=5
strategy("UnknownCurrency", overlay=true, currency=currency.USDXYZ123)
"""
    r = analyze_coverage(src)
    assert "currency.USDXYZ123" in r.unsupported_attributes, (
        "Unknown currency constant should be unsupported "
        "(no prefix-based whitelist). codex G.0 P1 #3."
    )


@pytest.mark.parametrize(
    "constant",
    [
        "strategy.fixed",
        "strategy.cash",
        "strategy.percent_of_equity",
    ],
)
def test_strategy_constants_supported(constant: str) -> None:
    """_STRATEGY_CONSTANTS 의 명시 항목은 supported (RsiD strategy.fixed 통과 의무)."""
    src = f"""
//@version=5
strategy("StrategyConstants", overlay=true, default_qty_type={constant})
"""
    r = analyze_coverage(src)
    assert constant not in r.unsupported_attributes, (
        f"{constant} should be supported. "
        f"unsupported_attributes={r.unsupported_attributes}"
    )


def test_strategy_unknown_constant_rejected() -> None:
    """strategy.* prefix 가 _ENUM_PREFIXES 에 추가되지 않아야 false-pass 차단."""
    src = """
//@version=5
strategy("UnknownStrategy", overlay=true, default_qty_type=strategy.foobar_qty_type)
"""
    r = analyze_coverage(src)
    assert "strategy.foobar_qty_type" in r.unsupported_attributes, (
        "Unknown strategy constant should be unsupported. codex G.0 P1 #3."
    )


@pytest.mark.parametrize(
    "constant",
    [
        "timeframe.period",
        "timeframe.multiplier",
        "timeframe.isintraday",
    ],
)
def test_timeframe_constants_remain_unsupported(constant: str) -> None:
    """timeframe.* 는 unsupported 유지 (codex G.2 P1 #1 — runtime 미구현).

    Sprint 21 v2 plan 에선 `_TIMEFRAME_CONSTANTS` 추가했지만 interpreter._eval_attribute
    의 `timeframe.*` runtime 평가가 없어 preflight pass 후 runtime fail = silent corruption.
    Sprint 22+ 의 interpreter NOP 추가 또는 strict toggle 설계 후 supported 전환.
    """
    src = f"""
//@version=5
strategy("TimeframeConstants", overlay=true)
tf = {constant}
"""
    r = analyze_coverage(src)
    assert constant in r.unsupported_attributes, (
        f"{constant} should be unsupported (Sprint 21 G.2 fix — runtime 미구현). "
        f"unsupported_attributes={r.unsupported_attributes}"
    )


def test_timeframe_unknown_constant_rejected() -> None:
    """timeframe.* prefix 가 _ENUM_PREFIXES 에 추가되지 않아야 false-pass 차단."""
    src = """
//@version=5
strategy("UnknownTimeframe", overlay=true)
tf = timeframe.barbaz_unknown
"""
    r = analyze_coverage(src)
    assert "timeframe.barbaz_unknown" in r.unsupported_attributes


# --------------------------------------------------------------------
# A.2.3 study NOP (v2/v3 declaration alias)
# --------------------------------------------------------------------


def test_study_declaration_alias_nop() -> None:
    """study() 는 v2/v3 의 indicator alias. NOP 처리, supported."""
    src = """
//@version=2
study("StudyAlias", overlay=true)
plot(close)
"""
    r = analyze_coverage(src)
    assert "study" not in r.unsupported_functions, (
        f"study() should be NOP-supported (declaration alias). "
        f"unsupported_functions={r.unsupported_functions}"
    )


# --------------------------------------------------------------------
# A.2.4 Trust Layer 유지 — heikinashi / security 는 unsupported (NOT NOP)
# --------------------------------------------------------------------


def test_heikinashi_remains_unsupported() -> None:
    """heikinashi 는 silent corruption risk 로 unsupported 유지 (Trust Layer P1 #2)."""
    src = """
//@version=5
indicator("HeikinashiTest", overlay=true)
ha = heikinashi(close)
"""
    r = analyze_coverage(src)
    # heikinashi 가 함수 또는 attribute 로 unsupported 분류
    is_unsupported = (
        "heikinashi" in r.unsupported_functions
        or "heikinashi" in r.unsupported_attributes
        or any("heikinashi" in u for u in r.all_unsupported)
    )
    assert is_unsupported, (
        f"heikinashi should remain unsupported (ADR-013 §4 Trust Layer). "
        f"unsupported_functions={r.unsupported_functions}, "
        f"unsupported_attributes={r.unsupported_attributes}"
    )


def test_security_no_namespace_remains_unsupported() -> None:
    """security() (no-namespace, v4 form) 는 unsupported 유지 (Trust Layer P1 #2)."""
    src = """
//@version=4
strategy("SecurityV4")
htf_close = security("BINANCE:BTCUSDT", "60", close)
"""
    r = analyze_coverage(src)
    is_unsupported = (
        "security" in r.unsupported_functions
        or any(u == "security" for u in r.all_unsupported)
    )
    assert is_unsupported, (
        f"security (no-namespace) should remain unsupported. "
        f"unsupported_functions={r.unsupported_functions}"
    )


def test_request_security_remains_unsupported() -> None:
    """request.security 도 명시 unsupported 유지 (Trust Layer 기존 정책)."""
    src = """
//@version=5
indicator("RequestSecurityTest", overlay=true)
htf_close = request.security("BINANCE:BTCUSDT", "60", close)
"""
    r = analyze_coverage(src)
    assert "request.security" in r.unsupported_functions


# --------------------------------------------------------------------
# A.2.5 통합: RsiD 의 8 unsupported 가 모두 supported 로 분류
# --------------------------------------------------------------------


def test_rsid_eight_unsupported_all_supported_after_fix() -> None:
    """RsiD strategy hard 의 8 unsupported (Day 0 측정) 가 모두 supported.

    abs / barssince / currency.USD / max / pivothigh / pivotlow / strategy.fixed / valuewhen
    """
    src = """
//@version=4
strategy("RsidLikeMinimal", overlay=true, default_qty_type=strategy.fixed, currency=currency.USD)

// v4 no-namespace 8개
a = abs(-5)
mx = max(close, open)
mn = min(close, open)
ph = pivothigh(high, 5, 5)
pl = pivotlow(low, 5, 5)
bs = barssince(close > open)
vw = valuewhen(close > open, close, 0)

if close > open
    strategy.entry("L", strategy.long, qty=1)
"""
    r = analyze_coverage(src)
    assert r.is_runnable, (
        f"RsiD-style minimal should be runnable after Sprint 21 expansion. "
        f"unsupported_functions={r.unsupported_functions}, "
        f"unsupported_attributes={r.unsupported_attributes}"
    )
