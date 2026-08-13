"""B-4: request.security 및 request.* 함수들 coverage 검증.

Sprint Y1 Trust Layer 철학:
- coverage analyzer는 pre-flight에서 미지원 함수를 명시적으로 보고해야 함
- request.security는 interpreter가 NOP으로 처리하지만 사용자에게 "미지원" 명시 필요

Sprint 29 Slice A 변경:
- request.security 는 graceful (단일 timeframe 가정) → SUPPORTED 로 이전
- 이전 test 중 _KNOWN_UNSUPPORTED_FUNCTIONS 에 포함 검증하던 항목은 Sprint 29 정책 반영으로 갱신
"""

from __future__ import annotations

from src.strategy.pine_v2.coverage import (
    _KNOWN_UNSUPPORTED_FUNCTIONS,
    SUPPORTED_FUNCTIONS,
    analyze_coverage,
)

# -------- _KNOWN_UNSUPPORTED_FUNCTIONS 상수 검증 -----------------------


def test_known_unsupported_no_longer_contains_request_security() -> None:
    """Sprint 29 Slice A: request.security 는 graceful → _KNOWN_UNSUPPORTED 에서 제거됨."""
    assert "request.security" not in _KNOWN_UNSUPPORTED_FUNCTIONS
    # SUPPORTED_FUNCTIONS 에 포함되어야 함
    assert "request.security" in SUPPORTED_FUNCTIONS


def test_known_unsupported_contains_request_family() -> None:
    """request.* 계열 중 미처리 항목은 여전히 KNOWN_UNSUPPORTED."""
    expected = {
        # "request.security",  # Sprint 29 Slice A: graceful → SUPPORTED
        "request.security_lower_tf",
        "request.dividends",
        "request.earnings",
        "request.financial",
    }
    for fn in expected:
        assert fn in _KNOWN_UNSUPPORTED_FUNCTIONS, f"{fn} not in _KNOWN_UNSUPPORTED_FUNCTIONS"


# -------- analyze_coverage 동작 검증 -----------------------------------


def test_request_security_now_supported() -> None:
    """Sprint 29 Slice A: request.security → supported (graceful single-timeframe 가정)."""
    source = """//@version=5
indicator("test")
x = request.security("BTCUSD", "D", close)
"""
    report = analyze_coverage(source)
    assert "request.security" not in report.unsupported_functions


def test_request_security_makes_runnable() -> None:
    """Sprint 29 Slice A: request.security 단독 사용 시 is_runnable=True."""
    source = """//@version=5
indicator("test")
btc_close = request.security("BINANCE:BTCUSDT", "D", close)
"""
    report = analyze_coverage(source)
    assert report.is_runnable


def test_request_security_in_used_functions() -> None:
    """request.security가 used_functions에도 포함됨."""
    source = '//@version=5\nindicator("t")\nx = request.security("A", "D", close)\n'
    report = analyze_coverage(source)
    assert "request.security" in report.used_functions


def test_ticker_new_in_unsupported_functions() -> None:
    """ticker.new 포함 스크립트 → unsupported_functions에 포함."""
    source = """//@version=5
indicator("test")
t = ticker.new("BINANCE", "BTCUSDT")
"""
    report = analyze_coverage(source)
    assert "ticker.new" in report.unsupported_functions


def test_normal_script_no_false_positive() -> None:
    """request.security 없는 스크립트는 unsupported_functions에 포함 안 됨."""
    source = """//@version=5
indicator("test")
ma = ta.sma(close, 14)
"""
    report = analyze_coverage(source)
    assert "request.security" not in report.unsupported_functions


def test_request_security_in_comment_not_detected() -> None:
    """주석 내 request.security는 감지 안 됨."""
    source = """//@version=5
indicator("test")
// x = request.security("A", "D", close)  // 이건 주석
ma = ta.ema(close, 9)
"""
    report = analyze_coverage(source)
    assert "request.security" not in report.unsupported_functions
    assert report.is_runnable


def test_all_unsupported_excludes_request_security() -> None:
    """Sprint 29 Slice A: request.security → supported, all_unsupported 에서 제외됨."""
    source = '//@version=5\nindicator("t")\nx = request.security("A", "D", close)\n'
    report = analyze_coverage(source)
    assert "request.security" not in report.all_unsupported
