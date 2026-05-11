# StrictDecimalInput Request-boundary validator 단위 검증 (Sprint 53 BL-226).

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from src.common.strict_decimal_input import StrictDecimalInput


class _M(BaseModel):
    """Pydantic test wrapper."""

    v: StrictDecimalInput


# === String input (FE isFiniteDecimalString mirror) ===


def test_accepts_integer_string() -> None:
    m = _M.model_validate({"v": "10"})
    assert m.v == Decimal("10")


def test_accepts_fractional_string() -> None:
    m = _M.model_validate({"v": "0.5"})
    assert m.v == Decimal("0.5")


def test_accepts_negative_string() -> None:
    m = _M.model_validate({"v": "-1.25"})
    assert m.v == Decimal("-1.25")


def test_rejects_scientific_notation_str() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"v": "1e-3"})


def test_rejects_leading_dot_str() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"v": ".5"})


def test_rejects_plus_prefix_str() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"v": "+1"})


def test_rejects_nan_str() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"v": "NaN"})


def test_rejects_infinity_str() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"v": "Infinity"})


def test_rejects_empty_str() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"v": ""})


def test_rejects_whitespace_str() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"v": " "})


# === Decimal instance input (codex P1#9 canonicalization) ===


def test_accepts_canonical_decimal_instance() -> None:
    """canonical Decimal 인스턴스 통과 (finite + no exponent)."""
    m = _M.model_validate({"v": Decimal("1.25")})
    assert m.v == Decimal("1.25")


def test_accepts_integer_decimal_instance() -> None:
    """정수 Decimal 인스턴스 통과."""
    m = _M.model_validate({"v": Decimal("10")})
    assert m.v == Decimal("10")


def test_rejects_nan_decimal_instance() -> None:
    """Decimal('NaN') = non-finite → reject (codex P1#9)."""
    with pytest.raises(ValidationError):
        _M.model_validate({"v": Decimal("NaN")})


def test_rejects_infinity_decimal_instance() -> None:
    """Decimal('Infinity') = non-finite → reject (codex P1#9)."""
    with pytest.raises(ValidationError):
        _M.model_validate({"v": Decimal("Infinity")})


def test_rejects_large_positive_exponent_decimal_instance() -> None:
    """Decimal('1E+5') = exponent repr 유지 → reject (codex P1#9).

    Python `Decimal('1E-3')` 는 자동 정규화돼서 `str = '0.001'` canonical form.
    반면 `Decimal('1E+5')` 는 `str = '1E+5'` exponent 유지 — FE regex 와 mismatch.
    canonicalization check 가 큰 양수 exponent 만 reject (`str(v)` regex fullmatch).
    """
    with pytest.raises(ValidationError):
        _M.model_validate({"v": Decimal("1E+5")})


def test_rejects_decimal_fraction_exponent_instance() -> None:
    """Decimal('1.5E+10') = exponent repr 유지 → reject (codex P1#9)."""
    with pytest.raises(ValidationError):
        _M.model_validate({"v": Decimal("1.5E+10")})


def test_accepts_auto_normalized_small_exponent_instance() -> None:
    """Decimal('1E-3') 는 Python 안 자동 정규화 ('0.001' canonical) — 통과.

    test_rejects_large_positive_exponent_decimal_instance 의 짝 — 작은 exponent
    는 canonical form 정규화 + 큰 양수 exponent 만 reject.
    """
    m = _M.model_validate({"v": Decimal("1E-3")})
    assert m.v == Decimal("0.001")


def test_rejects_int_input() -> None:
    """int 인스턴스 reject (Request-boundary 만 — 외부 input 은 string 전용).

    내부 코드가 Decimal(10) 으로 명시 인스턴스 생성 시 OK (test_accepts_integer_decimal_instance).
    """
    with pytest.raises(ValidationError):
        _M.model_validate({"v": 10})


def test_rejects_float_input() -> None:
    """float 인스턴스 reject — IEEE 754 precision 손실 회피."""
    with pytest.raises(ValidationError):
        _M.model_validate({"v": 0.5})


def test_rejects_huge_digit_string_overflow() -> None:
    """codex G.4 P1#1 — FE `Number.isFinite` parity.

    BE Decimal 은 `"9" * 400` 같은 큰 자릿수 표현 가능. FE 는 `Number(s)` 가
    `Infinity` 반환 후 isFinite reject. BE 도 동일 finite check 강제.
    """
    huge = "9" * 400
    with pytest.raises(ValidationError):
        _M.model_validate({"v": huge})
