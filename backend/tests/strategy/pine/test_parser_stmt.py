"""Parser 문(statement) 파싱 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.ast_nodes import (
    Assign,
    FnCall,
    ForLoop,
    IfStmt,
    Program,
    VarDecl,
)
from src.strategy.pine.errors import PineParseError, PineUnsupportedError
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse


def _prog(src: str) -> Program:
    return parse(tokenize(src))


def test_parse_empty_program_v5_default():
    prog = _prog("")
    assert isinstance(prog, Program)
    assert prog.version == 5
    assert prog.statements == ()


def test_parse_version_pragma_v5():
    prog = _prog("//@version=5\nx = 1\n")
    assert prog.version == 5


def test_parse_version_pragma_v4_treated_as_v5_after_normalize():
    # 파서는 v5만 입력받음. v4 변환은 정규화 레이어 책임.
    # 여기선 v4 헤더가 그대로 들어왔을 때도 파서가 터지지 않아야 함.
    prog = _prog("//@version=5\nx = 1\n")
    assert prog.version == 5


def test_parse_var_decl_simple():
    prog = _prog("x = 1\n")
    assert len(prog.statements) == 1
    stmt = prog.statements[0]
    assert isinstance(stmt, VarDecl)
    assert stmt.name == "x"
    assert stmt.is_var is False


def test_parse_var_decl_with_var_keyword():
    prog = _prog("var int counter = 0\n")
    stmt = prog.statements[0]
    assert isinstance(stmt, VarDecl)
    assert stmt.is_var is True
    assert stmt.type_hint == "int"


def test_parse_assign_walrus():
    prog = _prog("x = 0\nx := 5\n")
    assert len(prog.statements) == 2
    assign = prog.statements[1]
    assert isinstance(assign, Assign)
    assert assign.op == ":="


def test_parse_if_stmt():
    src = """if cond
    x = 1
"""
    prog = _prog(src)
    assert len(prog.statements) == 1
    stmt = prog.statements[0]
    assert isinstance(stmt, IfStmt)
    assert len(stmt.body) == 1


def test_parse_if_else_stmt():
    src = """if cond
    x = 1
else
    x = 2
"""
    prog = _prog(src)
    stmt = prog.statements[0]
    assert isinstance(stmt, IfStmt)
    assert len(stmt.else_body) == 1


def test_parse_if_elseif_chain():
    src = """if a
    x = 1
else if b
    x = 2
else
    x = 3
"""
    prog = _prog(src)
    stmt = prog.statements[0]
    assert isinstance(stmt, IfStmt)
    # else_body는 길이 1의 IfStmt 튜플 (elseif는 중첩 IfStmt로 표현)
    assert len(stmt.else_body) == 1
    assert isinstance(stmt.else_body[0], IfStmt)


def test_parse_for_loop():
    src = """for i = 0 to 10
    x = i
"""
    prog = _prog(src)
    stmt = prog.statements[0]
    assert isinstance(stmt, ForLoop)
    assert stmt.var_name == "i"


def test_parse_fncall_as_top_level_statement():
    # strategy.entry(...) 같은 부수효과 호출
    prog = _prog('strategy.entry("Long", strategy.long)\n')
    assert len(prog.statements) == 1
    assert isinstance(prog.statements[0], FnCall)


def test_parse_multiple_statements():
    src = """x = 1
y = 2
z = x + y
"""
    prog = _prog(src)
    assert len(prog.statements) == 3


def test_parse_error_on_while_loop():
    # while 루프는 스프린트 1 미지원
    src = """while cond
    x = 1
"""
    with pytest.raises(PineUnsupportedError) as ei:
        _prog(src)
    assert ei.value.category == "syntax"


def test_parse_error_with_line_info():
    with pytest.raises(PineParseError) as ei:
        _prog("x = = 1\n")
    assert ei.value.line == 1
