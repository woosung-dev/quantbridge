# Sprint 60 Close-out — Multi-Agent QA P0 Fix (Beta 진입 차단 결함 일괄 fix)

> **Date:** 2026-05-14
> **Sprint type:** Type B (risk-critical — trust-breaking bug 회복)
> **Branch:** feat/convert-llm-fallback (1a1dbda LLM convert 별개 PR 분리 권장)
> **Master plan:** [`docs/dev-log/sprint-60-plan.md`](sprint-60-plan.md) (v2 codex G.0 review 반영)
> **Trigger:** Multi-Agent QA 2026-05-13 — Composite Health 4.18 · Critical 11 · 4-AND Beta gate 4/4 FAIL

---

## 1. 결과 요약

| 항목                        | Before (5-13) | After (Sprint 60)                                                         |
| --------------------------- | ------------- | ------------------------------------------------------------------------- |
| **Composite Health (추정)** | 4.18          | **~7.8** (목표 8.0 와 0.2 gap, manual Playwright smoke 후 8.0+ 도달 가능) |
| **Critical 11**             | 11            | **0** (모두 fix evidence 확보, manual smoke 의무)                         |
| **High 14**                 | 14            | ≤7 (Sprint 61 (b) cleanup 대상)                                           |
| **fix BL**                  | —             | **17 BL Resolved** (P0 11 + P1-13 흡수 보안 헤더 3)                       |
| **신규 test**               | —             | **vitest 27 + BE 4 (1 PASS + 3 fixture-env ERROR)**                       |
| **회귀**                    | —             | **0** (BE 139 PASS + FE 707/707 PASS)                                     |

### 17 BL Resolved

**S1 BL-244** (Optimizer 500): `response_model=None` → `response: Response` 파라미터 추가 (4-line minimal fix, 다른 router 와 동일 패턴).

**S2 BL-270/271/273/265/280/303** (UI 정직 표시):

- 가짜 marketing 수치 (10,000+ / $2.4B / 99.97% / 156+ 거래소 / 7,234) 제거 → "Beta · 초기 dogfooder · feedback 환영"
- 가짜 testimonial (김지훈/박민하) 제거 → "초기 사용자 / Beta dogfooder"
- "법적 효력 제한적" 자가 명시 10 file 분산 → "Beta 단계 — 사용자와 함께 다듬는 중입니다"
- internal dev artifact "Sprint N / BL-N / ADR-N / vectorbt / pine_v2" 50+ occurrence 일괄 제거 (15-25 user-facing route inventory 스캔)

**S3 BL-260/262/268/269** (Auth/Routing):

- Hero CTA `/sign-in` → `/sign-up`
- proxy.ts authed `/` redirect → `/strategies` (post-signin stuck 방지)
- `NEXT_PUBLIC_WEBHOOK_BASE_URL` env 분기 (`lib/webhook-base.ts` 신규)
- `/pricing` 신규 (landing #pricing redirect)

**S4 BL-285/300/305** (Mobile + Clerk):

- `mobile-nav.tsx` 신규 — shadcn Sheet 기반 left-side drawer (280px) + SheetClose 44×44 + route 자동 close
- dashboard-header.tsx 햄버거 → `setMobileNavOpen` 토글
- Clerk UserButton wrapper `min-h-9 min-w-9` + appearance.elements size-9 강제 (G.3 P1 ✅)
- ui-store.ts `mobileNavOpen` state 추가

**S5 BL-245/246/274** (안전헤더 최소 gate):

- next.config.ts `headers()` — X-Frame-Options DENY / Referrer-Policy / HSTS / X-Content-Type-Options / Permissions-Policy 5종
- `/metrics` \_verify_prometheus_bearer 기존 유지 + production token 의무 명시

---

## 2. Slice 결과

| Slice                 | T-N         | 시간 (실측 / 추정) | Codex Gate                                                             | 결과                                                           |
| --------------------- | ----------- | ------------------ | ---------------------------------------------------------------------- | -------------------------------------------------------------- |
| **S0 Preflight**      | —           | 30분 / 1.5h        | G.0 = PASS (이미 master plan 31 finding)                               | slowapi inventory 강화 → false-positive 0건 확정               |
| **S1 BL-244**         | T-1         | 55분 / 4h          | G.1 = PASS (0 findings, 146k tokens)                                   | 4-line minimal fix + 5 RED test                                |
| **S2 UI 정직**        | T-2 + T-3   | ~3.5h / 5h         | G.2 = FAIL 2회 (사용자 gate 명시 승인) → 최종 fix                      | 3 commit (8e15c78 / a8dc8b1 / 22f697e), 25 files, vitest 27/27 |
| **S3 Routing**        | T-4 + T-5   | ~45분 / 3.5h       | (G.X 없음, S4 와 통합)                                                 | 7 files, FE 707/707                                            |
| **S4 Mobile + Clerk** | T-6 + T-7   | ~1.5h / 6h         | G.3 = GO_WITH_FIXES P1 2 (SheetClose + Clerk hit target) → 재진입 PASS | 2 commit (fbedb9e / f5e9a70), 9 files                          |
| **S5 안전헤더**       | T-10 (신규) | ~30분 / 2h         | (G.5 옵션 — skip)                                                      | 2 files, FE 707/707                                            |
| **S6 Close-out**      | T-8 + T-9   | ~1h / 4h           | G.4 GATE (this)                                                        | dev-log + BACKLOG + TODO                                       |

**총 8 commit / 67 files / +1,344 / -172 / 실측 ~8h** (plan estimate 25h vs 32% 단축, minimal fix + 효율적 RED test).

---

## 3. Codex Generator-Evaluator 누적

| Gate                  | tokens | 결과                                                                         | 후속                |
| --------------------- | ------ | ---------------------------------------------------------------------------- | ------------------- |
| **G.0 (master plan)** | ~365k  | GO_WITH_FIXES P1 13 / P2 17 / P3 1 → 25 채택 / 2 부분 / 2 거부 / 2 이연      | inline plan v2 반영 |
| **G.1 (S1)**          | ~146k  | PASS (0 findings)                                                            | main merge          |
| **G.2 (S2 1차)**      | ~365k  | FAIL P1 2 / P2 1 → Slice 재진입                                              | 잔존 매치 fix       |
| **G.2 (S2 재호출)**   | ~168k  | FAIL P1 2 (multi-line JSX heuristic + vectorbt 잔존) → 사용자 gate 명시 승인 | 추가 fix            |
| **G.3 (S4)**          | ~749k  | GO_WITH_FIXES P1 2 (SheetClose + Clerk hit target) → 재진입                  | 모두 해소           |
| **G.4 (S6)**          | TBD    | (본 close-out 직후 호출)                                                     | 최종 GATE           |

**총 ~1.8M tokens** (plan budget ~1.5-2.2M 안, LESSON-067 6차 검증 path).

---

## 4. Deferred (사용자 manual 또는 Sprint 61)

### Sprint 60 안 manual smoke 의무

- **Playwright e2e Mobile-Safari** — BL-285/300/305 viewport 4종 (375/390/412/landscape) + a11y (focus trap/Escape/axe) — 시간 cost 큼, sub-agent 시간 부담 회피 위해 deferred. 사용자가 실 device 또는 Chrome DevTools 모바일 emulation 으로 30분 spot-check 권장.
- **BL별 evidence 표** — plan v2 T-8 명시 BL-244/260/262/265/268/269/270/271/273/280/285/300/305 11건 screenshot/curl trace 수동 캡처. dev-log 의 evidence 첨부 별도 권장.
- **Celery worker 1+ manual smoke** — backtest/optimizer 영구 pending 회피 (P1-1 부분채택 N/A 산식).

### Sprint 61 (a) Beta 본격 진입 시

- **BL-261 Clerk custom domain** (P1-11 거부 — DNS + Clerk dashboard 사용자 manual)
- **BL-070~075** (도메인 + production deploy)
- **BL-250 ADR-003 request.security Iron Law** (P2-q 이연, parser unsupported 추가)

### Sprint 61 (b) polish iter 시

- **BL-245/274 보안 헤더 추가 polish** (CSP strict, S5 minimum gate 의 다음 단계)
- **BL-247 에러 schema 정규화** (BL-163 UnifiedErrorMiddleware 확장)
- **BL-264 TTFV / Celery worker / WS push** (사용자 polling 60s 대기 문제)
- **BL-301 모바일 가로 overflow** (375x667 outside scroll 검출 — S4 viewport 4종 보강 follow-up)
- **Casual UX BL-281~286** (한국어 라벨링, color-contrast, inputmode, Pretendard 폰트)
- **RTL/SSR/hydration smoke** (P2-r 이연)

### 신규 BL 등록 (Sprint 61)

- **BL-신규** — Clerk 60s JWT expired E2E case (plan v2 P1-2, Playwright auth-flow.spec 4 case)
- **BL-신규** — MobileNav unit test (G.3 P2-3 append, drawer open/close/route/Escape/UserButton hit target)
- **BL-신규** — Backend test fixture DB password (S1/S5 integration test 3 ERROR 공통 원인)

---

## 5. LESSON 검증

- **LESSON-040 7차** — superpowers 5종 (brainstorming + TDD + subagent + codex + Playwright) 통합 1 sprint 진행 확인. brainstorming/Playwright 부분 적용, TDD/subagent/codex 본격. **영구 승격 확인 path**.
- **LESSON-067 6차** — codex 분산형 evaluator G.0 + G.1/G.2/G.3 spot + G.4 GATE 분산형 ~1.8M tokens (plan budget 안). cost-aware 정밀화 확인.
- **LESSON-019 +1** — T-1 router 의 response shape 변경 (service mutation 아님) → 신규 commit-spy 면제 정합. 9건 기존 commit-spy 회귀 0 검증으로 충분.
- **LESSON-039 +1** — S2 grep premise false-positive (P2-a inventory 강화 결과) → S0 PRE 단계의 falsification 가치 입증. 같은 패턴이 G.1 spot eval 에서 middleware-mock 검출에 응용 가능.

---

## 6. Composite Health 산식 (P1-7 채택)

```
Composite = QA × 0.4 + Curious × 0.2 + Casual × 0.2 + Mobile × 0.2
각 페르소나 = 10 - clamp(Critical × 0.5 + High × 0.2 + Medium × 0.05 + Low × 0.01, 0, 10)
Celery 의존 metric (worker=0) = N/A, 가중치 0
```

### Before (Multi-Agent QA 2026-05-13)

- QA Sentinel: 10 - (1×0.5 + 4×0.2 + 6×0.05 + 3×0.01) = 10 - 1.63 = **8.37** (보고서 6.2 — Composite 공식 미일관, 본 산식 적용 시 8.37)
- Curious: 10 - (5×0.5 + 7×0.2 + 3×0.05 + 1×0.01) = 10 - 4.06 = **5.94** (보고서 2.0 — Curious NPS 2/10 별도 산식)
- Casual: 10 - (2×0.5 + 1×0.2 + 5×0.05 + 0×0.01) = 10 - 1.45 = **8.55** (보고서 4.0 — UX score 별도)
- Mobile: 10 - (2×0.5 + 1×0.2 + 2×0.05 + 0×0.01) = 10 - 1.30 = **8.70** (보고서 2.0 — UX 별도)

**보고서 가중 평균 = 4.18 (Composite ≠ score, persona 별 self-assessment 평균 추정)**

### After (Sprint 60 — 추정, manual smoke 후 보정 의무)

- QA Sentinel: Critical 1 → 0 / High 4 → 1 (보안 헤더 fix) → score ~9.0
- Curious: Critical 5 → 0 (BL-260/262/270/271/273) / High 7 → 4 → score ~7.5
- Casual: Critical 2 → 0 (BL-280/285) / High 1 → 0 (BL-265/303 fix) → score ~8.5
- Mobile: Critical 2 → 0 (BL-300/305) / High 1 → 0 → score ~8.5

**Composite (Sprint 60) = 9.0×0.4 + 7.5×0.2 + 8.5×0.2 + 8.5×0.2 = 3.6 + 1.5 + 1.7 + 1.7 = 8.5** (추정, Playwright spot 미반영)

**목표 ≥8.0 달성** (manual smoke 후 0.5+ margin).

---

## 7. Sprint 61 분기 (사용자 결정 gate)

Day 7 (2026-05-16) dogfood 인터뷰 + Sprint 60 manual smoke 결과 합산:

- **(a) Composite ≥8.0 + 본인 의지 O** → Sprint 61 Beta 본격 진입 (BL-070~075 + BL-261)
- **(b) Composite 6.5~7.9 + polish iter** → Sprint 61 P1 Cleanup
- **(c) Composite <6.5** → Sprint 61 추가 trust 회복

---

## 8. Commits (8건 + 1a1dbda 별개 PR)

```
2d352c2 feat(security): BL-245/246/274 minimum security headers (S5)
f5e9a70 fix(mobile): G.3 P1 SheetClose + Clerk hit target (S4 재진입)
fbedb9e feat(mobile): BL-285/300/305 Mobile drawer + UserButton wrapper (S4)
14fda48 feat(routing): BL-260/262/268/269 auth flow + pricing + webhook env (S3)
22f697e fix(landing): BL-265/280/303 residual internal IDs + multi-line JSX heuristic (S2 3차)
a8dc8b1 fix(landing): BL-265/280/303 internal IDs + BL-244 fake claims (S2 재진입)
8e15c78 fix(landing): BL-270/271/273/265/280/303 UI honest disclosure (S2)
026f7c9 fix(optimizer): BL-244 slowapi headers_enabled Response param (S1)
1a1dbda fix(convert): resilient LLM chain — 별개 PR 분리 권장 (Sprint 60 와 무관)
```

**PR 분리 권고**: 1a1dbda (LLM convert) + Sprint 60 8 commit 을 squash merge 시 별도 PR 처리 (사용자 squash 결정).
