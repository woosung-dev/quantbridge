"""parser_adapter 에러 경로 + 엣지 케이스 테스트 (Day 8 L1 보강).

Day 1 baseline은 valid corpus의 성공 경로만 다뤘음. 실제 사용 환경에서는:
- 빈 입력
- 공백/주석만
- 구문 오류
- 토큰 인식 실패

어떤 예외가 올라오는지 알아야 Week 2+ 에러 UX 설계 시 재활용 가능.

pynescript 0.3.0 관찰 결과: 모든 파싱 실패는 표준 `SyntaxError`로 통일됨.
"""
from __future__ import annotations

import pytest
from pynescript.ast.error import SyntaxError as PyneSyntaxError

from src.strategy.pine_v2.parser_adapter import parse_to_ast


def test_empty_source_parses_as_empty_script() -> None:
    """빈 문자열 입력은 파싱 성공 + body 빈 리스트."""
    tree = parse_to_ast("")
    assert hasattr(tree, "body")
    assert tree.body == []


def test_whitespace_only_source_parses_as_empty_script() -> None:
    tree = parse_to_ast("   \n\n  \t  \n")
    assert tree.body == []


def test_comment_only_source_parses_as_empty_script() -> None:
    """주석만 있어도 구문 요소 없음 → body 비어있음."""
    tree = parse_to_ast("// header comment\n// second line\n")
    assert tree.body == []


def test_valid_minimal_indicator_parses_with_one_statement() -> None:
    tree = parse_to_ast('//@version=5\nindicator("x")\n')
    assert len(tree.body) == 1


def test_syntax_error_raises_pynescript_syntax_error() -> None:
    """pynescript는 `pynescript.ast.error.SyntaxError` (자체 클래스, Python 내장 미상속)를 던진다.

    Week 2+ 에러 UX에서 이 예외를 잡아 사용자 친화 메시지로 매핑해야 함.
    """
    with pytest.raises(PyneSyntaxError) as excinfo:
        parse_to_ast('//@version=5\nindicator("x"\n  [')
    msg = str(excinfo.value).lower()
    assert "viable" in msg or "token" in msg or "indicator" in msg


def test_invalid_token_raises_pynescript_syntax_error() -> None:
    """정의되지 않은 토큰(@@@)은 PyneSyntaxError."""
    with pytest.raises(PyneSyntaxError):
        parse_to_ast('//@version=5\nindicator("x") @@@ ##')


def test_unbalanced_paren_raises_pynescript_syntax_error() -> None:
    """괄호 불일치 — 흔한 사용자 실수."""
    with pytest.raises(PyneSyntaxError):
        parse_to_ast('//@version=5\nindicator("x"\n')


def test_pynescript_syntax_error_is_not_builtin_subclass() -> None:
    """pynescript의 SyntaxError는 Python 내장 SyntaxError를 상속하지 않는다 (확인).

    Week 2+ error handling에서 except 절 설계 시 이 전제 필수.
    """
    import builtins
    assert not issubclass(PyneSyntaxError, builtins.SyntaxError), (
        "전제 파괴 — Week 2 error UX가 builtin SyntaxError로도 잡을 수 있어짐"
    )


def test_very_long_single_line_still_parses() -> None:
    """긴 한 줄도 파서가 처리 (스택 오버플로 없음)."""
    # 50개의 BinOp 체인
    expr = " + ".join("1" for _ in range(50))
    src = f'//@version=5\nindicator("x")\ny = {expr}\n'
    tree = parse_to_ast(src)
    assert len(tree.body) == 2  # indicator call + assignment


def test_unicode_string_literal_parses() -> None:
    """한글/이모지 포함 문자열 리터럴 파싱."""
    src = '//@version=5\nindicator("테스트 💎")\n'
    tree = parse_to_ast(src)
    assert len(tree.body) == 1
