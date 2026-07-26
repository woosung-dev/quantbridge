# Pine Script 호환성 실험 설계 — A / B / C-text / C-ast 비교

**날짜:** 2026-05-12  
**스프린트:** Sprint 59 사전 연구  
**목적:** 미지원 함수로 실행 불가한 Pine Script indicator를 strategy로 변환하는 최적 방법을 데이터로 확정

---

## 배경 및 문제

QuantBridge의 `coverage.py`는 미지원 함수가 1개라도 있으면 `is_runnable=False`로 차단한다.  
실제 사용자 indicator의 상당수가 다음 이유로 차단된다.

- 드로잉 API: `array.new_box`, `box.new`, `line.new`, `label.new`, `table.*`
- 멀티 타임프레임: `request.security_lower_tf`, `ticker.new`
- 미구현 TA: `ta.highestbars`, `ta.lowestbars`, `color.from_gradient`, `chart.fg_color`

핵심 인사이트: **신호 조건 자체(bull/bear)는 지원 함수만으로 구성되는 경우가 많다.**  
드로잉 코드와 신호 코드를 분리하면 실행 가능성이 크게 올라간다.

---

## 실험 범위

### 접근법 4가지

| 방식       | 설명                                             | LLM 사용 | 코드 변경 |
| ---------- | ------------------------------------------------ | -------- | --------- |
| **A**      | 전체 코드 → Claude API 직접 (연구용 스크립트)    | 항상     | 없음      |
| **B**      | 전체 코드 → FastAPI 엔드포인트 → Claude          | 항상     | 신규 모듈 |
| **C-text** | 텍스트 슬라이싱 → runnable이면 직접 / 아니면 LLM | 조건부   | 신규 모듈 |
| **C-ast**  | AST 슬라이싱 → runnable이면 직접 / 아니면 LLM    | 조건부   | 신규 모듈 |

### 테스트 스크립트 3개

1. **DrFXGOD_indicator_hard.pine** (기존)
   - 미지원 ~15개 (`array.*`, `request.security_lower_tf`, `ta.bb`, `ta.dmi`, `fixnan` 등)
   - 핵심 신호: `bull = ta.crossover(close, supertrend) and close >= sma9`
   - `supertrend()`는 `ta.atr`만 사용 → C 슬라이싱 후 runnable 기대

2. **LuxAlgo_indicator_medium.pine** (기존)
   - 미지원 0개 (이미 runnable) → baseline / 회귀 검증용
   - 신호: `upos > upos[1]` (ta.pivothigh/pivotlow 기반)

3. **supply_demand_zones_medium_hard.pine** (세션 중 생성)
   - 미지원 6개: `array.new_box`, `box.new`, `ta.highestbars`, `ta.lowestbars`, `chart.fg_color`, `color.from_gradient`
   - 핵심 신호: `ta.pivothigh/pivotlow` + close 비교 (지원 함수만)
   - C 슬라이싱 후 ~50줄 → ~15줄 기대

### 평가 매트릭스

**4 접근법 × 3 스크립트 = 12 케이스**

| 지표              | 측정 방법                               | 자동 |
| ----------------- | --------------------------------------- | ---- |
| `is_runnable`     | `analyze_coverage(result).is_runnable`  | 자동 |
| `trades_count`    | 백테스트 엔진 실행 결과                 | 자동 |
| `input_tokens`    | Claude API `usage.input_tokens`         | 자동 |
| `output_lines`    | 생성 코드 줄 수                         | 자동 |
| `slicing_ratio`   | C-text/C-ast: sliced줄 / original줄     | 자동 |
| `signal_accuracy` | 원본 신호 조건 텍스트 vs 생성 조건 비교 | 수동 |

---

## 아키텍처

### 파일 구조

```
tmp_code/
  experiment/
    runner.py                   — 12 케이스 순차 실행 + 메트릭 수집
    approach_a.py               — 전체 코드 → Claude API (연구용 baseline)
    results.md                  — 자동 생성 비교 테이블
  pine_code/
    DrFXGOD_indicator_hard.pine     (기존)
    LuxAlgo_indicator_medium.pine   (기존)
    supply_demand_zones.pine        (신규 생성)

backend/src/strategy/
  convert/                      — B: API 엔드포인트 (신규 모듈)
    __init__.py
    router.py                   — POST /api/v1/strategies/convert-indicator
    service.py                  — LLM 호출 + 응답 파싱
    prompt.py                   — 프롬프트 템플릿 (A/B/C 공유)
  pine_v2/
    signal_extractor.py         — C: AST 슬라이싱 엔진 (신규)

frontend/
  features/backtest/components/
    BacktestUnsupportedBanner.tsx  — "AI 변환" CTA 추가 (기존 컴포넌트 수정)
```

---

## 상세 설계

### A: 연구용 스크립트 (`approach_a.py`)

```python
def convert_with_full_code(source: str, model: str = "claude-sonnet-4-6") -> ConversionResult:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=CONVERSION_PROMPT,
        messages=[{"role": "user", "content": source}],
    )
    return ConversionResult(
        converted_code=response.content[0].text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
```

A는 B의 엔드포인트를 거치지 않는다. 동일 프롬프트로 직접 호출하여 인프라 overhead 없는 순수 LLM 성능을 측정한다.

> **A vs B 정확도:** 동일 프롬프트 + 동일 모델이므로 `signal_accuracy`는 같아야 한다. B의 차별점은 정확도가 아니라 프로덕션 UX (인증, 에러핸들링, 관찰가능성)다.

---

### B: FastAPI 엔드포인트

**라우터:** `POST /api/v1/strategies/convert-indicator`

```python
class ConvertIndicatorRequest(BaseModel):
    code: str
    strategy_name: str = "Converted Strategy"
    mode: Literal["full", "sliced"] = "full"  # B=full, C=sliced

class ConvertIndicatorResponse(BaseModel):
    converted_code: str
    input_tokens: int
    output_tokens: int
    warnings: list[str]         # 제거된 함수 목록 등
    sliced_from: int | None     # C 모드: 슬라이싱 전 줄 수
    sliced_to: int | None       # C 모드: 슬라이싱 후 줄 수
```

**인증:** 기존 Clerk JWT 미들웨어 재사용  
**설정:** `core/config.py`에 `anthropic_api_key: SecretStr | None` 추가  
**환경변수:** `.env.example`에 `ANTHROPIC_API_KEY=` 추가  
**모델:** `claude-sonnet-4-6` (기본값, config으로 override 가능)

---

### C: Signal Extractor

**파일:** `backend/src/strategy/pine_v2/signal_extractor.py`

```python
@dataclass
class ExtractionResult:
    sliced_code: str
    signal_vars: list[str]          # ['bull', 'bear']
    removed_lines: int
    removed_functions: list[str]
    is_runnable: bool
    token_reduction_pct: float      # (1 - sliced/original) * 100

class SignalExtractor:
    def extract(self, source: str, mode: Literal["text", "ast"] = "ast") -> ExtractionResult:
        ...
```

**알고리즘 — C-text (텍스트 기반):**

```
1. 신호 소스 탐지 (정규식)
   a. strategy.entry(when=<cond>) 패턴
   b. plotshape(<cond>, ...) 패턴
   c. label.new(<var> ? ... : na, ...) 패턴

2. 의존성 역추적 (텍스트 기반, 최대 depth=5)
   필요한 변수명 집합 S = {bull, bear, ...}
   for each var in S:
     regex로 "var =" 또는 "var :=" 라인 찾기
     해당 라인의 우변에서 새 변수명 추출 → S에 추가
   → 사용자 정의 함수 body도 포함

3. 드로잉 API 라인 제거
   array.*, box.*, line.*, label.new, table.*,
   chart.fg_color, color.from_gradient 포함 라인 제거

4. 코드 재조합
   - input() 선언 전부 포함
   - 필요한 라인 원본 순서 유지
   - //@version=5 + strategy() 헤더 추가

5. runnable 판정
   if analyze_coverage(sliced_code).is_runnable:
     → strategy.entry/exit 래퍼 자동 추가 (LLM 없음)
   else:
     → B 엔드포인트에 sliced_code 전달 (mode="sliced")
```

**알고리즘 — C-ast (AST 기반):**

```
위 C-text와 동일하나 Step 1-2가 다름:

1. pynescript.parse(source) → AST tree
2. 신호 소스 탐지: AST Call 노드에서
   - strategy.entry → when= kwarg 추출
   - plotshape → 첫 번째 arg 추출
   - label.new → 첫 번째 arg의 삼항 조건 추출

2. 의존성 역추적 (AST Name 노드 순회)
   condition AST에서 모든 Name 노드 수집 → 필요 변수명
   AST Assign 노드에서 해당 변수 정의 탐색
   → 재귀적으로 우변 Name 노드 추가 수집

강점: 주석/문자열 내 변수명 오탐 없음, 중첩 표현식 정확 처리
```

---

### UI: AI 변환 CTA

**트리거:** coverage 결과에 `unsupported_functions`가 1개 이상일 때  
**위치:** 기존 백테스트 실패 배너 컴포넌트  
**플로우:**

1. "AI로 변환하기" 버튼 클릭
2. `POST /api/v1/strategies/convert-indicator` 호출
3. 응답 코드를 전략 에디터에 표시 (사용자 검토용)
4. "이 코드로 저장" 버튼으로 확정

---

### 공유 프롬프트 템플릿

```
SYSTEM:
당신은 TradingView Pine Script v5 전문가입니다.
아래 indicator 코드를 QuantBridge 실행 가능한 strategy로 변환하세요.

규칙:
1. buy/sell 신호 조건을 strategy.entry("Long", strategy.long, when=<buy_cond>)로 변환
2. 드로잉 코드 완전 제거: box.*, line.*, label.*, table.*, array.*
3. 미지원 데이터: request.security_lower_tf, ticker.new 제거
4. 미지원 색상: chart.fg_color, color.from_gradient 제거
5. input() 파라미터 전부 보존
6. //@version=5 + strategy("이름", overlay=true) 헤더 추가
7. 코드만 반환 (설명/마크다운 없음)

USER: <pine_script_code>
```

---

## 테스트 전략 (TDD)

각 신규 모듈마다 실패 테스트 먼저 작성:

### signal_extractor.py 테스트

```python
# tests/strategy/pine_v2/test_signal_extractor.py
def test_extract_plotshape_signal():
    source = """
    //@version=5
    indicator("Test")
    bull = ta.crossover(close, ta.sma(close, 20))
    some_array = array.new_float(0)  // 미지원
    plotshape(bull, "Buy", shape.triangleup, location.belowbar)
    """
    result = SignalExtractor().extract(source, mode="text")
    assert result.is_runnable
    assert "bull" in result.signal_vars
    assert "array.new_float" not in result.sliced_code

def test_extract_strategy_entry_signal():
    ...  # strategy.entry(when=condition) 케이스

def test_c_text_vs_c_ast_same_output():
    ...  # 동일 입력에서 두 방식이 같은 신호 변수 추출
```

### convert endpoint 테스트

```python
# tests/strategy/convert/test_convert_router.py
def test_convert_indicator_auth_required():
    response = client.post("/api/v1/strategies/convert-indicator", json={...})
    assert response.status_code == 401

def test_convert_indicator_no_api_key():
    # ANTHROPIC_API_KEY 없을 때 503 반환
    ...
```

---

## 구현 순서

1. **3번째 스크립트 생성** — `supply_demand_zones.pine`
2. **C-text 구현 + 테스트** — 의존성 추적 알고리즘 (단순, 빠르게)
3. **C-ast 구현 + 테스트** — AST 기반으로 정확도 향상
4. **B 엔드포인트 구현 + 테스트** — config, router, service, prompt
5. **A 연구 스크립트** — `approach_a.py` (코드 변경 없음)
6. **실험 러너 + 메트릭 수집** — `runner.py`
7. **UI CTA 추가** — BacktestUnsupportedBanner
8. **12 케이스 실행 → results.md 생성**

---

## 성공 기준

최소 1개 접근법이 DrFXGOD에 대해:

- `is_runnable = True`
- `trades_count > 0`
- `signal_accuracy ≥ 80%` (수동 검증)

그리고 C-text vs C-ast 비교에서:

- token_reduction_pct 차이 측정
- signal_accuracy 차이 측정
- 구현 복잡도 vs 정확도 gain 트레이드오프 결론 도출

---

## 미결 사항

- [ ] ANTHROPIC_API_KEY를 `.env.local`에 추가 (사용자 직접)
- [ ] 실험 결과 기반 프로덕션 default 결정 (C-text / C-ast / B 중 선택)
- [ ] C-ast에서 pynescript AST ↔ 원본 소스 라인 매핑 구현 복잡도 검증 필요 (구현 중 발견 시 C-text fallback)

> **C-ast 구현 리스크:** pynescript AST 노드에 소스 라인 번호가 없을 경우 AST 재구성(`_stringify`) 결과물의 문법 정확도가 낮을 수 있다. 구현 착수 전 `pynescript.parse(source)` 결과의 `lineno` 속성 존재 여부를 사전 확인한다. 없으면 C-text로 대체.
