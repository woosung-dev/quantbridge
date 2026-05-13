# Mobile(모바일 전용) Report — QuantBridge Multi-Agent QA 2026-05-13

## Persona

스마트폰만 사용하는 사용자 (지하철 / 카페 / 침대). 한 손 사용 가정. 데스크톱 미보유 또는 보유해도 거의 안 씀. 모바일에서 작동 안 하면 100% 이탈.

## Executive Summary

- **모바일 도입 결정: No (현재 상태)** — 모바일 사용자는 페이지 간 이동 불가능 + 로그아웃 불가능. fundamental navigation 결여.
- **모바일 UX 점수: 2/10** — 페이지 별로 렌더링은 됨 (Backtest 결과 차트 17 canvas 정상). 그러나 information architecture (sidebar) 가 desktop-only `<aside class="hidden">` 로 죽어있고, 햄버거 버튼은 `aria-expanded` 만 toggle 할 뿐 sidebar 의 `hidden` 클래스를 제거 못 함 → **모바일 = 첫 페이지 들어간 후 다른 페이지 못 감**.
- **터치 타겟 위반: 페이지당 12~24 개** (`button/a/input/select` 중 ~80~96%) — Apple HIG 44pt 기준 위반.
- **한 손 도달률: 0%** — Primary CTA (`새 전략`, `최근 수정순`) 가 viewport 상단 (y=155, 346). thumb zone (y≥500) 에 primary action 0 개. BottomNav 미존재.
- **PWA: 1/10** — `<link rel="manifest">` 없음, theme-color meta 없음, apple-touch-icon 없음, service worker 0 registered. viewport meta 만 있음.
- **가로 스크롤 (`/backtests` & `/trading`):** 모든 viewport 에서 `docWidth=456~602 > viewport (375/393/412)` 로 발생. iPhone SE = 81px overflow, Pixel 7 Trading = 190px overflow.
- **한국어 폰트 미지정:** Inter / Plus Jakarta Sans (라틴 only) — `-apple-system` fallback 으로 iOS 만 SF Pro 한국어 글리프. Android (Pixel 7) Roboto fallback 으로 표시되지만 명시적 Pretendard/Noto Sans KR 미지정.

## viewport 별 결과 (3종 cross-check)

| viewport              | strategies overflow | backtests overflow | backtest detail | trading   | optimizer | hamburger 동작        |
| --------------------- | ------------------- | ------------------ | --------------- | --------- | --------- | --------------------- |
| 375x667 iPhone SE     | 없음                | **81px**           | 18px            | (skip)    | (skip)    | 죽음 (aria 만 toggle) |
| 393x852 iPhone 14 Pro | 없음                | **63px**           | (skip)          | (skip)    | (skip)    | 죽음 (동일 패턴)      |
| 412x892 Pixel 7       | 없음                | **44px**           | (skip)          | **190px** | 없음      | (skip — 동일 가정)    |

3 viewport 동일한 `<aside class="hidden">` sidebar 패턴 — Tailwind responsive breakpoint (`md:flex`) 적용 없이 mobile = display:none 강제. `/backtests` 페이지는 min content width 456px 고정.

## 시나리오 결과

| #   | 시나리오                  | 결과                                            | 점수 (1-10)     |
| --- | ------------------------- | ----------------------------------------------- | --------------- |
| 1   | viewport 3종 cross-check  | 동일 패턴 (sidebar dead, backtests overflow)    | 4 (렌더링은 됨) |
| 2   | 한 손 도달률 (thumb zone) | primary action 0/2 in y≥500                     | **1**           |
| 3   | 터치 타겟 (≥44pt)         | 80~96% 위반                                     | **2**           |
| 4   | 3G perceived perf         | (skip — 네트워크 throttle 미적용)               | n/a             |
| 5   | 모바일 키보드 type        | number 적용 / inputmode 없음                    | **6**           |
| 6   | 권한 흐름 (Clerk OAuth)   | (skip — pre-authenticated session 으로 진행)    | n/a             |
| 7   | PWA / manifest            | manifest/SW/theme-color 모두 부재               | **1**           |
| 8   | BottomNav / hamburger     | hamburger 죽음, BottomNav 없음                  | **0**           |
| 9   | 차트 인터랙션             | canvas 17개 렌더 OK, 테이블 inner overflow 없음 | 6               |
| 10  | 폰트 가독성               | 26 elements <13px, 한국어 폰트 미지정           | **4**           |

## 결함 상세

### BL-300 — 햄버거 메뉴 dead button (모바일 페이지 간 이동 100% 불가능) [Critical]

- **Severity: Critical · Confidence: High**
- **viewport 영향:** 375x667 / 393x852 / 412x892 (모든 모바일)
- **재현:**
  1. 모바일 viewport (<=412px) 로 `/strategies` 접속 (로그인 상태)
  2. 좌측 상단 햄버거 (메뉴 열기) 탭
  3. **결과: 시각적 변화 0**. `aria-expanded` 만 false → true 토글
- **DOM 증거:**
  - `<aside class="hidden flex-col border-r...">` — Tailwind `hidden` (display:none) 강제
  - 햄버거 click 시 `aside` 의 `hidden` 클래스 제거되지 않음
  - 모바일 sheet/drawer 컴포넌트 (`<div role="dialog">`) 0 개 렌더
  - 모든 nav 링크 (`/backtests`, `/trading`, `/optimizer`) 0x0 width
- **기대:** 햄버거 탭 시 좌측 또는 전체 화면 drawer 가 슬라이드인 + nav 노출
- **실제:** 햄버거는 시각적 효과 없는 dead button. 모바일 사용자는 URL 직접 입력 또는 로고 클릭 외 방법 없음
- **추천:** Sheet/Drawer 컴포넌트 (shadcn `<Sheet>` 또는 BottomNav fixed) 추가. `<aside>` `hidden md:flex` 분리 + 모바일 전용 `<MobileNav>` mount

### BL-301 — `/backtests` 리스트 + `/trading` 가로 스크롤 (min-width fixed) [High]

- **Severity: High · Confidence: High**
- **viewport 영향:** 375 (81px) / 393 (63px) / 412 (44px) / 412 trading (190px)
- **재현:**
  1. 모바일 viewport 로 `/backtests` 접속
  2. 페이지 좌우로 스와이프 가능 — 콘텐츠 잘림
- **DOM 증거:** `documentElement.scrollWidth = 456` (backtests) / `602` (trading) — `min-width` 또는 fixed-width 콘텐츠 박스 의심
- **기대:** 모바일 viewport 안 fit (overflow-x: hidden 또는 콘텐츠 reflow)
- **실제:** 좌우 스크롤 의무 — UX 매우 나쁨
- **추천:** `/backtests` 카드/테이블 max-width 제거 + reflow 디자인 또는 horizontal scroll container 명시 (table wrapper `overflow-x-auto`)

### BL-302 — Number input `inputmode="decimal"` 미적용 [Medium]

- **Severity: Medium · Confidence: Medium**
- **viewport 영향:** 모든 viewport
- **재현:** `/backtests/new` 의 `initial_capital`, `fees_pct`, `slippage_pct`, `default_qty_value` 필드
- **현재:** `type="number"` 적용. 그러나 `inputmode` attribute 없음
- **문제:** iOS Safari 에서 `type="number"` 만 적용하면 숫자 키패드가 뜨지만 소수점 컨트롤이 제한될 수 있음. Decimal 입력 (수수료 0.05% 등) 시 정확히는 `inputmode="decimal"` 권고
- **추천:** Decimal 값 필드는 `inputmode="decimal"` 명시 추가. autocomplete 도 `"off"` 명시 (현재 `none` 임 — 비표준)

### BL-303 — 사용자 노출 텍스트에 내부 sprint/ADR ref 누출 (모바일 cross-check) [Medium]

- **Severity: Medium · Confidence: High**
- **viewport 영향:** 모든 viewport
- **재현:** `/optimizer` 페이지 본문 = `Optimizer (Sprint 56)` + `Grid Search (서버 9 cell) / Bayesian (≤ 50 evaluation, ADR-013 §6)`. `/strategies/new` 본문 = `Sprint 7d+`. `/backtests` Beta 배너 = `법무 임시 — H2 말 정식 변호사 교체 예정`
- **모바일 강도 modifier:** 작은 viewport 에서 이 텍스트가 차지하는 vertical space 가 본 콘텐츠 대비 비율로 더 큼 (375x667 에서 Beta banner alone = 80~120px vertical) — 사용자 가독성 더 큰 손해
- **기대:** 내부 개발 ID/ADR ref 는 사용자 노출 카피에서 제거
- **추천:** 카피 정리 (Curious / Interested 페르소나도 동일 발견)

### BL-304 — 폰트 — 한국어 전용 typeface 미지정 + 26 elements <13px [Medium]

- **Severity: Medium · Confidence: High**
- **viewport 영향:** 모든 viewport
- **증거:**
  - `body { font-family: Inter, "Inter Fallback", ui-sans-serif, system-ui, -apple-system, sans-serif }` — Inter 는 라틴 only
  - 헤딩: `Plus Jakarta Sans` (라틴 only)
  - 한국어 글리프 = `-apple-system` (iOS = SF Pro Display KR) / `system-ui` (Android = Roboto) fallback
  - 픽셀 크기 분포 (`/strategies`): `10px:4 / 11px:11 / 12px:11 / 14px:7 / 16px:6`
  - **26 elements <13px** — Apple HIG 권장 17pt(=22px@72dpi) / Material 14sp 미달
- **모바일 강도 modifier:** 작은 viewport + 한국어 (글자 정보 밀도 영문 대비 1.5배) → 가독성 손실 가속
- **기대:** Pretendard 또는 Noto Sans KR 명시 font stack + 본문 14px 이상
- **추천:** `font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, ...` 적용

### BL-305 — Clerk UserButton 0x0 렌더 (모바일 로그아웃 불가) [Critical]

- **Severity: Critical · Confidence: High**
- **viewport 영향:** 모든 viewport
- **재현:**
  1. 우측 상단 `Open user menu` aria-label 버튼
  2. 시각적으로 보이지 않음 — `getBoundingClientRect()` = `{w:0, h:0}`
  3. 프로그램 .click() 으로는 popover (343x243) 정상 열림 → Clerk 자체 작동
  4. 손가락 탭으로는 0x0 영역 → 영원히 못 누름
- **DOM 증거:** `<button aria-label="Open user menu">` → `<span class="cl-userButtonBox">` (Clerk widget container) width=0 height=0. `display: flex / visibility: visible / opacity: 1` 인데 자식 element 가 collapsed.
- **기대:** 우측 상단에 44x44 이상 avatar 버튼 visible. 탭 시 sign-out / account 메뉴 popover
- **실제:** 모바일 사용자는 sign-out 불가능. 멀티 계정 전환 불가능. 결제/account 페이지 접근 경로 없음
- **추천:** Clerk `<UserButton appearance>` 의 `elements.userButtonBox` 에 explicit `width: 36px / height: 36px` (또는 Clerk `appearance.elements.avatarBox: { width: 36, height: 36 }`) 강제. 또는 모바일 header 에 native button + Clerk `signOut()` 직접 호출

## 강점 + 약점 Top 3

### 강점

1. **백테스트 결과 차트 정상 렌더링** — 17 canvas (equity, drawdown 등) 모바일 viewport 에서 잘림 없이 렌더 + 테이블 inner overflow 없음 (310px fit)
2. **viewport meta + Date input 모바일 친화** — `width=device-width, initial-scale=1` 정상. `type="date"` 적용으로 모바일 native date picker
3. **햄버거 버튼 자체 크기는 OK** — 44x44 (HIG 합격). 문제는 _동작_ 만 없음

### 약점

1. **모바일 IA 전체 부재** — `<aside class="hidden">` desktop-only + 햄버거 dead + BottomNav 없음. 페이지 간 이동 0 가능. 단일 페이지 만 사용하는 사용자만 가능
2. **Clerk UserButton 0x0** — sign-out / 계정 관리 모바일에서 완전히 막힘
3. **`/backtests` & `/trading` 가로 스크롤** — 가장 자주 쓰는 두 페이지가 좌우 스와이프 필요. 모바일 UX 가장 큰 적신호

## 평가 점수 표

| 차원                             | 점수 / 값  | 비고                                                                  |
| -------------------------------- | ---------- | --------------------------------------------------------------------- |
| 한 손 도달률 (%)                 | **0%**     | y≥500 thumb zone 안 primary action 0/2 (`/strategies`)                |
| 터치 타겟 위반 수 (페이지 합)    | **~90 개** | strategies 20 + backtests 24 + backtest detail 22 + trading 12 + 기타 |
| 모바일 UX (1-10)                 | **2**      | IA 부재 + 가로 overflow                                               |
| 키보드 type 정확성 (1-10)        | **6**      | `type="number"/date"` 양호, `inputmode` 미적용                        |
| PWA 점수 (manifest/SW 존재)      | **1/10**   | viewport meta 만 충족                                                 |
| BottomNav/hamburger 존재         | **N**      | hamburger 있지만 동작 안 함, BottomNav 없음                           |
| 폰트 가독성 (1-10)               | **4**      | <13px 26 elements + 한국어 폰트 미지정                                |
| 차트 인터랙션 (1-10)             | **6**      | 렌더 OK, 핀치 줌 미검증                                               |
| 모바일 페이지 간 이동 가능 (Y/N) | **N**      | 햄버거 dead, BottomNav 부재                                           |
| 모바일 도입 결정                 | **No**     | BL-300 + BL-305 = 모바일 fundamental 결여                             |

## 다른 페르소나 결함 cross-check (modifier 만 기록)

- **BL-285 (Casual 발견 — 햄버거 메뉴 부재):** **reframe 필요.** 햄버거 *버튼*은 있고 44x44 크기도 OK. 그러나 *동작*은 없음 = effectively absent. BL-300 으로 별도 등록 (Casual 발견과 다른 layer = 시각 부재 ≠ 동작 부재)
- **Optimizer raw Zod / 가짜 marketing / Sprint 56 H1 ref (Interested 발견):** 모바일 viewport 에서도 동일 노출. 작은 viewport 에서 vertical space 비중 더 커서 가독성 손해 가속. BL-303 으로 cross-confirm (modifier = 강도 1.5배)
