"""Tests for lexer token types and Token dataclass."""
from __future__ import annotations

import pytest

from src.strategy.pine.lexer import Token, TokenType


class TestTokenType:
    """Test TokenType enum members."""

    def test_token_type_members_exist(self) -> None:
        """Verify all required TokenType members are defined."""
        required = {
            "NUMBER",
            "STRING",
            "IDENT",
            "KEYWORD",
            "OP",
            "LPAREN",
            "RPAREN",
            "LBRACKET",
            "RBRACKET",
            "COMMA",
            "DOT",
            "COLON",
            "QUESTION",
            "ASSIGN",
            "WALRUS",
            "NEWLINE",
            "INDENT",
            "DEDENT",
            "COMMENT",
            "EOF",
        }
        actual = {member.name for member in TokenType}
        assert required.issubset(actual), f"Missing: {required - actual}"


class TestToken:
    """Test Token dataclass."""

    def test_token_creation(self) -> None:
        """Test creating a Token instance."""
        token = Token(type=TokenType.IDENT, value="close", line=1, column=0)
        assert token.type == TokenType.IDENT
        assert token.value == "close"
        assert token.line == 1
        assert token.column == 0

    def test_token_is_frozen(self) -> None:
        """Test that Token is immutable (frozen dataclass)."""
        token = Token(type=TokenType.NUMBER, value="42", line=2, column=5)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            token.value = "999"  # type: ignore
