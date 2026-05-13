# Sprint 60 Plan v2 — Multi-Agent QA P0 Fix (Beta 진입 차단 결함 일괄 fix) + Codex G.0 Review 반영

> **Date drafted:** 2026-05-14 (v1 → v2 sync, codex G.0 31 finding 반영)
> **Sprint type:** Type B (risk-critical — trust-breaking bug 회복)
> **Trigger:** Multi-Agent QA 2026-05-13 통합 보고서 — Composite Health **4.18/10** · Critical **11** · 4-AND Beta gate 4/4 FAIL
> **Origin doc:** [`docs/qa/2026-05-13/integrated-report.html`](../qa/2026-05-13/integrated-report.html)
> **Master plan:** `/Users/woosung/.claude/plans/proud-splashing-rossum.md` (사용자 승인 완료)
> **Parent decision:** TODO.md "다음 분기" §(d) trust-breaking bug 노출 → trust 회복 1 sprint 우선

---

## 1. Context

2026-05-13 QuantBridge 첫 공식 Multi-Agent QA (QA Sentinel · Curious · Casual · Mobile · 4-pack Exhaustive ~5h/persona) 결과 — Beta 본격 진입을 차단하는 P0 결함 다수 발견. 사용자 요청 **superpowers + TDD RED-first + Generator-Evaluator codex 통합** 으로 v2 재설계.

### 사용자 결정 (확정 ★★★★★ × 5)

| 항목                  | 선택                                                                 |
| --------------------- | -------------------------------------------------------------------- |
| Execution model       | 단일 메인 세션 (~25h ≈ 2.5-3 day)                                    |
| Codex strategy        | 분산형 5회 (~2.1M tokens) — G.0 + G.1/G.2/G.3 spot + G.4 GATE        |
| TDD scope             | 9 T 전부 RED-first 의무 (BE pytest + FE Playwright e2e)              |
| G.0 escalation        | P0 1+ 추가 발견 시 즉시 사용자 결정 gate (default = freeze)          |
| Codex G.0 review 결정 | 31 권고 중 25 채택 / 2 부분 / 2 거부 / 2 이연 (master plan §결정 표) |

### 핵심 발견 요약 (Critical 11 + ★★★ 공통 4건)

- **BL-244 Critical** — Optimizer 3 endpoint HTTP 500 + 14KB stack-trace 누설 (Sprint 55/56 e2e 불능). slowapi `_inject_headers` × Pydantic response_model 충돌. **slowapi inventory 확장 결과 = optimizer 3 만 영향, 다른 router (stress_test/backtest/strategy/waitlist/convert) 모두 `response: Response` 파라미터 있어 안전 (false positive grep 해소)**.
- **BL-270/271/273 Critical** — 가짜 marketing (10,000+/$2.4B/99.97%) + 가짜 testimonial + Disclaimer "법적 효력 제한적" 자가 명시. 한국 표시광고법 위반 가능.
- **BL-300/285/305 Critical** — 모바일 햄버거 dead button + `<aside hidden>` + Clerk UserButton 0×0 → mobile reach 0%.
- **BL-265/280/303 High ★★★** — Sprint 56 / BL-233 / ADR-013 / vectorbt 내부 dev artifact UI 노출 (3 페르소나 공통).

### 4-AND Beta gate 평가

| 조건               | 현재             | 결과 |
| ------------------ | ---------------- | ---- |
| (a) NPS ≥7         | Curious 2/10     | FAIL |
| (b) Critical = 0   | 11               | FAIL |
| (c) self-assess ≥7 | Composite 4.18   | FAIL |
| (d) 본인 의지      | Sprint 47 이후 X | FAIL |

**4/4 FAIL → Sprint 60 = trust 회복 + P0 fix sprint.**

---

## 2. 목표 (1줄)

> Multi-Agent QA 가 노출한 Beta 진입 차단 P0 결함 (BL-244 Optimizer 500 + BL-270/271/273 신뢰 / 법무 + BL-285/300/305 모바일 IA + BL-265 내부 ID 노출) 을 일괄 fix 하여 Composite Health 4.18 → ≥8.0, Critical 11 → 0 달성.

---

## 3. 범위

### In Scope (P0 결함 fix, 11건 + 안전헤더 최소 gate)

- BL-244 — Optimizer 3 endpoint 500 stack-trace fix (slowapi × Pydantic response)
- BL-260 — Hero CTA `/sign-in` → `/sign-up`
- BL-262 — post-signin `/` stuck → middleware redirect
- BL-265 / BL-280 / BL-303 — 내부 ID grep 일괄 제거 (route inventory 15-25 route)
- BL-270 / BL-271 — 가짜 marketing 수치 + testimonial 제거
- BL-273 — Disclaimer "법적 효력 제한적" 자가 명시 제거
- BL-268 — Webhook URL 환경 분기 (`NEXT_PUBLIC_WEBHOOK_BASE_URL`)
- BL-269 — `/pricing` 404 → 200
- BL-275 — Optimizer raw Zod error → `error.tsx` fallback (BL-244 secondary)
- BL-285 / BL-300 — 모바일 햄버거 Sheet/Drawer + `<aside hidden md:flex>` 분리
- BL-305 — Clerk UserButton wrapper ≥36×36
- **신규 P1-13 채택:** S5 안전헤더 최소 gate — CSP/X-Frame/Referrer + `/metrics` 인증

### Out of Scope (Sprint 61+)

- BL-245/274 보안 헤더 + BL-246 `/metrics` polish (P1, Sprint 61 cleanup)
- BL-264 TTFV WS push (P1)
- BL-247 에러 schema (P1)
- BL-250 ADR-003 request.security Iron Law fix (P2-q 이연)
- BL-261 Clerk custom domain (P1-11 거부 — DNS 사용자 manual)
- BL-263 Dashboard MVP
- BL-301 모바일 가로 overflow
- Casual UX BL-281~286 (한국어 라벨링, color-contrast, inputmode, Pretendard)
- RTL/SSR/hydration 검증 (P2-r 이연)

---

## 4. Slice 구조 + Superpowers Wire-up

**6 Slice / 25h** (v1 15.5h + codex G.0 P1 13 반영 + estimate 보수성 P2-e 채택)

| Slice                       | 묶음 T      | 시간 | Sup-skills                                                                               | Worktree                               | 진입 조건                                                            |
| --------------------------- | ----------- | ---- | ---------------------------------------------------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------- |
| **S0 Preflight**            | —           | 1.5h | brainstorming + writing-plans + systematic-debugging + verification-before-completion    | X (메인)                               | —                                                                    |
| **S1 BL-244 Optimizer 500** | T-1         | 4.0h | TDD + systematic-debugging + verification-before-completion                              | **O** `feat/sprint60-s1-bl244-slowapi` | S0 G.0 PASS                                                          |
| **S2 UI 정직 표시**         | T-2 + T-3   | 5.0h | TDD + dispatching-parallel-agents + verification-before-completion                       | **O** `feat/sprint60-s2-ui-honesty`    | S0 G.0 PASS                                                          |
| **S3 Auth/Routing**         | T-4 + T-5   | 3.5h | TDD + verification-before-completion                                                     | **O** `feat/sprint60-s3-routing`       | S0 G.0 PASS                                                          |
| **S4 Mobile + Clerk**       | T-6 + T-7   | 6.0h | TDD + verification-before-completion                                                     | **O** `feat/sprint60-s4-mobile`        | **S1+S2+S3 모두 main merge + green test** (P1-3 채택 preflight 강제) |
| **S5 안전헤더 최소 gate**   | T-10 (신규) | 2.0h | TDD + verification-before-completion                                                     | `feat/sprint60-s5-security-headers`    | —                                                                    |
| **S6 Gate + Close-out**     | T-8 + T-9   | 4.0h | finishing-a-development-branch + requesting-code-review + verification-before-completion | 통합 main merge                        | S1~S5 PASS                                                           |

### S4 진입 preflight command (P1-3 + P1-10 채택)

```bash
git fetch origin main
git log --oneline origin/main..HEAD                       # 1줄도 없어야 main 동기
S1_MERGED=$(git log --oneline origin/main --grep "BL-244" | head -1)
S2_MERGED=$(git log --oneline origin/main --grep "Sprint 60 S2" | head -1)
S3_MERGED=$(git log --oneline origin/main --grep "Sprint 60 S3" | head -1)
[ -z "$S1_MERGED" ] || [ -z "$S2_MERGED" ] || [ -z "$S3_MERGED" ] && { echo "BLOCKED: S1/S2/S3 미머지"; exit 1; }
```

---

## 5. Slice 별 세부 흐름

### S0 Preflight (1.5h)

**PRE (30분):**

- `brainstorming` — plan 결정 4건 + codex review 결정 표 확인 (이미 완료)
- `writing-plans` — `docs/dev-log/sprint-60-plan.md` v1 → v2 sync (본 파일)
- `systematic-debugging` — slowapi inventory grep (`@limiter.limit` route 가 `Response` 파라미터 갖는지 assert) — **결과: optimizer 3 만 BL-244 패턴, 나머지 안전 (false positive 해소)**

**MAIN (45분):**

- **codex G.0 호출** (JSON schema 강제, P2-d 채택) — **이미 완료 (master plan ExitPlanMode 직전 31 finding)**
- LESSON-039 falsification scan — `backend/tests/optimizer/` mock 패턴 검색 (현재 mock 없음 = 통합 테스트 부재 의심)

**POST (15분):**

- G.0 결과 분기 (master plan §결정 표):
  - 25 채택 inline / 2 부분채택 / 2 거부 / 2 이연
  - P0 추가 발견 = 0 (false positive 해소) → **PASS → S1 진입**

### S1 BL-244 Optimizer 500 (4.0h, P1-4 채택)

**RED (1.0h):**

- `backend/tests/optimizer/test_runs_error_response.py` (신규 5 test, P1-4 강화):
  - test 1-3: POST `/api/v1/optimizer/runs/{grid-search,bayesian,genetic}` real HTTPX → 현재 500 + `text/plain` traceback 확인
  - test 4: forced service exception (mock raise) → Content-Type=`application/json` + no traceback (P1-4)
  - test 5: 정상 → 202 + JSON
- RED 확인: `uv run pytest backend/tests/optimizer/test_runs_error_response.py -v` (3-5 FAIL)

**GREEN (1.5h):**

- `backend/src/optimizer/router.py` — 3 endpoint:
  ```python
  @router.post("/runs/grid-search", status_code=202)  # response_model 제거
  @limiter.limit("5/minute")
  async def submit_grid_search(
      request: Request,
      data: CreateOptimizationRunRequest,
      response: Response,  # 신규 — slowapi headers_enabled 호환
      user: CurrentUser = Depends(get_current_user),
      service: OptimizerService = Depends(get_optimizer_service),
  ) -> JSONResponse:
      result = await service.submit_grid_search(data, user_id=user.id)
      return JSONResponse(result.model_dump(mode='json'), status_code=202)
  ```
- 또는 `response: Response` 파라미터 추가만으로 fix (다른 router 패턴 동일) — S1 첫 step 에서 단순 fix 시도 (P1-4 RED 확인 후)
- `OptimizationExecutionError(public, internal)` 패턴 (Sprint 54 BL-230) — internal 누설 차단

**REFACTOR (45분):**

- `_to_run_response()` helper 또는 단순 `response: Response` 파라미터 추가 (다른 router 와 같은 minimal 패턴)
- LESSON-019 기존 8건 commit-spy 회귀 0 검증

**POST (45분):**

- `verification-before-completion` — curl smoke 3 endpoint
- **codex G.1 spot eval** (light, ~200k)

### S2 UI 정직 표시 (5.0h, P1-5/6 채택)

**RED (1.5h):**

- **route inventory 의무 (P1-5)** — `frontend/src/app/**/page.tsx` glob → user-facing route 전체 (15-25 route)
- `frontend/tests/e2e/landing-no-fake-metrics.spec.ts` (신규, **섹션 기반 P1-6**):
  - Hero/Stats/Testimonial section locator → known fake (10,000/156/7,234/$2.4B/99.97/김지훈/박민하/법적 효력 제한적) 0 match
  - 합법 문맥 false-positive 회피 (component-level locator)
- `frontend/tests/e2e/no-internal-ids.spec.ts` (신규, **route inventory 전체 P1-5**):
  - 모든 user-facing route 에서 regex `/(Sprint \d+|BL-\d+|ADR-\d+|vectorbt|pine_v2)/` 0 match

**GREEN (2.5h, 병렬, P2-l 채택):**

- `dispatching-parallel-agents` — write-set 명시:
  - **Sub-A (T-2)**: `frontend/src/app/(public)/page.tsx` + auth pages + disclaimer/terms/privacy
  - **Sub-B (T-3)**: `frontend/src/app/(dashboard)/optimizer/page.tsx` + Step1\*.tsx + features/backtest + BetaBanner.tsx
  - **공유 파일** = 메인 세션 직렬

**POST (30분):**

- 5 페이지 spot Playwright + route inventory 전체 grep
- **codex G.2 spot eval** (light, ~250k)

### S3 Auth/Routing (3.5h, P1-2 채택)

**RED (1.0h):**

- `frontend/tests/e2e/auth-flow.spec.ts` (신규 4 case, P1-2):
  - case 1: hero CTA `/sign-up`
  - case 2: authed `/` → `/strategies` redirect
  - case 3: **expired Clerk JWT (60s) → re-auth no loop**
  - case 4: **token tamper → 401 한국어**
- `frontend/tests/e2e/pricing-route.spec.ts` + `webhook-url.spec.ts` (신규)

**GREEN (1.5h):**

- `frontend/src/app/(public)/page.tsx` — Hero CTA `href="/sign-up"`
- **`frontend/src/proxy.ts` (P2-b 파일명 정정 — Next 16)** — authed `/` redirect + `@clerk/testing` expired-session handler
- `frontend/src/features/strategy/edit/WebhookCard.tsx` — `NEXT_PUBLIC_WEBHOOK_BASE_URL`
- **`.env.example` + `frontend/.env.example` 갱신 의무 (P2-h)** — `NEXT_PUBLIC_WEBHOOK_BASE_URL=http://localhost:8100`
- `frontend/src/app/pricing/page.tsx` (신규)

**POST (30분):**

- `verification-before-completion` — manual click flow + expired-session smoke

### S4 Mobile + Clerk (6.0h, P1-3/10 + P2-f/g 채택)

**선결 조건:** **S1 + S2 + S3 모두 main merge + green test (preflight command 강제)**

**RED (1.5h, P2-f/g 채택):**

- `frontend/tests/e2e/mobile-nav.spec.ts` (신규, `--project=Mobile-Safari`):
  - **viewport 4종 (P2-f)**: 375x667 / 390x844 / 412x892 / 568x320 landscape
  - case A: 햄버거 click → Sheet `[role="dialog"]` 보임 → nav link → URL 변경
  - case B: UserButton ≥36×36
  - **case C (P2-g)**: focus trap / Escape / overlay click / tab order / `aria-labelledby`
  - **case D (P2-g)**: axe-core scan — Sheet open 상태 a11y violations 0

**GREEN (3.5h):**

- **`frontend/src/components/layout/dashboard-sidebar.tsx` (P2-b 정정)** — `<aside hidden md:flex md:flex-col>`
- `frontend/src/components/layout/MobileNav.tsx` (신규) — shadcn `<Sheet>`
- **`frontend/src/components/layout/dashboard-header.tsx` (P2-b 정정)** — 햄버거 click → setMobileNavOpen
- Clerk UserButton wrapper `<div style="min-width: 36px; min-height: 36px">`

**POST (30분):**

- desktop 1280/1440/1920 viewport 회귀 spot
- **codex G.3 spot eval** (medium, ~350k)

### S5 안전헤더 최소 gate (2.0h, P1-13 신규)

**RED (30분):**

- `frontend/tests/e2e/security-headers.spec.ts` — CSP/X-Frame/Referrer-Policy 존재
- `backend/tests/health/test_metrics_auth.py` — `/metrics` 401 (no bearer) / 200 (valid bearer)

**GREEN (1.0h):**

- **`frontend/next.config.ts` (P2-b 정정 `.js` → `.ts`)** — headers() 추가
- `backend/src/main.py` — `_verify_prometheus_bearer` (이미 존재) fallback 차단 의무 (production)

**POST (30분):**

- curl smoke + (옵션) codex G.5

### S6 Gate + Close-out (4.0h, P1-7/8/12 채택)

**MAIN (2.5h):**

- T-8 Composite Health spot-check:
  - **명시된 산식 (P1-7)**:
    ```
    Composite = QA × 0.4 + Curious × 0.2 + Casual × 0.2 + Mobile × 0.2
    각 페르소나 = 10 - clamp(Critical × 0.5 + High × 0.2 + Medium × 0.05 + Low × 0.01, 0, 10)
    Celery 의존 metric (worker=0) = N/A, 가중치 0 (P1-1 부분채택)
    ```
  - **Critical 11→0 BL별 검증 표 (P1-8)** — BL별 재현/expected before/after/evidence
  - **BL-275/280 forced-error E2E (P1-12)** — `app/error.tsx` + 도메인별 + Zod fallback

**POST (1.5h):**

- **codex G.4 GATE** (heavy, ~700k) — **PASS_WITH_FOLLOWUP 엄격화 (P2-k)** — P2/P3 only, P0/P1 잔존 = FAIL
- `finishing-a-development-branch` — 통합 PR
- T-9 dev-log close-out + REFACTORING-BACKLOG.md + TODO.md

---

## 6. Codex Generator-Evaluator 명세 (분산형 5 gate, JSON schema)

모든 호출 STRICT JSON 출력 (P2-d):

```json
{
  "gate": "PASS" | "GO_WITH_FIXES" | "FAIL",
  "findings": [
    {"id": "G.X-N", "severity": "P0|P1|P2|P3", "category": "...", "repro": "...", "affected_files": [...], "blocking_rule": "auth|security|correctness|ux|docs", "evidence": "...", "required_fix": "..."}
  ],
  "tokens_used": N
}
```

| Gate    | 시점         | budget       | 명령                                                                        |
| ------- | ------------ | ------------ | --------------------------------------------------------------------------- |
| **G.0** | S0 종료      | ~600k heavy  | (이미 완료 — master plan ExitPlanMode 직전 31 finding)                      |
| **G.1** | S1 종료      | ~200k light  | `codex review --branch feat/sprint60-s1-bl244-slowapi --goal "..."`         |
| **G.2** | S2 종료      | ~250k light  | `codex review --branch feat/sprint60-s2-ui-honesty --goal "..."`            |
| **G.3** | S4 종료      | ~350k medium | `codex review --branch feat/sprint60-s4-mobile --goal "..."`                |
| **G.4** | S6 pre-merge | ~700k heavy  | `codex review --plan ... --branch main...sprint60-integration --goal "..."` |

**총 budget:** ~2.1M (Sprint 51 1.0-1.3M, 53 1.03M 누적 정합, LESSON-067 6차)

### Slice 재진입 정책 (P2-p 통일)

| Gate 결과                    | 처리                        | retry budget |
| ---------------------------- | --------------------------- | ------------ |
| PASS                         | 진행                        | —            |
| GO_WITH_FIXES P3 only        | append, 진행                | unlimited    |
| GO_WITH_FIXES P2 ≤3          | append, 진행 (사유 dev-log) | 1회          |
| GO_WITH_FIXES P2 ≥4 OR P1 ≥1 | Slice 재진입                | 1회          |
| FAIL                         | Slice 재진입                | 1회          |

### Tie-break (P2-o)

- P1+ → merge block default / 메인 거부 시 사용자 명시 승인 의무 + dev-log 사유
- P2 → backlog BL ID + 사유 / 진행 가능

---

## 7. TDD RED-First 의무 매트릭스 (v2)

| T              | RED 파일                                                                  | 시나리오                                                                                                                 | RED 확인                                              | GREEN 후       | REFACTOR                                     |
| -------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- | -------------- | -------------------------------------------- |
| T-1            | `backend/tests/optimizer/test_runs_error_response.py` (신규 5 test, P1-4) | 1-3: real HTTPX POST 3 endpoint → **500 + text/plain traceback** / 4: forced exception → JSON no traceback / 5: 202 JSON | `uv run pytest ...` (3-5 FAIL)                        | 5 PASS         | `response: Response` 파라미터 추가 (minimal) |
| T-2            | `frontend/tests/e2e/landing-no-fake-metrics.spec.ts` (P1-6 섹션 기반)     | Hero/Stats/Testimonial → 10,000/156/7,234/$2.4B/99.97/김지훈/박민하/법적 효력 제한적 0 match                             | `pnpm playwright test landing-no-fake-metrics` (FAIL) | PASS           | i18n (옵션)                                  |
| T-3            | `frontend/tests/e2e/no-internal-ids.spec.ts` (P1-5 route inventory)       | 15-25 route 전체 `/(Sprint\|BL-\|ADR-\|vectorbt\|pine_v2)/` 0 match                                                      | `pnpm playwright test no-internal-ids` (FAIL)         | PASS           | `<DevTag>` (옵션)                            |
| T-4            | `frontend/tests/e2e/auth-flow.spec.ts` (P1-2 4 case)                      | (a) CTA /sign-up (b) authed redirect (c) **expired 60s JWT no loop** (d) **token tamper 401 한국어**                     | `pnpm playwright test auth-flow` (4 FAIL)             | 4 PASS         | proxy matcher                                |
| T-5            | `pricing-route.spec.ts` + `webhook-url.spec.ts` + **.env.example 갱신**   | `/pricing` 200 / WebhookCard `localhost` 미노출                                                                          | (FAIL)                                                | PASS           | `getWebhookBaseUrl()`                        |
| T-6            | `mobile-nav.spec.ts` (P2-f viewport 4 + P2-g a11y)                        | A: Sheet open → URL / B: UserButton ≥36 / **C: focus trap/Escape / D: axe 0 violations**                                 | (FAIL)                                                | PASS           | shared `<MobileNav>`                         |
| T-7            | 위 case B (4 viewport)                                                    | UserButton ≥36×36                                                                                                        | 동일                                                  | PASS           | wrapper div min-size                         |
| T-8            | 명시된 산식 + Critical 11→0 BL별 검증 표 (P1-7/8)                         | Composite ≥8.0 / Critical=0 / BL별 evidence                                                                              | spot-check                                            | Composite ≥8.0 | —                                            |
| T-9            | docs only                                                                 | —                                                                                                                        | git diff                                              | —              | —                                            |
| T-10 (신규 S5) | `security-headers.spec.ts` + `test_metrics_auth.py` (P1-13)               | CSP/X-Frame/Referrer / `/metrics` 401                                                                                    | (FAIL)                                                | PASS           | —                                            |

**LESSON-019 commit-spy 의무:** T-1 router 변경 = response shape only (service mutation 아님) → 신규 commit-spy 불필요. 기존 8건 회귀 0 검증만.

---

## 8. Critical Files (P2-b 파일명 정정)

| 파일                                                       | 역할                                     |
| ---------------------------------------------------------- | ---------------------------------------- |
| `backend/src/optimizer/router.py`                          | T-1 fix                                  |
| `backend/src/main.py`                                      | T-10 `/metrics` 인증                     |
| `backend/tests/optimizer/test_runs_error_response.py`      | T-1 신규 RED (5건)                       |
| `backend/tests/health/test_metrics_auth.py`                | T-10 신규 RED                            |
| `backend/tests/optimizer/test_service_commits.py`          | LESSON-019 회귀 0                        |
| `frontend/src/app/(public)/page.tsx`                       | T-2 hero + Hero CTA                      |
| `frontend/src/app/(dashboard)/optimizer/page.tsx`          | T-3 H1 정정                              |
| **`frontend/src/components/layout/dashboard-sidebar.tsx`** | T-6 sidebar (P2-b)                       |
| `frontend/src/components/layout/MobileNav.tsx`             | T-6 신규                                 |
| **`frontend/src/components/layout/dashboard-header.tsx`**  | T-6 햄버거 + T-7 UserButton (P2-b)       |
| **`frontend/src/proxy.ts`**                                | T-4 authed redirect + JWT expired (P2-b) |
| `frontend/src/app/pricing/page.tsx`                        | T-5 신규                                 |
| **`frontend/next.config.ts`**                              | T-10 headers() (P2-b `.ts`)              |
| `frontend/.env.example` + `backend/.env.example`           | T-5 `NEXT_PUBLIC_WEBHOOK_BASE_URL`       |
| `frontend/src/app/error.tsx` + 도메인 error.tsx            | T-8 forced-error fallback (P1-12)        |
| `frontend/tests/e2e/*.spec.ts`                             | RED 7 spec                               |
| `docs/dev-log/2026-05-XX-sprint60-close.md`                | T-9                                      |
| `docs/REFACTORING-BACKLOG.md`                              | T-9 BL Resolved                          |
| `docs/TODO.md`                                             | T-9                                      |

---

## 9. 위험 + 완화책 (11건)

| #   | 위험                                                  | 완화                                                                                             |
| --- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | slowapi fix 다른 endpoint 영향                        | S0 inventory 강화 결과 = optimizer 만 영향 (false positive 해소)                                 |
| 2   | 가짜 수치 제거 marketing blowup                       | scope "제거만" / 신규 카피 Sprint 61                                                             |
| 3   | 모바일 햄버거 → desktop sidebar 회귀                  | S4 POST desktop viewport spot 의무                                                               |
| 4   | Clerk UserButton API upgrade                          | wrapper div min-size (Clerk API 비의존)                                                          |
| 5   | P1 묶기 blowup                                        | "P0 11 + S5 안전헤더만" 분할                                                                     |
| 6   | codex G.0 P0 추가 발견                                | 즉시 사용자 결정 gate (default freeze, freeze scope = code 금지/docs 허용/emergency 사용자 승인) |
| 7   | TDD RED test +30% 시간                                | 25h estimate 반영                                                                                |
| 8   | worktree 충돌                                         | S4 진입 전 S1+S2+S3 머지 preflight 강제                                                          |
| 9   | Evaluator-Generator 충돌                              | P1+ block / P2 backlog / P3 진행                                                                 |
| 10  | **Clerk 60초 JWT stale loop** (P1-2)                  | auth-flow.spec expired-session case 의무                                                         |
| 11  | **Celery worker=0 backtest 영구 pending** (P1-1 부분) | Composite 산식 Celery N/A 마킹 + close-out manual smoke 의무                                     |

---

## 10. Timeline (3 day, 25h)

```
Day 1 (10.5h):
 ├─ 09:00-10:30 S0 Preflight (codex G.0 이미 완료, sync overwrite)     [1.5h]
 ├─ 10:30-14:30 S1 BL-244 (RED 5건 + codex G.1 ~200k)                  [4.0h]
 ├─ 15:30-20:30 S2 UI 정직 (route inventory + 섹션 + G.2 ~250k)        [5.0h]

Day 2 (9.5h):
 ├─ 09:00-12:30 S3 Auth/Routing (Clerk JWT expired E2E)                [3.5h]
 ├─ 13:30-19:30 S4 Mobile + Clerk (viewport 4 + a11y + G.3 ~350k)      [6.0h]

Day 3 (6h):
 ├─ 09:00-11:00 S5 안전헤더 최소 gate (신규)                            [2.0h]
 ├─ 11:00-15:00 S6 Gate (T-8 산식 + Critical 11→0 + G.4 ~700k + T-9)   [4.0h]
```

Day 7 (2026-05-16) dogfood 인터뷰 = 별도 manual gate.

---

## 11. 검증 방법

### 자동

1. BE pytest 회귀 0 (Sprint 59 baseline 537+146+138 PASS 유지)
2. FE vitest 680 PASS 유지
3. 신규 BE test 5+1건 PASS
4. 신규 FE e2e 7 spec PASS
5. LESSON-019 commit-spy 8건 회귀 0

### codex 5 gate

- G.0 PASS (이미 완료 — 25 채택 inline)
- G.1/G.2/G.3 spot 모두 PASS
- G.4 PASS (P0/P1 잔존 = FAIL)

### 사용자 manual

- Critical 11→0 BL별 evidence 표 PASS
- Composite Health ≥8.0
- 4 페르소나 spot-check 5건
- Celery worker 1+ manual smoke (S6 종료)

### Composite Health 목표

| 항목        | Before | Target |
| ----------- | ------ | ------ |
| Composite   | 4.18   | ≥8.0   |
| Critical    | 11     | 0      |
| High        | 14     | ≤7     |
| Curious NPS | 2/10   | ≥6/10  |
| Mobile UX   | 2/10   | ≥6/10  |

---

## 12. 후속 (Sprint 61+)

- **(a) Composite ≥8.0 + 의지 O** → Sprint 61 Beta 본격 (BL-070~075 도메인+DNS + BL-261 Clerk custom domain)
- **(b) Composite 6.5~7.9** → Sprint 61 P1 Cleanup (BL-245/274/246 보안 + BL-247 schema + BL-250 ADR-003 + BL-264 WS + BL-301 모바일 가로 + Casual UX)
- **(c) Composite <6.5** → Sprint 61 추가 trust 회복

### LESSON 후보

- LESSON-040 7차 (superpowers 5종 영구)
- LESSON-067 6차 (codex 분산형 budget 정밀화)
- LESSON-019 +1 (router response shape 변경 spy 면제)
- LESSON-039 +1 (middleware-mock false-positive 검출 G.1 pattern)

---

## 13. Codex G.0 결정 표

> 365k tokens, P1 13 + P2 17 + P3 1 = 31 권고. 메인 결정 = 25 채택 / 2 부분 / 2 거부 / 2 이연. 상세는 [`master plan`](/Users/woosung/.claude/plans/proud-splashing-rossum.md) §결정 표.

**핵심 채택 11건 (P1):** P1-2 Clerk 60s JWT / P1-3 S4 선결 정정 / P1-4 T-1 RED 강화 / P1-5 route inventory / P1-6 섹션 assertion / P1-7 Composite 산식 / P1-8 Critical 11→0 검증 표 / P1-9 superpowers 실행형 / P1-10 S4 preflight / P1-12 error.tsx fallback / P1-13 S5 안전헤더 최소 gate.

**부분채택:** P1-1 Celery (산식 N/A + manual smoke).

**거부:** P1-11 BL-261 DNS manual (Sprint 61 (a) 이연).

**이연:** P2-q BL-250 / P2-r RTL/SSR (Sprint 61).
