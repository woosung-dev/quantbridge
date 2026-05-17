# Beta gate 완성 — Sprint 62 fix-first plan (P0 1 + P1 2 묶음)

**일자**: 2026-05-17 (Sprint 61 fix-first 머지 후 즉시)
**Type**: B (risk-critical fix-first, Sprint 60/61 패턴 재현)
**근거**: `docs/qa/2026-05-17-post-sprint61/integrated-report.html` Composite 7.5/10, 4-AND Beta gate (a) PASS / (b) PARTIAL / (c) borderline → fix-first 후 Beta 본격 진입 자격.

---

## 1. 목표 (1줄)

**Composite 7.5 → 8.5+ 회복. BL-350/354 ★★★ 공통 P0 + BL-356~359 모바일 터치 묶음 + BL-353 라벨 통일 → 4-AND Beta gate (b) Critical 0 + (c) High ≤ 3 완전 PASS → Beta 본격 진입 자격.**

---

## 2. 범위

### In Scope (P0 1 + P1 2 = 3 작업 묶음, 6-8 BL fix)

**P0 ★★★ 공통 (Curious + Casual 2 페르소나 발견)**:

- **T-1 BL-350+354** `/optimizer` Zod validation error JSON 도배 차단
  - **FE**: catch graceful degradation (raw JSON 노출 차단 + user-friendly empty state)
  - **BE**: `/optimizer/runs` listing 시 row-level resilience (Zod parse FAIL row 자동 skip + WARN log)
  - **DB**: 사용자 manual (Sprint 50-52 retro-incorrect row 재실행 또는 archive — 본 sprint scope 외)

**P1 (Mobile 페이지 내부 컨트롤)**:

- **T-2 BL-356 + BL-357 + BL-358 + BL-359** 모바일 viewport 페이지 내부 컨트롤 ≥44pt
  - **BL-356**: `/backtests/<id>` 탭 (38x25) + 기간 chips (38x32) + KPI tooltip `?` (16x16 × 5)
  - **BL-357**: `/strategies` "편집 →" 텍스트 링크 (38x16)
  - **BL-358**: UserButton width 28 잔존 + size-9 ghost DOM 8건 (SSR/hydration 이중 마운트)
  - **BL-359**: `/trading` "계정 삭제" 16x16 high risk

**P1 (UX 라이팅 통일)**:

- **T-3 BL-353** landing step 01 라벨 "전략 업로드" → "코드 붙여넣기" hero 정합

### Out of Scope (Sprint 63+ 이연)

- **BL-320 (Defer)** Development mode 배지 = Sprint 62 production deploy 시점 자동 해소 (BL-261 영역)
- **BL-321** Clerk dashboard application name 사용자 manual (선택)
- **BL-347** server header leak = uvicorn `--server-header=false` flag (production gunicorn config, 본 sprint scope 외)
- **BL-310 healthz 완전 PASS** = production 환경 검증 (Sprint 63+)
- **BL-351** SSO aria-label 영어 / **BL-352** Clerk app name manual / **BL-355** "Demo" → "데모" / **BL-360** backtests 9px overflow noise = P2/P3 batch

**사유**: P0 1 + P1 2 묶음 = 4-AND gate 직접 영향. 추가 작업 시 surface trust 회복 효과 희석.

---

## 3. 작업 분해

### T-1 BL-350+354 Optimizer Zod error fix · 4-5h

#### FE (2-3h)

- **대상**: `frontend/src/features/optimizer/` 또는 `frontend/src/app/(dashboard)/optimizer/` listing component (Zod safeparse 위치)
- **변경**:
  - `OptimizerRunsList` (또는 동일 역할 컴포넌트) 의 React Query response 처리에 try/catch
  - Zod `.parse()` → `.safeParse()` row-level 적용 + parse FAIL row 자동 skip
  - 전체 fail 시 graceful empty state: "이전 데이터 schema 불일치로 일부 row 가 표시되지 않습니다. 새 최적화를 시작해 보세요."
  - dev mode `console.warn` (production 무음)
- **테스트**: vitest unit — malformed row + valid row mix → valid row 만 표시 + warn 1건

#### BE (1-2h)

- **대상**: `backend/src/optimizer/router.py` 또는 `service.py` listing 엔드포인트
- **변경**:
  - `/optimizer/runs` 응답 시 row-level Zod/Pydantic parse 실패 → skip + `logger.warning("optimizer_run_skip_invalid_schema", run_id=...)`
  - 응답 schema 에 `total_count` + `skipped_count` 노출 (FE 가 graceful warn)
- **테스트**: pytest — invalid row mix → 200 + skipped_count > 0 + valid only

### T-2 BL-356+357+358+359 모바일 터치 ≥44pt 묶음 · 2-3h

#### Approach A: Tailwind plugin (global enforcement)

- **대상**: `frontend/tailwind.config.ts` (또는 v4 의 `app/globals.css` `@theme`)
- **변경**: 모바일 viewport (`@media (max-width: 640px)`) 에서 모든 `<button>` + `<a role="link">` 의 minimum size 44pt
- **위험**: 기존 디자인 영향 가능성 (지나친 enforcement). 대신 component-level fix 가 안전

#### Approach B: Component-level fix (권고 ★★★★★)

- **BL-356 /backtests/<id>**:
  - 탭 (Tabs component): `data-active=...` 의 height `h-7` → `h-11 md:h-7` 또는 동일 height
  - 기간 chips (date-preset-pills.tsx 추정): `h-7` → `min-h-11 md:min-h-0`
  - KPI tooltip `?` button: `size-4` → `inline-flex size-11 md:size-4` (모바일 hit area 확대, 데스크톱 시각 동일)
- **BL-357 /strategies "편집 →"**: row-wide tap target 또는 `min-h-11 px-3 md:min-h-0 md:px-0`
- **BL-358 UserButton**:
  - `dashboard-header.tsx` `rootBox: "shrink-0 size-11"` + `userButtonTrigger: "size-11"` ← 이미 적용 ✅
  - Mobile QA 발견 width 28 잔존 = `size-9 cl-userButton-root` ghost DOM 8건. SSR hydration 이중 마운트 진단 필요. **단순 fix 우선**: avatar-box width 강제 `w-11` + ghost DOM 원인 진단은 별도 BL
- **BL-359 /trading "계정 삭제"**: `dashboard/trading/_components/exchange-accounts-panel.tsx` 등의 삭제 버튼. `size-4` → `min-h-11 min-w-11` + confirmation modal 강화 (high risk 액션)

### T-3 BL-353 step 01 라벨 통일 · 5분

- **대상**: `frontend/src/app/_components/landing-how-it-works.tsx`
- **변경**: step 01 title "전략 업로드" → "전략 코드 붙여넣기" + description "Pine Script 코드를 붙여넣으면 자동으로 파싱 및 변환됩니다."
- **테스트**: 기존 landing-how-it-works.test.tsx 회귀 PASS (라벨 변경만)

---

## 4. 검증 기준

### 신규 테스트 (T-1 ~ T-3 각각 1건 이상)

- T-1: FE vitest (malformed mix → skip) + BE pytest (invalid row skip + skipped_count)
- T-2: e2e 또는 unit `getBoundingClientRect()` minimum size
- T-3: landing-how-it-works snapshot/text assertion

### 회귀

- BE 전체 + FE 전체 PASS
- ruff + mypy + tsc + lint clean

### Multi-Agent QA 재측정 (Sprint 종료 후)

- Curious + Casual + Mobile 페르소나 spot-check (~1.5h)
- Composite 7.5 → **8.5+ 의무**
- Critical 0 의무 (BL-339 페이지 내부 잔존도 회복)
- High ≤ 3 의무

---

## 5. 위험 + 완화

| 위험                                                                 | 완화                                                           |
| -------------------------------------------------------------------- | -------------------------------------------------------------- |
| Optimizer listing Zod row-level safeparse 가 정상 row 도 silent skip | log + skipped_count UI 노출. dev mode console.warn             |
| 모바일 component-level fix 가 디자인 영향                            | desktop md: 분기 의무 (`min-h-11 md:min-h-0`)                  |
| UserButton ghost DOM 원인 진단 길어짐                                | BL-358 = 단순 width 강제만 본 sprint, ghost DOM 원인은 별도 BL |
| /trading "계정 삭제" confirmation 추가 = 기존 UX 변경                | 모달 추가는 옵션. 본 sprint 는 터치 타겟만                     |

---

## 6. 자의 결정 라벨

- **Sprint Type**: B (Sprint 60/61 패턴 재현)
- **Worker pattern**: 단일 worker (6-8h scope, multi-worker ROI 없음)
- **G.0 codex consult**: ROI 낮음 (작은 fix 묶음). skip
- **G.4 final gate**: Multi-Agent QA 재측정 spot-check 로 대체
- **Sprint 63 분기**: gate 통과 → Beta 본격 진입 / 부족 시 추가 fix-first / mainnet 진입 결정

---

## 7. 예상 일정

| Phase                                     | 시간                                                                    |
| ----------------------------------------- | ----------------------------------------------------------------------- |
| Sprint plan (this) + 환경 verify          | 15분                                                                    |
| T-1 Optimizer Zod fix (FE 2-3h + BE 1-2h) | 3-5h                                                                    |
| T-2 모바일 터치 묶음                      | 2-3h                                                                    |
| T-3 step 01 라벨                          | 5분                                                                     |
| 테스트 + lint + commit + PR               | 30분                                                                    |
| **합**                                    | **6-8h 1 day single worker (Sprint 60/61 단축 패턴 적용 시 실측 3-4h)** |

---

## 8. 핵심 파일 경로

| 파일                                                                               | 역할       |
| ---------------------------------------------------------------------------------- | ---------- |
| `frontend/src/features/optimizer/` (listing component)                             | T-1 FE     |
| `backend/src/optimizer/router.py` 또는 `service.py`                                | T-1 BE     |
| `frontend/src/app/(dashboard)/backtests/[id]/_components/` (탭 + chips)            | T-2 BL-356 |
| `frontend/src/app/(dashboard)/strategies/_components/` (편집 링크)                 | T-2 BL-357 |
| `frontend/src/components/layout/dashboard-header.tsx` (UserButton)                 | T-2 BL-358 |
| `frontend/src/features/trading/components/exchange-accounts-panel.tsx` (계정 삭제) | T-2 BL-359 |
| `frontend/src/app/_components/landing-how-it-works.tsx`                            | T-3 BL-353 |

---

🟢 **Sprint 62 plan 작성 완료** — fix-first 3 작업 묶음, ≈ 6-8h scope, Composite 7.5 → 8.5+ 목표 → Beta 본격 진입 자격
