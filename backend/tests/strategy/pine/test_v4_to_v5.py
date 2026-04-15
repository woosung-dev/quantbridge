"""v4 → v5 자동 변환기 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.errors import PineUnsupportedError
from src.strategy.pine.v4_to_v5 import detect_version, normalize

# ---------------------------------------------------------------------------
# detect_version
# ---------------------------------------------------------------------------


def test_detect_version_v4() -> None:
    """//@version=4 헤더가 있으면 'v4'를 반환한다."""
    src = "//@version=4\nstudy('test')\n"
    assert detect_version(src) == "v4"


def test_detect_version_v5() -> None:
    """//@version=5 헤더가 있으면 'v5'를 반환한다."""
    src = "//@version=5\nindicator('test')\n"
    assert detect_version(src) == "v5"


def test_detect_version_no_header_defaults_v5() -> None:
    """버전 헤더가 없으면 기본값 'v5'를 반환한다."""
    src = "sma(close, 14)\n"
    assert detect_version(src) == "v5"


# ---------------------------------------------------------------------------
# normalize — 버전 헤더
# ---------------------------------------------------------------------------


def test_normalize_updates_version_header() -> None:
    """//@version=4 를 //@version=5 로 교체한다."""
    src = "//@version=4\nstudy('test')\n"
    result = normalize(src)
    assert "//@version=5" in result
    assert "//@version=4" not in result


def test_normalize_v5_passthrough() -> None:
    """이미 v5 코드는 변경 없이 반환된다."""
    src = "//@version=5\nindicator('test')\nplot(ta.sma(close, 14))\n"
    assert normalize(src) == src


# ---------------------------------------------------------------------------
# normalize — ta.* 프리픽스 변환
# ---------------------------------------------------------------------------


def test_normalize_sma_prefix() -> None:
    """sma(close, 14) → ta.sma(close, 14)"""
    src = "//@version=4\nplot(sma(close, 14))\n"
    result = normalize(src)
    assert "ta.sma(close, 14)" in result


def test_normalize_no_double_prefix() -> None:
    """이미 ta.sma는 ta.ta.sma로 이중 변환되지 않는다."""
    src = "//@version=5\nplot(ta.sma(close, 14))\n"
    result = normalize(src)
    assert "ta.ta.sma" not in result
    assert "ta.sma(close, 14)" in result


def test_normalize_preserves_string_literal() -> None:
    """문자열 리터럴 내부의 함수명은 변환되지 않는다."""
    src = '//@version=4\nlabel = "sma is a function"\n'
    result = normalize(src)
    # 문자열 안의 sma는 그대로여야 한다
    assert '"sma is a function"' in result


def test_normalize_preserves_comment() -> None:
    """주석 내부의 함수명은 변환되지 않는다."""
    src = "//@version=4\n// sma is calculated here\nplot(sma(close, 20))\n"
    result = normalize(src)
    # 주석 안의 sma는 그대로
    assert "// sma is calculated here" in result
    # 코드의 sma는 변환
    assert "ta.sma(close, 20)" in result


# ---------------------------------------------------------------------------
# normalize — unsupported v4 기능
# ---------------------------------------------------------------------------


def test_normalize_raises_on_security() -> None:
    """security() 호출은 PineUnsupportedError(category='v4_migration')를 발생시킨다."""
    src = "//@version=4\nval = security(tickerid, '1D', close)\n"
    with pytest.raises(PineUnsupportedError) as exc_info:
        normalize(src)
    assert exc_info.value.category == "v4_migration"


def test_normalize_raises_on_tickerid() -> None:
    """tickerid 사용은 PineUnsupportedError(category='v4_migration')를 발생시킨다."""
    src = "//@version=4\nval = security(tickerid, '1D', close)\n"
    with pytest.raises(PineUnsupportedError) as exc_info:
        normalize(src)
    assert exc_info.value.category == "v4_migration"


# ---------------------------------------------------------------------------
# normalize — input() 시그니처 변환
# ---------------------------------------------------------------------------


def test_normalize_input_int() -> None:
    """input(14) → input.int(14) 로 변환된다."""
    src = "//@version=4\nlength = input(14)\n"
    result = normalize(src)
    assert "input.int(14)" in result


def test_normalize_input_float() -> None:
    """input(1.5) → input.float(1.5) 로 변환된다."""
    src = "//@version=4\nval = input(1.5)\n"
    result = normalize(src)
    assert "input.float(1.5)" in result


def test_normalize_input_bool() -> None:
    """input(true) → input.bool(true) 로 변환된다."""
    src = "//@version=4\nflag = input(true)\n"
    result = normalize(src)
    assert "input.bool(true)" in result


def test_normalize_input_string() -> None:
    """input('close') → input.source('close') 로 변환된다."""
    src = "//@version=4\nsrc = input('close')\n"
    result = normalize(src)
    assert "input.source('close')" in result
