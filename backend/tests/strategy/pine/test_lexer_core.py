"""Tests for tokenize() core — literals, identifiers, operators, punctuation.

T9 테스트: 숫자, 문자열, 식별자, 연산자, 구두점 토크나이징 검증.
"""
from __future__ import annotations

import pytest

from src.strategy.pine.errors import PineLexError
from src.strategy.pine.lexer import Token, TokenType, tokenize


class TestTokenizeNumbers:
    """숫자 리터럴 토크나이징."""

    def test_integer(self) -> None:
        tokens = tokenize("42")
        assert tokens[0] == Token(TokenType.NUMBER, "42", 1, 1)

    def test_float(self) -> None:
        tokens = tokenize("3.14")
        assert tokens[0] == Token(TokenType.NUMBER, "3.14", 1, 1)

    def test_scientific_lower_e(self) -> None:
        tokens = tokenize("1e10")
        assert tokens[0] == Token(TokenType.NUMBER, "1e10", 1, 1)

    def test_scientific_upper_e(self) -> None:
        tokens = tokenize("2.5E3")
        assert tokens[0] == Token(TokenType.NUMBER, "2.5E3", 1, 1)


class TestTokenizeStrings:
    """문자열 리터럴 토크나이징."""

    def test_double_quoted(self) -> None:
        tokens = tokenize('"hello"')
        assert tokens[0] == Token(TokenType.STRING, "hello", 1, 1)

    def test_single_quoted(self) -> None:
        tokens = tokenize("'world'")
        assert tokens[0] == Token(TokenType.STRING, "world", 1, 1)

    def test_unterminated_raises(self) -> None:
        with pytest.raises(PineLexError):
            tokenize('"unterminated')


class TestTokenizeIdentifiersAndKeywords:
    """식별자 및 키워드 토크나이징."""

    def test_plain_identifier(self) -> None:
        tokens = tokenize("close")
        assert tokens[0] == Token(TokenType.IDENT, "close", 1, 1)

    def test_keyword(self) -> None:
        tokens = tokenize("if")
        assert tokens[0] == Token(TokenType.KEYWORD, "if", 1, 1)

    def test_dotted_access(self) -> None:
        """ta.sma → IDENT DOT IDENT."""
        tokens = tokenize("ta.sma")
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert types == [TokenType.IDENT, TokenType.DOT, TokenType.IDENT]


class TestTokenizeOperators:
    """연산자 토크나이징."""

    def test_single_plus(self) -> None:
        tokens = tokenize("+")
        assert tokens[0] == Token(TokenType.OP, "+", 1, 1)

    def test_less_equal(self) -> None:
        tokens = tokenize("<=")
        assert tokens[0] == Token(TokenType.OP, "<=", 1, 1)

    def test_walrus(self) -> None:
        tokens = tokenize(":=")
        assert tokens[0] == Token(TokenType.WALRUS, ":=", 1, 1)

    def test_bang_alone_raises(self) -> None:
        with pytest.raises(PineLexError):
            tokenize("!")


class TestTokenizeMisc:
    """기타 토크나이징 동작."""

    def test_eof_appended(self) -> None:
        tokens = tokenize("1")
        assert tokens[-1].type == TokenType.EOF

    def test_whitespace_skipped(self) -> None:
        tokens = tokenize("a b")
        non_eof = [t for t in tokens if t.type not in (TokenType.EOF, TokenType.NEWLINE)]
        assert len(non_eof) == 2
        assert all(t.type == TokenType.IDENT for t in non_eof)

    def test_multiline_line_tracking(self) -> None:
        tokens = tokenize("a\nb")
        b_token = next(t for t in tokens if t.value == "b")
        assert b_token.line == 2

    def test_column_tracking(self) -> None:
        tokens = tokenize("  x")
        x_token = next(t for t in tokens if t.value == "x")
        assert x_token.column == 3
