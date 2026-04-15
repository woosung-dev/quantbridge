"""Pine Script AST 노드 정의 — 불변 frozen dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from src.strategy.pine.types import SourceSpan

# Node 유니온 타입 — 재귀 참조를 위한 전방 선언 (문자열 forward ref)
Node = Union[
    "Literal",
    "Ident",
    "BinOp",
    "Kwarg",
    "FnCall",
    "VarDecl",
    "Assign",
    "IfExpr",
    "IfStmt",
    "ForLoop",
    "HistoryRef",
    "TupleReturn",
    "Program",
]


@dataclass(frozen=True)
class Literal:
    """숫자·문자열·불리언 리터럴."""

    source_span: SourceSpan
    value: object
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Ident:
    """변수·내장 식별자 참조."""

    source_span: SourceSpan
    name: str
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class BinOp:
    """이항 연산자 표현식 (left op right)."""

    source_span: SourceSpan
    op: str
    left: Node
    right: Node
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Kwarg:
    """함수 호출 시 키워드 인자 (key=value)."""

    source_span: SourceSpan
    key: str
    value: Node
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class FnCall:
    """함수 호출 표현식."""

    source_span: SourceSpan
    name: str
    args: tuple[Node, ...]
    kwargs: tuple[Kwarg, ...]
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class VarDecl:
    """변수 선언문 (var / varip 포함)."""

    source_span: SourceSpan
    name: str
    is_var: bool
    type_hint: str | None
    expr: Node
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Assign:
    """변수 재할당문."""

    source_span: SourceSpan
    target: Node
    op: str
    value: Node
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class IfExpr:
    """3항 조건 표현식 (condition ? then : else 형태)."""

    source_span: SourceSpan
    cond: Node
    then: Node
    else_: Node
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class IfStmt:
    """if 문 (블록 형태)."""

    source_span: SourceSpan
    cond: Node
    body: tuple[Node, ...]
    else_body: tuple[Node, ...]
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class ForLoop:
    """for 루프문."""

    source_span: SourceSpan
    var_name: str
    start: Node
    end: Node
    body: tuple[Node, ...]
    step: Node | None = None
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class HistoryRef:
    """히스토리 참조 (close[1] 형태)."""

    source_span: SourceSpan
    target: Node
    offset: Node
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class TupleReturn:
    """다중 반환값 튜플."""

    source_span: SourceSpan
    values: tuple[Node, ...]
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Program:
    """최상위 프로그램 노드."""

    source_span: SourceSpan
    version: int
    statements: tuple[Node, ...]
    annotations: dict[str, object] = field(default_factory=dict, compare=False, hash=False)
