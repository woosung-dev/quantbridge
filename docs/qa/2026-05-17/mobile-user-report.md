# Mobile (모바일 전용) — Sprint 60 → 61 Multi-Agent QA

**일자**: 2026-05-17 (Day 8 of dogfood)
**환경**: Isolated mode (FE :3100 / BE :8100), Git HEAD `60d8518`
**페르소나**: Mobile — 한 손 + 출퇴근. iPhone SE 375x667 / iPhone 15 Pro 393x852 / Galaxy S24 412x892
**깊이**: Exhaustive (90분 cap 내 완료), BL 시작 = BL-338
**다른 페르소나 의존**: Casual BL-285/300/303/305 PASS 보고 → 본 페르소나 = **3 viewport 다 재검증** + **PWA / 한 손 도달률 / 키보드 / 터치 타겟** 신규 차원

---

## 실행 요약 (TL;DR)

**Composite Mobile 점수: 3.8 / 10**

| Severity      | Count | 대표 BL                                                                                             |
| ------------- | ----- | --------------------------------------------------------------------------------------------------- |
| Critical (P0) | **2** | BL-340 (3페이지 horizontal overflow) + BL-339 (UserButton + 19+ touch target <44pt)                 |
| High (P1)     | **3** | BL-341 (PWA manifest 부재) + BL-342 (number input inputmode 누락) + BL-343 (모바일 sheet a11y 누락) |
| Medium (P2)   | **2** | BL-344 (Trading API key partial reveal 모바일) + BL-345 (backtests 테이블 cell wrap)                |
| Low (P3)      | **1** | BL-346 (dev floating widgets dogfood 방해)                                                          |

**핵심 메시지**: Casual 페르소나가 햄버거/UserButton/내부 ID 노출 "PASS" 보고했지만, **본 페르소나가 더 깊이 들어가서 (a) horizontal overflow 3/4 페이지 (b) 터치 타겟 19개+ 위반 (c) PWA 0/10 (d) Trading 페이지 API 키 partial reveal (e) "Live Strategy.trading_sessions" 코드 토큰 노출** 검출.

**Sprint 60 회귀 결과**:

- BL-285 (햄버거): **PASS** (3 viewport 다 열림/닫힘 OK).
- BL-300 (UserButton 0x0): **PARTIAL PASS** (DOM 2개 인스턴스 — 가시 1개는 28x36 가시, 1개는 0x0 hidden). **신규 문제**: 가시 트리거 28x28 = 44pt 미달.
- BL-303 (내부 ID 모바일 노출): **PARTIAL PASS** (`/strategies`, `/backtests`, `/trading` 3 페이지 traversal 클린 — but `/backtests/new` 폼에서 "Live Strategy.trading_sessions mirror" 노출 = 회귀).
- BL-305 (모바일 nav disabled): **PARTIAL FAIL** (Casual 가 "모바일에서는 disabled 3개 숨김" 보고했지만 본 테스트 = **데이터/템플릿/거래소 시각적으로 표시되어 있음**, 다만 ARIA 트리에서는 제외됨 — a11y 불일치).

---

## Mobile 평가

| 차원                | 점수 (1-10)  | 코멘트                                                                    |
| ------------------- | ------------ | ------------------------------------------------------------------------- |
| 3 viewport 일관성   | 6            | 375 / 393 / 412 layout 유사. 보관됨 필터 잘림 정도만 차이                 |
| PWA                 | 2            | manifest 없음, apple-touch-icon 없음, theme-color 없음                    |
| 한 손 도달률        | 4            | 핵심 CTA (새 전략, 검색, 공유, 재실행) 모두 상단. 백테스트 "실행" 만 하단 |
| 로딩/3G             | 6            | dev 모드 813ms total. 3G 환경 추정 2.5-4초                                |
| 모바일 키보드       | 3            | number input `inputmode` 누락, search field `spellcheck=true`             |
| 권한 흐름           | N/A          | 알림/위치/카메라 권한 요청 없음 (테스트 미진행)                           |
| 터치 타겟 ≥44pt     | **19+ 위반** | strategies 한 페이지에만 19. UserButton 28x28, 필터 chips 30h             |
| Sprint 60 회귀      | PARTIAL      | BL-285 PASS / BL-300 PARTIAL / BL-303 PARTIAL FAIL / BL-305 PARTIAL FAIL  |
| Horizontal overflow | **2/10**     | trading +227px / backtests +81px / backtest detail +18px                  |

---

## Sprint 60 회귀 결과 (집중 25분)

### BL-285 모바일 햄버거 dead — **PASS** ✅

3 viewport (375/393/412) 모두:

- 햄버거 클릭 → sheet 열림 (좌측 ~70% width)
- ESC → sheet 닫힘
- "전략" / "백테스트" / "트레이딩" 3 항목 클릭 가능
- ARIA: `role=dialog data-slot=sheet-content data-open=""` 정상 부착

증거: `screenshots/mobile-02-375x667-hamburger-open.png`

### BL-300 UserButton 0x0 — **PARTIAL PASS** ⚠️

**DOM 에 UserButton 2개 인스턴스**:

1. **`<button.cl-userButtonTrigger>` 첫 번째 = 0x0** (hidden, parent `inline-flex min-h-9 min-w-9` — desktop sidebar 슬롯 의심)
2. **`<button.cl-userButtonTrigger>` 두 번째 = 28x36 가시** (mobile header)

원래 BL-300 ("UserButton 0x0") fix 가 두 번째 사본을 가시화한 것은 사실이지만, **첫 번째 사본 0x0 = ghost element** 가 여전히 DOM 에 남음. JS querySelector 가 첫 사본을 잡으면 fail 재현 가능.

**신규 문제**: 가시 트리거 **28x28 = Apple HIG/Material 44pt 위반**.

증거: `js "Array.from(document.querySelectorAll('.cl-userButtonTrigger')).map(el => el.getBoundingClientRect())"` 결과 `[{w:0,h:0}, {w:28,h:36}]`

### BL-303 내부 ID 모바일 노출 — **PARTIAL PASS** ⚠️

**Clean 페이지** (`text` 출력에 Sprint/BL/ADR/vectorbt/Celery/Redis/Postgres 검색):

- `/strategies` ✅
- `/backtests` ✅
- `/trading` ✅
- `/backtests/<id>` ✅

**Leak 페이지**:

- `/backtests/new` Trading Sessions 설명에 **"Live Strategy.trading_sessions mirror. 빈 선택 = 24시간 거래"** = 코드 토큰 (`Strategy.trading_sessions`) + 영문 mixed.
- Backtest detail 차트 legend: "Buy & Hold 비교" + "Buy & Hold (단순보유)" — Sprint 60 한글화 했지만 영문 잔존 = 일관성 부족.

### BL-305 모바일 nav disabled — **PARTIAL FAIL** ❌

Casual 페르소나 보고 = "모바일에서는 disabled 3개 숨김". 본 테스트 결과:

- 햄버거 sheet 안에 **"데이터" / "템플릿" / "거래소" 시각적으로 표시되어 있음** (회색 흐림 처리만 됨).
- ARIA 트리에서는 제외됨 (snapshot -i 시 안 잡힘).
- 즉 **시각적 = 표시 / 접근성 = 숨김** = 화면 보는 사용자에게는 "왜 안 눌리지?" 혼란 + 스크린 리더 사용자에게는 사라짐 = a11y 불일치.

증거: `screenshots/mobile-02-375x667-hamburger-open.png` (좌측 시트에 5개 항목 가시).

---

## 신규 BL (BL-338 ~ BL-346)

### BL-338 (P3) — Dev floating widgets dogfood 시각 방해 [Low]

**증상**: 모든 페이지 좌하단 검정 "N" 동그라미 (Next.js dev tools) + 우하단 알록달록 풍경 동그라미 (Tanstack Query devtools) **상시 떠 있음**.

**환경**: dev 모드 only. production build 에서는 사라짐.

**영향**: 본인 dogfood 시 시각 방해 + 모바일 화면에서 두 widget 이 콘텐츠 카드 위에 겹쳐 시야 가림.

**Fix 후보**: dev tools 위치 변경 (좌상단/우상단 작은 토글로). 또는 `NEXT_PUBLIC_HIDE_DEVTOOLS=true` env 토글 제공.

**Severity**: P3 (production 영향 없음, dogfood 만).

---

### BL-339 (P0) — 터치 타겟 19+ 위반 (HIG 44pt 미달) [Critical]

**증상**: strategies 페이지 한 곳에서 button + link 19개가 44x44pt 미달.

**Top 위반**:
| Element | w x h |
|---|---|
| UserButton (Open user menu) | 28 x 36 |
| Disclaimer / Terms / Privacy 링크 | 32-54 x **14** |
| 필터 chips (모두/파싱 성공/미지원/파싱 실패) | 47-83 x **30** |
| 본문 바로가기 (skip link) | 1 x 1 |

**영향**: 모바일 한 손 사용자, 출퇴근 흔들리는 지하철 환경에서 오탑 빈번. 큰 손가락 / 손톱 / 장갑 사용자 더 심각. 14pt 베타 disclaimer 링크 = 거의 불가능.

**증거**:

```bash
$B js "Array.from(document.querySelectorAll('button, a')).filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && (r.width < 44 || r.height < 44); }).length"
# → 19
```

**Fix 후보**:

- 베타 disclaimer 링크 padding +12px (16→44pt height).
- 필터 chips height 30→44.
- UserButton size-9 (36) → size-11 (44).
- skip link 의도적 visually-hidden 이라면 OK (예외).

**Severity**: P0 (모바일 사용성 핵심).

---

### BL-340 (P0) — Horizontal overflow 3/4 페이지 (trading 최악 +227px) [Critical]

**증상**: 모바일 viewport 에서 페이지가 viewport 보다 가로로 넓어 **horizontal scroll 강제**.

**측정**:
| Page | 375x667 overflow | 393x852 overflow | 412x892 overflow |
|---|---|---|---|
| /strategies | 0 ✅ | 0 ✅ | 0 ✅ |
| /backtests (목록) | **+81** ❌ | (미측정) | (미측정) |
| /trading | **+227** ❌❌ | **+209** ❌ | **+190** ❌ |
| /backtests/<id> | +18 ⚠️ | (미측정) | (미측정) |

**Trading 페이지 원인**: root `<div.flex.flex-1.flex-col>` 가 602px 까지 늘어남. 자식 element 중 `<section.grid.grid-cols-2.md:grid-cols-4>` (554px) 가 가장 큰 후보 — md:grid-cols-4 가 모바일 breakpoint 에서도 강제 적용되는 듯.

**Backtests 목록 원인**: 6열 테이블 (심볼/TF/기간/상태/실행일/상세) cell 폭 부족 + 컬럼 누적 폭 = viewport 초과.

**영향**: 모바일 한 손 사용자가 trading 페이지 = stat 카드 우측 절반, "테스트 주문" 버튼, "계정 추가" 버튼 모두 viewport 밖. 가로 스와이프 + 세로 스크롤 = 한 손 불가능 → 양손 강제 → 출퇴근 시나리오 깨짐.

**증거**: `screenshots/mobile-04-375x667-trading.png` (스크린샷 자체가 페이지 폭이 viewport 보다 크게 나옴).

**Fix 후보**:

- Trading: 컨테이너 `max-w-[1200px] px-6` → 모바일 `px-4` + 자식 grid 명시 `grid-cols-2` (md: 분기 점검).
- Backtests 목록: 모바일 = card layout / accordion / horizontal-scroll 명시 wrapper (`overflow-x-auto` 부모 박스 안).

**Severity**: P0 (trading = revenue path).

---

### BL-341 (P1) — PWA 0/10 (manifest/apple-touch-icon/theme-color 부재) [High]

**증상**:

```js
{
  manifest_link: undefined,
  apple_icon: undefined,
  theme_color: undefined,
  viewport_meta: "width=device-width, initial-scale=1",
  sw_registered: true  // 단순 API 지원 여부, 실제 registration 별개
}
```

`/manifest.json` 직접 fetch → Clerk 401 redirect = manifest.json 라우트가 public 처리 안 됨.

**영향**: iOS Safari "홈 화면에 추가" 시 → 아이콘 = page screenshot 기반 + 라벨 = "localhost" / "QuantBridge". Android "PWA install banner" = 안 뜸. 오프라인 캐싱 = 0 (service worker 미등록).

**Fix 후보**:

- `frontend/public/manifest.json` 생성 + Clerk middleware 의 public route 에 `/manifest.json` 추가.
- `frontend/app/layout.tsx` 의 `<head>`:
  ```tsx
  <link rel="manifest" href="/manifest.json" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  <meta name="theme-color" content="#2563eb" />
  ```
- 192x192 + 512x512 PNG 아이콘 생성.

**Severity**: P1 (Beta 가능, H2 정식 출시 의무).

---

### BL-342 (P1) — Number input `inputmode` 누락 → 모바일 키패드 오동작 [High]

**증상**: `/backtests/new` 폼의 number input 3개:

- 초기 자본 (USDT): `type="number"`, `inputmode=null`
- 수수료 (소수): `type="number"`, `inputmode=null`
- 슬리피지 (소수): `type="number"`, `inputmode=null`

**영향**: iOS Safari + Chrome Android `type="number"` 단독 = numeric keyboard 가 나오긴 하지만 **소수점 키 (`.`) 가 없는 디바이스 다수**. `inputmode="decimal"` 명시해야 모든 모바일 키보드에서 `.` 키 제공.

**부수 발견 — 심볼 input**:

- type="text" + autocomplete="" + autocapitalize=null + spellcheck=true
- "BTC/USDT" 입력 시 모바일 자동 spell-check 가 빨간 줄 + 자동 대문자 첫글자 = 매번 수동 수정 필요.

**Fix 후보**:

- 모든 number input: `inputmode="decimal"` 추가.
- 심볼 input: `autocomplete="off" autocapitalize="characters" spellCheck={false}`.

**Severity**: P1.

---

### BL-343 (P1) — 모바일 nav sheet 메뉴 disabled 3개 시각 vs ARIA 불일치 [High]

**증상**: 햄버거 sheet 내부 "데이터" / "템플릿" / "거래소" 가:

- 시각적으로 **표시되어 있음** (회색/흐림 처리)
- ARIA snapshot 에는 **잡히지 않음** (interactive tree -i 에서 제외)

**영향**:

- 정상 사용자: "왜 안 눌리지?" 혼란 → 클릭 시도 → 무반응 → 좌절.
- Screen reader 사용자: 항목 자체 missing → 메뉴 구조 인지 X.
- a11y 위반 (WCAG 2.1 SC 4.1.2 Name, Role, Value).

**Casual 페르소나 보고 = "모바일에서는 disabled 3개 숨김"** → 보고 자체가 시각 관찰만 했을 가능성. 본 페르소나는 ARIA snapshot + 스크린샷 cross-reference 로 검출.

**Fix 후보**:

- `aria-disabled="true"` + visual treatment 유지 (둘 다 일관)
- OR display 완전 제거 + 사용자에게 "Coming soon" tooltip

**Severity**: P1 (a11y + UX 혼란).

---

### BL-344 (P2) — Trading 페이지 API key partial reveal 모바일 노출 [Medium]

**증상**: `/trading` "거래소 계정" 테이블 모바일 노출 — `API Key: 0Cai******ZhqX` partial reveal. 휴지통 삭제 버튼이 같은 줄 우측에 있음.

**영향**:

- **Privacy risk**: 모바일 한 손 사용자가 출퇴근 시 옆사람에게 API key partial 노출. partial 이지만 4글자 prefix + 4글자 suffix = brute force/SE attack 도움.
- **Destructive action 근접성**: 휴지통 버튼이 API key 같은 줄에 있어 큰 손가락 오탑 시 API key 삭제 위험.

**Fix 후보**:

- Mobile breakpoint: API key 컬럼 mask 강화 (`••••••••••` 만, hover/tap 으로 reveal).
- 삭제 버튼 separate row OR confirm dialog with 2-step.

**Severity**: P2 (HW key reveal 아니므로 critical 아님, 다만 production 출시 전 의무).

---

### BL-345 (P2) — Backtests 목록 모바일 cell wrap 가독성 [Medium]

**증상**: `/backtests` 목록 페이지, 6열 테이블 (심볼/TF/기간/상태/실행일/상세) 가 모바일 viewport 에서 그대로 표시 → "기간" 컬럼 = "2025-11-14 00:00 → 2026-05-13 00:00" 이 **4줄 wrap**, "상세 →" 가 2줄 wrap, "실행일" 도 wrap.

**영향**: 가독성 사고 + 가로 overflow +81px (BL-340 의 일부).

**Fix 후보**: 모바일 = card layout 또는 accordion. Desktop 만 table.

**Severity**: P2.

---

### BL-346 (P3) — Beta disclaimer banner 모바일 폭 압축 [Low]

**증상**: 베타 disclaimer ("Beta: QuantBridge is provided as-is. See Disclaimer · Terms · Privacy. (Beta 단계 — H2 말 정식 변호사 검토본 교체 예정)") 가 모바일 폭에서 매우 압축되어 표시 + 링크 14pt = BL-339 의 일부.

**Fix 후보**: 모바일 = "Beta. 자세히 →" 짧은 형식 + tap 시 modal.

**Severity**: P3.

---

## 환경 / 측정 메서드

- **Browser**: Chromium (browse skill via daemon)
- **Viewport**: 375x667 / 393x852 / 412x892
- **Network**: localhost (3G 추정 = 별도 throttle 미진행)
- **Auth**: 다른 페르소나가 만든 로그인 세션 재사용 (Clerk: 우성 장)
- **측정**: `getBoundingClientRect()` + ARIA snapshot + perf API
- **스크린샷**: `docs/qa/2026-05-17/screenshots/mobile-{01..09}-*.png` (9개)

---

## Summary

**Composite Mobile 점수: 3.8 / 10**

| 차원                    | 점수                                                   |
| ----------------------- | ------------------------------------------------------ |
| 3 viewport 일관성       | 6/10                                                   |
| PWA                     | 2/10                                                   |
| 한 손 도달률            | 4/10                                                   |
| 로딩/3G                 | 6/10 (추정)                                            |
| 모바일 키보드           | 3/10                                                   |
| 터치 타겟               | 2/10 (19+ 위반)                                        |
| **Horizontal overflow** | **1/10** (trading +227px)                              |
| Sprint 60 회귀          | 5/10 (4건 중 1 PASS / 1 PARTIAL PASS / 2 PARTIAL FAIL) |

**터치 타겟 위반**: strategies 페이지 단독 **19+**.
**PWA-readiness**: 2 / 10.

**결론**:

- 모바일 dogfood 가능성 = 매우 낮음. 한 손 사용자는 trading 페이지 (revenue path) 도달 불가.
- Sprint 60 P0 fix 4건 중 **2건 PARTIAL FAIL** = 회귀 fix 자체 의 깊이 부족 (UserButton DOM 사본 잔존, nav disabled 시각 vs ARIA 불일치).
- Casual 페르소나의 "PASS" 보고 = 깊이 부족 — 본 페르소나가 ARIA + bounding rect + cross-viewport 측정으로 false positive 검출.

**Sprint 61 권고**:

- **P0 즉시**: BL-340 trading overflow + BL-339 터치 타겟 (특히 UserButton 36→44, 필터 chips 30→44).
- **P1 1-2 sprint**: BL-341 PWA basics + BL-342 inputmode + BL-343 sheet a11y.
- **P2 H2 출시 전**: BL-344 API key mask + BL-345 backtests card layout.
- **P3 자투리**: BL-346 disclaimer compact + BL-338 dev widgets toggle.

---

🟢 **Mobile 페르소나 완료** — 9 스크린샷 + 9 BL 등재.
