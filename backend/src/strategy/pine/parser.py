"""Pine Script v5 재귀 하강 파서 — 표현식 파싱 (T11).

우선순위 (낮음 → 높음):
  ternary → or → and → not → eq/neq → cmp → add/sub → mul/div/mod → unary(-) → postfix([]) → primary

설계 결정:
  - 단항 마이너스: BinOp(op="-", left=Literal(0), right=operand)
  - not 표현식: BinOp(op="not", left=Literal(True), right=operand)
  - 점(.) 으로 연결된 식별자(ta.sma)는 단일 Ident(name="ta.sma")로 처리
  - 점 식별자 + '(' → FnCall
"""
from __future__ import annotations

from src.strategy.pine.ast_nodes import (
    BinOp,
    FnCall,
    HistoryRef,
    Ident,
    IfExpr,
    Kwarg,
    Literal,
    Node,
)
from src.strategy.pine.errors import PineParseError
from src.strategy.pine.lexer import Token, TokenType
from src.strategy.pine.types import SourceSpan


class _Parser:
    """재귀 하강 파서 내부 구현체."""

    def __init__(self, tokens: list[Token]) -> None:
        # NEWLINE/COMMENT/INDENT/DEDENT는 표현식 파싱 시 무시
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------
    # 헬퍼
    # ------------------------------------------------------------------

    def peek(self) -> Token:
        """현재 위치 토큰 반환 (소비하지 않음)."""
        while self._pos < len(self._tokens) and self._tokens[self._pos].type in (
            TokenType.NEWLINE,
            TokenType.INDENT,
            TokenType.DEDENT,
            TokenType.COMMENT,
        ):
            self._pos += 1
        if self._pos >= len(self._tokens):
            # 마지막 토큰은 EOF이어야 함
            return self._tokens[-1]
        return self._tokens[self._pos]

    def advance(self) -> Token:
        """현재 토큰 소비 후 반환."""
        tok = self.peek()
        self._pos += 1
        return tok

    def match(self, *types: TokenType) -> bool:
        """현재 토큰 타입이 types 중 하나이면 True."""
        return self.peek().type in types

    def match_value(self, *values: str) -> bool:
        """현재 토큰 값이 values 중 하나이면 True."""
        return self.peek().value in values

    def consume(self, type_: TokenType, value: str | None = None) -> Token:
        """기대 토큰을 소비. 불일치 시 PineParseError."""
        tok = self.peek()
        if tok.type != type_:
            raise PineParseError(
                f"예상 토큰 타입 {type_.name} 이지만 {tok.type.name}({tok.value!r}) 를 만남",
                line=tok.line,
                column=tok.column,
            )
        if value is not None and tok.value != value:
            raise PineParseError(
                f"예상 토큰 값 {value!r} 이지만 {tok.value!r} 를 만남",
                line=tok.line,
                column=tok.column,
            )
        return self.advance()

    def span_of(self, tok: Token) -> SourceSpan:
        """Token → SourceSpan 변환."""
        return SourceSpan(line=tok.line, column=tok.column, length=len(tok.value))

    def skip_newlines(self) -> None:
        """NEWLINE 토큰들을 모두 건너뜀."""
        while self._pos < len(self._tokens) and self._tokens[self._pos].type == TokenType.NEWLINE:
            self._pos += 1

    # ------------------------------------------------------------------
    # 표현식 진입점
    # ------------------------------------------------------------------

    def expression(self) -> Node:
        """최상위 표현식 파싱 (ternary 포함)."""
        return self._ternary()

    # ------------------------------------------------------------------
    # 우선순위별 파싱 메서드
    # ------------------------------------------------------------------

    def _ternary(self) -> Node:
        """ternary: or_expr ('?' or_expr ':' or_expr)?"""
        cond = self._or()
        if self.match(TokenType.QUESTION):
            q_tok = self.advance()
            then = self._or()
            self.consume(TokenType.COLON)
            else_ = self._ternary()  # 우결합
            span = SourceSpan(line=q_tok.line, column=q_tok.column, length=1)
            return IfExpr(source_span=span, cond=cond, then=then, else_=else_)
        return cond

    def _or(self) -> Node:
        """or: and_expr ('or' and_expr)*"""
        left = self._and()
        while self.match(TokenType.KEYWORD) and self.match_value("or"):
            op_tok = self.advance()
            right = self._and()
            span = self.span_of(op_tok)
            left = BinOp(source_span=span, op="or", left=left, right=right)
        return left

    def _and(self) -> Node:
        """and: not_expr ('and' not_expr)*"""
        left = self._not()
        while self.match(TokenType.KEYWORD) and self.match_value("and"):
            op_tok = self.advance()
            right = self._not()
            span = self.span_of(op_tok)
            left = BinOp(source_span=span, op="and", left=left, right=right)
        return left

    def _not(self) -> Node:
        """not: 'not' not_expr | eq_expr
        정규화: BinOp(op="not", left=Literal(True), right=operand)
        """
        if self.match(TokenType.KEYWORD) and self.match_value("not"):
            op_tok = self.advance()
            operand = self._not()
            span = self.span_of(op_tok)
            true_lit = Literal(source_span=span, value=True)
            return BinOp(source_span=span, op="not", left=true_lit, right=operand)
        return self._equality()

    def _equality(self) -> Node:
        """equality: comparison (('==' | '!=') comparison)*"""
        left = self._comparison()
        while self.match(TokenType.OP) and self.match_value("==", "!="):
            op_tok = self.advance()
            right = self._comparison()
            span = self.span_of(op_tok)
            left = BinOp(source_span=span, op=op_tok.value, left=left, right=right)
        return left

    def _comparison(self) -> Node:
        """comparison: additive (('<' | '<=' | '>' | '>=') additive)*"""
        left = self._additive()
        while self.match(TokenType.OP) and self.match_value("<", "<=", ">", ">="):
            op_tok = self.advance()
            right = self._additive()
            span = self.span_of(op_tok)
            left = BinOp(source_span=span, op=op_tok.value, left=left, right=right)
        return left

    def _additive(self) -> Node:
        """additive: multiplicative (('+' | '-') multiplicative)*"""
        left = self._multiplicative()
        while self.match(TokenType.OP) and self.match_value("+", "-"):
            op_tok = self.advance()
            right = self._multiplicative()
            span = self.span_of(op_tok)
            left = BinOp(source_span=span, op=op_tok.value, left=left, right=right)
        return left

    def _multiplicative(self) -> Node:
        """multiplicative: unary (('*' | '/' | '%') unary)*"""
        left = self._unary()
        while self.match(TokenType.OP) and self.match_value("*", "/", "%"):
            op_tok = self.advance()
            right = self._unary()
            span = self.span_of(op_tok)
            left = BinOp(source_span=span, op=op_tok.value, left=left, right=right)
        return left

    def _unary(self) -> Node:
        """unary: '-' unary | postfix
        정규화: BinOp(op="-", left=Literal(0), right=operand)
        """
        if self.match(TokenType.OP) and self.match_value("-"):
            op_tok = self.advance()
            operand = self._unary()
            span = self.span_of(op_tok)
            zero_lit = Literal(source_span=span, value=0)
            return BinOp(source_span=span, op="-", left=zero_lit, right=operand)
        return self._postfix()

    def _postfix(self) -> Node:
        """postfix: primary ('[' expr ']')*  (히스토리 참조)"""
        node = self._primary()
        while self.match(TokenType.LBRACKET):
            lb_tok = self.advance()
            offset = self.expression()
            self.consume(TokenType.RBRACKET)
            span = SourceSpan(line=lb_tok.line, column=lb_tok.column, length=1)
            node = HistoryRef(source_span=span, target=node, offset=offset)
        return node

    def _primary(self) -> Node:
        """primary: NUMBER | STRING | 'true' | 'false' | IDENT ('.' IDENT)* ('(' args ')')? | '(' expr ')'"""
        tok = self.peek()

        # 숫자 리터럴
        if tok.type == TokenType.NUMBER:
            self.advance()
            span = self.span_of(tok)
            # 정수 vs 부동소수점 구분
            value: int | float = float(tok.value) if "." in tok.value or "e" in tok.value.lower() else int(tok.value)
            return Literal(source_span=span, value=value)

        # 문자열 리터럴
        if tok.type == TokenType.STRING:
            self.advance()
            span = self.span_of(tok)
            return Literal(source_span=span, value=tok.value)

        # 불리언 키워드
        if tok.type == TokenType.KEYWORD and tok.value in ("true", "false"):
            self.advance()
            span = self.span_of(tok)
            return Literal(source_span=span, value=tok.value == "true")

        # 식별자 (단순 또는 점 표기 ta.sma)
        if tok.type == TokenType.IDENT:
            return self._parse_ident_or_fncall()

        # 괄호 표현식
        if tok.type == TokenType.LPAREN:
            self.advance()
            node = self.expression()
            self.consume(TokenType.RPAREN)
            return node

        raise PineParseError(
            f"예상치 못한 토큰 {tok.type.name}({tok.value!r})",
            line=tok.line,
            column=tok.column,
        )

    def _parse_ident_or_fncall(self) -> Node:
        """IDENT ('.' IDENT)* 를 파싱, 뒤에 '(' 이 오면 FnCall로 변환."""
        first_tok = self.advance()  # 첫 IDENT 소비
        span = self.span_of(first_tok)
        name_parts = [first_tok.value]

        # 점(.) 으로 연결된 식별자 조합 (ta.sma 등)
        while self.peek().type == TokenType.DOT:
            self.advance()  # DOT 소비
            next_tok = self.peek()
            if next_tok.type not in (TokenType.IDENT, TokenType.KEYWORD):
                raise PineParseError(
                    f"DOT 뒤에 식별자 예상, {next_tok.type.name}({next_tok.value!r}) 만남",
                    line=next_tok.line,
                    column=next_tok.column,
                )
            self.advance()
            name_parts.append(next_tok.value)

        full_name = ".".join(name_parts)

        # 함수 호출 여부 확인
        if self.peek().type == TokenType.LPAREN:
            return self._parse_fncall(full_name, span)

        return Ident(source_span=span, name=full_name)

    def _parse_fncall(self, name: str, span: SourceSpan) -> FnCall:
        """'(' [arglist] ')' 파싱 — 위치 인자와 키워드 인자 분리."""
        self.consume(TokenType.LPAREN)

        args: list[Node] = []
        kwargs: list[Kwarg] = []

        if not self.match(TokenType.RPAREN):
            # 첫 인자 파싱
            self._parse_arg(args, kwargs)
            while self.match(TokenType.COMMA):
                self.advance()  # COMMA 소비
                if self.match(TokenType.RPAREN):
                    break  # trailing comma 허용
                self._parse_arg(args, kwargs)

        self.consume(TokenType.RPAREN)
        return FnCall(
            source_span=span,
            name=name,
            args=tuple(args),
            kwargs=tuple(kwargs),
        )

    def _parse_arg(self, args: list[Node], kwargs: list[Kwarg]) -> None:
        """인자 하나 파싱 — IDENT '=' expr 이면 kwarg, 아니면 positional."""
        # 키워드 인자 미리보기: IDENT '='  (단, '==' 아님)
        tok = self.peek()
        if tok.type == TokenType.IDENT:
            # 한 칸 앞을 들여다봄
            saved_pos = self._pos
            self.advance()  # IDENT 소비
            next_tok = self.peek()
            if next_tok.type == TokenType.ASSIGN:
                # 키워드 인자
                self.advance()  # ASSIGN 소비
                value = self.expression()
                kw_span = SourceSpan(line=tok.line, column=tok.column, length=len(tok.value))
                kwargs.append(Kwarg(source_span=kw_span, name=tok.value, value=value))
                return
            else:
                # 일반 위치 인자 — 파서 위치 복원 후 재파싱
                self._pos = saved_pos

        node = self.expression()
        if kwargs:
            raise PineParseError(
                "키워드 인자 뒤에 위치 인자 사용 불가",
                line=tok.line,
                column=tok.column,
            )
        args.append(node)


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def parse_expression(tokens: list[Token]) -> Node:
    """토큰 목록에서 표현식 하나를 파싱하여 AST 노드 반환.

    Args:
        tokens: lexer.tokenize()가 반환한 Token 리스트.

    Returns:
        파싱된 AST 노드.

    Raises:
        PineParseError: 파싱 오류 발생 시.
    """
    parser = _Parser(tokens)
    return parser.expression()
