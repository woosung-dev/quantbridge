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
    "constant,expected_supported",
    [
        ("timeframe.period", True),   # Sprint 29 Slice A: interpreter._eval_attribute 구현 완료
        ("timeframe.multiplier", False),  # 미처리 — unsupported 유지
        ("timeframe.isintraday", False),  # 미처리 — unsupported 유지
    ],
)
def test_timeframe_constants_remain_unsupported(constant: str, expected_supported: bool) -> None:
    """timeframe.* 상수 지원 현황 (Sprint 21 G.2 + Sprint 29 Slice A 갱신).

    Sprint 21: runtime 미구현으로 전체 unsupported.
    Sprint 29 Slice A: timeframe.period 는 interpreter._eval_attribute 구현 완료 → SUPPORTED.
    나머지 timeframe.* 는 여전히 미구현 → unsupported 유지.
    """
    src = f"""
//@version=5
strategy("TimeframeConstants", overlay=true)
tf = {constant}
"""
    r = analyze_coverage(src)
    if expected_supported:
        assert constant not in r.unsupported_attributes, (
            f"{constant} should be supported (Sprint 29 Slice A). "
            f"unsupported_attributes={r.unsupported_attributes}"
        )
    else:
        assert constant in r.unsupported_attributes, (
            f"{constant} should be unsupported (runtime 미구현). "
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
# A.2.4 Trust Layer 갱신 — Sprint 29 Slice A (a) heikinashi + security 처리
# --------------------------------------------------------------------


def test_heikinashi_supported_with_dogfood_warning() -> None:
    """Sprint 29 Slice A (a): heikinashi → SUPPORTED + dogfood_only_warning 채워짐.

    Trust Layer 위반 인정 + dogfood-only flag.
    참고: docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md
    """
    src = """
//@version=5
indicator("HeikinashiTest", overlay=true)
ha = heikinashi(close)
"""
    r = analyze_coverage(src)
    assert "heikinashi" not in r.unsupported_functions, (
        f"heikinashi should be supported (Sprint 29 Slice A dogfood flag). "
        f"unsupported_functions={r.unsupported_functions}"
    )
    assert r.dogfood_only_warning is not None, (
        "heikinashi 사용 시 dogfood_only_warning 채워야 함"
    )


def test_security_no_namespace_now_supported() -> None:
    """Sprint 29 Slice A: security() (no-namespace, v4) → SUPPORTED (graceful)."""
    src = """
//@version=4
strategy("SecurityV4")
htf_close = security("BINANCE:BTCUSDT", "60", close)
"""
    r = analyze_coverage(src)
    assert "security" not in r.unsupported_functions, (
        f"security (no-namespace) should be supported (Sprint 29 Slice A). "
        f"unsupported_functions={r.unsupported_functions}"
    )


def test_request_security_now_supported() -> None:
    """Sprint 29 Slice A: request.security → SUPPORTED (graceful single-timeframe)."""
    src = """
//@version=5
indicator("RequestSecurityTest", overlay=true)
htf_close = request.security("BINANCE:BTCUSDT", "60", close)
"""
    r = analyze_coverage(src)
    assert "request.security" not in r.unsupported_functions


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
