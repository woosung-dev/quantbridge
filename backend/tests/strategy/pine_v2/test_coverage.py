"""Pre-flight coverage analyzer — Sprint Y1 (B+D).

Trust layer 철학: backtest 실행 *전* 에 미지원 Pine built-in 식별 → 사용자 명시.
Whack-a-mole 패턴 종식 (실행 → 다음 미지원 노출 → 추가 → 반복).
"""
from __future__ import annotations

from src.strategy.pine_v2.coverage import analyze_coverage


def test_supported_strategy_is_runnable() -> None:
    """ta.sma + strategy.entry 만 사용한 단순 전략 → 실행 가능."""
    src = """
//@version=5
strategy("S1", overlay=true)
ma = ta.sma(close, 20)
if close > ma
    strategy.entry("L", strategy.long)
"""
    r = analyze_coverage(src)
    assert r.is_runnable
    assert not r.unsupported_functions
    assert not r.unsupported_attributes


def test_unsupported_function_blocks() -> None:
    """ta.supertrend 같은 미지원 함수 호출 시 unsupported 로 표시."""
    src = """
//@version=5
strategy("S2")
[supertrend, dir] = ta.supertrend(3, 10)
"""
    r = analyze_coverage(src)
    assert not r.is_runnable
    assert "ta.supertrend" in r.unsupported_functions


def test_unsupported_attribute_blocks() -> None:
    """ta.tr 외의 attribute access 미지원 식별 (예: ta.tr_ohlc — 가공 케이스)."""
    src = """
//@version=5
strategy("S3")
x = ta.tr_unknown
"""
    r = analyze_coverage(src)
    assert not r.is_runnable
    assert "ta.tr_unknown" in r.unsupported_attributes


def test_ta_tr_is_supported_attribute() -> None:
    """ta.tr 은 attribute access 로 지원 (Sprint X1+X3 follow-up #3 hotfix)."""
    src = """
//@version=5
strategy("S4")
tr = ta.tr
"""
    r = analyze_coverage(src)
    assert r.is_runnable
    assert "ta.tr" not in r.unsupported_attributes


def test_user_defined_function_not_flagged() -> None:
    """사용자 정의 함수 호출은 unsupported 로 잡지 않음."""
    src = """
//@version=5
strategy("S5")
myFunc(x) => x * 2
result = myFunc(close)
"""
    r = analyze_coverage(src)
    # myFunc 는 user_defs 에 있어 unsupported_functions 에서 제외
    assert "myFunc" not in r.unsupported_functions


def test_i3_drfx_detects_unsupported() -> None:
    """i3_drfx 는 fixnan / ta.supertrend 등 미지원 다수 → 즉시 차단."""
    from pathlib import Path

    src = (Path(__file__).parent.parent.parent
           / "fixtures" / "pine_corpus_v2" / "i3_drfx.pine").read_text()
    r = analyze_coverage(src)
    assert not r.is_runnable
    # fixnan 또는 다른 미지원 함수가 잡혀야 함
    assert len(r.all_unsupported) > 0


def test_i2_luxalgo_runnable_after_x1x3_hotfixes() -> None:
    """i2_luxalgo 는 X1+X3 sprint 이후 모든 함수/속성 지원 → runnable."""
    from pathlib import Path

    src = (Path(__file__).parent.parent.parent
           / "fixtures" / "pine_corpus_v2" / "i2_luxalgo.pine").read_text()
    r = analyze_coverage(src)
    # 만약 미지원 발견 시, follow-up 으로 추적 (테스트는 알림용)
    if not r.is_runnable:
        # 실패 메시지에 정확한 미지원 항목 표시 — 다음 hotfix 의 정확한 scope
        raise AssertionError(
            f"i2_luxalgo unsupported items detected: {r.all_unsupported}. "
            f"Either add to coverage.SUPPORTED_* or document as deferred."
        )


def test_strict_string_literal_no_false_positive() -> None:
    """문자열 리터럴 안의 dot chain 은 unsupported 로 오탐하지 않음."""
    src = '''
//@version=5
strategy("S6")
msg = "ta.supertrend will be alerted here"
plot(close)
'''
    r = analyze_coverage(src)
    assert "ta.supertrend" not in r.unsupported_functions
    assert "ta.supertrend" not in r.unsupported_attributes
