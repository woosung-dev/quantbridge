# Pine Parser MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pine Script(v4/v5) → AST 인터프리터 파이프라인을 구현해 단순 전략(EMA Cross, SuperTrend 수준)에서 `SignalResult(entries, exits)`를 산출하고, Assignment 50개에 대한 Go/No-Go 판정 스크립트가 통과하게 한다.

**Architecture:** AST 인터프리터 (접근 1). v4는 전처리 레이어에서 v5로 기계적 변환 후 단일 v5 파이프라인 통과. stdlib은 pandas-ta 래퍼로 구현해 TradingView 재현성 확보. AST 노드는 불변(frozen dataclass) + source_span + annotations 슬롯으로 장기 확장(Python 렌더러, AI 변형) 수용.

**Tech Stack:** Python 3.11+, pandas, numpy, pandas-ta, pytest, pytest-asyncio

**Related docs:**
- Spec: `docs/superpowers/specs/2026-04-15-pine-parser-mvp-design.md`
- ADR-003: `docs/dev-log/003-pine-runtime-safety-and-parser-scope.md`
- ADR-004: `docs/dev-log/004-pine-parser-approach-selection.md`

**Working directory:** `backend/` (모든 상대 경로는 이 기준)

---

## Task 1: Pine Coverage Assignment 템플릿 문서 작성 (Phase A)

50개 TradingView 전략을 분류할 템플릿. 실제 수집은 사용자 수작업이지만, 구조와 기준을 문서로 먼저 확정.

**Files:**
- Create: `docs/01_requirements/pine-coverage-assignment.md`

- [ ] **Step 1: 템플릿 문서 작성**

````markdown
# Pine Coverage Assignment — 50개 TradingView 전략 분류

> **목적:** Pine 파서 스프린트 1의 지원 함수 우선순위와 티어별 커버리지 목표치를 데이터 기반으로 확정.
> **방법:** TradingView 커뮤니티 인기 전략 50개를 수집 → 본 문서에 메타데이터 기록 → 스프린트 1 범위 재조정.

---

## 1. 수집 기준

- TradingView 커뮤니티 `/scripts/` 에서 "Top Strategies" 또는 "Most Popular Indicators" 기반
- `strategy(...)` 선언 우선, `indicator(...)`는 부차 (시그널 추출 가능한 경우만)
- 중복 포크/변형은 제외
- 라이선스 명시된 MIT/MPL/CC-BY 등만 (재배포 아닌 분석용이라도 안전빵)

## 2. 난이도 티어 정의

| 티어 | 특징 | 예시 |
|------|------|------|
| **표준** (Standard) | 이름 있는 지표 + 단순 크로스오버/임계값 + 시간 윈도우. 커스텀 함수 없음 | EMA Cross, SuperTrend (변형 없음) |
| **중간** (Medium) | `var` 상태 + `if/else if/else` + `valuewhen` + 간단한 커스텀 수식. 커스텀 함수는 1~2개 | Moon Phases, Flawless Victory |
| **헤비** (Heavy) | 커스텀 함수 5개 이상, MTF(`request.security`), 배열 기반 상태 머신, 드로잉 집약 | DrFX Diamond Algo |

## 3. 전략 엔트리 템플릿

각 전략에 대해 아래 형식으로 추가:

```markdown
### S-01: [전략 이름]

- **원본 URL:** https://www.tradingview.com/script/...
- **저자 / 라이선스:** @username / MPL-2.0
- **Pine 버전:** v5 | v4
- **티어:** 표준 | 중간 | 헤비
- **핵심 지표:** ta.sma, ta.rsi, ta.atr
- **제어흐름:** if/else, for, ternary
- **상태 관리:** var 없음 | var + :=
- **커스텀 함수:** 없음 | `myFunc()`, `helper()`
- **주문 함수:** strategy.entry, strategy.close | strategy.exit(stop,limit)
- **시각화:** plotshape, barcolor (파서는 no-op)
- **MTF:** 없음 | request.security
- **블로커:** (스프린트 1 지원 불가 사유, 있으면 기록)
```

## 4. 집계 섹션 (50개 수집 완료 후 채움)

### 4.1 버전 분포
- v5: __개 / v4: __개

### 4.2 티어 분포
- 표준: __개 (__ %)
- 중간: __개 (__ %)
- 헤비: __개 (__ %)

### 4.3 함수 빈도 Top 20 (지원 우선순위 결정용)
| 순위 | 함수 | 빈도 | 스프린트 1 포함 여부 |
|------|------|------|---------------------|
| 1 | ta.sma | | ✅ |
| ... | | | |

### 4.4 티어별 스프린트 1 커버리지 목표
- 표준 티어: 100% (ground zero)
- 중간 티어: __% (데이터 근거 확정)
- 헤비 티어: 0% (Unsupported 처리)

### 4.5 v4→v5 변환 규칙 요구사항
- 함수 prefix 치환: `sma`→`ta.sma` 외 __종
- `input(...)` 재매핑: __건
- 기타 필요 변환: __

## 5. 수집 진행 상황

- [ ] S-01 ~ S-10 수집
- [ ] S-11 ~ S-20 수집
- [ ] S-21 ~ S-30 수집
- [ ] S-31 ~ S-40 수집
- [ ] S-41 ~ S-50 수집
- [ ] 집계 섹션 §4 채움
- [ ] 스프린트 1 범위 재조정 완료 (스펙 §2 / §7.2 업데이트)

---

> **중요:** 50개 수집이 완료되기 전에도 Task 2 이후 파서 구현은 "Ground zero" 기준(EMA Cross, SuperTrend 등 표준 티어 대표 샘플)을 가정해 진행한다. Phase A 결과가 나오면 stdlib 함수 목록과 커버리지 목표치를 조정한다.
````

- [ ] **Step 2: 커밋**

```bash
git add docs/01_requirements/pine-coverage-assignment.md
git commit -m "docs: add Pine coverage assignment template for sprint 1 parser"
```

---

## Task 2: Python 의존성 추가 (pandas, numpy, pandas-ta)

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: `pyproject.toml`의 `[project] dependencies` 섹션에 아래 항목 추가**

```toml
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "pandas-ta>=0.3.14b",
```

`[dependency-groups] dev` 섹션에 아래 항목 추가:

```toml
    "pandas-stubs>=2.2.0",
```

- [ ] **Step 2: 의존성 동기화**

Run: `cd backend && uv sync`
Expected: `Resolved N packages in X ms` (에러 없이 완료)

- [ ] **Step 3: 설치 확인**

Run: `cd backend && uv run python -c "import pandas, numpy, pandas_ta; print(pandas.__version__, numpy.__version__, pandas_ta.__version__)"`
Expected: 3개 버전 문자열 출력

- [ ] **Step 4: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(backend): add pandas/numpy/pandas-ta for pine parser"
```

---

## Task 3: pine 모듈 스켈레톤 생성

`backend/src/strategy/` 하위에 `pine/` 디렉토리를 만들고 빈 모듈 파일들을 준비.

**Files:**
- Create: `backend/src/strategy/pine/__init__.py`
- Create: `backend/src/strategy/pine/errors.py`
- Create: `backend/src/strategy/pine/types.py`
- Create: `backend/src/strategy/pine/ast_nodes.py`
- Create: `backend/src/strategy/pine/v4_to_v5.py`
- Create: `backend/src/strategy/pine/lexer.py`
- Create: `backend/src/strategy/pine/parser.py`
- Create: `backend/src/strategy/pine/stdlib.py`
- Create: `backend/src/strategy/pine/interpreter.py`
- Create: `backend/tests/strategy/__init__.py`
- Create: `backend/tests/strategy/pine/__init__.py`

- [ ] **Step 1: 디렉토리 + 빈 파일 생성**

```bash
cd backend
mkdir -p src/strategy/pine tests/strategy/pine
touch src/strategy/pine/__init__.py \
      src/strategy/pine/errors.py \
      src/strategy/pine/types.py \
      src/strategy/pine/ast_nodes.py \
      src/strategy/pine/v4_to_v5.py \
      src/strategy/pine/lexer.py \
      src/strategy/pine/parser.py \
      src/strategy/pine/stdlib.py \
      src/strategy/pine/interpreter.py \
      tests/strategy/__init__.py \
      tests/strategy/pine/__init__.py
```

- [ ] **Step 2: `src/strategy/pine/__init__.py`에 공개 API 플레이스홀더 작성**

```python
"""Pine Script parser and interpreter (AST-based, no exec/eval)."""
# 공개 API는 Task 22(parse_and_run)에서 추가된다.
```

- [ ] **Step 3: import 검증**

Run: `cd backend && uv run python -c "from src.strategy import pine; print(pine.__doc__)"`
Expected: 위 docstring 출력

- [ ] **Step 4: 커밋**

```bash
git add backend/src/strategy/pine backend/tests/strategy
git commit -m "feat(strategy/pine): scaffold module directory"
```

---

## Task 4: 예외 계층 작성 (`errors.py`)

**Files:**
- Create: `backend/tests/strategy/pine/test_errors.py`
- Modify: `backend/src/strategy/pine/errors.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/strategy/pine/test_errors.py`:

```python
"""PineError 예외 계층 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.errors import (
    PineError,
    PineLexError,
    PineParseError,
    PineRuntimeError,
    PineUnsupportedError,
)


def test_pine_error_is_exception():
    assert issubclass(PineError, Exception)


def test_pine_lex_error_inherits_pine_error():
    assert issubclass(PineLexError, PineError)


def test_pine_parse_error_inherits_pine_error():
    assert issubclass(PineParseError, PineError)


def test_pine_runtime_error_inherits_pine_error():
    assert issubclass(PineRuntimeError, PineError)


def test_pine_unsupported_error_has_feature_and_category():
    err = PineUnsupportedError(
        "ta.vwma not supported",
        feature="ta.vwma",
        category="function",
        line=12,
        column=8,
    )
    assert err.feature == "ta.vwma"
    assert err.category == "function"
    assert err.line == 12
    assert err.column == 8
    assert isinstance(err, PineError)


def test_pine_unsupported_error_category_literal():
    # category는 function | syntax | type | v4_migration 중 하나
    for cat in ("function", "syntax", "type", "v4_migration"):
        err = PineUnsupportedError("x", feature="x", category=cat)
        assert err.category == cat


def test_pine_error_carries_line_column_optional():
    err = PineParseError("unexpected token", line=None, column=None)
    assert err.line is None
    assert err.column is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_errors.py -v`
Expected: `ImportError` (errors.py가 빈 상태)

- [ ] **Step 3: `errors.py` 구현**

```python
"""Pine 파서/인터프리터 전용 예외 계층.

모든 예외는 PineError를 상속. line/column은 소스 위치 추적용 (모를 때 None).
"""
from __future__ import annotations

from typing import Literal

UnsupportedCategory = Literal["function", "syntax", "type", "v4_migration"]


class PineError(Exception):
    """Pine 처리 과정의 모든 에러 베이스."""

    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.line = line
        self.column = column


class PineLexError(PineError):
    """토큰화 실패 (잘못된 문자, 닫히지 않은 문자열 등)."""


class PineParseError(PineError):
    """문법 오류 (예상 토큰 불일치)."""


class PineUnsupportedError(PineError):
    """ADR-003 핵심: 지원 범위 밖. 호출부는 즉시 실행을 중단해야 한다."""

    def __init__(
        self,
        message: str,
        *,
        feature: str,
        category: UnsupportedCategory,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message, line=line, column=column)
        self.feature = feature
        self.category: UnsupportedCategory = category


class PineRuntimeError(PineError):
    """지원 함수 실행 중 런타임 예외 (0 나누기, 타입 불일치 등)."""
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_errors.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/errors.py backend/tests/strategy/pine/test_errors.py
git commit -m "feat(strategy/pine): add exception hierarchy (errors.py)"
```

---

## Task 5: 타입 정의 (`types.py` — SourceSpan, SignalResult, ParseOutcome)

**Files:**
- Create: `backend/tests/strategy/pine/test_types.py`
- Modify: `backend/src/strategy/pine/types.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/strategy/pine/test_types.py`:

```python
"""Pine 타입(SourceSpan, SignalResult, ParseOutcome) 테스트."""
from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine.errors import PineParseError
from src.strategy.pine.types import ParseOutcome, SignalResult, SourceSpan


def test_source_span_frozen_and_fields():
    span = SourceSpan(start_line=1, start_col=0, end_line=1, end_col=10)
    assert span.start_line == 1
    assert span.start_col == 0
    assert span.end_line == 1
    assert span.end_col == 10
    with pytest.raises(Exception):  # frozen: FrozenInstanceError
        span.start_line = 5  # type: ignore[misc]


def test_signal_result_minimal_entries_exits():
    entries = pd.Series([False, True, False])
    exits = pd.Series([False, False, True])
    sr = SignalResult(entries=entries, exits=exits)
    pd.testing.assert_series_equal(sr.entries, entries)
    pd.testing.assert_series_equal(sr.exits, exits)
    assert sr.direction is None
    assert sr.sl_stop is None
    assert sr.tp_limit is None
    assert sr.position_size is None
    assert sr.metadata == {}


def test_signal_result_fields_frozen_field_names_match_vectorbt():
    # vectorbt Portfolio.from_signals() 파라미터와 1:1 대응 확인
    expected_fields = {
        "entries",
        "exits",
        "direction",
        "sl_stop",
        "tp_limit",
        "position_size",
        "metadata",
    }
    import dataclasses

    actual = {f.name for f in dataclasses.fields(SignalResult)}
    assert expected_fields <= actual


def test_parse_outcome_ok_status():
    entries = pd.Series([True])
    exits = pd.Series([False])
    sr = SignalResult(entries=entries, exits=exits)
    outcome = ParseOutcome(
        status="ok",
        result=sr,
        error=None,
        supported_feature_report={"functions_used": ["ta.sma"]},
        source_version="v5",
    )
    assert outcome.status == "ok"
    assert outcome.result is sr
    assert outcome.error is None
    assert outcome.source_version == "v5"


def test_parse_outcome_unsupported_status():
    outcome = ParseOutcome(
        status="unsupported",
        result=None,
        error=None,
        supported_feature_report={},
        source_version="v4",
    )
    assert outcome.status == "unsupported"
    assert outcome.result is None


def test_parse_outcome_error_status_carries_exception():
    err = PineParseError("bad syntax", line=3, column=0)
    outcome = ParseOutcome(
        status="error",
        result=None,
        error=err,
        supported_feature_report={},
        source_version="v5",
    )
    assert outcome.error is err
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_types.py -v`
Expected: `ImportError`

- [ ] **Step 3: `types.py` 구현**

```python
"""Pine 파서/인터프리터 타입 정의.

- SourceSpan: AST 노드가 원본 소스에서 차지하는 영역 (에러/역출력용).
- SignalResult: 인터프리터 산출물. 필드는 vectorbt Portfolio.from_signals() 파라미터와
  1:1 대응하도록 선언 (스프린트 1에선 entries/exits만 채움).
- ParseOutcome: API 경계에서 사용자에게 전달되는 최종 결과 객체.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from src.strategy.pine.errors import PineError


@dataclass(frozen=True)
class SourceSpan:
    """원본 소스의 위치 정보 (0-based line/col)."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass
class SignalResult:
    """인터프리터 산출물.

    스프린트 1: entries/exits만 채움. 나머지 필드는 None으로 선언만 (vectorbt 호환
    스키마를 먼저 얼려 다음 스프린트 통합 시 API 경계 변동 방지).
    """

    entries: pd.Series
    exits: pd.Series
    direction: pd.Series | None = None
    sl_stop: pd.Series | None = None
    tp_limit: pd.Series | None = None
    position_size: pd.Series | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseOutcome:
    """API 경계 반환 형태. status로 성공/미지원/에러 분기."""

    status: Literal["ok", "unsupported", "error"]
    result: SignalResult | None
    error: PineError | None
    supported_feature_report: dict[str, Any]
    source_version: Literal["v4", "v5"]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_types.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/types.py backend/tests/strategy/pine/test_types.py
git commit -m "feat(strategy/pine): add SourceSpan, SignalResult, ParseOutcome types"
```

---

## Task 6: AST 노드 정의 (`ast_nodes.py`)

모든 핵심 AST 노드를 frozen dataclass로 정의. 공통 필드는 각 노드에 직접 선언 (상속 대신 mixin 또는 반복 — frozen dataclass 상속이 까다로워 직접 선언 방식 채택).

**Files:**
- Create: `backend/tests/strategy/pine/test_ast_nodes.py`
- Modify: `backend/src/strategy/pine/ast_nodes.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/strategy/pine/test_ast_nodes.py`:

```python
"""AST 노드 타입 테스트."""
from __future__ import annotations

import dataclasses

import pytest

from src.strategy.pine.ast_nodes import (
    Assign,
    BinOp,
    FnCall,
    ForLoop,
    HistoryRef,
    Ident,
    IfExpr,
    IfStmt,
    Literal,
    Program,
    TupleReturn,
    VarDecl,
)
from src.strategy.pine.types import SourceSpan

SPAN = SourceSpan(0, 0, 0, 0)


def test_literal_node():
    node = Literal(source_span=SPAN, value=42)
    assert node.value == 42
    assert node.source_span is SPAN
    assert node.annotations == {}


def test_ident_node():
    node = Ident(source_span=SPAN, name="close")
    assert node.name == "close"


def test_binop_node():
    left = Literal(source_span=SPAN, value=1)
    right = Literal(source_span=SPAN, value=2)
    node = BinOp(source_span=SPAN, op="+", left=left, right=right)
    assert node.op == "+"
    assert node.left is left
    assert node.right is right


def test_fncall_node_with_kwargs():
    node = FnCall(
        source_span=SPAN,
        name="ta.sma",
        args=(Ident(source_span=SPAN, name="close"), Literal(source_span=SPAN, value=14)),
        kwargs=(),
    )
    assert node.name == "ta.sma"
    assert len(node.args) == 2
    assert node.kwargs == ()


def test_var_decl_node():
    expr = Literal(source_span=SPAN, value=1)
    node = VarDecl(source_span=SPAN, name="x", is_var=False, type_hint=None, expr=expr)
    assert node.name == "x"
    assert node.is_var is False
    assert node.expr is expr


def test_var_decl_with_var_keyword():
    expr = Literal(source_span=SPAN, value=0.0)
    node = VarDecl(source_span=SPAN, name="counter", is_var=True, type_hint="float", expr=expr)
    assert node.is_var is True
    assert node.type_hint == "float"


def test_assign_node_supports_walrus():
    target = Ident(source_span=SPAN, name="x")
    value = Literal(source_span=SPAN, value=5)
    node = Assign(source_span=SPAN, target=target, op=":=", value=value)
    assert node.op == ":="
    assert node.target is target


def test_if_expr_ternary():
    cond = Literal(source_span=SPAN, value=True)
    then = Literal(source_span=SPAN, value=1)
    else_ = Literal(source_span=SPAN, value=2)
    node = IfExpr(source_span=SPAN, cond=cond, then=then, else_=else_)
    assert node.cond is cond


def test_if_stmt_with_body():
    cond = Literal(source_span=SPAN, value=True)
    body_stmt = Assign(
        source_span=SPAN,
        target=Ident(source_span=SPAN, name="x"),
        op="=",
        value=Literal(source_span=SPAN, value=1),
    )
    node = IfStmt(source_span=SPAN, cond=cond, body=(body_stmt,), else_body=())
    assert node.body == (body_stmt,)
    assert node.else_body == ()


def test_for_loop_node():
    start = Literal(source_span=SPAN, value=0)
    end = Literal(source_span=SPAN, value=10)
    body = ()
    node = ForLoop(
        source_span=SPAN,
        var_name="i",
        start=start,
        end=end,
        step=None,
        body=body,
    )
    assert node.var_name == "i"


def test_history_ref_node():
    target = Ident(source_span=SPAN, name="close")
    offset = Literal(source_span=SPAN, value=1)
    node = HistoryRef(source_span=SPAN, target=target, offset=offset)
    assert node.target is target


def test_tuple_return_node():
    a = Ident(source_span=SPAN, name="a")
    b = Ident(source_span=SPAN, name="b")
    node = TupleReturn(source_span=SPAN, values=(a, b))
    assert len(node.values) == 2


def test_program_node_holds_statements():
    stmt = VarDecl(
        source_span=SPAN, name="x", is_var=False, type_hint=None,
        expr=Literal(source_span=SPAN, value=0),
    )
    prog = Program(source_span=SPAN, version=5, statements=(stmt,))
    assert prog.version == 5
    assert prog.statements == (stmt,)


def test_all_nodes_are_frozen():
    node = Literal(source_span=SPAN, value=1)
    with pytest.raises(Exception):
        node.value = 2  # type: ignore[misc]


def test_all_nodes_have_annotations_slot():
    # annotations dict는 모든 노드에 존재해야 함 (미래 AI/변형용)
    node = Ident(source_span=SPAN, name="x")
    assert hasattr(node, "annotations")
    assert node.annotations == {}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_ast_nodes.py -v`
Expected: `ImportError`

- [ ] **Step 3: `ast_nodes.py` 구현**

```python
"""Pine AST 노드 정의.

모든 노드는 @dataclass(frozen=True)로 불변 + source_span + annotations 포함.
annotations는 현재 빈 dict지만 Phase 2+ AI 변형/전략 병합용 확장 슬롯.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from src.strategy.pine.types import SourceSpan


# 전방선언: 모든 노드의 유니온 타입
Node = Union[
    "Literal",
    "Ident",
    "BinOp",
    "FnCall",
    "Kwarg",
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
    source_span: SourceSpan
    value: Any  # int | float | str | bool | None
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Ident:
    source_span: SourceSpan
    name: str
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class BinOp:
    source_span: SourceSpan
    op: str  # "+" "-" "*" "/" "and" "or" ">" "<" ">=" "<=" "==" "!=" "%"
    left: Node
    right: Node
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Kwarg:
    source_span: SourceSpan
    name: str
    value: Node
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FnCall:
    source_span: SourceSpan
    name: str
    args: tuple[Node, ...]
    kwargs: tuple[Kwarg, ...]
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class VarDecl:
    source_span: SourceSpan
    name: str
    is_var: bool  # `var` 키워드 여부 (bar 간 상태 유지)
    type_hint: str | None
    expr: Node
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Assign:
    source_span: SourceSpan
    target: Node  # Ident 또는 HistoryRef 등
    op: str  # "=" | ":="
    value: Node
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class IfExpr:
    """Ternary: cond ? then : else_"""

    source_span: SourceSpan
    cond: Node
    then: Node
    else_: Node
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class IfStmt:
    source_span: SourceSpan
    cond: Node
    body: tuple[Node, ...]
    else_body: tuple[Node, ...]  # else if 는 IfStmt를 포함한 길이 1 튜플로 표현
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ForLoop:
    source_span: SourceSpan
    var_name: str
    start: Node
    end: Node
    step: Node | None
    body: tuple[Node, ...]
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class HistoryRef:
    """Pine의 `x[N]` — N바 전 값 참조."""

    source_span: SourceSpan
    target: Node
    offset: Node
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TupleReturn:
    """Pine의 `[a, b] = fn()` — 멀티리턴."""

    source_span: SourceSpan
    values: tuple[Node, ...]
    annotations: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Program:
    source_span: SourceSpan
    version: int  # 4 | 5 (원본 버전. v4는 전처리 후 v5로 변환되지만 이 필드는 원본 기록)
    statements: tuple[Node, ...]
    annotations: dict = field(default_factory=dict)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_ast_nodes.py -v`
Expected: 14 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/ast_nodes.py backend/tests/strategy/pine/test_ast_nodes.py
git commit -m "feat(strategy/pine): define AST node dataclasses (frozen + source_span + annotations)"
```

---

## Task 7: v4→v5 자동 변환기 (`v4_to_v5.py`)

Pine v4 소스를 v5 문법으로 기계적 치환. 주된 규칙:
- `sma(`, `ema(`, `rsi(`, `atr(`, `stdev(`, `tr`, `crossover(`, `crossunder(`, `valuewhen(`, `barssince(`, `change(`, `highest(`, `lowest(`, `pivothigh(`, `pivotlow(`, `alma(`, `wma(`, `sar(`, `obv`, `mom(`, `bb(`, `dmi(`, `cross(`, `nz(`, `na(`, `fixnan(` → `ta.` prefix 붙임
- `input(10, title="x")` → `input.int(10, title="x")` (타입 추론: int/float/bool/string)

변환기는 문자열 단위 정규식 치환 + 토큰 인식으로 안전하게 수행. `//@version=` 선언 감지 + 줄 단위 처리. 주석/문자열 리터럴 안쪽은 건드리지 않음.

**Files:**
- Create: `backend/tests/strategy/pine/test_v4_to_v5.py`
- Modify: `backend/src/strategy/pine/v4_to_v5.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Pine v4 → v5 자동 변환기 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.errors import PineUnsupportedError
from src.strategy.pine.v4_to_v5 import detect_version, normalize


def test_detect_v4_from_header():
    src = "//@version=4\nstrategy('x')\n"
    assert detect_version(src) == "v4"


def test_detect_v5_from_header():
    src = "//@version=5\nstrategy('x')\n"
    assert detect_version(src) == "v5"


def test_detect_version_defaults_v5_when_missing():
    # 헤더 누락 시 v5로 가정 (TV 최신 기본값)
    src = "strategy('x')\n"
    assert detect_version(src) == "v5"


def test_normalize_v5_passthrough():
    src = "//@version=5\nx = ta.sma(close, 20)\n"
    assert normalize(src) == src


def test_normalize_v4_header_converted():
    src = "//@version=4\nx = sma(close, 20)\n"
    out = normalize(src)
    assert "//@version=5" in out
    assert "ta.sma(close, 20)" in out


def test_normalize_v4_multiple_ta_functions():
    src = """//@version=4
a = sma(close, 14)
b = ema(close, 20)
c = rsi(close, 14)
d = atr(14)
e = crossover(a, b)
"""
    out = normalize(src)
    assert "ta.sma(close, 14)" in out
    assert "ta.ema(close, 20)" in out
    assert "ta.rsi(close, 14)" in out
    assert "ta.atr(14)" in out
    assert "ta.crossover(a, b)" in out


def test_normalize_v4_input_int_inference():
    src = '//@version=4\nlen = input(14, title="Length")\n'
    out = normalize(src)
    assert "input.int(14" in out


def test_normalize_v4_input_float_inference():
    src = '//@version=4\nmult = input(3.0, title="Mult")\n'
    out = normalize(src)
    assert "input.float(3.0" in out


def test_normalize_v4_input_bool_inference():
    src = '//@version=4\nshow = input(true, title="Show")\n'
    out = normalize(src)
    assert "input.bool(true" in out


def test_normalize_v4_input_string_inference():
    src = '//@version=4\nsym = input("BTCUSD", title="Symbol")\n'
    out = normalize(src)
    assert 'input.string("BTCUSD"' in out


def test_normalize_does_not_touch_comments():
    src = "//@version=4\n// sma(x) 이건 주석\nx = sma(close, 10)\n"
    out = normalize(src)
    # 주석 안의 sma는 그대로, 실제 코드의 sma는 ta.sma로
    assert "// sma(x) 이건 주석" in out
    assert "ta.sma(close, 10)" in out


def test_normalize_does_not_touch_string_literals():
    src = '//@version=4\nx = "sma(100)"\n'
    out = normalize(src)
    assert '"sma(100)"' in out


def test_normalize_preserves_existing_ta_prefix():
    # v4라도 이미 ta.sma로 쓰였으면 중복 변환 금지
    src = "//@version=4\nx = ta.sma(close, 14)\n"
    out = normalize(src)
    assert "ta.ta.sma" not in out
    assert "ta.sma(close, 14)" in out


def test_normalize_unknown_v4_feature_raises():
    # 변환 규칙 없는 v4 전용 기능 (예: tickerid) — 현재 범위 밖
    # 대표로 "security" 같은 난해한 v4 패턴이 들어오면 v4_migration Unsupported
    src = '//@version=4\nx = security(tickerid, "D", close)\n'
    with pytest.raises(PineUnsupportedError) as ei:
        normalize(src)
    assert ei.value.category == "v4_migration"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_v4_to_v5.py -v`
Expected: ImportError

- [ ] **Step 3: `v4_to_v5.py` 구현**

```python
"""Pine v4 → v5 자동 변환 전처리기.

규칙:
- ta.* prefix 누락 함수명에 prefix 삽입.
- input(value, ...) → value 타입 기반 input.{int|float|bool|string}(...) 변환.
- 주석/문자열 리터럴 내부는 변환 대상에서 제외.
- 변환 불가 v4 전용 기능(security, tickerid 등) 감지 시 PineUnsupportedError(v4_migration).
"""
from __future__ import annotations

import re
from typing import Literal

from src.strategy.pine.errors import PineUnsupportedError

Version = Literal["v4", "v5"]

# v4 → v5에서 ta. prefix가 필요한 함수들
_TA_FUNCTIONS = {
    "sma", "ema", "rma", "wma", "alma", "atr", "rsi", "stdev", "tr",
    "crossover", "crossunder", "cross",
    "valuewhen", "barssince", "change",
    "highest", "lowest", "pivothigh", "pivotlow",
    "sar", "obv", "mom", "bb", "dmi",
    "nz", "na", "fixnan",
}

# 현재 스프린트 1에서 자동 변환 불가로 분류한 v4 전용 기능
_UNSUPPORTED_V4_FEATURES = {
    "security",
    "tickerid",
    "request.security_lower_tf",  # v4에서 쓰이면 security로 변환 필요하지만 매핑 난해
}

_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)")


def detect_version(source: str) -> Version:
    """`//@version=N` 선언에서 버전 추출. 없으면 v5로 가정."""
    match = _VERSION_RE.search(source)
    if not match:
        return "v5"
    v = int(match.group(1))
    return "v4" if v <= 4 else "v5"


def normalize(source: str) -> str:
    """Pine 소스를 v5 호환으로 정규화.

    v5 입력은 passthrough. v4 입력은 치환 규칙 적용.
    변환 불가 감지 시 PineUnsupportedError(category='v4_migration').
    """
    version = detect_version(source)
    if version == "v5":
        return source

    # 라인 단위 처리로 주석/문자열 보호
    lines = source.splitlines(keepends=True)
    converted: list[str] = []
    for idx, line in enumerate(lines):
        converted.append(_convert_line(line, line_no=idx + 1))

    result = "".join(converted)
    # 헤더를 v5로 갱신
    result = _VERSION_RE.sub("//@version=5", result, count=1)
    return result


def _convert_line(line: str, *, line_no: int) -> str:
    """한 줄에 대해 변환 규칙 적용 (주석/문자열 내부 보호)."""
    code, trailing_comment = _split_code_and_comment(line)

    # 주석 아닌 코드 부분에만 변환 적용
    # 문자열 리터럴을 자리표시자로 빼낸 뒤 변환 → 복원
    placeholders: dict[str, str] = {}
    code_noliteral = _mask_string_literals(code, placeholders)

    # 금지된 v4 전용 기능 감지
    for feat in _UNSUPPORTED_V4_FEATURES:
        if re.search(rf"\b{re.escape(feat)}\s*\(", code_noliteral):
            raise PineUnsupportedError(
                f"v4 feature '{feat}' is not auto-convertible to v5",
                feature=feat,
                category="v4_migration",
                line=line_no,
            )

    # ta.* prefix 붙이기 (이미 ta. 로 시작하는 건 건너뜀)
    for fn in _TA_FUNCTIONS:
        pattern = rf"(?<![\w.]){re.escape(fn)}\s*\("
        code_noliteral = re.sub(pattern, f"ta.{fn}(", code_noliteral)

    # input(...) → input.{type}(...)
    code_noliteral = _convert_input_calls(code_noliteral)

    # 자리표시자 복원
    for key, original in placeholders.items():
        code_noliteral = code_noliteral.replace(key, original)

    return code_noliteral + trailing_comment


_COMMENT_RE = re.compile(r"(?<!:)//")  # URL(https://) 보호를 위해 :앞 제외


def _split_code_and_comment(line: str) -> tuple[str, str]:
    """코드와 //주석 분리 (문자열 리터럴 밖의 // 만 주석 시작으로 간주)."""
    in_string: str | None = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            if ch == "\\" and i + 1 < len(line):
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_string = ch
            i += 1
            continue
        if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            return line[:i], line[i:]
        i += 1
    return line, ""


_STR_LITERAL_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


def _mask_string_literals(code: str, placeholders: dict[str, str]) -> str:
    """문자열 리터럴을 __PINE_STR_N__ 자리표시자로 치환."""

    def repl(match: re.Match[str]) -> str:
        key = f"__PINE_STR_{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    return _STR_LITERAL_RE.sub(repl, code)


_INPUT_CALL_RE = re.compile(r"\binput\s*\(\s*([^,)]+?)\s*(,[^)]*)?\)")


def _convert_input_calls(code: str) -> str:
    """input(value, ...) → input.{type}(value, ...). 타입은 value 리터럴로 추론."""

    def repl(match: re.Match[str]) -> str:
        value = match.group(1).strip()
        rest = match.group(2) or ""
        kind = _infer_input_type(value)
        if kind is None:
            return match.group(0)  # 추론 실패 시 원본 유지 (파서가 처리)
        return f"input.{kind}({value}{rest})"

    return _INPUT_CALL_RE.sub(repl, code)


def _infer_input_type(literal: str) -> str | None:
    s = literal.strip()
    if s in ("true", "false"):
        return "bool"
    if s.startswith(("'", '"')) or s.startswith("__PINE_STR_"):
        return "string"
    try:
        if "." in s or "e" in s or "E" in s:
            float(s)
            return "float"
        int(s)
        return "int"
    except ValueError:
        return None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_v4_to_v5.py -v`
Expected: 13 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/v4_to_v5.py backend/tests/strategy/pine/test_v4_to_v5.py
git commit -m "feat(strategy/pine): add v4->v5 normalizer with ta.* prefix rules"
```

---

## Task 8: Lexer — TokenType 정의 + 토큰 데이터클래스

**Files:**
- Create: `backend/tests/strategy/pine/test_lexer_tokens.py`
- Modify: `backend/src/strategy/pine/lexer.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Lexer 토큰 데이터 구조 테스트."""
from __future__ import annotations

from src.strategy.pine.lexer import Token, TokenType


def test_token_type_has_required_members():
    required = {
        "NUMBER", "STRING", "IDENT", "KEYWORD", "OP",
        "LPAREN", "RPAREN", "LBRACKET", "RBRACKET",
        "COMMA", "DOT", "COLON", "QUESTION",
        "ASSIGN", "WALRUS",
        "NEWLINE", "INDENT", "DEDENT",
        "COMMENT", "EOF",
    }
    actual = {m.name for m in TokenType}
    assert required <= actual


def test_token_is_frozen():
    tok = Token(type=TokenType.NUMBER, value="42", line=1, column=0)
    import pytest
    with pytest.raises(Exception):
        tok.value = "x"  # type: ignore[misc]


def test_token_equality():
    a = Token(type=TokenType.IDENT, value="close", line=1, column=0)
    b = Token(type=TokenType.IDENT, value="close", line=1, column=0)
    assert a == b
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_lexer_tokens.py -v`
Expected: ImportError

- [ ] **Step 3: `lexer.py` 기초 선언 추가**

```python
"""Pine v5 Lexer.

전체 lexer는 여러 Task에 걸쳐 구현된다:
- Task 8: TokenType + Token dataclass
- Task 9: 핵심 토크나이저 (리터럴, 식별자, 연산자)
- Task 10: 인덴트/개행/주석/키워드/에러 처리
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    KEYWORD = auto()
    OP = auto()          # +, -, *, /, %, <, >, <=, >=, ==, !=, and, or, not
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    QUESTION = auto()
    ASSIGN = auto()      # =
    WALRUS = auto()      # :=
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    COMMENT = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int            # 1-based
    column: int          # 0-based
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_lexer_tokens.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/lexer.py backend/tests/strategy/pine/test_lexer_tokens.py
git commit -m "feat(strategy/pine): lexer TokenType + Token dataclass"
```

---

## Task 9: Lexer — 핵심 토크나이저 (리터럴/식별자/연산자)

**Files:**
- Create: `backend/tests/strategy/pine/test_lexer_core.py`
- Modify: `backend/src/strategy/pine/lexer.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Lexer 핵심 토큰화 테스트 (리터럴, 식별자, 연산자)."""
from __future__ import annotations

import pytest

from src.strategy.pine.errors import PineLexError
from src.strategy.pine.lexer import TokenType, tokenize


def _types(src: str) -> list[TokenType]:
    return [t.type for t in tokenize(src) if t.type not in (TokenType.NEWLINE, TokenType.EOF)]


def test_tokenize_integer():
    toks = tokenize("42")
    assert toks[0].type == TokenType.NUMBER
    assert toks[0].value == "42"


def test_tokenize_float():
    toks = tokenize("3.14")
    assert toks[0].type == TokenType.NUMBER
    assert toks[0].value == "3.14"


def test_tokenize_scientific_notation():
    toks = tokenize("2.5e10")
    assert toks[0].type == TokenType.NUMBER
    assert toks[0].value == "2.5e10"


def test_tokenize_string_double_quote():
    toks = tokenize('"hello"')
    assert toks[0].type == TokenType.STRING
    assert toks[0].value == "hello"


def test_tokenize_string_single_quote():
    toks = tokenize("'hi'")
    assert toks[0].type == TokenType.STRING
    assert toks[0].value == "hi"


def test_tokenize_identifier():
    toks = tokenize("close")
    assert toks[0].type == TokenType.IDENT
    assert toks[0].value == "close"


def test_tokenize_identifier_with_dot_namespacing():
    # ta.sma 는 IDENT "ta", DOT, IDENT "sma"로 분리
    assert _types("ta.sma") == [TokenType.IDENT, TokenType.DOT, TokenType.IDENT]


def test_tokenize_arithmetic_operators():
    assert _types("1 + 2 - 3 * 4 / 5 % 6") == [
        TokenType.NUMBER, TokenType.OP, TokenType.NUMBER,
        TokenType.OP, TokenType.NUMBER, TokenType.OP, TokenType.NUMBER,
        TokenType.OP, TokenType.NUMBER, TokenType.OP, TokenType.NUMBER,
    ]


def test_tokenize_comparison_operators():
    assert _types("a < b > c <= d >= e == f != g") == [
        TokenType.IDENT, TokenType.OP, TokenType.IDENT,
        TokenType.OP, TokenType.IDENT, TokenType.OP, TokenType.IDENT,
        TokenType.OP, TokenType.IDENT, TokenType.OP, TokenType.IDENT,
        TokenType.OP, TokenType.IDENT,
    ]


def test_tokenize_logical_operators_as_keywords():
    # and, or, not 은 KEYWORD
    assert _types("a and b or not c") == [
        TokenType.IDENT, TokenType.KEYWORD, TokenType.IDENT,
        TokenType.KEYWORD, TokenType.KEYWORD, TokenType.IDENT,
    ]


def test_tokenize_assignment_ops():
    assert _types("x = 1") == [TokenType.IDENT, TokenType.ASSIGN, TokenType.NUMBER]
    assert _types("x := 1") == [TokenType.IDENT, TokenType.WALRUS, TokenType.NUMBER]


def test_tokenize_punctuation():
    assert _types("(a, b)[0]") == [
        TokenType.LPAREN, TokenType.IDENT, TokenType.COMMA, TokenType.IDENT, TokenType.RPAREN,
        TokenType.LBRACKET, TokenType.NUMBER, TokenType.RBRACKET,
    ]


def test_tokenize_ternary_operators():
    assert _types("a ? b : c") == [
        TokenType.IDENT, TokenType.QUESTION, TokenType.IDENT, TokenType.COLON, TokenType.IDENT,
    ]


def test_tokenize_line_column_tracking():
    toks = tokenize("  close")
    ident = next(t for t in toks if t.type == TokenType.IDENT)
    assert ident.line == 1
    assert ident.column == 2


def test_tokenize_unterminated_string_raises():
    with pytest.raises(PineLexError):
        tokenize('"no_close')


def test_tokenize_invalid_character_raises():
    with pytest.raises(PineLexError):
        tokenize("x = @")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_lexer_core.py -v`
Expected: ImportError (`tokenize`가 아직 없음)

- [ ] **Step 3: `lexer.py`에 토크나이저 구현 추가**

기존 파일 끝에 아래 내용 추가:

```python
from src.strategy.pine.errors import PineLexError


# Pine v5 예약 키워드 (KEYWORD로 분류됨 — parser에서 구분 처리)
_KEYWORDS = {
    "and", "or", "not",
    "if", "else",
    "for", "to", "by",
    "while",
    "true", "false",
    "var", "varip",
    "import", "export",
    "switch", "case",
}

# 단일 글자 토큰 맵
_SINGLE_CHAR = {
    "(": "LPAREN", ")": "RPAREN",
    "[": "LBRACKET", "]": "RBRACKET",
    ",": "COMMA", ".": "DOT",
    "?": "QUESTION",
    "+": "OP", "-": "OP", "*": "OP", "/": "OP", "%": "OP",
}


def tokenize(source: str) -> list[Token]:
    """Pine v5 소스를 토큰 리스트로 변환.

    인덴트/주석/키워드는 Task 10에서 추가된다.
    이 Task에선 기본 리터럴·식별자·연산자·구두점만.
    """
    tokens: list[Token] = []
    i = 0
    line = 1
    line_start = 0  # 현재 라인의 시작 인덱스 (column 계산용)

    while i < len(source):
        ch = source[i]
        col = i - line_start

        # 공백 (개행 제외)
        if ch in (" ", "\t"):
            i += 1
            continue

        # 개행
        if ch == "\n":
            tokens.append(Token(TokenType.NEWLINE, "\\n", line, col))
            line += 1
            line_start = i + 1
            i += 1
            continue

        # 숫자
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

        # 문자열 리터럴
        if ch in ("'", '"'):
            quote = ch
            j = i + 1
            while j < len(source) and source[j] != quote:
                if source[j] == "\\" and j + 1 < len(source):
                    j += 2
                    continue
                if source[j] == "\n":
                    raise PineLexError(
                        "unterminated string literal", line=line, column=col
                    )
                j += 1
            if j >= len(source):
                raise PineLexError(
                    "unterminated string literal", line=line, column=col
                )
            tokens.append(Token(TokenType.STRING, source[i + 1:j], line, col))
            i = j + 1
            continue

        # 식별자 / 키워드
        if ch.isalpha() or ch == "_":
            j = i
            while j < len(source) and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            tt = TokenType.KEYWORD if word in _KEYWORDS else TokenType.IDENT
            tokens.append(Token(tt, word, line, col))
            i = j
            continue

        # 2글자 연산자 우선
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
                    "standalone '!' is not valid (use '!=')", line=line, column=col
                )

        # 단일 글자 토큰
        if ch in _SINGLE_CHAR:
            tt_name = _SINGLE_CHAR[ch]
            tokens.append(Token(TokenType[tt_name], ch, line, col))
            i += 1
            continue

        raise PineLexError(f"unexpected character: {ch!r}", line=line, column=col)

    tokens.append(Token(TokenType.EOF, "", line, i - line_start))
    return tokens
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_lexer_core.py -v`
Expected: 16 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/lexer.py backend/tests/strategy/pine/test_lexer_core.py
git commit -m "feat(strategy/pine): lexer — literals, identifiers, operators, punctuation"
```

---

## Task 10: Lexer — 주석 + 인덴트/데덴트 + 키워드

Pine v5의 블록 구조는 들여쓰기 기반이다 (Python처럼). 주석은 `//`로 시작. 이 Task에서 INDENT/DEDENT 토큰 생성 + 주석 처리를 추가.

**Files:**
- Create: `backend/tests/strategy/pine/test_lexer_indent.py`
- Modify: `backend/src/strategy/pine/lexer.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_lexer_indent.py -v`
Expected: 일부 fail (INDENT/DEDENT 미구현, 주석 처리 미구현)

- [ ] **Step 3: `lexer.py` 수정 — 주석 스킵 + 인덴트 추적**

`tokenize` 함수의 while 루프 진입 직전에 인덴트 상태 변수를 추가하고, 주석/인덴트 처리 로직을 삽입. 아래처럼 전면 수정:

```python
def tokenize(source: str) -> list[Token]:
    """Pine v5 소스를 토큰 리스트로 변환.

    주석은 스킵. 들여쓰기는 INDENT/DEDENT 토큰으로 변환 (Python 스타일).
    """
    tokens: list[Token] = []
    i = 0
    line = 1
    line_start = 0
    at_line_start = True
    indent_stack: list[int] = [0]

    while i < len(source):
        ch = source[i]
        col = i - line_start

        # 라인 시작 시 인덴트 계산
        if at_line_start:
            # 빈 줄/주석만 있는 줄은 인덴트 계산 제외
            j = i
            while j < len(source) and source[j] in (" ", "\t"):
                j += 1
            if j >= len(source) or source[j] == "\n":
                # 빈 줄
                i = j
                if i < len(source) and source[i] == "\n":
                    tokens.append(Token(TokenType.NEWLINE, "\\n", line, 0))
                    line += 1
                    line_start = i + 1
                    i += 1
                at_line_start = True
                continue
            # 주석만 있는 줄
            if j + 1 < len(source) and source[j] == "/" and source[j + 1] == "/":
                # 주석 끝까지 스킵
                while j < len(source) and source[j] != "\n":
                    j += 1
                i = j
                if i < len(source) and source[i] == "\n":
                    line += 1
                    line_start = i + 1
                    i += 1
                at_line_start = True
                continue
            # 실제 인덴트 레벨 계산 (탭을 공백 4개로 취급)
            indent_width = 0
            k = i
            while k < j:
                indent_width += 4 if source[k] == "\t" else 1
                k += 1
            if indent_width > indent_stack[-1]:
                indent_stack.append(indent_width)
                tokens.append(Token(TokenType.INDENT, "", line, 0))
            while indent_width < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(Token(TokenType.DEDENT, "", line, 0))
            i = j
            at_line_start = False
            continue

        # 주석 (인라인)
        if ch == "/" and i + 1 < len(source) and source[i + 1] == "/":
            while i < len(source) and source[i] != "\n":
                i += 1
            continue

        # 공백
        if ch in (" ", "\t"):
            i += 1
            continue

        # 개행
        if ch == "\n":
            tokens.append(Token(TokenType.NEWLINE, "\\n", line, col))
            line += 1
            line_start = i + 1
            i += 1
            at_line_start = True
            continue

        # 숫자
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

        # 문자열
        if ch in ("'", '"'):
            quote = ch
            j = i + 1
            while j < len(source) and source[j] != quote:
                if source[j] == "\\" and j + 1 < len(source):
                    j += 2
                    continue
                if source[j] == "\n":
                    raise PineLexError(
                        "unterminated string literal", line=line, column=col
                    )
                j += 1
            if j >= len(source):
                raise PineLexError(
                    "unterminated string literal", line=line, column=col
                )
            tokens.append(Token(TokenType.STRING, source[i + 1:j], line, col))
            i = j + 1
            continue

        # 식별자 / 키워드
        if ch.isalpha() or ch == "_":
            j = i
            while j < len(source) and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            tt = TokenType.KEYWORD if word in _KEYWORDS else TokenType.IDENT
            tokens.append(Token(tt, word, line, col))
            i = j
            continue

        # 2글자 연산자
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
                    "standalone '!' is not valid (use '!=')", line=line, column=col
                )

        # 단일 글자
        if ch in _SINGLE_CHAR:
            tt_name = _SINGLE_CHAR[ch]
            tokens.append(Token(TokenType[tt_name], ch, line, col))
            i += 1
            continue

        raise PineLexError(f"unexpected character: {ch!r}", line=line, column=col)

    # 종료 시 남은 인덴트 해소
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token(TokenType.DEDENT, "", line, 0))
    tokens.append(Token(TokenType.EOF, "", line, i - line_start))
    return tokens
```

- [ ] **Step 4: 기존 core 테스트 + 신규 indent 테스트 모두 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_lexer_core.py tests/strategy/pine/test_lexer_indent.py -v`
Expected: 모두 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/lexer.py backend/tests/strategy/pine/test_lexer_indent.py
git commit -m "feat(strategy/pine): lexer — comments + indent/dedent + keyword detection"
```

---

## Task 11: Parser — 표현식 파싱 (리터럴, 식별자, 이항연산, 히스토리 참조)

재귀 하강 파서. 이 Task는 표현식(expression) 수준만 다룬다. 연산자 우선순위:

```
or
and
not
== !=
< <= > >=
+ -
* / %
unary -
history_ref [N]
primary (literal | ident | paren | fncall)
```

**Files:**
- Create: `backend/tests/strategy/pine/test_parser_expr.py`
- Modify: `backend/src/strategy/pine/parser.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Parser 표현식 파싱 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.ast_nodes import (
    BinOp,
    FnCall,
    HistoryRef,
    Ident,
    IfExpr,
    Literal,
)
from src.strategy.pine.errors import PineParseError
from src.strategy.pine.parser import parse_expression
from src.strategy.pine.lexer import tokenize


def _expr(src: str):
    tokens = tokenize(src)
    return parse_expression(tokens)


def test_parse_integer_literal():
    node = _expr("42")
    assert isinstance(node, Literal)
    assert node.value == 42


def test_parse_float_literal():
    node = _expr("3.14")
    assert isinstance(node, Literal)
    assert node.value == 3.14


def test_parse_string_literal():
    node = _expr('"hello"')
    assert isinstance(node, Literal)
    assert node.value == "hello"


def test_parse_true_false_literal():
    assert _expr("true").value is True
    assert _expr("false").value is False


def test_parse_identifier():
    node = _expr("close")
    assert isinstance(node, Ident)
    assert node.name == "close"


def test_parse_dotted_identifier():
    # ta.sma는 FnCall name="ta.sma"가 아닌 이름 조립 규칙
    # 단독 식별자로는 "ta.sma" 가 Ident(name="ta.sma")로 파싱
    node = _expr("ta.sma")
    assert isinstance(node, Ident)
    assert node.name == "ta.sma"


def test_parse_addition():
    node = _expr("1 + 2")
    assert isinstance(node, BinOp)
    assert node.op == "+"
    assert isinstance(node.left, Literal) and node.left.value == 1
    assert isinstance(node.right, Literal) and node.right.value == 2


def test_parse_precedence_multiply_before_add():
    # 1 + 2 * 3 → (1 + (2 * 3))
    node = _expr("1 + 2 * 3")
    assert isinstance(node, BinOp)
    assert node.op == "+"
    assert isinstance(node.right, BinOp)
    assert node.right.op == "*"


def test_parse_precedence_comparison_vs_arithmetic():
    # a + b < c → ((a + b) < c)
    node = _expr("a + b < c")
    assert isinstance(node, BinOp)
    assert node.op == "<"


def test_parse_logical_and_lower_than_comparison():
    # a < b and c < d → ((a < b) and (c < d))
    node = _expr("a < b and c < d")
    assert isinstance(node, BinOp)
    assert node.op == "and"


def test_parse_paren_grouping():
    # (1 + 2) * 3
    node = _expr("(1 + 2) * 3")
    assert isinstance(node, BinOp)
    assert node.op == "*"
    assert isinstance(node.left, BinOp)
    assert node.left.op == "+"


def test_parse_ternary_if_expr():
    node = _expr("a > b ? 1 : 2")
    assert isinstance(node, IfExpr)


def test_parse_history_reference():
    node = _expr("close[1]")
    assert isinstance(node, HistoryRef)
    assert isinstance(node.target, Ident)
    assert isinstance(node.offset, Literal)
    assert node.offset.value == 1


def test_parse_fncall_no_args():
    node = _expr("bar_index()")
    assert isinstance(node, FnCall)
    assert node.name == "bar_index"
    assert node.args == ()


def test_parse_fncall_positional_args():
    node = _expr("ta.sma(close, 20)")
    assert isinstance(node, FnCall)
    assert node.name == "ta.sma"
    assert len(node.args) == 2


def test_parse_fncall_with_named_args():
    node = _expr('input.int(10, title="Len")')
    assert isinstance(node, FnCall)
    assert len(node.kwargs) == 1
    assert node.kwargs[0].name == "title"


def test_parse_nested_fncall():
    node = _expr("ta.crossover(close, ta.sma(close, 20))")
    assert isinstance(node, FnCall)
    assert node.name == "ta.crossover"
    assert isinstance(node.args[1], FnCall)


def test_parse_unary_minus():
    # -close → BinOp(-, 0, close) 또는 UnaryOp. 여기선 BinOp(op="-", left=Literal(0), right=Ident) 로 정규화
    node = _expr("-close")
    assert isinstance(node, BinOp)
    assert node.op == "-"
    assert isinstance(node.left, Literal) and node.left.value == 0


def test_parse_error_on_unexpected_token():
    with pytest.raises(PineParseError):
        _expr("1 + * 2")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_parser_expr.py -v`
Expected: ImportError

- [ ] **Step 3: `parser.py` 구현**

```python
"""Pine v5 재귀 하강 파서.

연산자 우선순위 (낮음 → 높음):
  or, and, not, == !=, < <= > >=, + -, * / %, unary -, history [N], primary
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
    TupleReturn,
    VarDecl,
)
from src.strategy.pine.errors import PineParseError, PineUnsupportedError
from src.strategy.pine.lexer import Token, TokenType
from src.strategy.pine.types import SourceSpan


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    # --- 공통 유틸 ---
    def peek(self, offset: int = 0) -> Token:
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def match(self, tt: TokenType, value: str | None = None) -> bool:
        tok = self.peek()
        if tok.type != tt:
            return False
        if value is not None and tok.value != value:
            return False
        return True

    def consume(self, tt: TokenType, value: str | None = None) -> Token:
        if not self.match(tt, value):
            tok = self.peek()
            raise PineParseError(
                f"expected {tt.name}{' ' + value if value else ''}, got {tok.type.name} {tok.value!r}",
                line=tok.line,
                column=tok.column,
            )
        return self.advance()

    def span_of(self, start: Token, end: Token | None = None) -> SourceSpan:
        end_tok = end or start
        return SourceSpan(start.line, start.column, end_tok.line, end_tok.column + len(end_tok.value))

    # 개행/인덴트 토큰은 표현식 파싱에서 일반적으로 무시할 수 있도록 스킵
    def skip_newlines(self) -> None:
        while self.peek().type == TokenType.NEWLINE:
            self.advance()

    # --- 표현식 파싱 (최상위 = 삼항) ---
    def parse_expression(self) -> Node:
        return self._ternary()

    def _ternary(self) -> Node:
        cond = self._or()
        if self.match(TokenType.QUESTION):
            start = self.advance()
            then_ = self._ternary()
            self.consume(TokenType.COLON)
            else_ = self._ternary()
            return IfExpr(
                source_span=self.span_of(start),
                cond=cond,
                then=then_,
                else_=else_,
            )
        return cond

    def _or(self) -> Node:
        left = self._and()
        while self.match(TokenType.KEYWORD, "or"):
            op_tok = self.advance()
            right = self._and()
            left = BinOp(
                source_span=self.span_of(op_tok),
                op="or",
                left=left,
                right=right,
            )
        return left

    def _and(self) -> Node:
        left = self._not()
        while self.match(TokenType.KEYWORD, "and"):
            op_tok = self.advance()
            right = self._not()
            left = BinOp(
                source_span=self.span_of(op_tok),
                op="and",
                left=left,
                right=right,
            )
        return left

    def _not(self) -> Node:
        if self.match(TokenType.KEYWORD, "not"):
            op_tok = self.advance()
            operand = self._not()
            # not은 BinOp(op="not", left=Literal(True), right=operand)로 정규화
            return BinOp(
                source_span=self.span_of(op_tok),
                op="not",
                left=Literal(source_span=self.span_of(op_tok), value=True),
                right=operand,
            )
        return self._equality()

    def _equality(self) -> Node:
        left = self._comparison()
        while self.match(TokenType.OP) and self.peek().value in ("==", "!="):
            op_tok = self.advance()
            right = self._comparison()
            left = BinOp(
                source_span=self.span_of(op_tok),
                op=op_tok.value,
                left=left,
                right=right,
            )
        return left

    def _comparison(self) -> Node:
        left = self._additive()
        while self.match(TokenType.OP) and self.peek().value in ("<", ">", "<=", ">="):
            op_tok = self.advance()
            right = self._additive()
            left = BinOp(
                source_span=self.span_of(op_tok),
                op=op_tok.value,
                left=left,
                right=right,
            )
        return left

    def _additive(self) -> Node:
        left = self._multiplicative()
        while self.match(TokenType.OP) and self.peek().value in ("+", "-"):
            op_tok = self.advance()
            right = self._multiplicative()
            left = BinOp(
                source_span=self.span_of(op_tok),
                op=op_tok.value,
                left=left,
                right=right,
            )
        return left

    def _multiplicative(self) -> Node:
        left = self._unary()
        while self.match(TokenType.OP) and self.peek().value in ("*", "/", "%"):
            op_tok = self.advance()
            right = self._unary()
            left = BinOp(
                source_span=self.span_of(op_tok),
                op=op_tok.value,
                left=left,
                right=right,
            )
        return left

    def _unary(self) -> Node:
        if self.match(TokenType.OP, "-"):
            op_tok = self.advance()
            operand = self._unary()
            # -x → (0 - x)
            return BinOp(
                source_span=self.span_of(op_tok),
                op="-",
                left=Literal(source_span=self.span_of(op_tok), value=0),
                right=operand,
            )
        return self._postfix()

    def _postfix(self) -> Node:
        node = self._primary()
        while self.match(TokenType.LBRACKET):
            lb = self.advance()
            offset = self.parse_expression()
            self.consume(TokenType.RBRACKET)
            node = HistoryRef(
                source_span=self.span_of(lb),
                target=node,
                offset=offset,
            )
        return node

    def _primary(self) -> Node:
        tok = self.peek()
        if tok.type == TokenType.NUMBER:
            self.advance()
            value: int | float = float(tok.value) if ("." in tok.value or "e" in tok.value.lower()) else int(tok.value)
            return Literal(source_span=self.span_of(tok), value=value)
        if tok.type == TokenType.STRING:
            self.advance()
            return Literal(source_span=self.span_of(tok), value=tok.value)
        if tok.type == TokenType.KEYWORD and tok.value in ("true", "false"):
            self.advance()
            return Literal(source_span=self.span_of(tok), value=(tok.value == "true"))
        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return expr
        if tok.type == TokenType.IDENT:
            # 식별자 조립: a.b.c
            parts = [self.advance().value]
            while self.match(TokenType.DOT):
                self.advance()
                ident_tok = self.consume(TokenType.IDENT)
                parts.append(ident_tok.value)
            name = ".".join(parts)
            ident_span = self.span_of(tok)
            # 함수 호출 여부
            if self.match(TokenType.LPAREN):
                return self._parse_fncall(name, ident_span)
            return Ident(source_span=ident_span, name=name)
        raise PineParseError(
            f"unexpected token {tok.type.name} {tok.value!r} in expression",
            line=tok.line,
            column=tok.column,
        )

    def _parse_fncall(self, name: str, span: SourceSpan) -> FnCall:
        self.consume(TokenType.LPAREN)
        args: list[Node] = []
        kwargs: list[Kwarg] = []
        if not self.match(TokenType.RPAREN):
            while True:
                # named arg: IDENT '=' expr
                if (
                    self.peek().type == TokenType.IDENT
                    and self.peek(1).type == TokenType.ASSIGN
                ):
                    name_tok = self.advance()
                    self.advance()  # =
                    value = self.parse_expression()
                    kwargs.append(
                        Kwarg(
                            source_span=self.span_of(name_tok),
                            name=name_tok.value,
                            value=value,
                        )
                    )
                else:
                    args.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    self.advance()
                    continue
                break
        self.consume(TokenType.RPAREN)
        return FnCall(
            source_span=span,
            name=name,
            args=tuple(args),
            kwargs=tuple(kwargs),
        )


def parse_expression(tokens: list[Token]) -> Node:
    """토큰 리스트에서 단일 표현식 파싱 (테스트/외부용 헬퍼)."""
    p = _Parser(tokens)
    p.skip_newlines()
    return p.parse_expression()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_parser_expr.py -v`
Expected: 18 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/parser.py backend/tests/strategy/pine/test_parser_expr.py
git commit -m "feat(strategy/pine): parser — expressions (literals/binops/ternary/history/fncall)"
```

---

## Task 12: Parser — 문(statement) + 프로그램 파싱

변수 선언, 할당, if 문, for 루프, 그리고 최상위 `parse(tokens) -> Program`.

**Files:**
- Create: `backend/tests/strategy/pine/test_parser_stmt.py`
- Modify: `backend/src/strategy/pine/parser.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Parser 문(statement) 파싱 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.ast_nodes import (
    Assign,
    FnCall,
    ForLoop,
    IfStmt,
    Literal,
    Program,
    VarDecl,
)
from src.strategy.pine.errors import PineParseError, PineUnsupportedError
from src.strategy.pine.parser import parse
from src.strategy.pine.lexer import tokenize


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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_parser_stmt.py -v`
Expected: fail/error (parse 미구현)

- [ ] **Step 3: `parser.py`에 문 파싱 로직 추가**

기존 `_Parser` 클래스에 메서드 추가 + 최상위 `parse()` 함수 추가. 파일 끝에 아래 내용 추가:

```python
# --- _Parser 클래스에 아래 메서드들 추가 ---

    def parse_program(self) -> Program:
        # 버전 검출: lexer가 주석을 버리므로 원본에서 정규식으로 뽑아야 하지만,
        # 여기선 v5 고정 (v4 변환은 외부 레이어 책임)
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
                start_tok.line, start_tok.column,
                end_tok.line, end_tok.column,
            ),
            version=5,
            statements=tuple(statements),
        )

    def _parse_statement(self) -> Node:
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
        # var 선언
        if tok.type == TokenType.KEYWORD and tok.value in ("var", "varip"):
            return self._parse_var_decl(is_var=True)
        # 그 외: 식별자로 시작하면 var_decl | assign | fncall 중 하나
        if tok.type == TokenType.IDENT:
            return self._parse_ident_statement()
        # 독립 표현식 (드물지만 허용)
        return self.parse_expression()

    def _parse_var_decl(self, *, is_var: bool) -> VarDecl:
        start = self.advance() if is_var else self.peek()
        # 선택적 타입 힌트
        type_hint: str | None = None
        if is_var and self.peek().type == TokenType.IDENT and self.peek(1).type == TokenType.IDENT:
            type_hint = self.advance().value
        name_tok = self.consume(TokenType.IDENT)
        self.consume(TokenType.ASSIGN)
        expr = self.parse_expression()
        return VarDecl(
            source_span=self.span_of(start),
            name=name_tok.value,
            is_var=is_var,
            type_hint=type_hint,
            expr=expr,
        )

    def _parse_ident_statement(self) -> Node:
        """IDENT로 시작하는 문 — 다음 토큰으로 분기:
        - `=`      → VarDecl
        - `:=`     → Assign (walrus)
        - `(`      → FnCall (부수효과, statement로 취급)
        - `.`      → 점 접근 후 위 중 하나
        """
        # 식별자 조립 (a.b.c)
        start = self.peek()
        parts = [self.advance().value]
        while self.match(TokenType.DOT):
            self.advance()
            parts.append(self.consume(TokenType.IDENT).value)
        name = ".".join(parts)
        span = self.span_of(start)

        # `(` → FnCall statement
        if self.match(TokenType.LPAREN):
            return self._parse_fncall(name, span)

        # `=` → VarDecl (단, 이미 존재하는 변수라도 파서 레벨에선 VarDecl로 표현; 인터프리터가 구분)
        if self.match(TokenType.ASSIGN):
            self.advance()
            expr = self.parse_expression()
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
            expr = self.parse_expression()
            return Assign(
                source_span=span,
                target=Ident(source_span=span, name=name),
                op=":=",
                value=expr,
            )

        # 그 외 → 이미 조립한 식별자를 표현식 시작으로 간주하기 어려우니 에러
        tok = self.peek()
        raise PineParseError(
            f"expected '=' ':=' or '(' after identifier '{name}', got {tok.value!r}",
            line=tok.line,
            column=tok.column,
        )

    def _parse_if_stmt(self) -> IfStmt:
        if_tok = self.advance()  # 'if'
        cond = self.parse_expression()
        self.skip_newlines()
        body = self._parse_block()
        else_body: tuple[Node, ...] = ()
        if self.match(TokenType.KEYWORD, "else"):
            self.advance()
            if self.match(TokenType.KEYWORD, "if"):
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
        for_tok = self.advance()  # 'for'
        var_name = self.consume(TokenType.IDENT).value
        self.consume(TokenType.ASSIGN)
        start = self.parse_expression()
        self.consume(TokenType.KEYWORD, "to")
        end = self.parse_expression()
        step: Node | None = None
        if self.match(TokenType.KEYWORD, "by"):
            self.advance()
            step = self.parse_expression()
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

    def _parse_block(self) -> tuple[Node, ...]:
        """INDENT ... DEDENT 블록."""
        if not self.match(TokenType.INDENT):
            # 한 줄 블록은 미지원 (들여쓰기 필수로 강제)
            tok = self.peek()
            raise PineParseError(
                "expected indented block",
                line=tok.line,
                column=tok.column,
            )
        self.advance()  # INDENT
        statements: list[Node] = []
        while not self.match(TokenType.DEDENT) and self.peek().type != TokenType.EOF:
            statements.append(self._parse_statement())
            self.skip_newlines()
        if self.match(TokenType.DEDENT):
            self.advance()
        return tuple(statements)


def parse(tokens: list[Token]) -> Program:
    """최상위 파서 엔트리포인트."""
    p = _Parser(tokens)
    return p.parse_program()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_parser_stmt.py tests/strategy/pine/test_parser_expr.py -v`
Expected: 모두 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/parser.py backend/tests/strategy/pine/test_parser_stmt.py
git commit -m "feat(strategy/pine): parser — statements, if/else, for, var_decl, walrus assign"
```

---

## Task 13: Stdlib — 화이트리스트 레지스트리 + ta.* 래퍼 구현

Pine 내장 함수를 pandas-ta/pandas/numpy로 위임. 각 함수는 pandas Series를 받고 반환.

**Files:**
- Create: `backend/tests/strategy/pine/test_stdlib.py`
- Modify: `backend/src/strategy/pine/stdlib.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Pine stdlib (화이트리스트 + 참조 구현) 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine.stdlib import SUPPORTED, is_supported, call_supported


@pytest.fixture
def close() -> pd.Series:
    return pd.Series([10.0, 11.0, 12.0, 11.5, 10.8, 10.5, 11.2, 12.5, 13.0, 12.8], name="close")


def test_is_supported_known_functions():
    assert is_supported("ta.sma")
    assert is_supported("ta.ema")
    assert is_supported("ta.rsi")
    assert is_supported("ta.atr")
    assert is_supported("ta.stdev")
    assert is_supported("ta.crossover")
    assert is_supported("ta.crossunder")
    assert is_supported("ta.highest")
    assert is_supported("ta.lowest")
    assert is_supported("ta.change")
    assert is_supported("nz")
    assert is_supported("na")


def test_is_supported_rejects_unknown():
    assert not is_supported("ta.vwma")
    assert not is_supported("request.security")


def test_ta_sma_matches_rolling_mean(close):
    result = call_supported("ta.sma", close, 3)
    expected = close.rolling(3).mean()
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_ta_ema_basic(close):
    result = call_supported("ta.ema", close, 3)
    # pandas ewm span=3 (adjust=False) 와 일치 — Pine과 동일 공식
    expected = close.ewm(span=3, adjust=False).mean()
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_ta_crossover_detects_upward_cross():
    a = pd.Series([1.0, 2.0, 3.0, 4.0])
    b = pd.Series([2.0, 2.0, 2.0, 2.0])
    result = call_supported("ta.crossover", a, b)
    # a가 1→2→3→4로 오르고 b는 2 고정. a>b인 첫 bar(index=2, 값 3>2)에서 True.
    # ta.crossover는 "직전 bar에서 a<=b이고 현재 bar에서 a>b"인 시점만 True
    assert result.iloc[0] is False or result.iloc[0] == False  # noqa: E712
    assert result.iloc[2] == True  # noqa: E712


def test_ta_crossunder_detects_downward_cross():
    a = pd.Series([4.0, 3.0, 2.0, 1.0])
    b = pd.Series([2.0, 2.0, 2.0, 2.0])
    result = call_supported("ta.crossunder", a, b)
    assert result.iloc[2] == True  # noqa: E712


def test_ta_highest_lowest(close):
    hi = call_supported("ta.highest", close, 3)
    lo = call_supported("ta.lowest", close, 3)
    pd.testing.assert_series_equal(hi, close.rolling(3).max(), check_names=False)
    pd.testing.assert_series_equal(lo, close.rolling(3).min(), check_names=False)


def test_ta_change(close):
    result = call_supported("ta.change", close, 1)
    expected = close.diff(1)
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_nz_replaces_na_with_zero():
    s = pd.Series([1.0, np.nan, 3.0])
    result = call_supported("nz", s)
    expected = pd.Series([1.0, 0.0, 3.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_nz_with_replacement():
    s = pd.Series([1.0, np.nan, 3.0])
    result = call_supported("nz", s, -1.0)
    expected = pd.Series([1.0, -1.0, 3.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_na_checks_nan():
    s = pd.Series([1.0, np.nan, 3.0])
    result = call_supported("na", s)
    expected = pd.Series([False, True, False])
    pd.testing.assert_series_equal(result, expected, check_names=False)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_stdlib.py -v`
Expected: ImportError

- [ ] **Step 3: `stdlib.py` 구현**

```python
"""Pine 내장 함수 화이트리스트 + 참조 구현.

각 함수는 pandas Series를 입력받고 반환. pandas-ta / pandas / numpy 위임으로
TradingView 재현성 확보.

스프린트 1 범위: EMA Cross / SuperTrend 수준 전략을 돌릴 최소 셋.
Phase A 결과에 따라 함수 추가.
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd


def _ta_sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).mean()


def _ta_ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=int(length), adjust=False).mean()


def _ta_rma(series: pd.Series, length: int) -> pd.Series:
    # Wilder's smoothing = EMA with alpha = 1/length
    return series.ewm(alpha=1.0 / int(length), adjust=False).mean()


def _ta_rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    avg_up = _ta_rma(up, length)
    avg_down = _ta_rma(down, length)
    rs = avg_up / avg_down.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(100.0)  # down=0인 경우 RSI=100


def _ta_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _ta_rma(tr, length)


def _ta_stdev(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).std(ddof=0)


def _ta_crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    prev_a = a.shift(1)
    prev_b = b.shift(1)
    return (a > b) & (prev_a <= prev_b)


def _ta_crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    prev_a = a.shift(1)
    prev_b = b.shift(1)
    return (a < b) & (prev_a >= prev_b)


def _ta_cross(a: pd.Series, b: pd.Series) -> pd.Series:
    return _ta_crossover(a, b) | _ta_crossunder(a, b)


def _ta_highest(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).max()


def _ta_lowest(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).min()


def _ta_change(series: pd.Series, length: int = 1) -> pd.Series:
    return series.diff(int(length))


def _nz(series: pd.Series, replacement: float = 0.0) -> pd.Series:
    return series.fillna(replacement)


def _na(series: pd.Series) -> pd.Series:
    return series.isna()


SUPPORTED: dict[str, Callable[..., Any]] = {
    "ta.sma": _ta_sma,
    "ta.ema": _ta_ema,
    "ta.rma": _ta_rma,
    "ta.rsi": _ta_rsi,
    "ta.atr": _ta_atr,
    "ta.stdev": _ta_stdev,
    "ta.crossover": _ta_crossover,
    "ta.crossunder": _ta_crossunder,
    "ta.cross": _ta_cross,
    "ta.highest": _ta_highest,
    "ta.lowest": _ta_lowest,
    "ta.change": _ta_change,
    "nz": _nz,
    "na": _na,
}


def is_supported(name: str) -> bool:
    return name in SUPPORTED


def call_supported(name: str, *args: Any, **kwargs: Any) -> Any:
    if name not in SUPPORTED:
        raise KeyError(f"unsupported function: {name}")
    return SUPPORTED[name](*args, **kwargs)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_stdlib.py -v`
Expected: 11 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/stdlib.py backend/tests/strategy/pine/test_stdlib.py
git commit -m "feat(strategy/pine): stdlib whitelist with ta.* wrappers (pandas-based)"
```

---

## Task 14: Stdlib — AST 사전 검증 (2-pass 화이트리스트 게이트)

AST 전체를 훑어 미지원 함수 호출을 **인터프리트 시작 전에** 탐지. 한 개라도 발견되면 즉시 Unsupported (ADR-003).

**Files:**
- Create: `backend/tests/strategy/pine/test_stdlib_validate.py`
- Modify: `backend/src/strategy/pine/stdlib.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""AST 사전 검증(validate) 테스트."""
from __future__ import annotations

import pytest

from src.strategy.pine.errors import PineUnsupportedError
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse
from src.strategy.pine.stdlib import validate_functions


# strategy.* / indicator / input.* 등은 "파서가 아는 구조적 호출"로 간주해 화이트리스트와 별도
# (인터프리터가 직접 처리). 여기선 ta.*, nz, na, math.* 등 "연산 함수" 화이트리스트를 검사.
_ALLOWED_NON_STDLIB = {
    "strategy",
    "strategy.entry",
    "strategy.close",
    "strategy.exit",
    "indicator",
    "input",
    "input.int",
    "input.float",
    "input.bool",
    "input.string",
    "plot",
    "plotshape",
    "bgcolor",
    "barcolor",
    "fill",
    "alert",
    "alertcondition",
    "timestamp",
    "color.new",
    "color.red",
    "color.green",
    "color.blue",
    "color.white",
    "color.black",
}


def _report(src: str) -> dict:
    prog = parse(tokenize(src))
    return validate_functions(prog, allowed_structural=_ALLOWED_NON_STDLIB)


def test_validate_ok_for_supported_functions():
    src = "x = ta.sma(close, 20)\ny = ta.crossover(close, x)\n"
    report = _report(src)
    assert "ta.sma" in report["functions_used"]
    assert "ta.crossover" in report["functions_used"]


def test_validate_raises_on_unsupported_ta_function():
    src = "x = ta.vwma(close, 20)\n"
    with pytest.raises(PineUnsupportedError) as ei:
        _report(src)
    assert ei.value.feature == "ta.vwma"
    assert ei.value.category == "function"


def test_validate_allows_structural_calls():
    # strategy.entry 같은 구조적 호출은 통과
    src = 'strategy.entry("Long", strategy.long)\n'
    # parse_stmt에선 strategy.long이 식별자라 함수 호출 아님
    report = _report(src)
    assert "strategy.entry" in report["functions_used"]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_stdlib_validate.py -v`
Expected: ImportError (`validate_functions` 없음)

- [ ] **Step 3: `stdlib.py` 끝에 `validate_functions` 추가**

```python
from src.strategy.pine.ast_nodes import (
    Assign,
    BinOp,
    FnCall,
    ForLoop,
    HistoryRef,
    IfExpr,
    IfStmt,
    Kwarg,
    Node,
    Program,
    VarDecl,
)
from src.strategy.pine.errors import PineUnsupportedError


def validate_functions(
    program: Program,
    *,
    allowed_structural: set[str],
) -> dict[str, Any]:
    """AST 전체 순회해 함수 호출을 화이트리스트와 대조.

    - stdlib SUPPORTED 에 있거나 allowed_structural 에 있으면 통과.
    - 아무 데도 없으면 PineUnsupportedError(category='function') 즉시 throw.
    - 리턴: 사용된 함수/식별자 리포트 (supported_feature_report).
    """
    used: set[str] = set()

    def walk(node: Node) -> None:
        if isinstance(node, FnCall):
            used.add(node.name)
            if not is_supported(node.name) and node.name not in allowed_structural:
                raise PineUnsupportedError(
                    f"function not supported: {node.name}",
                    feature=node.name,
                    category="function",
                    line=node.source_span.start_line,
                    column=node.source_span.start_col,
                )
            for arg in node.args:
                walk(arg)
            for kw in node.kwargs:
                walk(kw.value)
            return
        # 재귀 순회
        if isinstance(node, BinOp):
            walk(node.left)
            walk(node.right)
            return
        if isinstance(node, IfExpr):
            walk(node.cond)
            walk(node.then)
            walk(node.else_)
            return
        if isinstance(node, IfStmt):
            walk(node.cond)
            for s in node.body:
                walk(s)
            for s in node.else_body:
                walk(s)
            return
        if isinstance(node, ForLoop):
            walk(node.start)
            walk(node.end)
            if node.step is not None:
                walk(node.step)
            for s in node.body:
                walk(s)
            return
        if isinstance(node, VarDecl):
            walk(node.expr)
            return
        if isinstance(node, Assign):
            walk(node.value)
            return
        if isinstance(node, HistoryRef):
            walk(node.target)
            walk(node.offset)
            return

    for stmt in program.statements:
        walk(stmt)

    return {"functions_used": sorted(used)}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_stdlib_validate.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/stdlib.py backend/tests/strategy/pine/test_stdlib_validate.py
git commit -m "feat(strategy/pine): 2-pass function whitelist validation on AST"
```

---

## Task 15: Interpreter — 환경 + 표현식 평가 (Literal/Ident/BinOp/HistoryRef/IfExpr)

인터프리터의 핵심 표현식 평가기. 이 Task는 **문이 아닌 표현식만** 평가한다.

**Files:**
- Create: `backend/tests/strategy/pine/test_interpreter_expr.py`
- Modify: `backend/src/strategy/pine/interpreter.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Interpreter 표현식 평가 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine.interpreter import Environment, evaluate_expression
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse_expression


def _env_with_ohlcv() -> Environment:
    close = pd.Series([10.0, 11.0, 12.0, 11.5, 10.8], name="close")
    high = close + 0.5
    low = close - 0.5
    open_ = close - 0.1
    volume = pd.Series([100.0] * 5)
    return Environment.with_ohlcv(
        open_=open_, high=high, low=low, close=close, volume=volume,
    )


def _eval(src: str, env: Environment | None = None):
    env = env or _env_with_ohlcv()
    expr = parse_expression(tokenize(src))
    return evaluate_expression(expr, env)


def test_eval_int_literal():
    assert _eval("42") == 42


def test_eval_float_literal():
    assert _eval("3.14") == 3.14


def test_eval_boolean_literals():
    assert _eval("true") is True
    assert _eval("false") is False


def test_eval_string_literal():
    assert _eval('"hello"') == "hello"


def test_eval_close_identifier_returns_series():
    result = _eval("close")
    assert isinstance(result, pd.Series)
    assert len(result) == 5


def test_eval_arithmetic_with_series():
    # close + 1 → Series broadcast
    result = _eval("close + 1")
    expected = pd.Series([11.0, 12.0, 13.0, 12.5, 11.8])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_arithmetic_scalar():
    assert _eval("2 + 3 * 4") == 14
    assert _eval("(2 + 3) * 4") == 20


def test_eval_comparison_returns_bool_series():
    result = _eval("close > 11")
    expected = pd.Series([False, False, True, True, False])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_logical_and_series():
    result = _eval("close > 10 and close < 12")
    expected = pd.Series([False, True, False, True, True])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_history_reference_shift():
    # close[1] → close.shift(1)
    result = _eval("close[1]")
    expected = pd.Series([np.nan, 10.0, 11.0, 12.0, 11.5])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_ternary_series():
    # close > 11 ? close : 0
    result = _eval("close > 11 ? close : 0")
    expected = pd.Series([0.0, 0.0, 12.0, 11.5, 0.0])
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_fncall_ta_sma():
    result = _eval("ta.sma(close, 3)")
    close = _env_with_ohlcv().lookup("close")
    expected = close.rolling(3).mean()
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_eval_not_operator():
    result = _eval("not (close > 11)")
    expected = pd.Series([True, True, False, False, True])
    pd.testing.assert_series_equal(result, expected, check_names=False)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_expr.py -v`
Expected: ImportError

- [ ] **Step 3: `interpreter.py` 구현**

```python
"""Pine AST 인터프리터 (비지터 패턴).

스프린트 1: 표현식 평가 + 기본 문 처리. `:=` self-reference와 복잡한 var 상태
추적은 단순 전략 한정으로 최소 범위에서 지원.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

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
    TupleReturn,
    VarDecl,
)
from src.strategy.pine.errors import PineRuntimeError, PineUnsupportedError
from src.strategy.pine.stdlib import SUPPORTED, is_supported


@dataclass
class Environment:
    """이름 → 값 매핑. Pine의 series는 pandas.Series로, scalar는 원시 타입."""

    variables: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def with_ohlcv(
        cls,
        *,
        open_: pd.Series,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> "Environment":
        env = cls()
        env.variables.update({
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "hl2": (high + low) / 2,
            "hlc3": (high + low + close) / 3,
            "ohlc4": (open_ + high + low + close) / 4,
            "bar_index": pd.Series(range(len(close)), index=close.index),
            # strategy.long / strategy.short 등은 단순 상수로 매핑
            "strategy.long": "long",
            "strategy.short": "short",
            # 자주 쓰이는 na
            "na": float("nan"),
        })
        return env

    def lookup(self, name: str) -> Any:
        if name not in self.variables:
            raise PineRuntimeError(f"undefined identifier: {name}")
        return self.variables[name]

    def bind(self, name: str, value: Any) -> None:
        self.variables[name] = value


def evaluate_expression(node: Node, env: Environment) -> Any:
    """표현식 노드 평가."""
    if isinstance(node, Literal):
        return node.value

    if isinstance(node, Ident):
        return env.lookup(node.name)

    if isinstance(node, BinOp):
        return _eval_binop(node, env)

    if isinstance(node, IfExpr):
        cond = evaluate_expression(node.cond, env)
        then_ = evaluate_expression(node.then, env)
        else_ = evaluate_expression(node.else_, env)
        if isinstance(cond, pd.Series):
            # 시리즈 삼항 → np.where
            return pd.Series(
                np.where(cond, then_, else_),
                index=cond.index,
            )
        return then_ if cond else else_

    if isinstance(node, HistoryRef):
        target = evaluate_expression(node.target, env)
        offset = evaluate_expression(node.offset, env)
        if not isinstance(target, pd.Series):
            raise PineRuntimeError("history reference on non-series value")
        return target.shift(int(offset))

    if isinstance(node, FnCall):
        return _eval_fncall(node, env)

    raise PineRuntimeError(f"cannot evaluate node type: {type(node).__name__}")


def _eval_binop(node: BinOp, env: Environment) -> Any:
    op = node.op
    left = evaluate_expression(node.left, env)
    right = evaluate_expression(node.right, env)
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        return left / right
    if op == "%":
        return left % right
    if op == "<":
        return left < right
    if op == ">":
        return left > right
    if op == "<=":
        return left <= right
    if op == ">=":
        return left >= right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op == "and":
        if isinstance(left, pd.Series) or isinstance(right, pd.Series):
            return (left) & (right)
        return bool(left) and bool(right)
    if op == "or":
        if isinstance(left, pd.Series) or isinstance(right, pd.Series):
            return (left) | (right)
        return bool(left) or bool(right)
    if op == "not":
        # not은 (True, operand) 로 정규화되어 있음 — right가 피연산자
        if isinstance(right, pd.Series):
            return ~right.astype(bool)
        return not bool(right)
    raise PineRuntimeError(f"unknown operator: {op}")


def _eval_fncall(node: FnCall, env: Environment) -> Any:
    # input.* → 첫 인자(defval) 반환 (스프린트 1 단순화: 실제 입력 UI 없음)
    if node.name.startswith("input") or node.name == "input":
        if node.args:
            return evaluate_expression(node.args[0], env)
        return None

    # timestamp(...) → 미래 확장 (스프린트 1에선 0 반환하여 시간 윈도우 비활성화)
    if node.name == "timestamp":
        return 0

    # color.* / strategy.long 등 (이미 env에 등록) — 식별자 경로지만 함수 호출로 파싱됐을 수 있음
    # 여기선 화이트리스트 stdlib만 실행 함수로 간주
    if is_supported(node.name):
        args = [evaluate_expression(a, env) for a in node.args]
        kwargs = {kw.name: evaluate_expression(kw.value, env) for kw in node.kwargs}
        try:
            return SUPPORTED[node.name](*args, **kwargs)
        except Exception as e:
            raise PineRuntimeError(
                f"runtime error in {node.name}: {e}",
                line=node.source_span.start_line,
                column=node.source_span.start_col,
            ) from e

    # 여기까지 왔으면 validate_functions에서 이미 구조적 호출로 분류됐거나
    # 인터프리터 자체에서 처리할 의미 있는 함수가 아님.
    # Task 16에서 strategy.entry/close 등의 부수효과 호출을 처리.
    return None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_expr.py -v`
Expected: 13 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/interpreter.py backend/tests/strategy/pine/test_interpreter_expr.py
git commit -m "feat(strategy/pine): interpreter — expression evaluation (visitor pattern)"
```

---

## Task 16: Interpreter — 문 실행 + 시그널 수집

`VarDecl`/`Assign`/`IfStmt`/`FnCall` 문 실행. `strategy.entry/close` 호출을 감지해 `entries`/`exits` Series에 누적. `strategy.exit(stop, limit)` 형태는 Unsupported.

**Files:**
- Create: `backend/tests/strategy/pine/test_interpreter_stmt.py`
- Modify: `backend/src/strategy/pine/interpreter.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Interpreter 문 실행 + 시그널 수집 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine.errors import PineUnsupportedError
from src.strategy.pine.interpreter import execute_program
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse


def _ohlcv(n: int = 10) -> dict[str, pd.Series]:
    close = pd.Series(np.linspace(10.0, 20.0, n))
    return {
        "open_": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": pd.Series([100.0] * n),
    }


def test_var_decl_then_reference():
    src = """x = close
y = x + 1
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    pd.testing.assert_series_equal(
        result.metadata["vars"]["y"],
        result.metadata["vars"]["x"] + 1,
        check_names=False,
    )


def test_strategy_entry_sets_entries_series():
    src = """buy = close > 15
if buy
    strategy.entry("Long", strategy.long)
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    # close=[10..20] 10개 중 > 15인 지점에서 True
    assert result.entries.any()
    # index >= 5에서 True (linspace(10,20,10) 기준)
    assert bool(result.entries.iloc[-1]) is True
    assert bool(result.entries.iloc[0]) is False


def test_strategy_close_sets_exits_series():
    src = """sell = close > 18
if sell
    strategy.close("Long")
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    assert result.exits.any()


def test_strategy_exit_with_bracket_order_raises_unsupported():
    # stop/limit 인자가 있으면 스프린트 1에서 Unsupported
    src = """x = close
strategy.exit("tp", "Long", stop=x, limit=x)
"""
    with pytest.raises(PineUnsupportedError) as ei:
        execute_program(parse(tokenize(src)), **_ohlcv())
    assert ei.value.feature == "strategy.exit(stop,limit)"


def test_assign_walrus_updates_binding():
    # 스프린트 1: :=는 scalar/series 치환으로 단순 처리 (bar-by-bar 루프 없음)
    src = """x = 0
x := close
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    assert isinstance(result.metadata["vars"]["x"], pd.Series)


def test_if_stmt_without_signal_call_is_noop():
    src = """if close > 15
    y = close
"""
    result = execute_program(parse(tokenize(src)), **_ohlcv())
    # entries/exits는 모두 False (signal 호출 없음)
    assert not result.entries.any()
    assert not result.exits.any()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_stmt.py -v`
Expected: ImportError (`execute_program` 없음)

- [ ] **Step 3: `interpreter.py`에 문 실행 추가**

파일 끝에 아래 추가:

```python
from src.strategy.pine.types import SignalResult


@dataclass
class _SignalAccumulator:
    """if-문 조건을 시그널로 누적."""

    entries: pd.Series
    exits: pd.Series

    @classmethod
    def zero_like(cls, series: pd.Series) -> "_SignalAccumulator":
        false_like = pd.Series(False, index=series.index)
        return cls(entries=false_like.copy(), exits=false_like.copy())


def execute_program(
    program: Program,
    *,
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> SignalResult:
    """AST 프로그램 실행 → SignalResult 반환."""
    env = Environment.with_ohlcv(
        open_=open_, high=high, low=low, close=close, volume=volume,
    )
    signals = _SignalAccumulator.zero_like(close)

    for stmt in program.statements:
        _execute_statement(stmt, env, signals, gate=None)

    return SignalResult(
        entries=signals.entries,
        exits=signals.exits,
        metadata={"vars": dict(env.variables)},
    )


def _execute_statement(
    node: Node,
    env: Environment,
    signals: _SignalAccumulator,
    *,
    gate: pd.Series | bool | None,
) -> None:
    """문 실행. `gate`는 상위 if의 누적 조건 (시그널 Series와 AND 결합)."""
    if isinstance(node, VarDecl):
        env.bind(node.name, evaluate_expression(node.expr, env))
        return

    if isinstance(node, Assign):
        # := 는 기존 바인딩 갱신. 스프린트 1에선 벡터 단위 치환.
        assert isinstance(node.target, Ident)
        env.bind(node.target.name, evaluate_expression(node.value, env))
        return

    if isinstance(node, IfStmt):
        cond_value = evaluate_expression(node.cond, env)
        new_gate = _combine_gate(gate, cond_value)
        for s in node.body:
            _execute_statement(s, env, signals, gate=new_gate)
        if node.else_body:
            neg = ~cond_value if isinstance(cond_value, pd.Series) else (not cond_value)
            else_gate = _combine_gate(gate, neg)
            for s in node.else_body:
                _execute_statement(s, env, signals, gate=else_gate)
        return

    if isinstance(node, FnCall):
        _execute_fncall_stmt(node, env, signals, gate=gate)
        return

    if isinstance(node, ForLoop):
        # 스프린트 1: 단순 전략 타겟이므로 for 루프 실행은 지원하지 않음.
        # (파서는 허용하되 실행 시 Unsupported)
        raise PineUnsupportedError(
            "for loop execution is not supported in sprint 1",
            feature="for",
            category="syntax",
            line=node.source_span.start_line,
            column=node.source_span.start_col,
        )

    # 표현식 단독 statement (부수효과 없음) → 평가만 하고 버림
    evaluate_expression(node, env)


def _combine_gate(
    gate: pd.Series | bool | None,
    cond: pd.Series | bool,
) -> pd.Series | bool:
    if gate is None:
        return cond
    if isinstance(gate, pd.Series) or isinstance(cond, pd.Series):
        return (gate) & (cond)
    return bool(gate) and bool(cond)


def _execute_fncall_stmt(
    node: FnCall,
    env: Environment,
    signals: _SignalAccumulator,
    *,
    gate: pd.Series | bool | None,
) -> None:
    name = node.name

    # 브래킷 오더(TP/SL) → Unsupported (SignalResult 확장 필드 필요, 다음 스프린트)
    if name == "strategy.exit":
        kwarg_names = {kw.name for kw in node.kwargs}
        if "stop" in kwarg_names or "limit" in kwarg_names or "profit" in kwarg_names or "loss" in kwarg_names:
            raise PineUnsupportedError(
                "strategy.exit with bracket orders (stop/limit) is deferred to next sprint",
                feature="strategy.exit(stop,limit)",
                category="function",
                line=node.source_span.start_line,
                column=node.source_span.start_col,
            )
        # 인자 없는 exit은 현재 스프린트에선 무시
        return

    # 진입 시그널
    if name == "strategy.entry":
        signals.entries = signals.entries | _gate_as_bool_series(gate, signals.entries.index)
        return

    # 청산 시그널
    if name == "strategy.close":
        signals.exits = signals.exits | _gate_as_bool_series(gate, signals.exits.index)
        return

    # 시각화/알림/기타 부수효과 함수 — no-op
    if name in (
        "plot", "plotshape", "bgcolor", "barcolor", "fill",
        "alert", "alertcondition",
        "indicator", "strategy",
    ):
        return

    # 그 외는 표현식으로 평가 (값 폐기)
    evaluate_expression(node, env)


def _gate_as_bool_series(gate: pd.Series | bool | None, index: pd.Index) -> pd.Series:
    if gate is None or gate is True:
        return pd.Series(True, index=index)
    if gate is False:
        return pd.Series(False, index=index)
    if isinstance(gate, pd.Series):
        return gate.fillna(False).astype(bool)
    return pd.Series(bool(gate), index=index)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_stmt.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/src/strategy/pine/interpreter.py backend/tests/strategy/pine/test_interpreter_stmt.py
git commit -m "feat(strategy/pine): interpreter — statements + strategy.entry/close signal collection"
```

---

## Task 17: 공개 API — `parse_and_run()` + 파이프라인 통합

외부 호출자가 사용하는 단일 엔트리포인트. v4→v5 정규화 → 토크나이즈 → 파싱 → 검증 → 실행 → `ParseOutcome` 래핑. 각 단계의 예외를 `status="unsupported"` 또는 `status="error"`로 분류.

**Files:**
- Create: `backend/tests/strategy/pine/test_parse_and_run.py`
- Modify: `backend/src/strategy/pine/__init__.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""parse_and_run() 통합 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine import parse_and_run


def _ohlcv(n: int = 20) -> pd.DataFrame:
    close = pd.Series(np.linspace(10.0, 30.0, n))
    return pd.DataFrame({
        "open": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": [100.0] * n,
    })


def test_empty_source_returns_ok():
    outcome = parse_and_run("", _ohlcv())
    assert outcome.status == "ok"
    assert outcome.result is not None
    assert not outcome.result.entries.any()
    assert outcome.source_version == "v5"


def test_simple_v5_ema_cross_returns_ok():
    src = """//@version=5
strategy("X")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "ok"
    assert outcome.source_version == "v5"
    assert "ta.ema" in outcome.supported_feature_report["functions_used"]


def test_v4_ema_cross_auto_migrated_and_ok():
    src = """//@version=4
strategy("X")
fast = ema(close, 3)
slow = ema(close, 8)
if crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if crossunder(fast, slow)
    strategy.close("Long")
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "ok"
    assert outcome.source_version == "v4"


def test_unsupported_function_returns_unsupported_status():
    src = """//@version=5
x = ta.vwma(close, 20)
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert outcome.error.feature == "ta.vwma"


def test_syntax_error_returns_error_status():
    src = "x = = 1\n"
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "error"
    assert outcome.error is not None


def test_strategy_exit_with_bracket_returns_unsupported():
    src = """//@version=5
strategy("X")
if close > 15
    strategy.entry("Long", strategy.long)
strategy.exit("tp", "Long", stop=close - 1, limit=close + 1)
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "bracket" in str(outcome.error).lower() or outcome.error.feature.startswith("strategy.exit")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_parse_and_run.py -v`
Expected: ImportError (`parse_and_run` 미구현)

- [ ] **Step 3: `src/strategy/pine/__init__.py` 완성**

```python
"""Pine Script parser and interpreter (AST-based, no exec/eval).

공개 API:
- parse_and_run(source, ohlcv) -> ParseOutcome
"""
from __future__ import annotations

import pandas as pd

from src.strategy.pine.errors import (
    PineError,
    PineLexError,
    PineParseError,
    PineRuntimeError,
    PineUnsupportedError,
)
from src.strategy.pine.interpreter import execute_program
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse
from src.strategy.pine.stdlib import validate_functions
from src.strategy.pine.types import ParseOutcome, SignalResult, SourceSpan
from src.strategy.pine.v4_to_v5 import detect_version, normalize


# 구조적 호출 (stdlib 외) — 인터프리터가 직접 처리하는 함수들
_ALLOWED_STRUCTURAL: set[str] = {
    "strategy",
    "strategy.entry",
    "strategy.close",
    "strategy.exit",
    "indicator",
    "input",
    "input.int",
    "input.float",
    "input.bool",
    "input.string",
    "plot",
    "plotshape",
    "bgcolor",
    "barcolor",
    "fill",
    "alert",
    "alertcondition",
    "timestamp",
    "color.new",
    "color.red",
    "color.green",
    "color.blue",
    "color.white",
    "color.black",
}


def parse_and_run(source: str, ohlcv: pd.DataFrame) -> ParseOutcome:
    """Pine Script(v4 or v5)를 해석·실행. 미지원 감지 시 전체 중단.

    ohlcv는 open/high/low/close/volume 컬럼을 가진 DataFrame.
    """
    original_version = detect_version(source)

    try:
        normalized = normalize(source)
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        tokens = tokenize(normalized)
    except PineError as e:
        return ParseOutcome(
            status="error",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        program = parse(tokens)
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )
    except PineError as e:
        return ParseOutcome(
            status="error",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        report = validate_functions(program, allowed_structural=_ALLOWED_STRUCTURAL)
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        result = execute_program(
            program,
            open_=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
            volume=ohlcv["volume"],
        )
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report=report,
            source_version=original_version,
        )
    except PineError as e:
        return ParseOutcome(
            status="error",
            result=None,
            error=e,
            supported_feature_report=report,
            source_version=original_version,
        )

    return ParseOutcome(
        status="ok",
        result=result,
        error=None,
        supported_feature_report=report,
        source_version=original_version,
    )


__all__ = [
    "parse_and_run",
    "ParseOutcome",
    "SignalResult",
    "SourceSpan",
    "PineError",
    "PineLexError",
    "PineParseError",
    "PineUnsupportedError",
    "PineRuntimeError",
]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_parse_and_run.py -v`
Expected: 6 passed

- [ ] **Step 5: 전체 테스트 재실행 — 아무 것도 깨지지 않았는지**

Run: `cd backend && uv run pytest tests/strategy/pine/ -v`
Expected: 모두 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/src/strategy/pine/__init__.py backend/tests/strategy/pine/test_parse_and_run.py
git commit -m "feat(strategy/pine): public parse_and_run() API wiring full pipeline"
```

---

## Task 18: 골든 테스트 인프라 (`test_golden/`)

`.pine` 파일 + 기대 결과 JSON 쌍을 읽어 자동 비교하는 파라미터라이즈드 테스트.

**Files:**
- Create: `backend/tests/strategy/pine/test_golden.py`
- Create: `backend/tests/strategy/pine/golden/__init__.py`
- Create: `backend/tests/strategy/pine/golden/conftest.py`

- [ ] **Step 1: 골든 테스트 인프라 작성**

`backend/tests/strategy/pine/golden/__init__.py`:
```python
```

`backend/tests/strategy/pine/test_golden.py`:

```python
"""골든 파일 기반 통합 테스트.

tests/strategy/pine/golden/ 하위의 각 서브디렉토리는 아래 파일 구조를 가진다:
  <case-name>/
    strategy.pine       # Pine 소스
    expected.json       # 기대 결과 (status, entries_indices, exits_indices 등)
    ohlcv.csv           # (선택) OHLCV fixture. 없으면 기본 fixture 사용.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine import parse_and_run


GOLDEN_DIR = Path(__file__).parent / "golden"


def _default_ohlcv(n: int = 30) -> pd.DataFrame:
    # 상승 → 횡보 → 하락 → 반등 패턴으로 crossover 발생하도록
    seg1 = np.linspace(10.0, 20.0, 10)   # 상승
    seg2 = np.full(5, 20.0)               # 횡보
    seg3 = np.linspace(20.0, 12.0, 10)   # 하락
    seg4 = np.linspace(12.0, 18.0, 5)    # 반등
    close = np.concatenate([seg1, seg2, seg3, seg4])[:n]
    return pd.DataFrame({
        "open": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": [100.0] * n,
    })


def _load_ohlcv(case_dir: Path) -> pd.DataFrame:
    csv_path = case_dir / "ohlcv.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return _default_ohlcv()


def _discover_cases() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return [p for p in sorted(GOLDEN_DIR.iterdir()) if p.is_dir() and (p / "strategy.pine").exists()]


@pytest.mark.parametrize("case_dir", _discover_cases(), ids=lambda p: p.name)
def test_golden_case(case_dir: Path) -> None:
    src = (case_dir / "strategy.pine").read_text()
    expected = json.loads((case_dir / "expected.json").read_text())
    ohlcv = _load_ohlcv(case_dir)

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == expected["status"], (
        f"status mismatch: got {outcome.status!r}, expected {expected['status']!r}; "
        f"error={outcome.error}"
    )
    assert outcome.source_version == expected.get("source_version", "v5")

    if expected["status"] == "ok":
        assert outcome.result is not None
        expected_entries = expected.get("entries_indices", [])
        expected_exits = expected.get("exits_indices", [])
        actual_entries = [int(i) for i, v in enumerate(outcome.result.entries) if bool(v)]
        actual_exits = [int(i) for i, v in enumerate(outcome.result.exits) if bool(v)]
        assert actual_entries == expected_entries, (
            f"entries mismatch:\n  expected: {expected_entries}\n  actual:   {actual_entries}"
        )
        assert actual_exits == expected_exits, (
            f"exits mismatch:\n  expected: {expected_exits}\n  actual:   {actual_exits}"
        )
    elif expected["status"] == "unsupported":
        assert outcome.error is not None
        if "feature" in expected:
            assert outcome.error.feature == expected["feature"]


def test_golden_directory_has_cases():
    # 인프라 자체가 작동하는지 확인 (Task 19에서 실제 케이스 추가)
    cases = _discover_cases()
    # 최소 1개 이상의 골든 케이스 필요 (Task 19 이후)
    assert len(cases) >= 0  # 이 Task에선 빈 디렉토리 허용
```

- [ ] **Step 2: 테스트 실행 확인 (케이스 없이도 통과해야 함)**

Run: `cd backend && uv run pytest tests/strategy/pine/test_golden.py -v`
Expected: `test_golden_directory_has_cases` 1건 passed (나머지는 케이스 없음)

- [ ] **Step 3: 커밋**

```bash
git add backend/tests/strategy/pine/test_golden.py backend/tests/strategy/pine/golden/__init__.py
git commit -m "test(strategy/pine): add golden test infrastructure"
```

---

## Task 19: 골든 케이스 추가 — EMA Cross (Ground Zero)

스펙 §2의 ground zero 기준: EMA/SMA 크로스오버 + `strategy.entry when=` + 시간 윈도우. 이 케이스가 통과하지 못하면 스프린트 전면 실패.

**Files:**
- Create: `backend/tests/strategy/pine/golden/ema_cross_v5/strategy.pine`
- Create: `backend/tests/strategy/pine/golden/ema_cross_v5/expected.json`
- Create: `backend/tests/strategy/pine/golden/ema_cross_v4/strategy.pine`
- Create: `backend/tests/strategy/pine/golden/ema_cross_v4/expected.json`

- [ ] **Step 1: v5 EMA Cross 케이스 작성**

`backend/tests/strategy/pine/golden/ema_cross_v5/strategy.pine`:

```pine
//@version=5
strategy("EMA Cross")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
```

- [ ] **Step 2: 기대 결과 파일 작성 — 실제 결과를 확인해 채움**

먼저 기대값을 확인하기 위한 확인 스크립트 실행:

Run:
```bash
cd backend && uv run python -c "
from src.strategy.pine import parse_and_run
import pandas as pd
import numpy as np

seg1 = np.linspace(10.0, 20.0, 10)
seg2 = np.full(5, 20.0)
seg3 = np.linspace(20.0, 12.0, 10)
seg4 = np.linspace(12.0, 18.0, 5)
close = np.concatenate([seg1, seg2, seg3, seg4])[:30]
df = pd.DataFrame({'open': close-0.1, 'high': close+0.5, 'low': close-0.5, 'close': close, 'volume':[100.0]*30})

src = open('tests/strategy/pine/golden/ema_cross_v5/strategy.pine').read()
o = parse_and_run(src, df)
print('status:', o.status)
print('entries:', [i for i,v in enumerate(o.result.entries) if bool(v)])
print('exits:', [i for i,v in enumerate(o.result.exits) if bool(v)])
"
```

출력된 entries/exits 인덱스를 아래 `expected.json`에 그대로 복사해 넣는다.

`backend/tests/strategy/pine/golden/ema_cross_v5/expected.json`:

```json
{
  "status": "ok",
  "source_version": "v5",
  "entries_indices": [PASTE_FROM_CONFIRMATION],
  "exits_indices": [PASTE_FROM_CONFIRMATION],
  "description": "EMA(3)/EMA(8) crossover — ground zero v5 case"
}
```

- [ ] **Step 3: v4 EMA Cross 케이스 작성 (동일 로직, v4 문법)**

`backend/tests/strategy/pine/golden/ema_cross_v4/strategy.pine`:

```pine
//@version=4
strategy("EMA Cross v4")
fast = ema(close, 3)
slow = ema(close, 8)
if crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if crossunder(fast, slow)
    strategy.close("Long")
```

`backend/tests/strategy/pine/golden/ema_cross_v4/expected.json`:

```json
{
  "status": "ok",
  "source_version": "v4",
  "entries_indices": [SAME_AS_V5],
  "exits_indices": [SAME_AS_V5],
  "description": "EMA Cross v4 — should produce identical result after v4->v5 normalization"
}
```

v5 결과와 **정확히 동일**해야 한다 (v4 정규화의 시맨틱 보존성 검증).

- [ ] **Step 4: 골든 테스트 실행**

Run: `cd backend && uv run pytest tests/strategy/pine/test_golden.py -v`
Expected:
- `test_golden_case[ema_cross_v5]` passed
- `test_golden_case[ema_cross_v4]` passed

- [ ] **Step 5: 커밋**

```bash
git add backend/tests/strategy/pine/golden/
git commit -m "test(strategy/pine): add ground zero golden cases (EMA Cross v4 + v5)"
```

---

## Task 20: Go/No-Go 판정 스크립트 (`pine_coverage_report.py`)

Assignment 50개 전체에 `parse_and_run`을 돌려 티어별 통과율을 출력. Ground zero 실패 시 exit 2, 티어 목표 미달 시 exit 1, 전부 만족 시 exit 0.

**Files:**
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/pine_coverage_report.py`
- Create: `backend/tests/strategy/pine/test_coverage_script.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
"""Go/No-Go 판정 스크립트 테스트."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.pine_coverage_report import (
    CoverageReport,
    evaluate_case,
    run_report,
)


def _ohlcv(n: int = 30) -> pd.DataFrame:
    close = pd.Series([10.0 + i for i in range(n)])
    return pd.DataFrame({
        "open": close - 0.1, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": [100.0] * n,
    })


def test_evaluate_case_ok():
    src = """//@version=5
strategy("X")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
"""
    res = evaluate_case(case_id="S-01", tier="standard", source=src, ohlcv=_ohlcv())
    assert res.status == "ok"


def test_evaluate_case_unsupported():
    src = """//@version=5
x = ta.vwma(close, 20)
"""
    res = evaluate_case(case_id="S-02", tier="heavy", source=src, ohlcv=_ohlcv())
    assert res.status == "unsupported"


def test_coverage_report_ground_zero_failure_sets_flag():
    # 표준 티어 중 하나라도 실패하면 ground_zero_passed = False
    cases = [
        {"case_id": "S-01", "tier": "standard", "source": "x = ta.vwma(close, 20)\n"},
    ]
    report = run_report(cases, ohlcv_factory=lambda cid: _ohlcv())
    assert report.ground_zero_passed is False


def test_coverage_report_ground_zero_success():
    cases = [
        {"case_id": "S-01", "tier": "standard", "source": """//@version=5
strategy("X")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
"""},
    ]
    report = run_report(cases, ohlcv_factory=lambda cid: _ohlcv())
    assert report.ground_zero_passed is True


def test_coverage_report_tier_pass_rates():
    cases = [
        # 표준 2개 (둘 다 ok)
        {"case_id": "S-01", "tier": "standard", "source": "x = ta.sma(close, 5)\n"},
        {"case_id": "S-02", "tier": "standard", "source": "x = ta.ema(close, 5)\n"},
        # 중간 2개 (1개 ok, 1개 unsupported)
        {"case_id": "S-03", "tier": "medium", "source": "x = ta.rsi(close, 14)\n"},
        {"case_id": "S-04", "tier": "medium", "source": "x = ta.vwma(close, 20)\n"},
    ]
    report = run_report(cases, ohlcv_factory=lambda cid: _ohlcv())
    assert report.tier_pass_rate("standard") == 1.0
    assert report.tier_pass_rate("medium") == 0.5
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_coverage_script.py -v`
Expected: ImportError

- [ ] **Step 3: `scripts/__init__.py` 생성 (빈 파일)**

```bash
touch backend/scripts/__init__.py
```

- [ ] **Step 4: `scripts/pine_coverage_report.py` 구현**

```python
"""Pine Coverage Go/No-Go 판정 스크립트.

사용법:
  uv run python scripts/pine_coverage_report.py [--cases docs/01_requirements/pine-coverage-assignment.yaml]

기본은 docs/01_requirements/pine-coverage-assignment.yaml 에서 케이스 목록을 읽는다.
파일이 없거나 Phase A가 아직 진행 중이면 `--cases` 생략 시 경고 후 0건 리포트.

exit code:
  0 — 모든 티어 목표 + ground zero 통과
  1 — 티어 목표 미달 (중간/헤비)
  2 — ground zero 실패 (표준 티어 불합격)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from src.strategy.pine import parse_and_run

Tier = Literal["standard", "medium", "heavy"]


@dataclass
class CaseResult:
    case_id: str
    tier: Tier
    status: Literal["ok", "unsupported", "error"]
    feature: str | None = None


@dataclass
class CoverageReport:
    cases: list[CaseResult] = field(default_factory=list)

    def by_tier(self, tier: Tier) -> list[CaseResult]:
        return [c for c in self.cases if c.tier == tier]

    def tier_pass_rate(self, tier: Tier) -> float:
        tier_cases = self.by_tier(tier)
        if not tier_cases:
            return 1.0  # 케이스 0개는 제약 없음
        oks = sum(1 for c in tier_cases if c.status == "ok")
        return oks / len(tier_cases)

    @property
    def ground_zero_passed(self) -> bool:
        """표준 티어 100%가 ground zero 기준."""
        return self.tier_pass_rate("standard") == 1.0

    def unsupported_features_top(self, n: int = 10) -> list[tuple[str, int]]:
        from collections import Counter
        counter = Counter(
            c.feature for c in self.cases
            if c.status == "unsupported" and c.feature
        )
        return counter.most_common(n)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ground_zero_passed": self.ground_zero_passed,
            "tier_pass_rates": {
                "standard": self.tier_pass_rate("standard"),
                "medium": self.tier_pass_rate("medium"),
                "heavy": self.tier_pass_rate("heavy"),
            },
            "case_count": len(self.cases),
            "by_tier_counts": {
                "standard": len(self.by_tier("standard")),
                "medium": len(self.by_tier("medium")),
                "heavy": len(self.by_tier("heavy")),
            },
            "unsupported_top": [
                {"feature": f, "count": c}
                for f, c in self.unsupported_features_top()
            ],
            "cases": [
                {
                    "case_id": c.case_id,
                    "tier": c.tier,
                    "status": c.status,
                    "feature": c.feature,
                }
                for c in self.cases
            ],
        }


def evaluate_case(
    *,
    case_id: str,
    tier: Tier,
    source: str,
    ohlcv: pd.DataFrame,
) -> CaseResult:
    outcome = parse_and_run(source, ohlcv)
    feature = None
    if outcome.error is not None and hasattr(outcome.error, "feature"):
        feature = getattr(outcome.error, "feature", None)
    return CaseResult(
        case_id=case_id,
        tier=tier,
        status=outcome.status,
        feature=feature,
    )


def run_report(
    cases: list[dict[str, Any]],
    *,
    ohlcv_factory: Callable[[str], pd.DataFrame],
) -> CoverageReport:
    report = CoverageReport()
    for case in cases:
        result = evaluate_case(
            case_id=case["case_id"],
            tier=case["tier"],
            source=case["source"],
            ohlcv=ohlcv_factory(case["case_id"]),
        )
        report.cases.append(result)
    return report


def _default_ohlcv(_case_id: str) -> pd.DataFrame:
    import numpy as np
    close = pd.Series(np.linspace(10.0, 30.0, 30))
    return pd.DataFrame({
        "open": close - 0.1, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": [100.0] * 30,
    })


def _load_cases_from_yaml(path: Path) -> list[dict[str, Any]]:
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed; please add 'pyyaml' to dependencies or pass cases as JSON.", file=sys.stderr)
        return []
    if not path.exists():
        print(f"[warn] cases file not found: {path}", file=sys.stderr)
        return []
    raw = yaml.safe_load(path.read_text())
    return raw.get("cases", []) if isinstance(raw, dict) else raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("docs/01_requirements/pine-coverage-assignment.yaml"),
    )
    parser.add_argument(
        "--medium-target",
        type=float,
        default=0.0,
        help="중간 티어 최소 통과율 (0.0~1.0). 기본값은 Phase A 결과로 덮어쓰기.",
    )
    args = parser.parse_args(argv)

    cases = _load_cases_from_yaml(args.cases)
    if not cases:
        print("[info] no cases to evaluate; exiting 0")
        return 0

    report = run_report(cases, ohlcv_factory=_default_ohlcv)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))

    if not report.ground_zero_passed:
        print("[FAIL] ground zero (standard tier) not 100%", file=sys.stderr)
        return 2
    if report.tier_pass_rate("medium") < args.medium_target:
        print(
            f"[FAIL] medium tier {report.tier_pass_rate('medium'):.1%} < target {args.medium_target:.1%}",
            file=sys.stderr,
        )
        return 1
    print("[OK] all coverage targets met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_coverage_script.py -v`
Expected: 5 passed

- [ ] **Step 6: CLI 동작 smoke 테스트**

Run: `cd backend && uv run python scripts/pine_coverage_report.py --cases /nonexistent.yaml; echo "exit=$?"`
Expected: `[info] no cases to evaluate; exiting 0` 그리고 `exit=0`

- [ ] **Step 7: 커밋**

```bash
git add backend/scripts/ backend/tests/strategy/pine/test_coverage_script.py
git commit -m "feat(strategy/pine): Go/No-Go coverage report script"
```

---

## Task 21: 전체 테스트 + 린트 + 타입체크 + 최종 통합 검증

스프린트 1 마무리 단계. 모든 품질 게이트 통과 확인.

- [ ] **Step 1: 전체 pine 테스트 재실행**

Run: `cd backend && uv run pytest tests/strategy/pine/ -v`
Expected: 모든 테스트 passed

- [ ] **Step 2: 기존 health 테스트 + 다른 테스트도 깨지지 않았는지 확인**

Run: `cd backend && uv run pytest -v`
Expected: 전체 passed

- [ ] **Step 3: 커버리지 측정 (핵심 모듈 ≥85%)**

Run: `cd backend && uv run pytest --cov=src/strategy/pine --cov-report=term-missing`
Expected: `src/strategy/pine/*` 전체 라인 커버리지 ≥85% (핵심 모듈 ≥95%)

미달 시 누락된 브랜치 테스트를 신규 케이스로 추가. 각 추가 후 커밋.

- [ ] **Step 4: 린트**

Run: `cd backend && uv run ruff check src/strategy/pine tests/strategy/pine scripts/`
Expected: `All checks passed!` 또는 `no issues found`

실패 시 자동 수정 가능한 것은 `uv run ruff check --fix`로 적용 후 커밋.

- [ ] **Step 5: 타입 체크**

Run: `cd backend && uv run mypy src/strategy/pine scripts/pine_coverage_report.py`
Expected: `Success: no issues found in N source files`

타입 에러 발생 시 수정 후 해당 파일 커밋.

- [ ] **Step 6: 최종 커밋 (타이트닝 변경사항 있을 시)**

```bash
git add -u
git commit -m "chore(strategy/pine): tighten types and lint for sprint 1 close-out"
```

- [ ] **Step 7: 스프린트 1 Ground Zero 증명 실행 (수동 확인)**

Run: `cd backend && uv run python -c "
from src.strategy.pine import parse_and_run
import pandas as pd, numpy as np

seg1 = np.linspace(10.0, 20.0, 10)
seg2 = np.full(5, 20.0)
seg3 = np.linspace(20.0, 12.0, 10)
seg4 = np.linspace(12.0, 18.0, 5)
close = np.concatenate([seg1, seg2, seg3, seg4])[:30]
df = pd.DataFrame({'open': close-0.1, 'high': close+0.5, 'low': close-0.5, 'close': close, 'volume':[100.0]*30})

v5 = '''//@version=5
strategy(\"EMA Cross\")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry(\"Long\", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close(\"Long\")
'''
v4 = v5.replace('//@version=5', '//@version=4').replace('ta.ema', 'ema').replace('ta.crossover', 'crossover').replace('ta.crossunder', 'crossunder')

for tag, src in [('v5', v5), ('v4', v4)]:
    o = parse_and_run(src, df)
    print(f'--- {tag} ---')
    print('status:', o.status, 'version:', o.source_version)
    print('entries:', [i for i,v in enumerate(o.result.entries) if bool(v)])
    print('exits:', [i for i,v in enumerate(o.result.exits) if bool(v)])
"`

Expected:
- v5, v4 둘 다 `status: ok`
- 두 경우의 entries/exits 인덱스가 **완전히 동일** (v4 정규화의 시맨틱 보존성 증명)

---

## 최종 확인 체크리스트 (스프린트 완료 조건)

- [ ] Task 1~21 모두 완료
- [ ] `cd backend && uv run pytest tests/strategy/pine/` 전체 통과
- [ ] `cd backend && uv run ruff check src/strategy/pine tests/strategy/pine scripts/` 통과
- [ ] `cd backend && uv run mypy src/strategy/pine scripts/pine_coverage_report.py` 통과
- [ ] Task 21 Step 7의 수동 Ground Zero 증명 성공 (v4/v5 결과 일치)
- [ ] Phase A (Assignment 50개 수집) 진행 상황을 `docs/01_requirements/pine-coverage-assignment.md` 에 기록
- [ ] Phase A 완료 시 `scripts/pine_coverage_report.py --cases docs/01_requirements/pine-coverage-assignment.yaml` 실행해 Go/No-Go 최종 판정

> **Phase A 완료 전에도 Task 21까지 구현 가능.** Phase A는 병행/후속으로 완료하면서 중간 티어 목표치(`--medium-target`)를 데이터 기반으로 갱신한다.

---

## 스펙 커버리지 자기검토 (self-review)

| 스펙 섹션 | 구현 Task |
|-----------|-----------|
| §1.2 Phase A (Assignment) | Task 1 |
| §1.2 Phase B1 (v4→v5) | Task 7 |
| §1.2 Phase B2 (파서 MVP) | Task 3~6, 8~17 |
| §1.4 AST 중앙 표현 (source_span/annotations) | Task 6 |
| §2 Go/No-Go 기준 + Ground Zero | Task 19, 20, 21 |
| §3.1 AST 인터프리터 채택 | Task 15, 16 |
| §3.2 디렉토리 구조 | Task 3 |
| §3.3 외부 인터페이스 `parse_and_run` | Task 17 |
| §4.1 v4→v5 | Task 7 |
| §4.2 Lexer | Task 8, 9, 10 |
| §4.3 Parser | Task 11, 12 |
| §4.4 AST Nodes | Task 6 |
| §4.5 Interpreter | Task 15, 16 |
| §4.6 Stdlib 화이트리스트 | Task 13 |
| §4.7 SignalResult 확장 필드 | Task 5 (값은 None, 필드만 선언) |
| §4.8 ParseOutcome | Task 5 |
| §5 데이터 플로우 (2-pass 검증 + 단방향) | Task 14, 17 |
| §6 에러 처리 | Task 4 (계층) + Task 17 (status 매핑) |
| §7 테스트 전략 | Task 4~20 TDD로 각 레이어 |
| §7.4 Go/No-Go 스크립트 | Task 20 |
| §8 리스크 (v4 편중/브래킷/flaky) | Task 7 (v4 고립), Task 16 (브래킷 unsupported), Task 13 (±1e-8) |
| §9 장기 확장 (source_span/annotations) | Task 6 |

공백 없음 확인 완료.

---
