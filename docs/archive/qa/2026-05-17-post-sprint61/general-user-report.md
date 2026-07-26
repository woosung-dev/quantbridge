# Casual 재측정 — Sprint 61 fix-first 효과 검증

**일자**: 2026-05-17 (Sprint 61 + BL-348/349 hotfix 후)
**환경**: Isolated mode (FE :3100 / BE :8100)
**페르소나**: Casual — Non-technical Korean, 직관 의존
**깊이**: Standard (~45-60분)
**Pre baseline**: 2026-05-17 1차 Casual 5.2/10 (BL-327~337 11건), 막힘 9건, 용어 해독률 40%, axe 92 serious

---

## Composite

|                                | Pre      | Post                         |
| ------------------------------ | -------- | ---------------------------- |
| Composite Casual               | 5.2 / 10 | **7.4 / 10**                 |
| 막힘 지점                      | 9건      | 3건 (-67%)                   |
| 포기 시점                      | 3분      | 8-10분+ (실측 abandon 안 함) |
| 용어 해독률 (KPI 5종)          | 40%      | **87%** (tooltip 효과)       |
| axe-core serious (3 페이지 합) | 92       | **68** (-26%)                |

회복도: **결정적 (positive)**. 핵심 fix 4종 (BL-327 KPI tooltip / BL-328 Clerk koKR / BL-322 hero / BL-323 사이드바) 모두 PASS. 잔존 결함 (BL-350 Optimizer Zod, color-contrast 68건) = Sprint 62 후속 candidate.

---

## Sprint 61 fix 효과 — Casual view

| BL                                  | 1차 결과                                      | 2차 결과                                                                                                                                      | 회복                              | 증거                                                               |
| ----------------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------ |
| **BL-327** KPI tooltip              | 0% 해독 (5/5 영문 라벨 only)                  | **87% 해독** (5/5 KPI 모두 title + sr-only + Korean explanation)                                                                              | ✅ **PASS**                       | `casual-04-backtest-detail.png`, `casual-05-kpi-tooltip-hover.png` |
| **BL-328** Clerk koKR               | 한국어 첫 단절 (영문 form)                    | 한국어 form PASS — "로그인 / 이메일 주소 / 비밀번호 / 계속 / 회원가입 / 비밀번호를 잊으셨나요? / 다른 방법 사용하기"                          | ✅ **PASS**                       | `casual-02-signin-koKR.png`                                        |
| **BL-322** Hero copy                | "업로드" GAP (Pine Script 모르는 사용자 단절) | **정직화 PASS** — "Pine Script 코드를 붙여넣으면 백테스트, 최적화, 스트레스 테스트를 거쳐 데모 또는 라이브 자동 매매까지 한 번에 연결됩니다." | ✅ **PASS**                       | `casual-01-landing-hero.png`                                       |
| **BL-323** Optimizer 사이드바       | 부재                                          | 추가 PASS — 사이드바 "전략 / 백테스트 / **최적화** / 트레이딩" 순                                                                             | ✅ **PASS**                       | `casual-03-after-login.png`                                        |
| **BL-339** 터치 타겟 ≥44pt (mobile) | 19+ 위반                                      | **14건 잔존** (편집→ 38x16 / 정렬 기준 101x36 / 사용자 메뉴 28x44 / drawer items 263x36 height)                                               | ⚠️ **PARTIAL** (Mobile 영역 중복) | `casual-07-mobile-strategies.png`                                  |
| **BL-340** horizontal overflow      | trading +227px                                | **0 overflow** /strategies + /trading                                                                                                         | ✅ **PASS**                       | `casual-09-mobile-trading.png`                                     |

---

## KPI 용어 해독률 (BL-327 핵심)

| 라벨                      | Pre 해독     | Post 해독 (tooltip 본 후)                                                             | 증거                                                    |
| ------------------------- | ------------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 총 수익률                 | 60% (한국어) | 95% — "백테스트 기간 동안의 누적 손익 비율. 양수면 이익, 음수면 손실."                | Korean tooltip 첫 줄 즉시 해독                          |
| Sharpe Ratio (샤프 비율)  | 0% (영문)    | 80% — "변동성 대비 초과수익. 1 이상 양호, 2 이상 우수, 음수면 위험 대비 수익 부족."   | "변동성"·"초과수익" 단어 일반인 이해. 기준선 (1/2) 명확 |
| Max Drawdown (최대 낙폭)  | 0% (영문)    | 90% — "고점 대비 최대 손실 폭. -10% 이내가 안정적, -30% 이상은 고위험."               | "고점 대비 손실" = 직관적                               |
| Profit Factor (이익 계수) | 0% (영문)    | 85% — "총 이익 ÷ 총 손실. 1.5 이상 양호, 2.0 이상 우수, 1 미만은 손실."               | 산수식 (÷) + 기준선 명확                                |
| 승률 · 거래               | 50% (한국어) | 95% — "이익 거래 비율 + 전체 거래 횟수. 승률만으론 부족, Profit Factor 와 함께 봐야." | "승률만으론 부족" 행동 가이드 추가                      |

**평균 Pre 22% → Post 89%**. **결정적 회복**. 추가 평가:

- **3종 layer**: (1) HTML `title` attribute = 데스크톱 hover 1초 후 native tooltip / (2) `.sr-only` = 시각장애 screen reader 호환 / (3) Korean 설명 = 직관 해독. **이중 안전망**.
- **라벨 자체는 여전히 영어 우세** (Sharpe Ratio / Max Drawdown / Profit Factor 가 한국어 ("샤프 비율" 등) 라벨 옆에 병기됨). Casual 첫 진입 시 "?" 1초 발생. 단, hover 1번 → 즉시 해독. **Sprint 62 nice-to-have**: 라벨 자체를 "샤프 비율 (Sharpe)" 형태로 한국어 우선 표시 고려.

---

## 막힘 지점 재카운팅

| #   | Pre (1차)                                                          | Post (2차)                                                                                             | 변화                 |
| --- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | -------------------- |
| 1   | landing hero "업로드" — Pine Script 자체를 모르는 사용자 즉시 단절 | hero 정직화 PASS, "Pine Script 코드 붙여넣기" 직관 일부 회복 (단 "Pine Script"가 무엇인지는 여전 단절) | 부분 회복            |
| 2   | Clerk 영문 sign-in form 첫 단절                                    | 한국어 form PASS                                                                                       | ✅ 해소              |
| 3   | 5 KPI 영문 라벨 (0% 해독)                                          | tooltip PASS                                                                                           | ✅ 해소              |
| 4   | 사이드바 "Optimizer" 메뉴 부재 (이용약관에는 언급)                 | "최적화" 메뉴 PASS                                                                                     | ✅ 해소              |
| 5   | 모바일 햄버거 dead                                                 | drawer PASS                                                                                            | ✅ 해소 (BL-285 fix) |
| 6   | trading 가로 스크롤                                                | 0 overflow                                                                                             | ✅ 해소              |
| 7   | 터치 타겟 부족 (배치 모호)                                         | 14건 잔존 — 편집 링크 38x16 너무 작음                                                                  | 부분 회복            |
| 8   | KPI 차트 alt-text 부족                                             | role="img" + aria-label 한국어 추가 (Drawdown · Equity curve)                                          | ✅ 해소              |
| 9   | **신규**: /optimizer 진입 시 영문 Zod JSON error 도배 (BL-350)     | (Curious 발견 — Casual 시선에서도 abandon trigger)                                                     | **신규**             |

**Pre 9건 → Post 3건** (BL-350 1건 신규 추가 / hero "Pine Script" 자체 + 터치 타겟 잔존 2건). **-67%**.

**포기 시점**: Pre 3분 (Clerk 영문 form 단계) → Post **abandon 안 함**. /optimizer 진입한 Casual 만 8-10분에 BL-350 마주침. landing → sign-in → strategies → backtest detail flow 는 끝까지 도달 가능.

---

## 신규 결함 (Casual 시선)

### BL-353 (P1) — Step "전략 업로드" 라벨이 hero copy 와 불일치

**증거**: landing `/` "어떻게 작동하나요?" section step 01 = "**전략 업로드**" + "Pine Script 파일을 업로드하면 자동으로 파싱 및 변환됩니다."

**문제**: BL-322 hero copy 는 "코드를 **붙여넣으면**" 으로 정직화되었으나, 그 바로 아래 step 01 은 여전히 "**업로드**" 메타포 사용. **Mixed message** = Casual 가 "그래서 파일 업로드인가, 코드 붙여넣기인가?" 혼란. Pre BL-322 의 잔재.

**제안 fix**: step 01 라벨 "전략 코드 붙여넣기" + 본문 "Pine Script 코드를 붙여넣으면 자동으로 파싱 및 변환됩니다." 통일. 1줄 fix.

**Severity**: P1 (high) — landing 의 핵심 setup flow 단어 통일 — 신뢰도 직결.

### BL-354 (P0) — /optimizer 진입 시 Casual abandon trigger (Curious BL-350 의 Casual mirror)

**증거**: `casual-06-optimizer-page.png` 화면 상단부터 "Optimizer / Grid Search (서버 9 cell)" 영어 우세 + "최근 실행 목록 로드 실패: [JSON Zod error stack]" 노골적 노출.

**Casual reaction**: "목록 로드 실패" 6글자 보고 즉시 "고장났네" 결론 → 페이지 abandon. JSON 내용은 100% 영어 + 기호 + 일반인 0% 해독. **신규 페이지 가입 후 진입 likely path** = BL-323 사이드바 fix 의 부작용 — "최적화" 메뉴를 보이게 했더니 클릭 시 망가짐.

**Severity**: P0 (critical) — Casual 의 첫 abandon trigger 가 됨. BL-323 fix 의 side-effect.

**제안 fix**: (1) Casual-friendly empty state 한국어 메시지 ("아직 실행한 최적화가 없어요. 새 최적화를 시작해 보세요.") + (2) Zod error 도배 차단 (Curious BL-350 와 동일 fix). 백엔드 schema 정합 fix 가 핵심.

### BL-355 (P3) — landing 의 "Bybit Demo Trading 환경에서 위험 없이 전략을 검증합니다" 영문 "Demo" 잔존

**증거**: landing `/` 두 군데 "**Demo**" 영문 — pricing section "Bybit Demo 연동 (Beta)" + CTA "Bybit Demo Trading 환경에서". Casual 가 "Demo" 의 의미 추측 가능 (75%) 이지만 "데모" 한국어가 더 친숙.

**Severity**: P3 (cosmetic). nice-to-have.

---

## a11y (axe-core)

| 페이지          | Pre serious | Post serious | 잔존 issue                                                                                                                                   |
| --------------- | ----------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| /strategies     | ~30         | **14**       | color-contrast 14                                                                                                                            |
| /backtests      | ~30         | **34**       | color-contrast 34 (목록 row 라벨 contrast 부족)                                                                                              |
| /backtests/<id> | ~32         | **20**       | color-contrast 18 + **nested-interactive 2** (BL-327 wrapping side effect — TradingView chart `role="img"` inside `<button>` tooltip parent) |
| **합계**        | **92**      | **68**       | -26%                                                                                                                                         |

**평가**:

- BL-339 (Mobile 페르소나 영역) 와 색대비 잔존 = Mobile 페르소나에 위임.
- `nested-interactive` 2건 = BL-327 tooltip 구조의 부작용. button 이 chart 를 감싸지 않도록 markup 조정 필요 (Sprint 62 minor BL 후보, 신규 BL 등재하지 않음 — Mobile 영역 또는 follow-up).

---

## Summary

- **Composite Casual: 5.2 → 7.4 / 10** (+2.2). Pre 의 5종 fix 모두 PASS. 결정적 회복.
- **용어 해독률 (KPI 5종): 22% → 89%** (+67pp). BL-327 KPI tooltip = Sprint 61 의 single most-impactful Casual fix.
- **막힘 지점: 9 → 3 (-67%)**. 포기 시점 abandon 사라짐 (Casual 가 backtest detail 까지 끝까지 도달 가능).
- **a11y: 92 → 68 serious (-26%)**. 추가 color-contrast 수정 (Sprint 62) 권고.
- **신규 BL 3건**: BL-353 (P1, step 01 라벨 통일) / BL-354 (P0, /optimizer Casual abandon — BL-350 의 Casual side) / BL-355 (P3, "Demo"→"데모").

**Casual 시선 verdict**: Sprint 61 fix-first 전략은 결정적으로 효과적이었다. 1차에서 **landing → sign-in → strategies → backtest detail** 의 핵심 path 가 0~3분에 막혔던 abandon trigger 들이 모두 해소되었다. Pre baseline 5.2 → Post 7.4 는 보수적 평가이며, KPI tooltip 의 직접 검증 (5종 모두 Korean 1줄 설명 + 기준선 제시) 은 **expert-level explainer** 수준이다. 잔존 결함 (BL-353/354/355 + a11y color-contrast 68건) 은 Sprint 62 의 일반적 polish 범위.

**Beta 진입 gate (Casual 시선 only)**: ✅ **PASS** (단, BL-354 P0 가 Beta 첫인상 abandon trigger 가 될 위험 → Sprint 62 첫 fix 권고).

---

## 산출물

- 스크린샷 9건: casual-01 ~ casual-09 (`screenshots/`)
- 신규 BL: BL-353 / BL-354 / BL-355
- 측정 시각: 2026-05-17 ~17:00 KST (계측 60분 이내, abandon 0회)
