# ADR-016: Sprint Y1 — Pre-flight Pine Coverage Analyzer (Trust Layer 사용자 축 완성)

> **상태:** 회고 (사후 기록, 2026-04-23 작성) · **Trust Layer 엔지니어 축 (Path β) 의 prerequisite**
> **일자:** 2026-04-23 (PR #61 merge)
> **브랜치:** `feat/sprint-y1-pine-coverage-analyzer`
> **관련 ADR:** [ADR-011 Pine v4](./011-pine-execution-strategy-v4.md), [ADR-013 Trust Layer CI](./013-trust-layer-ci-design.md) (후속)
> **상위 문서:** [`04_architecture/trust-layer-architecture.md`](../04_architecture/trust-layer-architecture.md)

---

## 1. 배경 — Whack-a-mole 의 종식

Sprint 8a ~ 8c + X1+X3 완료 후 dogfood 시도 과정에서 발견된 패턴:

```
1. backtest 실행 → FAILED "Call to 'ta.sar' not supported"
2. ta.sar 추가 → PR merge
3. backtest 재실행 → FAILED "Call to 'ta.rma' not supported"
4. ta.rma 추가 → PR merge
5. backtest 재실행 → FAILED "Attribute access not supported: ta.tr"
6. ta.tr 추가 → PR merge
7. backtest 재실행 → FAILED "Call to 'fixnan' not supported"
... (무한)
```

매 반복마다 docker rebuild + 5~10분 대기 + 감정적 피로. 사용자 관점에서 "내가 돈 내고 쓸 품질" 미달 (dogfood-first 철학 ↔ 실제 경험 불일치).

근본 원인: **backtest 실행 시점에서야** 미지원이 드러남. 실행 전에 체크할 장치가 없었다.

---

## 2. 결정 요약

> **`backend/src/strategy/pine_v2/coverage.py` 를 SSOT 로 하고, strategy 등록/수정/백테스트 시점에서 pre-flight 로 `analyze_coverage(source)` 를 호출해 `is_runnable=false` 면 422 로 reject 한다.**

### 2.1 SSOT 구조

`SUPPORTED_FUNCTIONS` (91 항목) + `SUPPORTED_ATTRIBUTES` (21 항목) + `SUPPORTED_ENUM_CONSTANTS` (40+ 항목).

그룹별 분류:

- `_TA_FUNCTIONS` (17): ta.sma, ta.ema, ta.rsi, ta.pivothigh, ta.sar, ta.barssince, ta.valuewhen, ...
- `_STRATEGY_FUNCTIONS` (4): strategy.entry/close/close_all/exit
- `_UTILITY_FUNCTIONS` (2): na, nz
- `_DECLARATION_FUNCTIONS` (3): indicator, strategy, library
- `_PLOT_FUNCTIONS` (18): plot, plotshape, bgcolor, label.new, box.new, alertcondition, alert, color.new, ...
- `_INPUT_FUNCTIONS` (12): input, input.int, input.float, input.source, input.timeframe, ...
- `_STRING_FUNCTIONS` (7): str.tostring, str.format, tostring, request.security (NOP), ...
- `_MATH_FUNCTIONS` (14): math.max/min/abs/sqrt/log/pow/round/...
- `_V4_ALIASES` (14): rma, sma, ema, rsi, atr, iff, switch, ...

### 2.2 호출 위치

- `POST /api/v1/strategies` (create) → parse_preview 시 자동 호출 → 응답에 `coverage.unsupported_builtins` 포함
- `PATCH /api/v1/strategies/{id}` (update) → 동일
- `POST /api/v1/backtests` → re-check, `is_runnable=false` 시 **422 StrategyNotRunnable**

### 2.3 Regex 기반 구현 (정밀 AST 는 Path β Stage 1+ 로 이연)

현재 `analyze_coverage` 는 **regex 기반** (빠르고 단순). Limitation:

- false positive: 사용자 변수 method (예: `myObj.supertrend()`)
- false negative: 문자열 리터럴 안의 함수명 (예: `'alert(...)'` 주석)

**결정**: 이 한계를 수용. 실사용 패턴에서 문제가 된 적 없음. **AST 기반 정밀화 는 Path γ** (Coverage Analyzer AST 기반, 2~3일) 로 이연 — 우선순위 데이터 (dogfood 피드백) 후 재평가.

---

## 3. UX 변화

### 3.1 Strategy Edit — TabParse

`parse_preview` 응답에 `coverage.unsupported_builtins=[...]` 포함 시 **노란 경고 박스**:

```
⚠️ 미지원 (3건): fixnan, ta.supertrend, request.security
   이 전략은 백테스트 실행이 차단됩니다. 지원 함수 목록:
   [docs/02_domain/supported-indicators.md]
```

### 3.2 Backtest 생성 — 422 Reject

```json
POST /api/v1/backtests
→ 422 {
  "detail": {
    "error": "strategy_not_runnable",
    "strategy_id": "...",
    "unsupported_functions": ["fixnan", "ta.supertrend"],
    "unsupported_attributes": [],
    "unsupported_enum_constants": [],
    "message": "전략의 일부 함수/속성을 QuantBridge 가 아직 지원하지 않습니다."
  }
}
```

---

## 4. 테스트 & 결과

| 항목                  |       직전 (Sprint X1+X3)        |       Sprint Y1 말 (PR #61)       |
| --------------------- | :------------------------------: | :-------------------------------: |
| backend tests         |               946                |           **961 (+15)**           |
| FE tests              |               167                |            167 (동일)             |
| i3_drfx 백테스트 시도 | 실행 도중 FAILED (ta.supertrend) |        **사전 422 reject**        |
| 평균 실패 UX 시간     |   docker rebuild + wait 5~10분   | **즉시** (parse_preview 응답 <1s) |

---

## 5. Trust Layer 철학 정합 (Path β prerequisite)

Sprint Y1 은 **Trust Layer 의 사용자 축** 을 완성한다. Path β 의 **엔지니어 축** 은 이 SSOT 를 활용:

| 축                  |   Sprint    | 역할                                                                             |
| ------------------- | :---------: | -------------------------------------------------------------------------------- |
| **사용자 facing**   | Y1 (본 ADR) | 실행 전에 unsupported 명시 → 422 reject                                          |
| **엔지니어 facing** |   Path β    | coverage.py SSOT ⟺ 실제 stdlib/interpreter 동기화 (P-2) + 실행 결과 재현성 (P-3) |

두 축이 맞물려야 완전한 Trust Layer. Y1 없이 Path β 만 하면 "CI 는 통과하는데 사용자는 매일 whack-a-mole", Y1 만 하면 "사용자 경험은 좋은데 코드 regression silent".

### 핵심 제약: coverage.py 는 3 파일 동시 갱신 규약

stdlib 에 새 함수 추가 시:

1. `stdlib.py` 에 구현
2. `interpreter.py` 의 `_STDLIB_NAMES` 또는 dispatch 에 등록
3. `coverage.py` 의 해당 group frozenset 에 추가

**이 규약의 위반** 이 whack-a-mole 원인이었고, **Path β P-2 (Coverage SSOT Sync)** 가 이를 CI 에서 자동 포착한다 — ADR-013 §4.2 참조.

---

## 6. 학습

### L-1: 사용자 UX 의 "예측 가능성" 이 trust 의 핵심

- 실패 자체보다 **"언제 어떻게 실패하는지 모르는 상태"** 가 trust 를 깨뜨린다
- Pre-flight coverage 는 "빠른 실패" — 실행 전에 알려주는 것만으로 UX 점수 급상승 (주관 평가: 6/10 → 9/10)

### L-2: SSOT 1개 규약이 whack-a-mole 을 구조적으로 제거

- Sprint 8a~8c 에서 누적된 patch (ta.rma, ta.sar, ta.tr, fixnan 후보 등) 를 **목록으로 고정** 하는 것만으로 종식
- 목록이 거짓말을 하지 않도록 P-2 (Coverage SSOT Sync) 로 CI 자동화 — Path β 로 이어짐

### L-3: Regex 시작 → 필요 시 AST 정밀화 전략이 실용적

- MVP 는 regex 로 빠르게 ship → 실사용에서 문제 없으면 AST 투자 안 함
- Path γ 로 AST 기반 정밀화 후보 두되, 실제 착수는 dogfood 피드백 기반

### L-4: "Coverage Analyzer 가 Y1 sprint 1 건 가치" 라는 직관

- X1+X3 끝난 뒤 "Bulk stdlib 추가" 의 유혹이 있었으나, SUPPORTED set 을 SSOT 로 고정하는 작업이 **이후 모든 stdlib 확장의 기반** 이 됨
- 작은 구조적 투자가 큰 UX + 엔지니어 생산성 이득

---

## 7. 영향

### 코드

- `backend/src/strategy/pine_v2/coverage.py` 신규 (~260 줄)
- `backend/src/strategy/service.py` 에 parse_preview coverage 통합
- `backend/src/backtest/service.py` 에 pre-flight re-check + 422 raise
- FE: `TabParse` 에 unsupported 경고 박스 + 링크

### Trust Layer 의 관점

- Path β ADR-013 의 P-2 가 coverage.py SSOT 를 양방향 검증 (coverage ↔ stdlib/interpreter 리플렉션)
- P-1 의 pynescript baseline 확장 대상에 coverage 영향 없음 (coverage 는 QB 자체 자산, pynescript 는 외부 파서)

### 문서

- `02_domain/supported-indicators.md` (FE 링크 대상, 기존 존재)
- `01_requirements/pine-coverage-assignment.md` (기존 존재, Y1 이 공식화)

---

## 8. 다음 단계

- [x] Path β ADR-013 에 Y1 prerequisite 로 명시
- [ ] Path β P-2 Coverage SSOT Sync 구현 (Stage 2)
- [ ] Coverage AST 정밀화 (Path γ 후보, 2~3일)
- [ ] `supported-indicators.md` 의 list 자동 생성 (coverage.py 파싱) — H2 검토

---

## 9. 변경 이력

| 날짜       | 사유                  | 변경                                                             |
| ---------- | --------------------- | ---------------------------------------------------------------- |
| 2026-04-23 | 최초 작성 (사후 회고) | Path β Stage 0 Wave B. Y1 결정 근거 + Trust Layer 2 축 관계 명시 |
