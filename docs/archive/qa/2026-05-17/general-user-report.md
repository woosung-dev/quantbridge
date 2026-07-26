# Casual (일반 사용자) — Sprint 60 → 61 Multi-Agent QA

**일자**: 2026-05-17 (Day 8 of dogfood)
**환경**: Isolated mode (FE :3100 / BE :8100)
**페르소나**: Casual — Non-technical Korean, 직관 의존, 막히면 포기
**깊이**: Exhaustive (60-90분)
**Git HEAD**: 60d8518 (main)
**스크린샷**: 16장 (casual-01 ~ casual-16)

---

## 핵심 요약

| 차원                       | 점수 (1-10)    | 코멘트                                                                                                                           |
| -------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 용어 해독률 (%)            | **40%**        | 핵심 KPI 4종 (Sharpe / Drawdown / Profit Factor / 슬리피지) 0% — tooltip 없음. Pine Script / 파싱 / TF / Kill Switch 영어 그대로 |
| 라벨/메뉴 직관성           | **5/10**       | sidebar 6개 중 3개 disabled (대시보드/템플릿/거래소) — `title="곧 출시"` tooltip 만으로 추측 강요                                |
| 데스크톱 UX                | **5/10**       | header nav (3) + sidebar (6, half disabled) 이중 noise. KPI 라벨 정보 없음. Buy & Hold 등 일부 라벨 보조 한국어 친절             |
| 모바일 UX                  | **7/10**       | 햄버거 작동 양호 (Sprint 60 BL-285/300/305 fix 회귀 X). 모바일 menu = 활성 3개만 노출 (일관성 OK)                                |
| 에러 회복                  | **6/10**       | new strategy "다음 단계" 빈 코드 시 disabled — 양호. 404 페이지 한국어 + 가이드 link 친절                                        |
| a11y (axe-core, WCAG 2 AA) | **92 serious** | color-contrast violations 누적 (5 페이지 합계). nested-interactive 2건 (backtest detail)                                         |
| Keyboard nav               | **6/10**       | skip-to-content link 작동. focus-visible ring 측정 안 됨. Clerk widget keyboard 가능                                             |
| i18n 일관성                | **3/10**       | Clerk sign-in/sign-up 전체 영어 + "Development mode" 노출. Beta 배너 영-한 혼합. "Open user menu" 영어                           |

**Composite Casual 점수: 5.2 / 10**

---

## 막힘 지점 (timestamp + 위치 + 이유)

1. **0:00 — landing page 진입.** "Pine Script 전략을 자동 트레이딩으로". → "Pine Script 가 뭐지?" 즉시 의문. CTA `무료로 시작하기` 클릭 망설임. 가이드 / 설명 link 없음.
2. **0:30 — sign-in/sign-up.** "Welcome back! / Sign in to continue / Email address Last used Password Continue / Apple Google / Development mode" **전부 영어**. 한국 일반인 첫 진입 = 신뢰 즉시 하락 ("앱이 진짜 한국어인가?"). 5초 멈춤.
3. **1:30 — logged-in /strategies.** sidebar "대시보드 / 템플릿 / 거래소" 회색 + cursor-not-allowed. Hover 안 하면 의문 해소 X (`title="곧 출시"` 가 있어도 모름).
4. **2:00 — /strategies 의 카드.** "파싱 성공 / Pine v5 / BTC/USDT 1h" 정보 + "편집 →" 만. **일반인 = "백테스트는 어디서 누르지?"** 카드 안 백테스트 진입 CTA 없음 (편집 가야 함).
5. **3:00 — /backtests 진입.** 컬럼명 **"TF"** (TimeFrame 약어). 일반인 = "TF 가 뭐지?" 의문.
6. **3:30 — backtest detail.** **KPI 4종 (Sharpe Ratio / Max Drawdown / Profit Factor / 승률 · 거래)** 라벨에 tooltip 없음. 숫자만 보고 "이게 좋은 건지 나쁜 건지" 0% 판단 가능.
7. **4:30 — /dashboard 직접 URL.** redirect → /strategies. **header 의 "대시보드" 라벨이 거짓** (실제 dashboard 페이지 없음 / strategies 가 default).
8. **5:00 — /trading.** "Kill Switch 0 정상" — "Kill Switch" 직관 X. 한국어 "긴급 차단" / "안전 정지" 등 i18n 보조 없음.
9. **5:30 — new strategy step 2.** "⌘+Enter 즉시 파싱" — Mac 단축키만. Windows 사용자 노이즈. "파싱" 단어 또 등장. 코드 영역 name="Editor content" (영어).

**포기 시점 (분): 약 3분.** 일반인 = sign-in 영어 + Pine Script 단어 + 첫 strategies 카드에서 어디 클릭할지 모름 → 3분 안에 뒤로.

---

## 시나리오별 상세

### 1. 데스크톱 + 모바일 양쪽 (1440x900 / 375x812)

**데스크톱 logged-in `/strategies`**:

- Header nav = 5 link ("QuantBridge / 전략 / 백테스트 / 트레이딩 / 새 전략")
- Sidebar (ASIDE > NAV) = 6 항목 — 3 enabled (전략 / 백테스트 / 트레이딩) + 3 disabled (대시보드 / 템플릿 / 거래소, `opacity-50 cursor-not-allowed`, `title="곧 출시"`)
- 헤더와 사이드바가 같은 항목 중복. 일반인 = "왜 두 군데에 같은 메뉴?"

**모바일 logged-in `/strategies`** (casual-14):

- 햄버거 버튼 정상 작동 (casual-15). 메뉴 안 = "전략 / 백테스트 / 트레이딩" 3개만.
- 데스크톱 sidebar 의 disabled 3개 (대시보드 / 템플릿 / 거래소) 가 모바일에서는 숨겨짐 = 일관성 OK.
- 일반 한국 사용자에게 모바일 UX 가 데스크톱보다 깔끔.

### 2. 용어/라벨 의미 추측 (UX 라이팅)

**일반인 0% 해독 (모르는 단어 그대로 노출)**:

- Pine Script / Pine v5 (.pine 파일)
- 파싱 (성공 / 실패 / 미지원)
- TF (TimeFrame 약어)
- Sharpe Ratio
- Max Drawdown / Drawdown
- Profit Factor
- 슬리피지
- Kill Switch
- Bayesian / Genetic (요금제 페이지)
- Monte Carlo / Walk-Forward (FAQ + landing)
- VaR (95%) (landing 시연 이미지)
- PnL / OHLCV / SOC 2 / API Key / Webhook (요금제)
- TradingView / Pine Editor (new strategy step 2)
- TV URL (new strategy step 1)
- H2 (Beta 배너 — "H2 말 정식 변호사 검토본")
- Development mode (Clerk widget)

**일반인 30~70% 해독 (애매)**:

- 백테스트 (트레이더 일부 알지만 비-트레이더 0%)
- 데모 트레이딩 / 라이브 트레이딩
- 포지션 모델 / 1x · 롱/숏
- 1M 3M 6M 전체 (월 단위?)
- 1h 단위 캔들

**일반인 80%+ 해독 (양호)**:

- 무료로 시작하기 / 라이브 데모 / 무료로 가입하기
- 전략 / 새 전략 / 편집 / 보관됨 / 즐겨찾기 / 그리드 뷰 / 목록 뷰
- 수수료 0.10% / 초기 자본 10,000 USDT / 총 수익률 / 승률
- Buy & Hold (단순보유) 보조 라벨 친절
- Equity (자본 곡선) / Drawdown (손실 폭) 보조 라벨 친절
- 활성 세션 / 대기 중 / 연결된 거래소 / API 연결 정상
- 4단계 wizard 진행 표시 (업로드 → 코드 입력 → 확인)

**용어 해독률 = 약 40%** (트레이딩 비-친화 일반인 기준).

### 3. 막힘 지점 카운팅 → 위 "막힘 지점" 섹션 참조 (9건)

### 4. 핵심 워크플로우 직관성

**"내 첫 백테스트" 만들기 (sign-up → strategy → backtest)**:

- Sign-up: Clerk 영어 100% → 첫 단절. (BL-309)
- New strategy: "Pine Script 직접 입력" 가 first option 인데 일반인이 Pine Script 못 씀. "어디서 Pine Script 받아오나?" 가이드 link 없음.
- Backtests: "새 백테스트" 버튼 OK. 그러나 strategy 가 필요 / 어떤 strategy 가 backtest-able 인지 시각 cue 없음.

**결과 화면 KPI 5개 (총수익률 -2.53% / Sharpe -1.13 / MaxDD -4.13% / Profit Factor 0.70 / 승률 32.98%)**:

- "총수익률 -2.53%" — 일반인 100% (음수 = 손실).
- 나머지 4개 = 0% 의미. 일반인 = "이 백테스트는 좋은 결과인가 나쁜 결과인가" 판단 불가.
- **Critical UX gap — primary KPI 라벨에 hover tooltip + "초보 설명" 모드 부재.**

### 5. 에러 회복

- `/exchanges` 404 → "찾으시는 페이지가 있으신가요? 내 전략 보기 / 백테스트 결과 / 대시보드" 가이드 link **친절**. 양호.
- new strategy step 2 "다음 단계 →" 코드 미입력 시 disabled. 양호.
- "Open Tanstack query devtools" 버튼 노출 — dev 도구 production-like 모드에서 보이면 일반인 혼란 (a11y label).

### 6. 모바일 BottomNav / 터치 타겟

- BottomNav 없음 (sidebar/header 만).
- 햄버거 작동 양호. Sprint 60 BL-285/300/305 fix 회귀 검증 PASS (Curious 보고와 일치).
- UserButton 영역 (Open user menu) 가시. 터치 가능.

### 7. axe-core a11y violations

| Page            | violations                                                                     |
| --------------- | ------------------------------------------------------------------------------ |
| /strategies     | color-contrast (13 nodes, serious)                                             |
| /backtests      | color-contrast (33 nodes, serious)                                             |
| /trading        | color-contrast (16 nodes, serious)                                             |
| /strategies/new | color-contrast (11 nodes, serious)                                             |
| /backtests/<id> | color-contrast (19 nodes, serious) + **nested-interactive (2 nodes, serious)** |

**Total = 92 color-contrast + 2 nested-interactive = 94 serious violations.**
WCAG 2.1 AA 위반.

### 8. Keyboard navigation

- Skip-to-content link 정상 (`a[href="#main-content"]` + `#main-content` 존재). 양호.
- Tab 순서 + focus-visible ring 측정 안 됨 (페이지 첫 진입 focus 검출 X).
- Clerk widget 자체는 keyboard 가능 (E2E 로그인 성공).

---

## 신규 BL (BL-327 ~)

> BL ID = BL-326 (Curious max) + 1 부터 시작.

### BL-327 [P1] 핵심 KPI 라벨에 hover tooltip + 초보 설명 부재

- **위치**: `/backtests/<id>` (성과 지표 카드).
- **문제**: Sharpe Ratio / Max Drawdown / Profit Factor / 승률 · 거래 라벨에 `title` / `aria-describedby` / tooltip 일체 없음. 일반인이 숫자만 보고 의미 판단 0%.
- **검증**: `document.querySelectorAll('*').filter(...Sharpe...).map(el => el.getAttribute('title'))` → 모두 `null`.
- **제안**:
  - 각 KPI 라벨 옆 `?` 아이콘 + Radix Tooltip (한국어 1줄 설명: "샤프 비율: 변동성 대비 초과수익. 1 이상 양호").
  - `aria-describedby` 로 a11y 호환.
- **노력**: 4h (5 KPI × 30분 + tooltip 컴포넌트 재사용).

### BL-328 [P1] Clerk sign-in/sign-up 한국어 localization 미적용

- **위치**: `/sign-in`, `/sign-up` (Clerk widget).
- **문제**: "Sign in to quant-bridge / Welcome back! / Email address Last used Password Continue / Apple Google / Sign up / Secured by / Development mode" **전체 영어**. 한국어 페이지에 영어 인증 = 신뢰 단절.
- **검증**: `casual-05-signin.png`, `casual-06-signup.png`.
- **제안**:
  - `@clerk/localizations` 의 `koKR` import + `<ClerkProvider localization={koKR}>` 적용.
  - "Development mode" 라벨 → production 빌드에서 hide.
- **노력**: 2h (npm install + provider 수정 + dev mode env-gate).
- **영향**: Beta 진입 가장 큰 i18n 단절 — 4-AND gate (a) self-assessment 직접 영향.

### BL-329 [P2] Sidebar disabled 3개 (대시보드 / 템플릿 / 거래소) tooltip 만 의존 = 일반인 의문 해소 X

- **위치**: 데스크톱 sidebar (ASIDE > NAV).
- **문제**: `cursor-not-allowed opacity-50 title="곧 출시"` — hover 안 하면 무의미. 일반인 = "이건 무료 플랜이라 잠긴 건가?" 추측.
- **제안**:
  - 라벨 옆 inline 배지 (`<Badge variant="muted">곧 출시</Badge>`) — title 만으로는 부족.
  - 혹은 sidebar 에서 완전 제거 (모바일 메뉴와 일관성).
- **노력**: 1h.

### BL-330 [P2] Header "대시보드" 라벨이 거짓 (실제 dashboard 페이지 부재 — /strategies 로 redirect)

- **위치**: 헤더 sidebar 의 "대시보드" 항목 + `/dashboard` 직접 URL.
- **문제**: 사용자 "대시보드" 클릭 → strategies 로 자동 redirect. 라벨이 약속한 화면을 제공하지 않음 (잔고 / 수익 / 손익 panel 부재).
- **검증**: `$B goto /dashboard → $B url → /strategies`.
- **제안**:
  - (A) 실제 dashboard 페이지 신설 (포트폴리오 / 손익 요약 / 활성 봇 / 최근 백테스트 위젯). Landing page 의 모형 dashboard 가 dogfood reality 와 일치하지 않으므로 신설 필수.
  - (B) sidebar 의 "대시보드" 라벨 제거 + landing 의 dashboard 모형 hide.
- **노력**: (A) 12-16h (Sprint 61 candidate) / (B) 30분.
- **연관**: Sprint 60 BL-265/280/303 와 별개 — UX 약속-제공 mismatch.

### BL-331 [P2] 일반인 첫 진입 "Pine Script 가 뭐지?" 가이드 link 부재

- **위치**: `/`, `/strategies/new` step 1.
- **문제**: "Pine Script" 단어 즉시 등장. Hover 설명 / "Pine Script 는 무엇인가요?" FAQ link / 샘플 코드 download 없음.
- **제안**:
  - new strategy step 1 에 "Pine Script 가 처음이신가요? → TradingView 가이드" outbound link.
  - 또는 "예시 코드 채우기" 버튼 (이미 backend 에 sample strategy 있다면 활용).
- **노력**: 2h.

### BL-332 [P3] axe-core color-contrast 92 nodes (5 페이지 누적) WCAG AA 위반

- **위치**: 5 페이지 누적.
- **문제**: dimmed text (`.opacity-75`, sidebar disabled muted-foreground 등) 가 4.5:1 ratio 미달.
- **제안**:
  - `--muted-foreground` 토큰 명도 +10% 조정.
  - 또는 `.opacity-75` → `.opacity-90` swap (dark-mode 안전 검증 필요).
- **노력**: 3h (token 조정 + 전 페이지 회귀 screenshot diff).
- **연관**: Sprint 60 design-review 결과와 cross-check 필요.

### BL-333 [P3] /backtests 컬럼명 "TF" 약어 → "주기" 또는 "타임프레임"

- **위치**: `/backtests` 테이블 헤더.
- **문제**: "TF" 가 TimeFrame 약어. 일반인 0% 해독.
- **제안**: "TF" → "주기" 또는 "타임프레임".
- **노력**: 15분 (i18n 키 1개).

### BL-334 [P3] new strategy "⌘+Enter 즉시 파싱" — Mac 단축키 only

- **위치**: `/strategies/new` step 2.
- **문제**: Windows / Linux 사용자 = `⌘` 의미 불명.
- **제안**: `os` detect 후 `Ctrl+Enter` / `⌘+Enter` 분기 표시.
- **노력**: 1h.

### BL-335 [P3] "Open user menu" / "Open Tanstack query devtools" 영어 a11y 라벨

- **위치**: 모든 logged-in 페이지 헤더.
- **문제**: aria-label 영어. screen reader 한국어 사용자 단절.
- **제안**:
  - "Open user menu" → "사용자 메뉴 열기".
  - "Open Tanstack query devtools" → production 빌드에서 hide (또는 dev only).
- **노력**: 30분.

### BL-336 [P3] backtest detail nested-interactive 2 nodes (WCAG AA)

- **위치**: `/backtests/<id>` (axe-core 검출).
- **문제**: 클릭 가능 element 안에 또 다른 클릭 가능 element 중첩. screen reader navigation 혼란.
- **제안**: axe-core detail 확인 후 outer element 의 role/tabindex 정리.
- **노력**: 2h.

### BL-337 [P3] Beta 배너 "H2 말 정식 변호사 검토본" — 사내 용어 (반기) 노출

- **위치**: 모든 페이지 상단 sticky Beta 배너.
- **문제**: "H2" = 2nd Half (반기) — 사내 product 용어. 일반인 0% 해독.
- **제안**: "H2 말" → "2026년 하반기" 명시.
- **노력**: 5분.

---

## Summary

- **Composite Casual 점수: 5.2 / 10**
- **막힘 지점 수: 9건** (sign-in 영어 / sidebar disabled / KPI 라벨 / dashboard redirect 등)
- **포기 시점: 약 3분** (sign-in widget 영어 + Pine Script + 첫 strategies 카드 navigation 막힘)
- **용어 해독률: 40%** (트레이딩 비-친화 한국 일반인 기준)
- **a11y violations: 94 serious** (5 페이지 누적, color-contrast 92 + nested-interactive 2)
- **신규 BL: 11건 (BL-327 ~ BL-337)** — P1 2건 + P2 2건 + P3 7건
- **모바일 햄버거 회귀: PASS** (Sprint 60 BL-285/300/305 fix 정상)

### Beta 진입 차단 P1 후보

1. **BL-327 KPI tooltip 부재** — 결과 화면 의미 0% 해독 = 백테스트 후 사용자 막힘.
2. **BL-328 Clerk 한국어 localization 미적용** — 한국어 SaaS 첫 인상 단절.

**P1 합계 노력 ≈ 6h** = Sprint 61 P0 fix 1 day single-worker 권장.

### 결론

Sprint 60 의 사용자 신뢰 (Disclaimer / Beta 배너 / 가짜 testimonial 정리 / vectorbt UI hide) 는 정착됨. **그러나 일반인이 사용하려면 Beta 단계에서 2가지가 추가로 필요**:

1. **KPI 의미 hover tooltip** (BL-327) — 결과 화면이 가독성 0%.
2. **Clerk 한국어 localization** (BL-328) — sign-up 첫 단절.

이 2개 fix 만으로 Casual 점수가 **5.2 → 7.0+** 추정. Beta gate (a) self-assessment 8.0/10 진입 가능.

P2/P3 9건은 Sprint 62+ 점진 폴리시.
