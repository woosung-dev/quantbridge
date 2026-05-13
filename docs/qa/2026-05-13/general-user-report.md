# Casual(일반 사용자) Report — QuantBridge Multi-Agent QA 2026-05-13

## Persona

**Non-technical 일반 사용자.** 직관 의존. 도메인 지식 약함. 막히면 포기한다. Pine Script / Sharpe / Drawdown 같은 단어 의미 모른다. 코드 리딩 X — UI 만으로 판단.

## Executive Summary

| 차원                          | 값                                                                                              |
| ----------------------------- | ----------------------------------------------------------------------------------------------- |
| 시나리오 8/8 시도             | 완료 (모바일은 spot check 1회)                                                                  |
| **막힘 지점**                 | **5건 (메이저 3 + 마이너 2)**                                                                   |
| **메뉴 라벨 해독률**          | 약 **67%** (6/9 노출 메뉴 중 4-5개 의미 추측 가능)                                              |
| **모르는 단어**               | **20+ 개** (Pine Script, USDT, Sharpe, Drawdown, slippage, percent_of_equity, Kill Switch 등)   |
| **a11y 합계 violations**      | **22건 / 120+ color-contrast nodes (7개 핵심 페이지)**                                          |
| **데스크톱 UX (1-10)**        | **4/10** — 기능은 동작, 일반 사용자 친화 X                                                      |
| **에러 메시지 친절도 (1-10)** | **3/10** — Pine 파싱 실패 안내 부재 + Optimizer raw JSON 노출                                   |
| **한국어/영어 일관성 (1-10)** | **3/10** — 도메인 용어 영어 그대로 (slippage→슬리피지 음역, Trading Sessions, Manual sizing 등) |
| **Keyboard nav (1-10)**       | **7/10** — skip link + focus visible 정상. Tab 순서 일부 비효율적                               |
| **포기 / 완수**               | "백테스트 실행" 까지 가긴 했지만 모르는 단어 폭격에 도달 시점 **약 8분 + 포기 의지 강함**       |

**Bottom line:** **일반 사용자가 가입 후 첫 백테스트 완수에 도달할 가능성은 매우 낮다.** UI 는 한국어 골격을 갖췄으나 도메인 용어가 영어/축약형으로 노출 + 내부 개발 메타데이터(Sprint 56, BL-186, ADR-013, vectorbt) 가 사용자 화면에 그대로 보임. Optimizer 페이지는 raw Zod JSON 에러를 사용자에게 직접 노출하여 즉시 도주 시각.

---

## 시나리오 결과

### 1. 첫 페이지 의미 추측 (랜딩)

- http://localhost:3100 도착 → **/strategies 로 리다이렉트** ((`casual-01-landing.png`))
- 일반 사용자 추측 첫인상: 메뉴에 "트레이딩", "백테스트", "전략" 노출되어 **"트레이딩 / 투자 관련 사이트"** 로 추측 가능 (★ 좋음)
- 그러나 첫 페이지가 "전략 목록" 이라는 점이 어색 — **"이게 뭐 하는 사이트인지"** 한 줄 설명 없음. Hero / Landing copy 0.

### 2. UX 라이팅 의미 추측

**메뉴 라벨 6개 + 곧 출시 3개**:
| 라벨 | 일반 사용자 의미 추측 가능? |
|---|---|
| 대시보드 | △ (곧 출시) |
| 전략 | ○ |
| 템플릿 | △ (곧 출시) |
| 백테스트 | × (도메인 용어, 약 50% 인식) |
| 트레이딩 | ○ |
| 거래소 | △ (곧 출시) |

**해독률 ≈ 4/6 = 67%**. 핵심 기능 "백테스트" 는 일반 한국인 사용자 모름.

한국어/영어 혼재 심각:

- 메뉴 = 한국어
- 폼 라벨 = "Timeframe", "Trading Sessions", "source", "Manual sizing", "type", "value" 영어
- 코드 값 노출 = `percent_of_equity`, `cash`, `fixed` snake_case 그대로
- 페이지 H1 = "Optimizer (Sprint 56)" (영어 + 내부 메타)

### 3. 막힘 지점 (Stuck Count)

**"백테스트 1건 만들기" 목표 가정 — 5건 막힘**

| #   | 시각 | 페이지                           | 이유                                                                                                                | 일반 사용자 다음 행동 |
| --- | ---- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------- |
| 1   | T+1m | /strategies/new (Step 1)         | "Pine Script" 가 뭔지 모름. 도움말/예시 없음                                                                        | 검색 (이탈 위험 高)   |
| 2   | T+3m | /strategies/new (Step 2)         | 코드 입력 박스 — "어디서 코드 가져와?" TradingView 도 모름                                                          | 포기 시도             |
| 3   | T+5m | /strategies/new (Step 2 invalid) | 잘못된 코드 입력 시 "상태: 오류" 만 표시. 어떻게 고치라는 안내 0                                                    | 포기                  |
| 4   | T+7m | /backtests/new                   | 폼 라벨 영어 + 도메인 용어 폭격 (Timeframe, slippage, percent_of_equity, Trading Sessions, Kill Switch 미리보기 등) | 압도 → 포기           |
| 5   | T+8m | /optimizer                       | h1 "Optimizer (Sprint 56)" + raw JSON 에러 보고 즉시 도주                                                           | 신뢰도 파괴           |

### 4. 핵심 워크플로우 직관성

전략 → Pine 입력 → 백테스트 → 결과 보기.

| 단계                       | "다음에 뭐 해야 하지?" 모호도 (1-10, 낮을수록 좋음)                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------- |
| /strategies "새 전략" 버튼 | 2 ★ (명확)                                                                                          |
| Step 1 입력 방식 선택      | 4 — Pine Script 모름                                                                                |
| Step 2 코드 붙여넣기       | **8** — 코드 어디서? 예시? 템플릿 곧 출시 disabled                                                  |
| Step 3 확인                | (도달 X — 코드 모름)                                                                                |
| /backtests/new 전략 선택   | 5 — 드롭다운에 전략명만, 무엇을 선택해야 할지 hint 없음                                             |
| 백테스트 실행 → 결과       | 6 — 결과 페이지에서 SHARPE / MAX DRAWDOWN / PROFIT FACTOR 영어 헤딩 (★도메인 핵심 지표가 해독 불가) |

### 5. 에러 회복 가능성

- **Pine Script 잘못된 코드 ("xxx invalid yyy") 입력** → 사이드 패널 "상태: 오류" 한 단어. **어떻게 고치라는지 0 안내**. (`casual-04-invalid-pine.png`)
- **빈 폼에서 "백테스트 실행" 클릭** → "전략을 선택하세요" 한국어 alert. ★ OK
- **/optimizer 페이지** → "목록 로드 실패: [{ "expected": "number", "code": "invalid_type", ... }]" raw Zod JSON 직접 노출. 한국어 X. 일반 사용자 = **즉시 신뢰 파괴**. (`casual-09-optimizer.png`)

**평균 친절도: 3/10**.

### 6. axe-core a11y violations

페이지별 표:

| 페이지          | total  | id (impact, nodes)                                                                                                                                                       |
| --------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| /strategies     | 2      | color-contrast (serious, **13**), region (moderate, 1)                                                                                                                   |
| /strategies/new | 3      | aria-prohibited-attr (serious, 1), color-contrast (serious, **9**), region (moderate, 1)                                                                                 |
| /backtests      | 2      | color-contrast (serious, **33**), region (moderate, 1)                                                                                                                   |
| /backtests/new  | 3      | color-contrast (serious, **24**), heading-order (moderate, 1), region (moderate, 1)                                                                                      |
| /backtests/:id  | 3      | color-contrast (serious, **19**), nested-interactive (serious, 2), region (moderate, 1)                                                                                  |
| /trading        | 4      | color-contrast (serious, **16**), empty-table-header (minor, 1), page-has-heading-one (moderate, 1), region (moderate, 1)                                                |
| /optimizer      | 5      | color-contrast (serious, **6**), landmark-main-is-top-level (moderate, 1), landmark-no-duplicate-main (moderate, 1), landmark-unique (moderate, 1), region (moderate, 1) |
| **합계**        | **22** | **color-contrast 120 nodes** + nested-interactive 2 + aria-prohibited-attr 1 + heading-order 1 + empty-table-header 1 + page-has-h1 1 + landmark-x 3 + region 7          |

**핵심**: WCAG 2.1 AA color-contrast 가 전역 문제. 7개 페이지 모두 serious. 일반 사용자 + 시각 약자 모두 영향.

### 7. Keyboard navigation

- ★ **Skip link "본문으로 바로가기" 존재** (좋음)
- Tab 순서: Disclaimer/Terms/Privacy 가 메인 메뉴보다 앞에 옴 → 일반 사용자 5-Tab 후에야 본 메뉴 도달 (비효율)
- focus visible: outline auto 작동 (확인)
- 점수: **7/10** — 작동하지만 Tab 순서 최적화 필요

### 8. 모바일 spot check (375x667)

- 사이드바 0px 로 숨겨짐 (반응형 의도) **그러나 햄버거/메뉴 버튼 부재** → **모바일에서 페이지 간 이동 불가능**. (`casual-10-mobile-strategies.png`)
- bodyScrollWidth (366) > clientWidth (360) → 수평 overflow 발생
- 일반 사용자가 휴대폰에서 도착 시 = "전략 목록 한 화면 만 가능, 다른 메뉴 못 감" = **유실**
- 1-10: **2/10** (네비 부재 = critical)
- (상세는 Mobile 페르소나 영역)

---

## 결함 상세

### BL-280 — Optimizer 페이지에 raw Zod JSON 에러 + 내부 sprint 번호 노출 (Critical, Confidence 10/10)

- **위치**: `/optimizer` H1 + main 본문
- **재현**: http://localhost:3100/optimizer 도착
- **기대**: 한국어 친화적 에러 ("최근 실행 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.") + 페이지 제목 "최적화" (한국어)
- **실제**: H1 = `"Optimizer (Sprint 56)"`, 본문에 `목록 로드 실패: [{ "expected": "number", "code": "invalid_type", "path": [...], "message": "Invalid input: expected number, received null" }, ...]` 가 **raw JSON 으로 사용자에게 노출**. ADR-013 §6, BL-233 등 내부 백로그 ID 도 동시 노출.
- **Severity / Confidence**: P0 / 10
- **추천**: (a) H1 "Optimizer (Sprint 56)" → "최적화" 고정 (b) error boundary 또는 catch 후 일반 한국어 메시지 (c) Zod validation failure 시 sentry 로 보내고 UI 에는 안내만 (d) ADR/BL ID 본문에서 제거

### BL-281 — Pine Script 입력 단계에 "TradingView가 뭔지 모르는 사용자" 가이드 부재 (P1, 9/10)

- **위치**: `/strategies/new` Step 2
- **기대**: "Pine Script 예시 보기" 버튼 / 템플릿 / "TradingView 는 ..." 1줄 설명 + 외부 링크
- **실제**: 빈 Monaco 에디터 + 안내 한 줄 `"TradingView Pine Editor의 코드를 그대로 붙여넣으세요"` — TradingView 의 정체와 접근 경로 0
- **Severity / Confidence**: P1 / 9
- **추천**: Step 2 상단에 "Pine Script 가 뭔가요? / TradingView 에서 어떻게 가져오나요?" expand 가능 help block + 예시 1개 prefill 옵션

### BL-282 — Pine Script 파싱 "오류" 만 표시 / 어떻게 고치라는 안내 부재 (P1, 9/10)

- **위치**: `/strategies/new` Step 2 사이드 패널
- **재현**: `xxx invalid yyy` 같은 비-Pine 텍스트 붙여넣기
- **기대**: "1행 'xxx': 정의되지 않은 함수입니다. Pine Script 5 의 indicator(), strategy() 같은 함수로 시작해야 합니다." 같은 안내 + "예시 보기" CTA
- **실제**: 상태 = "오류" 한 단어. 진입/청산 신호 0. **사용자가 다음에 무엇을 시도해야 하는지 0 정보**.
- **Severity / Confidence**: P1 / 9
- **추천**: pine_v2 파서 에러를 라인/열 + 한국어 설명 + 자주 묻는 실수 link 로 변환

### BL-283 — 백테스트 새 폼에 내부 코드 식별자 + 영어 라벨 + sprint/BL 메타 노출 (P1, 10/10)

- **위치**: `/backtests/new`
- **목록 (예시 6건)**:
  - `Timeframe` 영어 헤딩 (→ "주기" / "시간단위" 권장)
  - `slippage` → "슬리피지" 음역만 (의미 0)
  - `주문 크기 source` (혼용)
  - `Manual sizing`, `Manual 입력 (form 우선)`, `type`, `value` 폼 라벨 영어
  - 라디오 라벨 = `자기자본 % (percent_of_equity)` / `고정 USDT (cash)` / `고정 수량 (fixed)` — **코드 식별자 사용자 UI 노출**
  - `Trading Sessions` 영어 헤딩 + `Asia / London / Ny` (Ny typo)
  - `funding rate / 강제 청산 / 유지 증거금 미반영 (BL-186 후속)` — **백로그 ID 노출**
  - 우측 사이드 패널: `vectorbt 벡터화 엔진 사용` — **라이브러리 이름 노출**
- **Severity / Confidence**: P1 / 10
- **추천**:
  (a) snake_case 코드 식별자 라디오 라벨에서 제거 (값은 form 내부에서만 유지)
  (b) `Timeframe`, `Trading Sessions`, `Manual sizing`, `source`, `type`, `value` 한국어 라벨화
  (c) `Ny` → `NY` 또는 "뉴욕"
  (d) "vectorbt", "BL-186" 같은 내부 메타데이터 사용자 UI 에서 제거
  (e) "슬리피지" → "체결 차이 (슬리피지)" 같이 의미 hint 부가

### BL-284 — 백테스트 결과 핵심 지표 영어 헤딩 (Sharpe / Drawdown / Profit Factor) — Casual 사용자 해독 불가 (P2, 9/10)

- **위치**: `/backtests/:id` 개요 탭
- **실제**: `SHARPE RATIO`, `MAX DRAWDOWN`, `PROFIT FACTOR` 영어 대문자 그대로
- **기대**: 한국어 라벨 + tooltip (예: `샤프 지수 ⓘ` hover 시 "수익 대비 변동성. 1.0 이상 양호").
- **추천**: 24 metric 헤딩 한국어화 + ⓘ tooltip + lesson glossary 페이지

### BL-285 — 모바일 햄버거 메뉴 부재 → 모바일 사용자 페이지 이동 불가 (P0, 9/10)

- **위치**: 모든 라우트, viewport ≤ 768px
- **재현**: 375x667 viewport → 사이드바 0px + 햄버거/메뉴 버튼 0
- **실제**: 일반 사용자가 모바일로 도착 시 "전략 목록" 만 보고 다른 메뉴 클릭 불가능 → 이탈
- **추천**: 헤더에 `aria-label="메뉴 열기"` 햄버거 + drawer/sheet pattern. (Mobile 페르소나 보고와 cross-ref)

### BL-286 — color-contrast WCAG AA 위반 7개 페이지 전역 (120 nodes) (P2, 10/10)

- **위치**: 모든 핵심 페이지
- **추천**: design token 의 muted/secondary text 색상 한 단계 어둡게 + axe-core CI 실행

### BL-287 — 트레이딩 페이지 h1 부재 + 테이블 헤더 빈 cell (P3, 8/10)

- **위치**: `/trading`
- **추천**: H1 "트레이딩" 추가, 액션 컬럼 헤더 `<th><span class="sr-only">액션</span></th>`

### BL-288 — "곧 출시" 메뉴 3건 + Step 1 의 "TV URL / 파일 업로드" disabled — 일반 사용자 기대 vs 실제 격차 (P3, 7/10)

- **위치**: 사이드바 (대시보드 / 템플릿 / 거래소), `/strategies/new` Step 1
- **실제**: 6 메뉴 중 3 메뉴가 "곧 출시" — 클릭 불가능 (절반이 placeholder)
- **추천**: 베타 단계에서는 "곧 출시" 메뉴 숨김 또는 별도 "Coming Soon" 섹션으로 분리

---

## a11y violations 페이지별 표 (재게재)

| 페이지          | impact   | id                         | nodes   | help                      |
| --------------- | -------- | -------------------------- | ------- | ------------------------- |
| /strategies     | serious  | color-contrast             | 13      | min contrast ratio        |
| /strategies     | moderate | region                     | 1       | page content in landmarks |
| /strategies/new | serious  | aria-prohibited-attr       | 1       | permitted ARIA            |
| /strategies/new | serious  | color-contrast             | 9       | contrast                  |
| /strategies/new | moderate | region                     | 1       | landmarks                 |
| /backtests      | serious  | color-contrast             | 33      | contrast                  |
| /backtests      | moderate | region                     | 1       | landmarks                 |
| /backtests/new  | serious  | color-contrast             | 24      | contrast                  |
| /backtests/new  | moderate | heading-order              | 1       | heading levels            |
| /backtests/new  | moderate | region                     | 1       | landmarks                 |
| /backtests/:id  | serious  | color-contrast             | 19      | contrast                  |
| /backtests/:id  | serious  | nested-interactive         | 2       | nested controls           |
| /backtests/:id  | moderate | region                     | 1       | landmarks                 |
| /trading        | serious  | color-contrast             | 16      | contrast                  |
| /trading        | minor    | empty-table-header         | 1       | th text                   |
| /trading        | moderate | page-has-heading-one       | 1       | h1 missing                |
| /trading        | moderate | region                     | 1       | landmarks                 |
| /optimizer      | serious  | color-contrast             | 6       | contrast                  |
| /optimizer      | moderate | landmark-main-is-top-level | 1       | nested main               |
| /optimizer      | moderate | landmark-no-duplicate-main | 1       | duplicate main            |
| /optimizer      | moderate | landmark-unique            | 1       | landmark uniqueness       |
| /optimizer      | moderate | region                     | 1       | landmarks                 |
| **합계**        | —        | —                          | **136** | 22 unique violations      |

---

## 평가 점수 표

| 차원                      | 점수 (1-10)                                  | 비고                                                                                                              |
| ------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 메뉴 라벨 해독률 (%)      | **67%**                                      | 6 메뉴 중 4 추측 가능                                                                                             |
| 모르는 단어 수            | **20+**                                      | Pine Script / USDT / Sharpe / Drawdown / Profit Factor / slippage / percent_of_equity / Kill Switch / vectorbt 등 |
| 막힘 지점 수              | **5건**                                      | 첫 백테스트 도달 전                                                                                               |
| 데스크톱 UX (1-10)        | **4**                                        | 기능 OK / 친화도 X                                                                                                |
| 에러 메시지 친절도 (1-10) | **3**                                        | Pine "오류" + Optimizer raw JSON                                                                                  |
| 한국어/영어 일관성 (1-10) | **3**                                        | 폼 라벨 영어 다수 + snake_case 노출                                                                               |
| axe-core 총 violations    | **22 (nodes 136)**                           | color-contrast 가 다수                                                                                            |
| Keyboard nav (1-10)       | **7**                                        | skip link + focus visible OK                                                                                      |
| 모바일 spot (1-10)        | **2**                                        | 햄버거 부재 = critical                                                                                            |
| 포기 시점 / 완수          | "백테스트 실행" 까지 약 8분 + 강한 포기 의지 |                                                                                                                   |

---

## 강점 (Top 3)

1. **Skip link + focus visible 작동** — 키보드 접근성 기본 잘 잡힘
2. **메뉴 메인 라벨 한국어** — "전략 / 백테스트 / 트레이딩" 3개 핵심 라벨이 한국어 (영어 그대로 두는 경쟁 제품 대비 우월)
3. **빈 폼 클릭 시 한국어 alert** — "전략을 선택하세요" 같은 즉각 폼 검증 메시지는 양호

## 약점 (Top 3)

1. **Optimizer 페이지 raw Zod JSON 에러 + Sprint 56 / BL-233 / ADR-013 / vectorbt 등 내부 메타데이터를 사용자 UI 에 그대로 노출** — 신뢰도 즉시 파괴 (BL-280, BL-283)
2. **도메인 핵심 지표 (Sharpe / Drawdown / Profit Factor) 영어 대문자 그대로 + 폼 라벨 (Timeframe / source / type / value / Manual sizing) 영어** — 일반 한국인 사용자 해독 불가 (BL-283, BL-284)
3. **모바일 햄버거 메뉴 부재 → 모바일 사용자 페이지 이동 0** + **색대비 전역 위반 (120 nodes)** — 모바일/접근성 두 축 모두 critical (BL-285, BL-286)

---

## 메모 (이전 페르소나 발견과 cross-ref)

- Sprint 55/56 FE 누락 / Optimizer 빈 main / "Sprint 56" 노출 → **BL-280 으로 확정 + raw Zod JSON 새 발견 추가**
- 가짜 marketing 수치 → Casual 시나리오에서는 랜딩 페이지 marketing copy 자체 부재. /strategies 가 첫 페이지라 marketing 영역 미도달.
- TTFV 약속 (~0.5초) — 폼에 표시되지만 실측은 다른 페르소나 영역
- 가입 직후 빈 화면 stuck — 실제로는 /strategies 로 리다이렉트되어 stuck 은 아님 (단, "여기서 뭘 해야지?" 라는 직관 부재는 별개 문제)
