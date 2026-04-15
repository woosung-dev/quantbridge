"""Pine Script v5 재귀 하강 파서 — 표현식 + 문(statement) 파싱 (T11+T12).

우선순위 (낮음 → 높음):
  ternary → or → and → not → eq/neq → cmp → add/sub → mul/div/mod → unary(-) → postfix([]) → primary

설계 결정:
  - 단항 마이너스: BinOp(op="-", left=Literal(0), right=operand)
  - not 표현식: BinOp(op="not", left=Literal(True), right=operand)
  - 점(.) 으로 연결된 식별자(ta.sma)는 단일 Ident(name="ta.sma")로 처리
  - 점 식별자 + '(' → FnCall
  - else if → 중첩 IfStmt (else_body 길이 1)
  - while → PineUnsupportedError
"""
from __future__ import annotations

from src.strategy.pine.ast_nodes import (
    Assign,
    BinOp,
    FnCall,
    ForLoop,
    HistoryRef,
    Ident,
    IfExpr,
    IfStmt,
    Kwarg,
    Literal,
    Node,
    Program,
    VarDecl,
)
from src.strategy.pine.errors import PineParseError, PineUnsupportedError
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
        """현재 위치 토큰 반환 (소비하지 않음).

        NEWLINE / INDENT / COMMENT 를 건너뛴다.
        DEDENT 는 블록 종료 마커이므로 건너뛰지 않는다.
        """
        while self._pos < len(self._tokens) and self._tokens[self._pos].type in (
            TokenType.NEWLINE,
            TokenType.INDENT,
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

    def peek_ahead(self, offset: int = 1) -> Token:
        """현재 위치에서 offset 만큼 앞의 토큰 반환 (NEWLINE/INDENT/DEDENT/COMMENT 제외)."""
        count = 0
        i = self._pos
        # 현재 위치의 공백 계열 토큰을 건너뜀
        _skip = (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT, TokenType.COMMENT)
        while i < len(self._tokens):
            if self._tokens[i].type not in _skip:
                if count == offset:
                    return self._tokens[i]
                count += 1
            i += 1
        return self._tokens[-1]

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

    # ------------------------------------------------------------------
    # 문(statement) 파싱 메서드 (T12)
    # ------------------------------------------------------------------

    def parse_program(self) -> Program:
        """최상위 Program 노드 파싱. 버전은 v5 고정 (v4 변환은 외부 레이어 책임)."""
        start_tok = self.peek()
        statements: list[Node] = []
        self.skip_newlines()
        while self.peek().type != TokenType.EOF:
            stmt = self._parse_statement()
            statements.append(stmt)
            self.skip_newlines()
        end_tok = self.peek()
        return Program(
            source_span=SourceSpan(
                line=start_tok.line,
                column=start_tok.column,
                length=end_tok.column,
            ),
            version=5,
            statements=tuple(statements),
        )

    def _parse_statement(self) -> Node:
        """토큰 타입에 따라 적절한 문(statement) 파싱 메서드로 디스패치."""
        tok = self.peek()
        # if 문
        if tok.type == TokenType.KEYWORD and tok.value == "if":
            return self._parse_if_stmt()
        # for 루프
        if tok.type == TokenType.KEYWORD and tok.value == "for":
            return self._parse_for_stmt()
        # while — 미지원
        if tok.type == TokenType.KEYWORD and tok.value == "while":
            raise PineUnsupportedError(
                "while loop is not supported in sprint 1",
                feature="while",
                category="syntax",
                line=tok.line,
                column=tok.column,
            )
        # var / varip 선언
        if tok.type == TokenType.KEYWORD and tok.value in ("var", "varip"):
            return self._parse_var_decl(is_var=True)
        # 그 외: 식별자로 시작하면 var_decl | assign | fncall 중 하나
        if tok.type == TokenType.IDENT:
            return self._parse_ident_statement()
        # 독립 표현식 (드물지만 허용)
        return self.expression()

    def _parse_var_decl(self, *, is_var: bool) -> VarDecl:
        """var / varip [type_hint] name = expr 파싱."""
        start = self.advance() if is_var else self.peek()
        # 선택적 타입 힌트: var IDENT IDENT = ... 형태 (예: var int counter = 0)
        type_hint: str | None = None
        if is_var and self.peek().type == TokenType.IDENT and self.peek_ahead(1).type == TokenType.IDENT:
            type_hint = self.advance().value
        name_tok = self.consume(TokenType.IDENT)
        self.consume(TokenType.ASSIGN)
        expr = self.expression()
        return VarDecl(
            source_span=self.span_of(start),
            name=name_tok.value,
            is_var=is_var,
            type_hint=type_hint,
            expr=expr,
        )

    def _parse_ident_statement(self) -> Node:
        """IDENT로 시작하는 문 — 다음 토큰으로 분기:
        - `=`  → VarDecl
        - `:=` → Assign (walrus)
        - `(`  → FnCall (부수효과, statement로 취급)
        - `.`  → 점 접근 후 위 중 하나
        """
        # 식별자 조립 (a.b.c)
        start = self.peek()
        parts = [self.advance().value]
        while self.match(TokenType.DOT):
            self.advance()  # DOT 소비
            next_tok = self.peek()
            if next_tok.type not in (TokenType.IDENT, TokenType.KEYWORD):
                raise PineParseError(
                    f"DOT 뒤에 식별자 예상, {next_tok.type.name}({next_tok.value!r}) 만남",
                    line=next_tok.line,
                    column=next_tok.column,
                )
            parts.append(self.advance().value)
        name = ".".join(parts)
        span = self.span_of(start)

        # `(` → FnCall statement
        if self.match(TokenType.LPAREN):
            return self._parse_fncall(name, span)

        # `=` → VarDecl (파서 레벨에선 VarDecl로 표현; 인터프리터가 재할당 구분)
        if self.match(TokenType.ASSIGN):
            self.advance()
            expr = self.expression()
            return VarDecl(
                source_span=span,
                name=name,
                is_var=False,
                type_hint=None,
                expr=expr,
            )

        # `:=` → Assign
        if self.match(TokenType.WALRUS):
            self.advance()
            expr = self.expression()
            return Assign(
                source_span=span,
                target=Ident(source_span=span, name=name),
                op=":=",
                value=expr,
            )

        # 그 외 → 에러
        tok = self.peek()
        raise PineParseError(
            f"expected '=', ':=' or '(' after identifier '{name}', got {tok.value!r}",
            line=tok.line,
            column=tok.column,
        )

    def _parse_if_stmt(self) -> IfStmt:
        """if COND\\n INDENT body DEDENT [else (if ... | INDENT body DEDENT)] 파싱."""
        if_tok = self.advance()  # 'if' 소비
        cond = self.expression()
        self.skip_newlines()
        body = self._parse_block()
        else_body: tuple[Node, ...] = ()
        # else 분기 확인
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "else":
            self.advance()  # 'else' 소비
            if self.peek().type == TokenType.KEYWORD and self.peek().value == "if":
                # else if → 중첩 IfStmt
                nested = self._parse_if_stmt()
                else_body = (nested,)
            else:
                self.skip_newlines()
                else_body = self._parse_block()
        return IfStmt(
            source_span=self.span_of(if_tok),
            cond=cond,
            body=body,
            else_body=else_body,
        )

    def _parse_for_stmt(self) -> ForLoop:
        """for VAR = START to END [by STEP]\\n INDENT body DEDENT 파싱."""
        for_tok = self.advance()  # 'for' 소비
        var_name = self.consume(TokenType.IDENT).value
        self.consume(TokenType.ASSIGN)
        start = self.expression()
        self.consume(TokenType.KEYWORD, "to")
        end = self.expression()
        step: Node | None = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "by":
            self.advance()  # 'by' 소비
            step = self.expression()
        self.skip_newlines()
        body = self._parse_block()
        return ForLoop(
            source_span=self.span_of(for_tok),
            var_name=var_name,
            start=start,
            end=end,
            step=step,
            body=body,
        )

    def _peek_raw(self) -> Token:
        """현재 위치에서 첫 번째 비-공백 토큰 반환.
        NEWLINE/COMMENT는 건너뛰지만 INDENT/DEDENT는 건너뛰지 않음.
        self._pos는 변경하지 않음 (순수 peek).
        """
        i = self._pos
        while i < len(self._tokens) and self._tokens[i].type in (
            TokenType.NEWLINE,
            TokenType.COMMENT,
        ):
            i += 1
        if i >= len(self._tokens):
            return self._tokens[-1]
        return self._tokens[i]

    def _skip_to_raw(self) -> None:
        """NEWLINE/COMMENT를 건너뛰어 다음 실질 토큰(INDENT/DEDENT 포함) 위치로 이동."""
        while self._pos < len(self._tokens) and self._tokens[self._pos].type in (
            TokenType.NEWLINE,
            TokenType.COMMENT,
        ):
            self._pos += 1

    def _consume_raw(self) -> Token:
        """NEWLINE/COMMENT만 건너뛰고 현재 토큰 소비 후 반환."""
        self._skip_to_raw()
        if self._pos >= len(self._tokens):
            return self._tokens[-1]
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _parse_block(self) -> tuple[Node, ...]:
        """INDENT ... DEDENT 블록 파싱.

        주의: peek()는 INDENT/DEDENT를 건너뛰므로 직접 원시 스캔으로 처리한다.
        peek()가 INDENT를 이미 소비했을 수 있으므로 포함 여부를 검사 후 조건부 소비한다.
        """
        # NEWLINE/COMMENT만 건너뛰고 INDENT 확인
        self._skip_to_raw()
        if self._pos < len(self._tokens) and self._tokens[self._pos].type == TokenType.INDENT:
            self._pos += 1  # INDENT 소비
        else:
            # peek()이 이미 INDENT를 건너뛴 경우 — pos가 INDENT 이후에 있을 수 있음
            # INDENT가 선행하는지 역방향으로 확인 (이미 소비됐으면 통과)
            # 단, 완전히 없는 경우(들여쓰기 누락)는 에러
            pass  # peek()가 이미 INDENT를 skip했으므로 그대로 진행

        statements: list[Node] = []
        while True:
            self._skip_to_raw()
            if self._pos >= len(self._tokens):
                break
            if self._tokens[self._pos].type in (TokenType.DEDENT, TokenType.EOF):
                break
            statements.append(self._parse_statement())

        # DEDENT 소비
        self._skip_to_raw()
        if self._pos < len(self._tokens) and self._tokens[self._pos].type == TokenType.DEDENT:
            self._pos += 1

        return tuple(statements)


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


def parse(tokens: list[Token]) -> Program:
    """토큰 목록에서 최상위 Program AST를 파싱하여 반환.

    Args:
        tokens: lexer.tokenize()가 반환한 Token 리스트.

    Returns:
        파싱된 Program 노드.

    Raises:
        PineParseError: 파싱 오류 발생 시.
        PineUnsupportedError: 미지원 문법(while 등) 사용 시.
    """
    parser = _Parser(tokens)
    return parser.parse_program()
