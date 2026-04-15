"""Lexer for Pine Script v5 → Python AST.

This module implements lexical analysis (tokenization) for Pine Script.
TokenType and Token are defined here; the tokenizer itself grows across T8/T9/T10.

참고:
  - T8: TokenType + Token 스캐폴딩
  - T9: 핵심 토크나이저 (숫자, 문자열, 식별자, 연산자)
  - T10: 주석 처리 + INDENT/DEDENT 계산
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Token types for Pine Script lexical analysis.

    Values are auto-assigned to allow future extension without collision.
    """

    # 리터럴과 식별자
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()

    # 키워드
    KEYWORD = auto()

    # 연산자와 구분자
    OP = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    QUESTION = auto()
    ASSIGN = auto()
    WALRUS = auto()

    # 화이트스페이스와 구조
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()

    # 주석
    COMMENT = auto()

    # 파일 끝
    EOF = auto()


@dataclass(frozen=True)
class Token:
    """A lexical token with type, value, and position.

    Attributes:
      type: TokenType 열거값.
      value: 토큰 문자열 (예: "42", "close", "+").
      line: 1-based 라인 번호.
      column: 1-based 컬럼 번호.

    이 dataclass는 불변(frozen=True)이므로, 생성 후 필드 수정 불가능.
    """

    type: TokenType
    value: str
    line: int
    column: int
