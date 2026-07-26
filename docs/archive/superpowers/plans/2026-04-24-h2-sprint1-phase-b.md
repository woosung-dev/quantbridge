# H2 Sprint 1 Phase B — pine_v2 H2 심화 SDD

> **작성일:** 2026-04-24  
> **상태:** 계획 확정  
> **목표:** pine_v2 런타임 메모리 무제한 성장 3종 + request.security 미지원 경고 수정  
> **선행 조건:** Phase A Gate 통과 (pytest tests/trading/ green)

---

## 배경

Sprint 8c에서 user function + 3-Track dispatcher 완성 후 남은 런타임 결함 4종:

1. `_var_series` list 무제한 성장 → 대용량 Pine 실행 시 OOM 위험
2. `valuewhen` hist list 무제한 축적 + O(n) insert → 희귀 이벤트 전략에서 메모리/성능 선형 저하
3. User function call-site별 ta.\* 상태 비격리 → 동일 함수 여러 call-site에서 공유 버퍼 오염
4. `request.security` 런타임 NOP이지만 Coverage Analyzer `unsupported_functions`에 명시 누락

---

## 사전 조사 결과 (실측 기반)

| 대상                      | 실제 구현 상태                                                              |
| ------------------------- | --------------------------------------------------------------------------- |
| `_var_series` 타입        | `dict[str, list[Any]]` — setdefault + append, maxlen 없음                   |
| `RunResult.var_series`    | `dict[str, list[Any]]` — **list 타입 명시. deque 전환 시 호환성 처리 필요** |
| `ta_valuewhen`            | `hist.insert(0, float(source))` O(n), maxlen 없음                           |
| `StdlibDispatcher`        | `@dataclass` — 필드 외 인스턴스 변수는 `__post_init__` 필요                 |
| `StdlibDispatcher.call()` | `node_id: int` — 현재 정수형. prefix 스택 연동 시 타입 주의                 |
| `CoverageReport`          | 실제 필드명 `unsupported_functions` (not `unsupported_builtins`)            |

---

## 태스크 분해

### B-1. `_var_series` Ring Buffer Cap

**파일:** `backend/src/strategy/pine_v2/interpreter.py`

**현재 구현 (라인 198, 216-227):**

```python
self._var_series: dict[str, list[Any]] = {}

def append_var_series(self) -> None:
    for name, value in self._transient.items():
        self._var_series.setdefault(name, []).append(value)
    for full_key, value in self.store.snapshot_dict().items():
        short = full_key.split("::", 1)[1] if "::" in full_key else full_key
        self._var_series.setdefault(short, []).append(value)
```

**수정 방향:**

```python
from collections import deque
from typing import Any

# __init__
self._max_bars_back: int = 500  # Pine 기본값 (max_bars_back() 함수 미지원 시 고정)
self._var_series: dict[str, deque[Any]] = {}

# append_var_series
def append_var_series(self) -> None:
    for name, value in self._transient.items():
        if name not in self._var_series:
            self._var_series[name] = deque(maxlen=self._max_bars_back)
        self._var_series[name].append(value)
    for full_key, value in self.store.snapshot_dict().items():
        short = full_key.split("::", 1)[1] if "::" in full_key else full_key
        if short not in self._var_series:
            self._var_series[short] = deque(maxlen=self._max_bars_back)
        self._var_series[short].append(value)
```

**`_eval_subscript` 호환성 (라인 522-530):**

```python
# deque는 series[-offset] 음수 인덱싱을 지원하므로 변경 불필요
series = self._var_series.get(name)
if series is None or len(series) < offset:   # len(deque) = O(1)
    return float("nan")
return series[-offset]   # deque에서 동일 동작
```

**⚠️ CRITICAL — RunResult 타입 호환:**

`event_loop.py`의 `RunResult.var_series` 필드는 `dict[str, list[Any]]`로 선언됨.  
`deque`를 직접 저장하면 타입 계약 파괴 → 다운스트림 코드(test assertions, serialization) 깨짐.

**해결책:** `append_var_series` 후 RunResult 생성 시 `list()` 변환:

```python
# event_loop.py 또는 interpreter.run() 반환 직전
var_series_as_lists: dict[str, list[Any]] = {
    k: list(v) for k, v in interpreter._var_series.items()
}
result = RunResult(..., var_series=var_series_as_lists)
```

또는 RunResult 타입 자체를 `dict[str, Sequence[Any]]`로 완화 (타입 변경 범위 검토 후 결정).

**에지 케이스:**

| 케이스                         | 처리 방식                                                                     |
| ------------------------------ | ----------------------------------------------------------------------------- |
| `x[0]` (현재 bar)              | `offset=0` → `_resolve_name(name)` 직접 조회 (series 미사용) — 기존 로직 유지 |
| `x[n]` where `n > len(series)` | `len(series) < offset` 체크 → `float("nan")`                                  |
| `x[-1]` (음수 offset)          | Pine 미지원. `offset < 0` → `float("nan")` 반환 추가                          |
| 첫 번째 bar에서 `x[1]`         | series 비어있음 → `len(series) < 1` → nan                                     |
| `max_bars_back()` Pine 함수    | H2 미지원 — `_max_bars_back` 전역 500 고정, TODO 추가                         |

**테스트 추가:**

```python
# test_var_series_ring_buffer.py
def test_ring_buffer_cap():
    """max_bars_back=3: 4번째 bar에서 x[3] → nan 반환."""
    interp = Interpreter(max_bars_back=3)
    # 4 bar 실행 후 x[3] 접근 → nan

def test_ring_buffer_negative_offset():
    """Pine 미지원 음수 offset → nan."""
    # x[-1] 접근 → float('nan')

def test_runresult_var_series_list_type():
    """RunResult.var_series 값이 list 타입인지 확인."""
    result = run_pine(script)
    for v in result.var_series.values():
        assert isinstance(v, list)
```

---

### B-2. `valuewhen` O(n) Insert + Maxlen Cap

**파일:** `backend/src/strategy/pine_v2/stdlib/stdlib.py` (라인 251-271)

**현재 구현:**

```python
hist: list[float] = slot["history"]
hist.insert(0, float(source))   # O(n) — list 앞 삽입
```

**수정 방향: `deque(maxlen=...)` + `appendleft` 로 O(1) 전환:**

```python
from collections import deque

_VALUEWHEN_MAX_HIST: int = 500  # 최대 저장 occurrence 수 (Pine 기본 max_bars_back)

def ta_valuewhen(
    state: IndicatorState,
    node_id: int,
    cond: Any,
    source: Any,
    occurrence: int,
) -> float:
    """Pine `ta.valuewhen(cond, source, occurrence)`.

    occurrence=0: 가장 최근 cond=true 시점의 source 값.
    최대 _VALUEWHEN_MAX_HIST개 true-event 저장.
    """
    # occurrence 유효성 검사
    if not isinstance(occurrence, int):
        occurrence = int(occurrence)  # Pine의 암묵적 float→int 변환
    if occurrence < 0:
        return float("nan")           # Pine 미지원 음수 occurrence

    slot = state.buffers.setdefault(node_id, {"history": deque(maxlen=_VALUEWHEN_MAX_HIST)})
    hist: deque[float] = slot["history"]

    cond_bool = bool(cond) if not _is_na(cond) else False
    if cond_bool and source is not None and not _is_na(source):
        hist.appendleft(float(source))   # O(1), maxlen 초과 시 오른쪽 자동 제거

    if occurrence >= len(hist):
        return float("nan")
    return hist[occurrence]
```

**⚠️ 기존 테스트 호환성:**  
기존 `slot["history"]`가 `list` 타입이었음 → `deque` 로 바꾸면 기존 slot이 있던 경우 타입 불일치.  
해결: `setdefault` 초기화 타입을 `deque`로 바꾸면 신규 슬롯에는 deque 생성. 하지만 **기존 pickle/직렬화 캐시가 없으므로** 인터프리터 재실행 시 항상 신규 슬롯 → 안전.

**에지 케이스:**

| 케이스                              | 처리 방식                                                |
| ----------------------------------- | -------------------------------------------------------- |
| `occurrence < 0`                    | `float("nan")` 즉시 반환                                 |
| `occurrence` float (Pine 암묵 변환) | `int(occurrence)` 로 truncate                            |
| 조건 501번 발생                     | `maxlen=500` 으로 자동 오래된 항목 제거 → len ≤ 500 보장 |
| `occurrence >= _VALUEWHEN_MAX_HIST` | 항상 nan — 문서 주석으로 명시                            |
| `cond = na`                         | `cond_bool = False` → 기록 안 함                         |
| `source = na`                       | `_is_na(source)` → 기록 안 함                            |

**테스트 추가:**

```python
def test_valuewhen_occurrence_cap():
    """501번 true → hist len은 500 이하."""

def test_valuewhen_negative_occurrence():
    """occurrence=-1 → nan."""

def test_valuewhen_float_occurrence():
    """occurrence=1.0 → int(1)로 처리."""

def test_valuewhen_o1_performance():
    """10000 bar 실행 시 insert가 O(1)인지 deque appendleft 사용 확인."""
```

---

### B-3. User Function Call-Site별 ta.\* 상태 격리

**파일:**

- `backend/src/strategy/pine_v2/stdlib/stdlib.py` (`StdlibDispatcher`)
- `backend/src/strategy/pine_v2/interpreter.py` (`_call_user_function`)

**문제 정확 진단:**

- `StdlibDispatcher.call(func_name, node_id: int, args, ...)` 에서 `node_id`는 AST 노드 식별자
- user function 내부 `ta.ema(close, 14)` → 항상 같은 AST node_id
- main 스크립트에서 같은 함수를 두 call-site에서 호출하면 → 동일 node_id → 동일 EMA 버퍼 공유 → 결과 오염

**수정 방향:**

#### stdlib.py — StdlibDispatcher 확장

`StdlibDispatcher`는 `@dataclass`. 새 인스턴스 변수는 반드시 `__post_init__`에 추가:

```python
@dataclass
class StdlibDispatcher:
    """Pine 함수명 → 호출 로직."""
    state: IndicatorState = field(default_factory=IndicatorState)

    def __post_init__(self) -> None:
        # @dataclass __init__ 이후 초기화 — dataclass field 아닌 인스턴스 변수
        self._prefix_stack: list[str] = []

    def push_call_prefix(self, prefix: str) -> None:
        self._prefix_stack.append(prefix)

    def pop_call_prefix(self) -> None:
        if self._prefix_stack:
            self._prefix_stack.pop()

    def _scoped_node_id(self, node_id: int) -> int:
        """call-site prefix를 포함한 합성 node_id 반환.

        prefix 없으면 원본 node_id 그대로.
        prefix 있으면 prefix hash와 node_id를 결합한 정수.
        정수 타입을 유지해 기존 buffers dict 키 타입과 호환.
        """
        if not self._prefix_stack:
            return node_id
        # prefix hash + node_id 결합 — 충돌 위험 낮음 (prefix는 고유 AST 위치)
        prefix_hash = hash("::".join(self._prefix_stack)) & 0xFFFF_FFFF
        return (prefix_hash << 32) | (node_id & 0xFFFF_FFFF)

    def call(
        self,
        func_name: str,
        node_id: int,
        args: list[Any],
        *,
        high: float = float("nan"),
        low: float = float("nan"),
        close_prev: float = float("nan"),
    ) -> Any:
        scoped_id = self._scoped_node_id(node_id)   # ← 여기서 치환
        # 이후 모든 state 접근에 scoped_id 사용 (기존 node_id 변수 대체)
        ...
```

> **타입 유지 이유:** `node_id`가 `int`인 기존 계약 유지. prefix 해시를 상위 32bit에 pack — `buffers` dict 키가 `int`이므로 타입 호환.

#### interpreter.py — `_call_user_function` 수정

```python
def _call_user_function(self, fn_def: Any, call_node: Any) -> Any:
    if len(self._scope_stack) >= self._max_call_depth:
        raise PineRuntimeError(f"user function call depth exceeded: {fn_def.name}")

    # call-site 식별자: node_id 우선, 없으면 AST lineno+col, 최후 메모리 주소
    call_prefix = str(
        getattr(call_node, "node_id", None)
        or getattr(call_node, "lineno", None)
        or id(call_node)
    )
    self.stdlib.push_call_prefix(call_prefix)

    # 인자 평가는 push 이후 — caller context에서 평가
    actual_args = [
        self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a)
        for a in call_node.args
    ]
    params = [p.name for p in fn_def.args]
    if len(actual_args) != len(params):
        raise PineRuntimeError(
            f"function '{fn_def.name}': expected {len(params)} args, got {len(actual_args)}"
        )

    frame: dict[str, Any] = dict(zip(params, actual_args, strict=True))
    self._scope_stack.append(frame)
    try:
        last_expr_val: Any = None
        for stmt in fn_def.body:
            if isinstance(stmt, pyne_ast.Expr):
                inner = stmt.value
                if isinstance(inner, pyne_ast.If):
                    self._exec_if(inner)
                    continue
                if isinstance(inner, pyne_ast.Tuple):
                    last_expr_val = tuple(self._eval_expr(e) for e in inner.elts)
                else:
                    last_expr_val = self._eval_expr(inner)
            else:
                self._exec_stmt(stmt)
        return last_expr_val
    finally:
        # LIFO 순서: scope 먼저 pop, 그 다음 prefix pop
        self._scope_stack.pop()
        self.stdlib.pop_call_prefix()
```

**에지 케이스:**

| 케이스                       | 처리 방식                                                                                                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 0-argument function          | `params=[]`, `actual_args=[]`, `zip` → 빈 frame. 정상 동작                                                  |
| 재귀 호출 (A→A)              | prefix_stack `[A, A, ...]` 성장 — scoped_id 각기 다름 → 각 재귀 레벨 독립 state. `max_call_depth` 이미 보호 |
| 상호 재귀 (A→B→A)            | prefix_stack `[A, B, A, ...]` — 동일하게 독립 state                                                         |
| `call_node.node_id` 없음     | `lineno` fallback, 없으면 `id(call_node)`. 동일 run 내에서는 stable                                         |
| `push` 중 예외 발생          | `push_call_prefix` 성공 후 `push` 직후 예외 시 `finally`에서 `pop` 실행 → stack 정합성 유지                 |
| 빈 `_prefix_stack`에서 `pop` | `if self._prefix_stack:` 가드로 보호                                                                        |

**테스트 추가:**

```python
def test_user_fn_two_callsites_independent_ema():
    """동일 함수 두 call-site: 각각 다른 source → EMA 결과 독립적."""
    script = """
    calcEma(src, len) =>
        ta.ema(src, len)
    a = calcEma(close, 14)
    b = calcEma(open, 14)
    """
    result = run_pine(script, ...)
    # a와 b가 다른 값이어야 함 (같으면 state 공유 버그)
    assert result["a"] != result["b"]

def test_s3_rsid_regression():
    """기존 s3_rsid strict=True E2E 회귀 없음."""

def test_user_fn_zero_args():
    """0-argument user function 정상 실행."""
```

---

### B-4. `request.security` Unsupported Coverage 명시

**파일:** `backend/src/strategy/pine_v2/coverage.py`

**현재 상태:**

- `CoverageReport` 필드명: `unsupported_functions`, `unsupported_attributes` (실측 확인)
- `request.security` → Sprint 8c에서 runtime NOP 구현
- Coverage 정적 분석이 `request.security`를 감지하는지 불명확

**수정 방향:**

```python
# coverage.py — 기존 SUPPORTED_FUNCTIONS 또는 별도 세트에 추가

# MTF/외부 데이터 함수 — 런타임 NOP + 명시적 unsupported 표시
_KNOWN_UNSUPPORTED_FUNCTIONS: frozenset[str] = frozenset({
    "request.security",      # 멀티-타임프레임 — H2+ 예정
    "request.dividends",     # 배당 데이터
    "request.earnings",      # 실적 데이터
    "request.quandl",        # Quandl 데이터
    "request.financial",     # 재무 데이터
    "ticker.new",            # 복합 심볼
})

# analyze_coverage 내부 — 함수 감지 후 unsupported_functions 포함 로직
# 주석/문자열 false positive 방지: 기존 _is_pine_namespace() 가드 활용
```

**API 응답 필드명 정합:**

`/api/v1/strategies/{id}/parse-preview` 응답의 `coverage` 객체:

```json
{
  "coverage": {
    "used_functions": ["ta.ema", "ta.rsi"],
    "used_attributes": ["strategy.position_size"],
    "unsupported_functions": ["request.security"],   ← 실제 필드명
    "unsupported_attributes": []
  }
}
```

**FE TabParse 메시지 매핑 (참고):**

| 함수                | 사용자 표시 메시지                              |
| ------------------- | ----------------------------------------------- |
| `request.security`  | "멀티-타임프레임 데이터 미지원 (H2+ 지원 예정)" |
| `request.dividends` | "배당 데이터 미지원"                            |
| 그 외 `request.*`   | "외부 데이터 요청 미지원"                       |

**에지 케이스:**

| 케이스                              | 처리 방식                                                                                                                   |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `# request.security` 주석 내 등장   | coverage.py 정적 분석 regex가 주석을 포함할 수 있음 → 기존 분석기 동작 확인 필요 (false positive 허용 — 보수적 차단이 안전) |
| `"request.security"` 문자열 리터럴  | 마찬가지로 false positive 가능 — 보수적 처리 유지                                                                           |
| runtime에서 `request.security` 호출 | pre-flight에서 차단됨. 만약 통과한 경우 → NOP + `PineRuntimeWarning` 로깅 (optional)                                        |

**완료 기준:**

- `request.security` 포함 Pine 스크립트 parse-preview → `coverage.unsupported_functions`에 포함
- Phase A T5 재검증 PASS

---

## 회귀 검증 명령

```bash
cd backend

# pine_v2 전용 (빠름)
uv run pytest tests/strategy/pine_v2/ -v

# 전체 백엔드
uv run pytest tests/ -q                         # 985+ green

# Mutation Oracle (선택적 — CI 예산 보호, nightly only)
uv run pytest tests/ --run-mutations -v         # 8/8 PASS

# 타입 체크
uv run mypy src/strategy/pine_v2/               # 에러 0
```

---

## 완료 기준 (Gate-B)

| 항목               | 검증 방법                                    | 기준                           |
| ------------------ | -------------------------------------------- | ------------------------------ |
| `_var_series` cap  | ring buffer 테스트 + mypy                    | deque[Any] 타입, maxlen=500    |
| RunResult 호환     | `test_runresult_var_series_list_type`        | 값이 list 타입                 |
| `valuewhen` cap    | `test_valuewhen_occurrence_cap`              | len ≤ 500, O(1) appendleft     |
| User function 격리 | `test_user_fn_two_callsites_independent_ema` | a ≠ b                          |
| s3_rsid 회귀       | E2E strict=True                              | 기존 trade count 유지          |
| request.security   | parse-preview API 응답                       | `unsupported_functions`에 포함 |
| 전체 테스트        | `pytest tests/ -q`                           | 985+ green                     |
| mypy               | `mypy src/strategy/pine_v2/`                 | 0 에러                         |

---

## 브랜치

`feat/h2s1-pine-v2-h2` → squash merge → `stage/h2-sprint1`

**커밋:**

```
c2 feat(pine-v2): _var_series deque ring buffer (max_bars_back=500) + RunResult list compat
c3 feat(pine-v2): valuewhen deque appendleft O(1) + cap 500 + edge case guards
c4 feat(pine-v2): user function call-site ta.* state isolation via prefix stack
c5 feat(pine-v2): request.security explicit unsupported_functions coverage
```
