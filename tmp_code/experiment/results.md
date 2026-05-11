# Pine Script 호환성 실험 결과

> C-text/C-ast: LLM 없이 AST 슬라이싱만 실행. A: 전체 코드 Claude API 직접 전달.

| Approach | Script                 | Runnable                                             | Tokens | Lines | Ratio | Lat(ms) |
|----------|------------------------|------------------------------------------------------|--------|-------|-------|---------|
| C-text   | DrFXGOD (hard)         | ✅                                           |    606 |   25 | 0.03  |      0 |
| C-ast    | DrFXGOD (hard)         | ✅                                           |    606 |   25 | 0.03  |      0 |
| A        | DrFXGOD (hard)         | ⚠️ (ANTHROPIC_API_KEY 환경변수 미설정)              |      0 |    0 | N/A   |      0 |
| C-text   | LuxAlgo (medium)       | ✅                                           |    329 |   28 | 0.23  |      0 |
| C-ast    | LuxAlgo (medium)       | ✅                                           |    329 |   28 | 0.23  |      0 |
| A        | LuxAlgo (medium)       | ⚠️ (ANTHROPIC_API_KEY 환경변수 미설정)              |      0 |    0 | N/A   |      0 |
| C-text   | SupplyDemand (medium-h | ✅                                           |    184 |   14 | 0.18  |      0 |
| C-ast    | SupplyDemand (medium-h | ✅                                           |    184 |   14 | 0.18  |      0 |
| A        | SupplyDemand (medium-h | ⚠️ (ANTHROPIC_API_KEY 환경변수 미설정)              |      0 |    0 | N/A   |      0 |

## 수동 평가 — Signal Accuracy

| Approach | Script | 원본 조건 | 생성 조건 | 일치율 |
|----------|--------|----------|---------|-------|
| C-text | DrFXGOD | ta.crossover(close, supertrend) and close >= sma9 | (결과 기입) | ?% |
| C-ast  | DrFXGOD | ta.crossover(close, supertrend) and close >= sma9 | (결과 기입) | ?% |
| A      | DrFXGOD | ta.crossover(close, supertrend) and close >= sma9 | (결과 기입) | ?% |

## 결론

- 추천 프로덕션 방식: (결과 기반 선택)
- C-text vs C-ast 정확도 차이: ?%
- LLM 없이 직접 실행 가능한 케이스 수: ?/9 (A 제외)
