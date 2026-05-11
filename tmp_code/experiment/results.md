# Pine Script 호환성 실험 결과

> C-text/C-ast: LLM 없이 AST 슬라이싱만 실행. A: 전체 코드 Claude API 직접 전달.
> 실행 일시: 2026-05-12

## 성능 측정 결과

| Approach | Script                 | Runnable                                             | Tokens | Lines | Ratio | Lat(ms) |
|----------|------------------------|------------------------------------------------------|--------|-------|-------|---------|
| C-text   | DrFXGOD (hard)         | ✅                                                   |    606 |   25 | 0.03  |      0 |
| C-ast    | DrFXGOD (hard)         | ✅                                                   |    606 |   25 | 0.03  |      0 |
| A        | DrFXGOD (hard)         | ⚠️ (ANTHROPIC_API_KEY 환경변수 미설정)                 |      0 |    0 | N/A   |      0 |
| C-text   | LuxAlgo (medium)       | ✅                                                   |    329 |   28 | 0.23  |      0 |
| C-ast    | LuxAlgo (medium)       | ✅                                                   |    329 |   28 | 0.23  |      0 |
| A        | LuxAlgo (medium)       | ⚠️ (ANTHROPIC_API_KEY 환경변수 미설정)                 |      0 |    0 | N/A   |      0 |
| C-text   | SupplyDemand (medium-h | ✅                                                   |    184 |   14 | 0.18  |      0 |
| C-ast    | SupplyDemand (medium-h | ✅                                                   |    184 |   14 | 0.18  |      0 |
| A        | SupplyDemand (medium-h | ⚠️ (ANTHROPIC_API_KEY 환경변수 미설정)                 |      0 |    0 | N/A   |      0 |

**Ratio**: slicing_ratio = (sliced_tokens / original_tokens). reduction = 1 - ratio.

## 수동 평가 — Signal Accuracy (DrFXGOD)

원본 신호: `bull = ta.crossover(close, supertrend) and close >= sma9`

DrFXGOD는 `plotshape()` / `strategy.entry()` 대신 `label.new()` 패턴으로 신호를 시각화함.
현재 SignalExtractor는 `label.new()` 조건 추출을 미지원 → `signal_vars=[]` (탐지 실패).

| Approach | Script | 원본 신호 패턴 | signal_vars 탐지 결과 | 일치율 |
|----------|--------|--------------|----------------------|-------|
| C-text | DrFXGOD | `bull` (crossover + close >= sma9) | `[]` — label.new 미지원 | 0% |
| C-ast  | DrFXGOD | `bull` (crossover + close >= sma9) | `[]` — label.new 미지원 | 0% |
| A      | DrFXGOD | `bull` (crossover + close >= sma9) | API key 미설정으로 미실행 | N/A |

### 발견 사항: label.new 패턴 미지원 (신규 BL 후보)

DrFXGOD 코드 내 신호 표시 방식:
```pine
buy  = bull and nbuysell and smartsignalsonly == false ? label.new(bar_index, y1, ...) : na
```

SignalExtractor가 탐지하는 패턴:
- `plotshape(series, ...)` — series 첫 번째 인자에서 변수 추출
- `strategy.entry(id, direction, ...)` — direction 인자 기반 추출

지원하지 않는 패턴:
- `label.new(bar_index, price, text, ...)` — 조건이 삼항 연산자 외부에 있음
- `alertcondition(bull, ...)` — alert 기반 신호 (line 489: `alertcondition(bull, title='Buy Signal')`)

**권고**: `alertcondition()` 첫 번째 인자 추출을 추가하면 DrFXGOD 케이스에서 `bull` 탐지 가능.

## 슬라이싱 효율

| Script | 원본 라인 수 | 슬라이싱 후 라인 | 토큰 감소율 |
|--------|------------|----------------|-----------|
| DrFXGOD (hard, ~524 lines) | ~524 | 25 | 97% |
| LuxAlgo (medium, ~120 lines) | ~120 | 28 | 77% |
| SupplyDemand (medium-hard, ~78 lines) | ~78 | 14 | 82% |

C-text와 C-ast의 출력이 동일함 — 현재 구현에서 두 모드의 슬라이싱 결과가 일치.

## 결론

- **C-text/C-ast 전 케이스 runnable=True** (6/6): 슬라이싱 자체는 성공.
- **signal_vars 탐지 실패 (DrFXGOD)**: `label.new()` 기반 스크립트에서 신호 변수 추출 불가.
- **C-text vs C-ast 차이**: 현재 구현에서 동일 결과 — AST 파싱 기반이지만 출력 코드가 같은 슬라이싱 로직 사용.
- **추천 프로덕션 방식**: 슬라이싱 후 LLM 전달 (C-text 또는 C-ast) — API key 없이도 토큰 77~97% 감소.
- **LLM 없이 실행 가능한 케이스**: 6/6 (슬라이싱 단계), 신호 탐지 성공은 0/6 (DrFXGOD) ~ 미측정 (LuxAlgo/SupplyDemand).

### 다음 단계 (신규 BL 후보)

1. `alertcondition()` 첫 번째 인자 신호 추출 지원 → DrFXGOD 케이스 해결
2. C-text vs C-ast 출력 다양화 — 현재 동일 결과; AST walk 기반 더 정밀한 의존성 분석 필요
3. Approach A 실측 (ANTHROPIC_API_KEY 설정 후) — LLM 변환 품질 vs 슬라이싱 방식 비교
