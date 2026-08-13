"""Pine Script 파싱·실행 예외 계층."""
from __future__ import annotations

from typing import Literal


class PineError(Exception):
    """모든 Pine 관련 오류의 기반 클래스."""

    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.line = line
        self.column = column


class PineLexError(PineError):
    """토큰화(lexing) 단계에서 발생하는 오류."""


class PineParseError(PineError):
    """파싱(AST 생성) 단계에서 발생하는 오류."""


class PineUnsupportedError(PineError):
    """지원하지 않는 Pine Script 기능 사용 시 발생하는 오류."""

    def __init__(
        self,
        message: str,
        *,
        feature: str,
        category: Literal["function", "syntax", "type", "v4_migration"],
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message, line=line, column=column)
        self.feature = feature
        self.category = category


class PineRuntimeError(PineError):
    """인터프리터 실행 단계에서 발생하는 오류."""
