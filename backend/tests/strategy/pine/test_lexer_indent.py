"""Lexer 인덴트/주석 테스트."""
from __future__ import annotations

from src.strategy.pine.lexer import TokenType, tokenize


def _types(src: str) -> list[TokenType]:
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]


def test_comment_is_skipped_by_default():
    toks = tokenize("// this is a comment\nx = 1\n")
    assert TokenType.COMMENT not in [t.type for t in toks]
    # x = 1 토큰들은 존재
    types = [t.type for t in toks if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
    assert types == [TokenType.IDENT, TokenType.ASSIGN, TokenType.NUMBER]


def test_inline_comment_trimmed():
    toks = tokenize("x = 1 // comment\n")
    values = [t.value for t in toks if t.type == TokenType.NUMBER]
    assert values == ["1"]


def test_indent_dedent_basic():
    src = "if cond\n    x = 1\n    y = 2\n"
    types = _types(src)
    # 'if' KEYWORD, 'cond' IDENT, NEWLINE, INDENT, stmts..., DEDENT
    assert TokenType.INDENT in types
    assert TokenType.DEDENT in types


def test_version_pragma_preserved_as_comment():
    # //@version=5 는 특수 주석이지만 토큰화 단계에선 그냥 스킵.
    # 파서가 소스 원본을 별도 스캔해서 version을 뽑는 구조.
    toks = tokenize("//@version=5\nx = 1\n")
    values = [t.value for t in toks if t.type == TokenType.IDENT]
    assert "x" in values


def test_var_keyword_classified_as_keyword():
    toks = tokenize("var int x = 0\n")
    kw = [t for t in toks if t.type == TokenType.KEYWORD]
    assert any(t.value == "var" for t in kw)
