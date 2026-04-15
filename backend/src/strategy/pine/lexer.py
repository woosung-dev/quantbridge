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
    """Pine v5 소스를 토큰 리스트로 변환.

    주석은 스킵. 들여쓰기는 INDENT/DEDENT 토큰으로 변환 (Python 스타일).

    Args:
        source: Pine Script v5 소스 코드.

    Returns:
        Token 목록 (마지막 요소는 항상 EOF).

    Raises:
        PineLexError: 인식할 수 없는 문자 또는 종료되지 않은 문자열.
    """
    tokens: list[Token] = []
    i = 0
    line = 1
    line_start = 0
    at_line_start = True
    indent_stack: list[int] = [0]

    while i < len(source):
        ch = source[i]
        col = i - line_start + 1  # 1-based column

        # 라인 시작 시 인덴트 계산
        if at_line_start:
            # 공백/탭 건너뛰어 첫 실제 문자 위치 확인
            j = i
            while j < len(source) and source[j] in (" ", "\t"):
                j += 1
            if j >= len(source) or source[j] == "\n":
                # 빈 줄: 인덴트 계산 제외, 개행만 처리
                i = j
                if i < len(source) and source[i] == "\n":
                    tokens.append(Token(TokenType.NEWLINE, "\n", line, i - line_start + 1))
                    line += 1
                    line_start = i + 1
                    i += 1
                at_line_start = True
                continue
            # 주석만 있는 줄
            if j + 1 < len(source) and source[j] == "/" and source[j + 1] == "/":
                # 주석 끝까지 스킵 (개행 미포함)
                while j < len(source) and source[j] != "\n":
                    j += 1
                i = j
                if i < len(source) and source[i] == "\n":
                    line += 1
                    line_start = i + 1
                    i += 1
                at_line_start = True
                continue
            # 실제 인덴트 레벨 계산 (탭 = 공백 4개)
            indent_width = 0
            k = i
            while k < j:
                indent_width += 4 if source[k] == "\t" else 1
                k += 1
            if indent_width > indent_stack[-1]:
                indent_stack.append(indent_width)
                tokens.append(Token(TokenType.INDENT, "", line, 1))
            while indent_width < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(Token(TokenType.DEDENT, "", line, 1))
            i = j
            at_line_start = False
            continue

        # 주석 (인라인): 줄 끝까지 스킵
        if ch == "/" and i + 1 < len(source) and source[i + 1] == "/":
            while i < len(source) and source[i] != "\n":
                i += 1
            continue

        # 공백/탭 스킵
        if ch in (" ", "\t", "\r"):
            i += 1
            continue

        # 개행
        if ch == "\n":
            tokens.append(Token(TokenType.NEWLINE, "\n", line, col))
            line += 1
            line_start = i + 1
            i += 1
            at_line_start = True
            continue

        # 숫자 리터럴: 정수, 부동소수점, 과학적 표기법
        if ch.isdigit() or (ch == "." and i + 1 < len(source) and source[i + 1].isdigit()):
            j = i
            has_dot = False
            has_exp = False
            while j < len(source):
                c = source[j]
                if c.isdigit():
                    j += 1
                elif c == "." and not has_dot and not has_exp:
                    has_dot = True
                    j += 1
                elif c in ("e", "E") and not has_exp:
                    has_exp = True
                    j += 1
                    if j < len(source) and source[j] in ("+", "-"):
                        j += 1
                else:
                    break
            tokens.append(Token(TokenType.NUMBER, source[i:j], line, col))
            i = j
            continue

        # 문자열 리터럴: 작은따옴표 또는 큰따옴표
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            chars: list[str] = []
            while j < len(source) and source[j] != quote:
                if source[j] == "\\":
                    # 이스케이프 처리
                    j += 1
                    if j < len(source):
                        chars.append(source[j])
                        j += 1
                    else:
                        raise PineLexError(
                            "종료되지 않은 이스케이프 시퀀스",
                            line=line,
                            column=col,
                        )
                elif source[j] == "\n":
                    raise PineLexError(
                        "unterminated string literal",
                        line=line,
                        column=col,
                    )
                else:
                    chars.append(source[j])
                    j += 1
            if j >= len(source):
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
            while j < len(source) and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            tok_type = TokenType.KEYWORD if word in _KEYWORDS else TokenType.IDENT
            tokens.append(Token(tok_type, word, line, col))
            i = j
            continue

        # 2글자 연산자: <=, >=, ==, !=, :=
        if ch in "<>=!:":
            nxt = source[i + 1] if i + 1 < len(source) else ""
            two = ch + nxt
            if two in ("<=", ">=", "==", "!=", ":="):
                tt = TokenType.WALRUS if two == ":=" else TokenType.OP
                tokens.append(Token(tt, two, line, col))
                i += 2
                continue
            if ch == ":":
                tokens.append(Token(TokenType.COLON, ":", line, col))
                i += 1
                continue
            if ch == "=":
                tokens.append(Token(TokenType.ASSIGN, "=", line, col))
                i += 1
                continue
            if ch in ("<", ">"):
                tokens.append(Token(TokenType.OP, ch, line, col))
                i += 1
                continue
            if ch == "!":
                raise PineLexError(
                    f"인식할 수 없는 문자 '!' (라인 {line}, 컬럼 {col}). '!=' 를 의미하셨나요?",
                    line=line,
                    column=col,
                )

        # 단일 문자 연산자 / 구두점
        if ch in _SINGLE_CHAR:
            tokens.append(Token(_SINGLE_CHAR[ch], ch, line, col))
            i += 1
            continue

        # 인식 불가 문자
        raise PineLexError(
            f"인식할 수 없는 문자 {ch!r} (라인 {line}, 컬럼 {col})",
            line=line,
            column=col,
        )

    # 종료 시 남은 인덴트 해소
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token(TokenType.DEDENT, "", line, 1))
    eof_col = (len(source) - line_start + 1) if len(source) > 0 else 1
    tokens.append(Token(TokenType.EOF, "", line, eof_col))
    return tokens
