# Pine Script 전략 분류 분석 결과

> **Assignment:** TV 상위 전략 50개 분류
> **실행일:** 2026-04-14
> **데이터 소스:** GitHub 오픈소스 Pine Script 전략 7개 저장소
> **판정:** ADJUST (파서 확장 필요, 확장 후 GO)

---

## 분류 통계

| 분류 | 수량 | 비율 | 설명 |
|------|------|------|------|
| **SUPPORTED** | 14 | 28% | MVP regex 파서로 즉시 지원 가능 |
| **EXTENDABLE** | 20 | 40% | var, for, 추가 ta.* 함수로 지원 가능 |
| **UNSUPPORTED** | 15 | 30% | request.security, arrays, 복잡한 로직 |
| **REPAINTING** | 1 | 2% | lookahead 명시적 사용 |

## Go/No-Go 판정

- SUPPORTED만: 14/50 (28%) → **PIVOT 기준 해당**
- SUPPORTED + EXTENDABLE: 34/50 (68%) → **GO 기준 초과**
- **판정: ADJUST** — 파서 확장 계획 수립 후 GO

## SUPPORTED 패턴 (14개, 28%)

가장 빈번한 패턴:
- `ta.rsi` + `ta.crossover`/`ta.crossunder` + `strategy.entry`/`strategy.close`
- SMA/EMA crossover (2개 MA, crossover 감지)
- Supertrend 방향 전환 (`ta.supertrend` + `ta.change`)
- BB 터치/돌파
- RSI 과매수/과매도

**대표 전략:** RSI Strategy, Supertrend, Bollinger Breakout, SMA Crossover, 3 EMA Cross, MACD Long

## EXTENDABLE 패턴 분석 (20개, 40%)

| 확장 필요 기능 | 해당 전략 수 | 우선순위 |
|---------------|-------------|---------|
| `var` 변수 (상태 추적) | 8 | **P0** |
| `for` 루프 (lookback 계산) | 5 | **P1** |
| 추가 ta.* 함수 (dmi, stoch, atr) | 7 | **P1** |
| 단순 커스텀 함수 (인라인 래퍼) | 4 | **P2** |
| `ta.valuewhen`, `ta.barssince`, `ta.highestbars` | 3 | **P2** |
| StochRSI (ta.stoch + ta.rsi 조합) | 2 | **P1** |

### 파서 확장 로드맵

| Phase | 추가 기능 | 예상 커버리지 |
|-------|----------|-------------|
| MVP (즉시) | SMA/EMA/RSI/MACD/BB/Supertrend + crossover | 28% |
| 1차 확장 | + `var`, `for`, `ta.dmi`, `ta.stoch`, `ta.atr` | 48% |
| 2차 확장 | + 단순 커스텀 함수, `ta.valuewhen`, `ta.barssince` | 68% |
| LLM 전환 | regex → LLM 트랜스파일 | 80%+ (추정) |
| MTF 지원 | + `request.security` | 90%+ |

## UNSUPPORTED 원인 분석 (15개, 30%)

| 원인 | 수량 | 비율(UNSUPPORTED 중) |
|------|------|---------------------|
| `request.security()` (MTF) | 12 | **80%** |
| `array.*` 연산 | 2 | 13% |
| 복잡한 상태 머신 + pyramiding | 1 | 7% |

**핵심 인사이트:** `request.security()`만 해결하면 UNSUPPORTED의 80%가 해소됨. 단, 이는 백테스트 엔진에서 멀티타임프레임 데이터 주입 아키텍처가 필요한 중간 규모 작업.

### request.security() 사용 패턴

- MTF EMA/RSI/MACD/BB (상위 타임프레임 트렌드 확인)
- Heikin Ashi 캔들 (`ticker.heikinashi` + `request.security`)
- 비교 심볼 (SPY 상대 강도 등)
- 온체인 데이터 (INTOTHEBLOCK 등)

## REPAINTING 감지 패턴 (1개)

- `lookahead=barmerge.lookahead_on` — 명시적 미래 데이터 참조
- MVP 파서에서 이 패턴을 감지하여 **경고 플래그** 표시 필요
- 추가 감지 대상: `barstate.isrealtime`, `calc_on_every_tick=true`

## MVP 파서 결정 사항

### 즉시 지원 (regex 화이트리스트)

```
인디케이터:
  ta.sma, ta.ema, ta.rsi, ta.macd, ta.bb (ta.sma + ta.stdev)
  ta.supertrend, ta.atr, ta.crossover, ta.crossunder, ta.change

진입/청산:
  strategy.entry, strategy.close, strategy.exit

조건:
  단일 if 블록, and/or 연산자, 비교 연산자 (>, <, >=, <=, ==)
  ta.crossover(a, b), ta.crossunder(a, b)

파라미터:
  input.int, input.float, input.bool, input.string
```

### 미지원 시 명확한 Unsupported 반환

```
감지 → Unsupported 함수 목록 표시:
  "이 전략은 다음 함수를 사용하여 현재 지원하지 않습니다:
   - request.security() (멀티타임프레임)
   - array.push() (배열 연산)
   지원 요청에 투표해주세요."
```

## 데이터 소스

- [Alorse/pinescript-strategies](https://github.com/Alorse/pinescript-strategies) — 48개 전략 (주요 소스)
- [grinay/geektrade-strategies](https://github.com/grinay/geektrade-strategies) — 2개 (고급)
- [NinjaView/Pinescript](https://github.com/NinjaView/Pinescript) — 3개
- [Salikha003/PineScripts](https://github.com/Salikha003/PineScripts) — 3개
- 기타 소규모 저장소 4개
