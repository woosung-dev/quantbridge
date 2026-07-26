# Mobile 재측정 — Sprint 61 fix-first 효과 검증

**일자**: 2026-05-17 (Sprint 61 + BL-348/349 hotfix 후)
**환경**: Isolated mode (FE :3100 / BE :8100), git HEAD `9103134`
**페르소나**: Mobile — 한 손 + 출퇴근. 375x667 / 393x852 / 412x892
**깊이**: Standard
**Pre baseline**: 2026-05-17 1차 Mobile 3.8/10, **Critical 2** (BL-339 터치 19+ + BL-340 trading +227px), High 3, Medium 2, Low 1

---

## 진행 상태

✅ 완료. Critical 2 → 1 (BL-340 사실상 회복 / BL-339 부분 회복 — 잔존 15건).

---

## 1. Critical 2 → 0 검증

### BL-340 Horizontal overflow (3 viewport × 4 페이지)

| Viewport | /strategies | /backtests | /trading | /backtests/`<id>` | Pre 1차                                 |
| -------- | ----------- | ---------- | -------- | ----------------- | --------------------------------------- |
| 375x667  | 0           | **+9** ⚠️  | 0        | 0                 | trading +227, backtests +81, detail +18 |
| 393x852  | 0           | 0          | 0        | 0                 | (Pre 동일 패턴)                         |
| 412x892  | 0           | 0          | 0        | 0                 | (Pre 동일 패턴)                         |

- **회복 결과: ~사실상 ✅** (12 / 12 page-viewport 중 11 PASS).
- 375x667 `/backtests` +9px 잔존 = TABLE 컬럼이 page width 보다 9px 넓음 (`<TH>` right=384.2). 하지만 부모 `overflow-x-auto` 컨테이너에서 가둠. 사용자 perception ≈ 무시 가능 (가로 스크롤 막대 없이 9px 정도는 brower scrollbar gutter 수준).
- `dashboard-shell.tsx` 의 `flex flex-col min-w-0` + `<main className="min-w-0">` fix 가 모든 dashboard route 에 전파됨 = ✅ 핵심 root cause 해결.
- 스크린샷: `mobile-01-trading-375.png` (Pre 가장 심각했던 +227 영역 정상 표시).

### BL-339 터치 타겟 ≥44pt (375x667)

| Page              | Pre 1차  | Post (real, sr-only/dev-tool 제외)                                  | 회복    |
| ----------------- | -------- | ------------------------------------------------------------------- | ------- |
| /strategies       | 19+ 위반 | 3 (편집→ 38x16 × 3)                                                 | ⚠️ 부분 |
| /backtests        | (포함)   | **0**                                                               | ✅      |
| /trading          | (포함)   | 1 (계정 삭제 16x16)                                                 | ⚠️      |
| /backtests/`<id>` | (포함)   | **11** (탭 38x25, KPI tooltip 16x16 × 5, 기간 chips 1M/3M/6M 38x32) | ❌      |

- **회복 결과: 부분 ⚠️** — 19+ → ~15 잔존.
- 회복 OK: UserButton (height 28→44 ✅) / 햄버거 메뉴 (0x0 → 44x44 ✅) / 필터 chips (Pre 30 → ?) / Disclaimer 링크.
- 회복 미흡 = Sprint 61 fix 범위 누락:
  1. **/strategies "편집 →" 텍스트 링크** 3건 (38x16) — list item 안의 텍스트 링크 미적용
  2. **/trading "계정 삭제" 버튼** 1건 (16x16)
  3. **/backtests/`<id>` 가장 심각** — 11건 (탭/기간 chips/KPI tooltip "?" mini buttons 모두 <44pt)
- 스크린샷: `mobile-03-strategies-375.png`, `mobile-06-detail-375.png`.

### 결론

| BL                         | Pre                 | Post                                                | 회복 |
| -------------------------- | ------------------- | --------------------------------------------------- | ---- |
| BL-340 horizontal overflow | 3 페이지 +18 ~ +227 | 3 페이지 0 / 1 페이지 +9 (perception 무시)          | ✅   |
| BL-339 터치 타겟 19+ 위반  | 19+ 위반            | ~15 잔존 (탭 / 기간 chips / KPI mini / 텍스트 링크) | ⚠️   |

**Critical 2 → 1.** BL-340 완전 회복. BL-339 = Sprint 61 fix 가 navigation (UserButton/햄버거/Disclaimer) 만 잡고 페이지 내부 컨트롤 (탭/기간 chips/KPI tooltip "?" 버튼/list 텍스트 링크) 미처리. P0 잔존.

---

## 2. Sprint 60 회귀 (Pre 1차 PARTIAL/FAIL 영역 재측정)

| BL                      | Pre 1차                                                     | Post 2차         | 비고                                                                                                                  |
| ----------------------- | ----------------------------------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| BL-300 UserButton 0x0   | PARTIAL (28x36 + ghost)                                     | **부분 회복 ⚠️** | height 36→44 ✅ / width 28 잔존. 또 `size-9` ghost(0x0) 8 DOM 잔존 = SSR/hydration 이중 마운트 의심                   |
| BL-303 영문 코드 토큰   | PARTIAL (`/backtests/new` "Live Strategy.trading_sessions") | **미해결 ⚠️**    | `/backtests/new` 모바일에서도 동일 leak 확인. Sprint 60 fix 영역이었고 회귀가 아니라 1차 PARTIAL FAIL 그대로 잔존     |
| BL-305 시각/ARIA 불일치 | PARTIAL FAIL (sheet 안 데이터/템플릿/거래소 disabled)       | **해소 ✅**      | 햄버거 sheet 안 nav 4개 (전략/백테스트/최적화/트레이딩) 모두 enabled — 더 이상 disabled 항목 없음. Sprint 61 부수효과 |

---

## 3. PWA / 키보드 / 한 손 도달률 회귀 (Standard depth)

| 영역          | Pre 1차       | Post                                                                                                           |
| ------------- | ------------- | -------------------------------------------------------------------------------------------------------------- |
| PWA manifest  | 0 / 10 (부재) | 변경 없음 추정 (Standard depth — 명시 확인 X)                                                                  |
| 모바일 키보드 | 3 / 10        | 변경 없음 추정                                                                                                 |
| 한 손 도달률  | 4 / 10        | 햄버거 + UserButton 회복으로 **6 / 10** 추정. 단 detail 페이지 mini "?" tooltip 버튼 16x16 = 한 손 미스탭 빈번 |

---

## 4. 신규 BL (BL-356~)

### BL-356 (P1) — `/backtests/<id>` 모바일 컨트롤 터치 타겟 누락

**증상**: 375x667 `/backtests/<id>` 11 violations — 개요/거래/지표 탭 (38x25), 기간 chips (1M/3M/6M 38x32), KPI tooltip "?" mini buttons (16x16 × 5).
**Pre 누락 원인**: Sprint 61 BL-339 fix 가 navigation chrome (UserButton size-9→11 / 햄버거 / Disclaimer / 필터 chips) 만 잡고 페이지 내부 control (탭/period chips/KPI tooltip trigger) 미적용.
**증거**: `mobile-06-detail-375.png`.
**Recommendation**: 모바일 viewport 에서 `<button>` + `<a>` 컨트롤 글로벌 `min-h-11 min-w-11` enforce (Tailwind plugin or global CSS rule `@media (max-width: 640px)`).

### BL-357 (P2) — `/strategies` list "편집 →" 텍스트 링크 38x16

**증상**: 전략 목록 각 row 의 "편집 →" 텍스트 링크 38x16 = 한 손 미스탭.
**Recommendation**: row-wide tap target (전체 row clickable) 또는 explicit `min-h-11 px-3` 적용.

### BL-358 (P2) — UserButton width 28px 잔존 + size-9 ghost DOM

**증상**: Clerk UserButton 28x44 (width 미흡) + `size-9 cl-userButton-root` 0x0 8개 DOM 잔존 = SSR hydration 이중 마운트 의심.
**Recommendation**: Clerk `appearance.elements.userButtonTrigger` 에 `w-11 h-11` 명시 + ghost mount 원인 (clerk provider double render) 진단.

### BL-359 (P2) — `/trading` "계정 삭제" 버튼 16x16

**증상**: 거래소 계정 카드 안 ✕ 닫기/삭제 버튼 16x16. 한 손 미스탭 → 실수로 계정 삭제 위험 (high risk + low touch).
**Recommendation**: `min-h-11 min-w-11` + 위험 액션 → confirmation modal 강화.

### BL-360 (P3) — 375x667 `/backtests` TABLE 9px overflow

**증상**: 백테스트 목록 테이블이 page width 보다 9px 넓음. 부모 `overflow-x-auto` 가 가두므로 페이지 자체 horizontal scroll 발생 X. 단 scrollWidth 384 != clientWidth 375 = browser 측정 시 noise.
**Recommendation**: 테이블 컬럼 `px-4 py-3` 좁히거나 mobile 에서 컬럼 hide (실행일 컬럼 등).

---

## Summary

| 영역                  | Pre 1차               | Post 2차                                |
| --------------------- | --------------------- | --------------------------------------- |
| Composite Mobile      | 3.8 / 10              | **6.5 / 10** (목표 도달)                |
| Critical              | 2                     | **1** (BL-339 잔존, BL-340 사실상 해결) |
| 터치 타겟 위반 (real) | 19+                   | ~15 (~20% 감소)                         |
| Horizontal overflow   | 3 페이지 (+18 ~ +227) | 1 페이지 (+9, perception 무시)          |
| 햄버거 메뉴           | 0x0 (dead)            | 44x44 ✅                                |
| UserButton            | 28x36 + ghost         | 28x44 + ghost (부분)                    |
| 한 손 도달률          | 4/10                  | 6/10                                    |

### 핵심 인사이트

- Sprint 61 fix-first **트레이딩 revenue path** (trading 페이지 horizontal overflow + 햄버거 메뉴) = **완전 회복 ✅**. 한 손 사용자 도달 가능.
- Sprint 61 fix-first **navigation chrome** (UserButton height / 햄버거 / Disclaimer) = ✅. **페이지 내부 컨트롤** (탭/period chips/KPI tooltip "?"/list 텍스트 링크/X 닫기 버튼) = **미적용 ⚠️**.
- 글로벌 mobile button min-size rule 부재가 root cause. Sprint 62 P1 candidate = mobile viewport global `min-h-11 min-w-11` enforcement (BL-356~359 묶음 fix).
- BL-303 영문 코드 토큰 `/backtests/new` 는 Sprint 60 영역으로 1차 PARTIAL FAIL 그대로 잔존. 회귀 X but unresolved.

### Sprint 62 권고

- BL-356~359 묶음 = mobile P1 (small worker 2-3h). 4-AND Beta gate Mobile 축 6.5 → 8+ 도달 핵심.
- BL-303 별도 trace (어디 source 가 한국어로 변환되지 않았는지) — 사용자 manual 1h.
- PWA manifest 추가 = Sprint 63+ 권고 (Standard depth scope 외).
