# Pine Script 파서 MVP — 설계 문서

- **작성일:** 2026-04-15
- **단계:** Stage 3 / Sprint 1
- **관련 ADR:** ADR-003 (Pine 런타임 안전성 + 파서 범위)
- **방법론:** brainstorming → writing-plans → TDD 구현
- **시간박스:** 없음. 완료 기준은 "파서 Go/No-Go 판정 가능".

---

## 1. 목적과 범위

### 1.1 왜 파서부터인가
Pine Script → Python 변환 능력이 QuantBridge의 핵심 기술 리스크다. UI/DB를 먼저 쌓아도 파서가 실패하면 전체 제품이 무가치해진다. 따라서 첫 스프린트는 파서의 기술적 타당성을 격리 검증하는 데 집중한다.

### 1.2 스프린트 범위
이 스프린트의 산출물은 **3개**다.

1. **Phase A — Pine Coverage Assignment** *(선행)*
   TradingView에서 수집한 전략 50개에 대한 분류표. 파서의 지원 함수 우선순위와 커버리지 목표치를 데이터 기반으로 확정.

2. **Phase B1 — Pine v4 → v5 자동 변환 레이어**
   v4 문법을 v5 문법으로 기계적으로 변환하는 전처리기. 내부적으로는 v5 파이프라인 단일 유지.

3. **Phase B2 — Pine v5 파서 MVP (AST 인터프리터)**
   `backend/src/strategy/pine/` 하위에 lexer + parser + interpreter + stdlib. 외부 인터페이스 1개: `parse_and_run(source, ohlcv) -> ParseOutcome`.

### 1.3 범위 밖 (다음 스프린트 이후)
- vectorbt 포트폴리오 실행 및 리포트 생성
- Strategy 도메인의 REST API 엔드포인트
- 프론트엔드 전략 편집기
- DB 저장 (Strategy 엔티티 CRUD)
- AST → Pine pretty printer (장기 확장)
- AST → Python 읽기 전용 렌더러 (장기 확장)
- AI 기반 AST 변형/병합 (장기 확장)

### 1.4 AST의 위상
이 스프린트의 AST는 실행 엔진의 입력일 뿐 아니라 **제품의 중앙 편집 가능 표현**이다. Phase 2 이후 AST 위에 Python 렌더러, AI 변형 엔진, 전략 병합, 초보자 빌더 UX 등이 얹힌다. AST 노드 설계 시 이를 고려한다 (§4.3 참조).

---

## 2. 완료 기준 (Go/No-Go)

스프린트 완료 기준은 아래 2개 모두 충족:

1. **커버리지:** Assignment 50개 중 "지원 대상"으로 분류된 전략 100%가 `status="ok"`로 해석된다.
2. **정확성:** 지원 전략에 대해 `SignalResult`가 기대값(`*.expected.json`)과 일치한다. TradingView 원본 백테스트 수치 대조는 다음 스프린트에서 ±Y% 내로 검증.

**Ground zero 기준 (반드시 통과해야 하는 최소 레벨):**
EMA/SMA 크로스오버 + `strategy.entry when=` + 시간 윈도우 필터로 구성된 단순 전략(예: 스크립트 #4 EMA Cross)은 100% 통과. 이조차 실패 시 스프린트 전면 실패.

Go/No-Go 판정 스크립트(`scripts/pine_coverage_report.py`)를 통과하지 못하면 스프린트 미종료.

---

## 3. 아키텍처 결정

### 3.1 접근 선택: AST 인터프리터
3가지 접근을 검토했다.

| 접근 | 보안 | 정확도 | 표현력/확장성 | 구현 비용 | 선택 |
|------|------|--------|---------------|-----------|------|
| AST 인터프리터 | ★★★ | ★★★ (*) | ★★★ | 중~높음 | ✅ |
| Python 트랜스파일 + RestrictedPython | ★★ | ★★★ | ★★★ | 중간 | ❌ 샌드박스 탈출 리스크, 접근 1 대비 유니크한 이점 없음 |
| 시그널 DSL 직매핑 | ★★★ | ★★★ | ★ | 낮음 | ❌ 제어흐름·커스텀 함수 표현 불가 |

(*) AST 인터프리터의 정확도는 stdlib 함수를 **검증된 라이브러리(TA-Lib / pandas-ta) 래퍼**로 구현한다는 전제에서 ★★★.

**결정 근거 요약:**
- 접근 1은 `exec`/`eval` 없이 비지터 패턴으로 실행 → ADR-003 만족.
- TV 실제 스크립트 5개 표본 검토 결과 **접근 1만 유일하게 모두 커버 가능**. 접근 3은 5개 중 1개만 깔끔하게 지원, 접근 2는 접근 1 대비 유니크한 이점 없음.
- AST는 실행 외 편집/변형/렌더링의 중앙 저장소 역할도 겸하므로 장기 로드맵 수용력이 가장 큼.

### 3.2 디렉토리 구조
```
backend/src/strategy/pine/
  __init__.py
  v4_to_v5.py       # Pine v4 → v5 자동 변환 전처리기
  lexer.py          # v5 토큰화
  parser.py         # 재귀 하강 파서 → AST
  ast_nodes.py      # @dataclass(frozen=True) 노드 정의
  interpreter.py    # 비지터 패턴 실행
  stdlib.py         # Pine 내장함수 화이트리스트 (검증된 라이브러리 래퍼)
  errors.py         # 예외 계층
  types.py          # SignalResult, ParseOutcome
```

### 3.3 외부 인터페이스
```python
def parse_and_run(
    source: str,
    ohlcv: pd.DataFrame,
) -> ParseOutcome:
    """Pine Script(v4 or v5)를 해석·실행. 미지원 감지 시 전체 중단."""
```

내부 파이프라인:
```
source (v4 or v5)
  → v4_to_v5.normalize()     # v4면 v5로 변환, v5면 passthrough
  → lexer.tokenize()
  → parser.parse()
  → stdlib.validate(ast)     # 2-pass 화이트리스트 검증
  → interpreter.run(ast, ohlcv)
  → ParseOutcome
```

---

## 4. 컴포넌트 상세

### 4.1 v4→v5 변환기 (`v4_to_v5.py`)
- 입력: Pine 소스 문자열
- 출력: v5 호환 소스 문자열 (v5 입력은 passthrough)
- 구현: `//@version=4` 감지 시 기계적 치환 규칙 적용
  - `sma(...)` → `ta.sma(...)`, `ema`, `rma`, `atr`, `rsi`, `stdev`, `tr`, `crossover`, `crossunder`, `valuewhen`, `barssince`, `change`, `highest`, `lowest`, `pivothigh`, `pivotlow`, `alma`, `wma`, `sar`, `obv`, `mom`, `bb`, `dmi`, `cross`, `nz`, `na`, `fixnan` 등
  - `input(...)` → v5 `input.{type}(...)` 매핑
  - `strategy.position_avg_price`는 v4/v5 동일 (변환 불필요)
- 변환 실패 시 → `PineUnsupportedError(category="v4_migration")` 반환

### 4.2 Lexer (`lexer.py`)
- 입력: Pine v5 소스 문자열
- 출력: `list[Token]` (KEYWORD / IDENT / NUMBER / STRING / OP / NEWLINE / INDENT / DEDENT)
- 의존성: 표준 라이브러리만

### 4.3 Parser (`parser.py`)
- 입력: `list[Token]`
- 출력: `Program` (AST 루트)
- 구현: 재귀 하강 파서. `//@version=5`, `indicator(...)`, `strategy(...)`, 변수 바인딩, 제어흐름(if/for/ternary), 함수 호출 지원.
- 미지원 문법 감지 시 → `PineUnsupportedError(category="syntax")` 즉시 throw.

### 4.4 AST Nodes (`ast_nodes.py`)
- `@dataclass(frozen=True)` 기반 **불변** 노드.
- 핵심: `Program`, `VarDecl`, `Assign`, `FnCall`, `BinOp`, `IfExpr`, `IfStmt`, `ForLoop`, `HistoryRef`, `Ident`, `Literal`, `TupleReturn`.

**모든 노드에 포함되는 공통 필드:**
```python
@dataclass(frozen=True)
class ASTNode:
    source_span: SourceSpan      # (start_line, start_col, end_line, end_col)
    annotations: dict = field(default_factory=dict)  # 향후 AI/변형/병합용 메타
```

**설계 의도:**
- `source_span`: 에러 라인 추적, 미래 Pine pretty printer 역출력, Python 렌더러에서 원본 라인 주석 삽입에 사용.
- `annotations`: Phase 2+ AI 변형/전략 병합/패턴 태깅용 확장 슬롯. 이번 스프린트에선 빈 dict로 두기만 함.

### 4.5 Interpreter (`interpreter.py`)
- 입력: `Program` + `ohlcv: pd.DataFrame`
- 출력: `SignalResult`
- 비지터 패턴 디스패치: `visit_<NodeType>()` 메서드.
- Pine의 series 개념을 pandas Series로 매핑.
- `var` 변수와 `:=` self-reference는 bar-by-bar 상태 루프로 처리 (스프린트 1은 단순 전략 타겟이므로 고급 상태 추적 최소 범위).
- 금융 숫자는 경계에서 `Decimal` 변환 (내부 계산은 pandas/NumPy float, 최종 metadata 금액은 Decimal).

### 4.6 Stdlib — 화이트리스트 (`stdlib.py`)
- `SUPPORTED: dict[str, Callable]` 레지스트리.
- **각 함수는 검증된 라이브러리(TA-Lib 또는 pandas-ta) 래퍼로 구현.** 자체 구현 대신 위임하여 TradingView 재현성 확보.
- Phase A 결과로 등록할 함수 확정 (예: `ta.sma`, `ta.ema`, `ta.rsi`, `ta.atr`, `ta.crossover`, `ta.crossunder`, `ta.highest`, `ta.lowest`, `ta.stdev`, `ta.change`, 등).
- 미등록 함수 조회 시 → 상위에서 `PineUnsupportedError(category="function")`로 변환.

### 4.7 SignalResult 타입 (`types.py`)

**스프린트 1에서는 필드를 확장 선언하되 실제 값 채움은 다음 스프린트에서 진행** (점진 확장).

```python
@dataclass
class SignalResult:
    entries: pd.Series                  # 진입 시점 bool [이번 스프린트에서 채움]
    exits: pd.Series                    # 수동 청산 시점 bool [이번 스프린트에서 채움]
    direction: pd.Series | None = None  # long/short/flat [이번 스프린트는 None]
    sl_stop: pd.Series | None = None    # 스탑로스 가격 [다음 스프린트에서 채움]
    tp_limit: pd.Series | None = None   # 익절 가격 [다음 스프린트에서 채움]
    position_size: pd.Series | None = None  # 포지션 크기 [다음 스프린트에서 채움]
    metadata: dict = field(default_factory=dict)
```

**설계 의도:**
- 필드명은 **vectorbt `Portfolio.from_signals()` 파라미터와 1:1 대응** → 다음 스프린트 통합 시 이름 재설계 불필요.
- 스프린트 1에선 `entries`/`exits`만 실제 값을 산출하고 나머지는 None. 타입 구조를 먼저 얼려 API 경계 변동을 방지.
- ADR-003("부분 실행 금지") 위반 방지: `strategy.exit(stop, limit)` 같은 브래킷 오더 구문이 등장하면, 스프린트 1에선 **`status="unsupported"`로 반환**하고 필드에 부분 값을 채우지 않는다. 필드 채움은 다음 스프린트에서 일괄 구현.

### 4.8 ParseOutcome 타입 (`types.py`)
```python
@dataclass
class ParseOutcome:
    status: Literal["ok", "unsupported", "error"]
    result: SignalResult | None
    error: PineError | None
    supported_feature_report: dict         # 사용된 함수/문법 목록
    source_version: Literal["v4", "v5"]    # 원본 Pine 버전
```

---

## 5. 데이터 플로우

### Phase A (선행, 지금 바로 시작)
```
TradingView 전략 수집 (N=50)
    ↓ 수동 분류 (난이도별 3티어)
docs/01_requirements/pine-coverage-assignment.md
    ├─ 필수 지원 함수 (빈도순)
    ├─ Pine v4 / v5 비율
    ├─ 난이도별 분포 (표준 / 중간 / 헤비)
    ├─ Unsupported 대상
    └─ 커버리지 목표치 X% (티어별)
```

### Phase B (파서 런타임)
```
Pine source (v4 or v5)
    ↓ v4_to_v5.normalize()        ── 변환 실패 → PineUnsupportedError(v4_migration)
v5 source
    ↓ lexer.tokenize()
list[Token]
    ↓ parser.parse()               ── 실패 → PineParseError
Program (AST)
    ↓ stdlib.validate(ast)         ── 미지원 → PineUnsupportedError (전체 중단)
Program (검증 완료)
    ↓ interpreter.run(ast, ohlcv)
SignalResult (entries/exits, 기타 필드 None)
    ↓ (다음 스프린트) vectorbt.Portfolio.from_signals()
백테스트 리포트
```

### 핵심 원칙
- **2-pass 검증:** 파싱 성공해도 인터프리트 전에 AST를 훑어 미지원 함수를 사전 탐지. 부분 실행으로 잘못된 결과가 나갈 여지 제거 (ADR-003).
- **단방향 흐름:** interpreter는 raw source를 다시 보지 않음 → 테스트 격리 용이.
- **v4/v5 단일화:** 파서 이하 모든 컴포넌트는 v5만 다룸. v4 처리는 전처리 레이어에 고립.

---

## 6. 에러 처리

### 6.1 예외 계층 (`errors.py`)
```python
class PineError(Exception):
    line: int | None
    column: int | None

class PineLexError(PineError): ...
class PineParseError(PineError): ...

class PineUnsupportedError(PineError):
    feature: str                                                   # 예: "ta.vwma", "while loop"
    category: Literal["function", "syntax", "type", "v4_migration"]

class PineRuntimeError(PineError): ...                             # 지원 함수 실행 중 예외
```

### 6.2 API 경계 반환 형태
`ParseOutcome` (§4.8)으로 래핑.

- `status="unsupported"` — 사용자 친화 분류. 프론트가 "이 전략은 아직 지원하지 않습니다 + 이유" 표시.
- `status="error"` — 파서 버그 가능성. 로깅 + Sentry 리포트.

### 6.3 불변 규칙 (ADR-003)
- Unsupported 감지 시 **즉시 중단**. 부분 SignalResult 반환 금지.
- 화이트리스트 외 함수를 silent skip 절대 금지.
- 브래킷 오더(`strategy.exit(stop, limit)`) 같이 SignalResult 확장 필드가 필요한 구문은 스프린트 1에서 Unsupported 처리 (§4.7 참조).

### 6.4 로깅
모든 `PineError`는 `line:column + feature`를 구조화 로그로 기록. Assignment 커버리지와 실사용 갭 추적에 사용.

---

## 7. 테스트 전략

### 7.1 레이어별 테스트 (pytest + pytest-asyncio)

| # | 대상 | 파일 | 방식 |
|---|------|------|------|
| 1 | v4→v5 변환기 | `test_v4_to_v5.py` | v4 샘플 → v5 출력 스냅샷 비교 |
| 2 | Lexer | `test_lexer.py` | 토큰 스트림 스냅샷 |
| 3 | Parser | `test_parser.py` | AST 구조 비교 (dataclass equality) + 에러 라인 검증 |
| 4 | Stdlib | `test_stdlib.py` | 참조 구현(TA-Lib/pandas-ta) ±1e-8 일치 |
| 5 | Interpreter | `test_interpreter.py` | 고정 OHLCV fixture → SignalResult 비교, Unsupported 즉시 throw |
| 6 | E2E 골든 | `test_golden/` | `.pine` + `.expected.json` 쌍 스냅샷 |
| 7 | 커버리지 리포트 | `scripts/pine_coverage_report.py` | Assignment 50개 일괄 실행, 티어별 통과율 리포트 |

### 7.2 난이도 티어별 커버리지 목표

Phase A 결과에서 50개를 3티어로 분류:

| 티어 | 특징 | 예시 | 스프린트 1 목표 | Phase 1 MVP |
|------|------|------|-----------------|-------------|
| **표준** | 이름 있는 지표 + 단순 시그널 | EMA Cross, SuperTrend | **100%** (ground zero) | 100% |
| **중간** | var + if/else + valuewhen + 커스텀 수식 | Moon Phases | Phase A 결과로 확정 | 60~80% |
| **헤비** | 커스텀 함수 + MTF + var state + 드로잉 집약 | DrFX Diamond | 0% (Unsupported 분류) | 0% |

### 7.3 커버리지 목표
- 단위 테스트 라인 커버리지: ≥85% (핵심 모듈 ≥95%)
- 골든 테스트: Assignment의 "지원 대상(표준+중간 일부)" 100% 통과

### 7.4 Go/No-Go 판정 스크립트
- Assignment 50개 전체를 파서에 통과시킨 뒤 `ok / unsupported / error` 분포와 Unsupported 사유 Top N 출력.
- 티어별 목표치 미달 시 exit code 1 → 스프린트 완료 차단.
- **Ground zero 기준 (§2) 실패 시 즉시 exit code 2.**

---

## 8. 리스크와 대응

| 리스크 | 대응 |
|--------|------|
| Assignment 결과가 v4 편중 → v4 변환 규칙이 예상보다 많음 | 변환 규칙을 `v4_to_v5.py`에 데이터로 분리하여 증분 추가. 변환 불가 문법은 `v4_migration` Unsupported로 명시 반환 |
| 중간 티어 커버리지 목표 달성 어려움 | Phase A 결과로 목표치를 데이터 기반으로 설정 (사전 수치 확정 금지) |
| Pine v5 세부 시맨틱 불명확 | 공식 레퍼런스 기준, 애매하면 TradingView 실기기 출력 비교 |
| 파서 구현 볼륨 과다 | Phase A 결과를 보고 stdlib 함수 수를 최소로 깎아 Phase B 착수. 헤비 티어는 0% 목표 |
| 부동소수점 오차 누적으로 골든 테스트 flakiness | 참조값 허용 오차 ±1e-8, 금융 최종값은 Decimal 비교 |
| 브래킷 오더 전략이 Assignment에 많음 → Unsupported 비율 증가 | 다음 스프린트에서 `sl_stop`/`tp_limit` 필드 채움으로 지원 확장. 스프린트 1은 의도적 보류 |

---

## 9. 다음 스프린트 및 장기 확장 연결

이 스프린트의 `SignalResult` 타입 형태는 다음 스프린트의 vectorbt 백테스트 레이어 입력이 된다. 따라서 타입 스키마는 이 스프린트 종료 시점에 얼어야 한다 (breaking change는 다음 스프린트 착수 전 결정).

**이 스프린트의 AST는 장기적으로 다음 기능군의 기반이 된다:**

- **Pine ↔ AST ↔ Pine 왕복** (pretty printer + trivia 슬롯 확장) — Phase 2
- **AST → Python 읽기 전용 렌더러** (학습/이식/AI 제안 연계) — Phase 2~3
  - 타겟: numpy/pandas 기본 (플랫폼 독립) + vectorbt 옵션
  - **실행은 하지 않음** — 사용자가 복사해서 로컬 Jupyter 등에서 쓸 수 있도록 표시만
  - ADR-003 보안 경계 유지 (동적 실행 없음)
- **AI 기반 AST 변환** — 지표 추가/교체, 필터 주입, 약점 분석 — Phase 2~3
- **여러 전략 AST 병합/차분** — 조합 전략 생성 — Phase 3
- **초보자용 카탈로그 UX 레이어** (접근 3 스타일) — AST를 생성/수정하는 드롭다운 빌더 — Phase 3
- **접근 3 패스트패스 (선택)** — Optimizer 성능 병목이 실제로 측정된 경우에만 검토. 로드맵 확정 항목 아님.

이 로드맵을 위해 AST 노드는 불변(dataclass frozen), `source_span` 보존, `annotations` 슬롯을 포함한다 (§4.4).

---

## 10. 참조

- ADR-003: Pine 런타임 안전성 + 파서 범위
- CLAUDE.md §QuantBridge 고유 규칙 (exec/eval 금지, Unsupported 전체 반환)
- docs/01_requirements/pine-script-analysis.md
- docs/01_requirements/pine-coverage-assignment.md (Phase A 산출물, 본 스프린트에서 작성)
