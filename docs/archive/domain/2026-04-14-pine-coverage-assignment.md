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
