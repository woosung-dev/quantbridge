"""Slice A — UtBot 4 unsupported 처리 회귀 test."""

from src.strategy.pine_v2.coverage import analyze_coverage


def test_barcolor_is_supported():
    src = "barcolor(color.green)\n"
    rep = analyze_coverage(src)
    assert "barcolor" not in rep.unsupported_functions, (
        f"barcolor must be supported (visual NOP): {rep.unsupported_functions}"
    )


def test_timeframe_period_is_supported():
    src = "tf = timeframe.period\n"
    rep = analyze_coverage(src)
    assert "timeframe.period" not in rep.unsupported_attributes, (
        f"timeframe.period must be supported: {rep.unsupported_attributes}"
    )


def test_security_is_supported_graceful():
    """request.security 는 단일 timeframe 가정으로 graceful — Slice A.

    interpreter.py:707-715 에서 expression 인자 그대로 반환 (이미 일부 처리).
    """
    src = 'data = request.security("BTCUSDT", "1D", close)\n'
    rep = analyze_coverage(src)
    assert "request.security" not in rep.unsupported_functions, (
        f"request.security graceful (single-timeframe assumption): {rep.unsupported_functions}"
    )


def test_heikinashi_emits_dogfood_warning():
    """heikinashi 사용 시 supported 처리 + dogfood_only_warning 필드 채워짐."""
    src = "[ho, hh, hl, hc] = heikinashi()\n"
    rep = analyze_coverage(src)
    assert "heikinashi" not in rep.unsupported_functions, (
        "heikinashi (a) Trust Layer 위반 + dogfood flag — supported"
    )
    assert rep.dogfood_only_warning is not None, (
        "heikinashi 사용 시 dogfood_only_warning 필드 채워야 함"
    )
    assert (
        "heikinashi" in rep.dogfood_only_warning.lower()
        or "trust" in rep.dogfood_only_warning.lower()
    )
