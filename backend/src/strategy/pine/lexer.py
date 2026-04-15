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

from src.strategy.pine.errors import PineLexError


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


# Pine Script v5 키워드 집합
_KEYWORDS: frozenset[str] = frozenset(
    {
        "and",
        "or",
        "not",
        "if",
        "else",
        "for",
        "to",
        "by",
        "while",
        "true",
        "false",
        "var",
        "varip",
        "import",
        "export",
        "switch",
        "case",
    }
)

# 단일 문자 → TokenType 매핑 (연산자 포함)
_SINGLE_CHAR: dict[str, TokenType] = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "?": TokenType.QUESTION,
    "+": TokenType.OP,
    "-": TokenType.OP,
    "*": TokenType.OP,
    "/": TokenType.OP,
    "%": TokenType.OP,
}


def tokenize(source: str) -> list[Token]:
    """Pine Script 소스 문자열을 토큰 목록으로 변환한다.

    주석 처리와 INDENT/DEDENT는 T10에서 추가된다.
    이 함수는 숫자, 문자열, 식별자, 연산자, 구두점을 처리한다.

    Args:
        source: Pine Script v5 소스 코드.

    Returns:
        Token 목록 (마지막 요소는 항상 EOF).

    Raises:
        PineLexError: 인식할 수 없는 문자 또는 종료되지 않은 문자열.
    """
    tokens: list[Token] = []
    i = 0
    n = len(source)
    line = 1
    line_start = 0  # 현재 라인의 시작 인덱스

    while i < n:
        ch = source[i]

        # 개행 문자 처리
        if ch == "\n":
            col = i - line_start + 1
            tokens.append(Token(TokenType.NEWLINE, "\n", line, col))
            line += 1
            i += 1
            line_start = i
            continue

        # 공백/탭 스킵 (INDENT/DEDENT는 T10에서 처리)
        if ch in (" ", "\t", "\r"):
            i += 1
            continue

        col = i - line_start + 1  # 1-based column

        # 숫자 리터럴: 정수, 부동소수점, 과학적 표기법
        if ch.isdigit():
            j = i
            while j < n and source[j].isdigit():
                j += 1
            if j < n and source[j] == ".":
                j += 1
                while j < n and source[j].isdigit():
                    j += 1
            if j < n and source[j] in ("e", "E"):
                j += 1
                if j < n and source[j] in ("+", "-"):
                    j += 1
                while j < n and source[j].isdigit():
                    j += 1
            tokens.append(Token(TokenType.NUMBER, source[i:j], line, col))
            i = j
            continue

        # 문자열 리터럴: 작은따옴표 또는 큰따옴표
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            chars: list[str] = []
            while j < n and source[j] != quote:
                if source[j] == "\\":
                    # 이스케이프 처리
                    j += 1
                    if j < n:
                        chars.append(source[j])
                        j += 1
                    else:
                        raise PineLexError(
                            "종료되지 않은 이스케이프 시퀀스",
                            line=line,
                            column=col,
                        )
                else:
                    chars.append(source[j])
                    j += 1
            if j >= n:
                raise PineLexError(
                    f"종료되지 않은 문자열 리터럴 (시작: 라인 {line}, 컬럼 {col})",
                    line=line,
                    column=col,
                )
            tokens.append(Token(TokenType.STRING, "".join(chars), line, col))
            i = j + 1  # 닫는 따옴표 다음으로 이동
            continue

        # 식별자 / 키워드
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            tok_type = TokenType.KEYWORD if word in _KEYWORDS else TokenType.IDENT
            tokens.append(Token(tok_type, word, line, col))
            i = j
            continue

        # 다중 문자 연산자: <=, >=, ==, !=, :=
        if i + 1 < n:
            two = source[i : i + 2]
            if two in ("<=", ">=", "==", "!="):
                tokens.append(Token(TokenType.OP, two, line, col))
                i += 2
                continue
            if two == ":=":
                tokens.append(Token(TokenType.WALRUS, two, line, col))
                i += 2
                continue

        # 단일 문자 연산자 / 구두점
        if ch in _SINGLE_CHAR:
            tokens.append(Token(_SINGLE_CHAR[ch], ch, line, col))
            i += 1
            continue

        # `=` 단독: ASSIGN
        if ch == "=":
            tokens.append(Token(TokenType.ASSIGN, ch, line, col))
            i += 1
            continue

        # `:` 단독: COLON
        if ch == ":":
            tokens.append(Token(TokenType.COLON, ch, line, col))
            i += 1
            continue

        # `<` 또는 `>` 단독 (비교 연산자)
        if ch in ("<", ">"):
            tokens.append(Token(TokenType.OP, ch, line, col))
            i += 1
            continue

        # `!` 단독은 오류 (`!=`는 위에서 처리됨)
        if ch == "!":
            raise PineLexError(
                f"인식할 수 없는 문자 '!' (라인 {line}, 컬럼 {col}). '!=' 를 의미하셨나요?",
                line=line,
                column=col,
            )

        # 인식 불가 문자
        raise PineLexError(
            f"인식할 수 없는 문자 {ch!r} (라인 {line}, 컬럼 {col})",
            line=line,
            column=col,
        )

    # EOF 토큰 추가
    eof_col = (n - line_start + 1) if n > 0 else 1
    tokens.append(Token(TokenType.EOF, "", line, eof_col))
    return tokens
