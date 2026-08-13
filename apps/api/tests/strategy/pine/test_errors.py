"""PineError 예외 계층 테스트."""
from __future__ import annotations

from src.strategy.pine.errors import (
    PineError,
    PineLexError,
    PineParseError,
    PineRuntimeError,
    PineUnsupportedError,
)


def test_pine_error_base() -> None:
    """PineError는 Exception의 서브클래스여야 한다."""
    err = PineError("base error")
    assert isinstance(err, Exception)
    assert str(err) == "base error"


def test_pine_error_line_column() -> None:
    """PineError는 line과 column 속성을 가진다."""
    err = PineError("msg", line=3, column=7)
    assert err.line == 3
    assert err.column == 7


def test_pine_error_defaults_none() -> None:
    """line과 column의 기본값은 None이어야 한다."""
    err = PineError("msg")
    assert err.line is None
    assert err.column is None


def test_subclass_hierarchy() -> None:
    """PineLexError, PineParseError, PineRuntimeError는 PineError 서브클래스여야 한다."""
    assert issubclass(PineLexError, PineError)
    assert issubclass(PineParseError, PineError)
    assert issubclass(PineRuntimeError, PineError)


def test_unsupported_error_is_subclass() -> None:
    """PineUnsupportedError는 PineError 서브클래스여야 한다."""
    assert issubclass(PineUnsupportedError, PineError)


def test_unsupported_error_fields() -> None:
    """PineUnsupportedError는 feature와 category 필드를 가진다."""
    err = PineUnsupportedError(
        "request() is not supported",
        feature="request",
        category="function",
        line=10,
    )
    assert err.feature == "request"
    assert err.category == "function"
    assert err.line == 10
    assert err.column is None


def test_unsupported_error_category_values() -> None:
    """PineUnsupportedError.category는 허용된 리터럴 값만 받는다."""
    for cat in ("function", "syntax", "type", "v4_migration"):
        err = PineUnsupportedError("test", feature="x", category=cat)  # type: ignore[arg-type]
        assert err.category == cat
