"""Pine Script AST 노드 정의 — 불변 frozen dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field

from src.strategy.pine.types import SourceSpan


@dataclass(frozen=True)
class Literal:
    """숫자·문자열·불리언 리터럴."""

    value: object
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Ident:
    """변수·내장 식별자 참조."""

    name: str
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class BinOp:
    """이항 연산자 표현식 (left op right)."""

    op: str
    left: Node
    right: Node
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Kwarg:
    """함수 호출 시 키워드 인자 (key=value)."""

    key: str
    value: Node
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class FnCall:
    """함수 호출 표현식."""

    name: str
    args: tuple[Node, ...]
    kwargs: tuple[Kwarg, ...]
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class VarDecl:
    """변수 선언문 (var / varip 포함, sprint 1에서는 None으로 통일)."""

    name: str
    value: Node
    var_type: str | None
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Assign:
    """변수 재할당문."""

    name: str
    value: Node
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class IfExpr:
    """3항 조건 표현식 (condition ? then : else 형태)."""

    condition: Node
    then_expr: Node
    else_expr: Node
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class IfStmt:
    """if 문 (블록 형태)."""

    condition: Node
    then_body: tuple[Node, ...]
    else_body: tuple[Node, ...]
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class ForLoop:
    """for 루프문."""

    var: str
    start: Node
    end: Node
    body: tuple[Node, ...]
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class HistoryRef:
    """히스토리 참조 (close[1] 형태)."""

    name: str
    index: Node
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class TupleReturn:
    """다중 반환값 튜플."""

    elements: tuple[Node, ...]
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Program:
    """최상위 프로그램 노드."""

    version: int
    body: tuple[Node, ...]
    source_span: SourceSpan
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


# Node 유니온 타입 — 재귀 참조를 위한 전방 선언
Node = (
    Literal
    | Ident
    | BinOp
    | Kwarg
    | FnCall
    | VarDecl
    | Assign
    | IfExpr
    | IfStmt
    | ForLoop
    | HistoryRef
    | TupleReturn
    | Program
)
