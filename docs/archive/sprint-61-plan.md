# 사용자 신뢰 회복 — Sprint 61 fix-first plan (P0 3 + P1 5)

**일자**: 2026-05-17 (Day 8 of dogfood, NPS+1)
**Type**: B (risk-critical fix-first)
**근거**: `docs/qa/2026-05-17/integrated-report.html` 4-페르소나 Multi-Agent QA. Composite 6.08/10, Critical 2, High 11. 4-AND Beta gate (a)(b)(c) **3/4 FAIL** → Beta 본격 진입 차단.

---

## 1. 목표 (1줄)

**Composite 6.08 → 7.5+ 회복. Mobile P0 + Clerk production + QA 보안 핵심 묶음 8 BL fix → Sprint 62 Beta 4-AND gate 재측정 진입 자격.**

---

## 2. 범위

### In Scope (P0 3 + P1 5 = 8 BL)

**P0 (Mobile 차단)**:

- **T-1 BL-340** Trading 페이지 horizontal overflow +227px fix (375x667)
- **T-2 BL-339** 터치 타겟 ≥44pt 보장 (UserButton + 필터 chips + disclaimer 링크 + skip link)

**P0 (Clerk dev surface fix ★★★ 3 페르소나 공통 — 로컬 dev key 그대로 OK)**:

- **T-3 BL-319 + BL-321 + BL-328** Clerk Hosted Pages → Embedded `<SignIn/>` `<SignUp/>` 전환 + application name "QuantBridge" + `@clerk/localizations.koKR`. **dev key 그대로 사용**. BL-320 ("Development mode" 배지) = dev instance 정상 표시 → Sprint 62 Beta production deploy 시점 자동 해소 (별도 BL-261 Clerk production domain 영역으로 이연).

**P1 (QA 보안)**:

- **T-4 BL-312** OpenAPI `/docs` `/redoc` `/openapi.json` production env-gate
- **T-5 BL-311** BE 보안 헤더 middleware (X-Frame / HSTS / nosniff / Referrer-Policy / server strip)
- **T-6 BL-310** healthz `/livez` (broker-skip) 분리 + `HEALTHZ_CELERY_TIMEOUT_S` env (default 8.0)

**P1 (Casual UX 핵심)**:

- **T-7 BL-327** KPI 라벨 tooltip + 초보 설명 (Sharpe / Drawdown / Profit Factor / 승률)
- **T-8 BL-322 + BL-323** Hero copy 정합 + 사이드바 Optimizer 메뉴 노출

### Out of Scope (Sprint 62+ 이연)

- **BL-320 "Development mode" Clerk 배지** = dev instance 정상 표시. Sprint 62 Beta production deploy 시점 = production Clerk instance (`pk_live_…` + `sk_live_…`) + custom domain `auth.quantbridge.io` DNS CNAME 설정으로 자동 해소. 기존 deferred BL-261 (Clerk production domain) 영역과 묶음.
- BL-313/314/315/316 응답 grammar / rate-limit / body size / Pydantic 422 = QA 영역 polish, Sprint 62 보안 1-day batch
- BL-329/330 sidebar disabled UX / 거짓 "대시보드" 라벨 = UX polish
- BL-332 axe color-contrast 92 nodes = Tailwind theme tweak Sprint 62
- BL-341/342/343 PWA / inputmode / sheet a11y = Mobile 2차 (Sprint 62)
- BL-317/318/324/325/326/331/333/334/335/336/337/338/344/345/346 = P2/P3 batch
- BL-308/309 trading architectural deepening 2차 = 별도 사용자 의지 게이트

**사유**:

- 23h scope (≈ 3 day single worker, Sprint 60 단축 패턴 적용 시 8-12h 실측) 가 본 sprint 의 적정 상한. 추가 시 surface trust 회복 효과 희석.
- T-1 ~ T-8 = 4-AND gate 항목별 직접 영향: T-1/2 → (b) Critical / T-4/5/6 → (a) 보안 점수 / T-3/7/8 → (a) UX 점수.

---

## 3. 작업 분해

### T-1 BL-340 Trading horizontal overflow fix · 4h

- **대상**: `frontend/src/app/(dashboard)/trading/page.tsx` 또는 layout component (`max-w-` / grid 정의 위치).
- **변경**: container `max-w-[1200px] px-4 md:px-6` + `<section>` 자식 grid `grid-cols-1 sm:grid-cols-2 md:grid-cols-4`. 모바일 breakpoint 검증.
- **의존성**: 없음
- **테스트**: Playwright e2e + viewport 375/393/412 모두 `scrollWidth <= clientWidth` assertion
- **검증**: `npx playwright test trading.spec --grep="no horizontal overflow"` PASS

### T-2 BL-339 터치 타겟 ≥44pt · 4h

- **대상**:
  - `frontend/src/components/layout/UserButton.tsx` (또는 Clerk wrapper) — size-9 (36) → size-11 (44)
  - `frontend/src/components/strategies/StrategyFilters.tsx` — chips `h-7` (30) → `h-11` (44)
  - `frontend/src/components/layout/BetaDisclaimer.tsx` — 링크 padding +12px (clickable area 44pt)
  - skip-to-content link — visually-hidden 의도 유지하되 BL-339 측정에서 제외 annotation
- **테스트**: a11y unit 또는 e2e 안 `getBoundingClientRect()` minimum size assertion
- **검증**: strategies 페이지에서 위반 0건 (현재 19+)

### T-3 BL-319+321+328 Clerk dev surface fix (로컬 dev 환경, dev key 그대로) · 3h

- **대상**:
  - **BL-319 fix** = Hosted Pages → Embedded 전환:
    - `frontend/src/app/sign-in/[[...sign-in]]/page.tsx`: `<SignIn />` 컴포넌트 임베드 (현재는 Clerk Hosted Pages redirect 추정)
    - `frontend/src/app/sign-up/[[...sign-up]]/page.tsx`: `<SignUp />` 컴포넌트 임베드
    - 결과: 자체 도메인 `localhost:3100/sign-in` 안 호스팅 → `accounts.dev` redirect 제거
  - **BL-321 fix** = Clerk dashboard application name 변경 1회 (사용자 manual 1분, dev instance 안에서):
    - Clerk dashboard → Application → Settings → Application name: `quant-bridge` → **QuantBridge**
    - 결과: 페이지 타이틀 "Sign in to QuantBridge"
  - **BL-328 fix** = i18n koKR:
    - `pnpm add @clerk/localizations`
    - `frontend/src/app/layout.tsx`: `<ClerkProvider localization={koKR}>`
    - 결과: "Sign in / Email / Password / Continue / Welcome back" → "로그인 / 이메일 / 비밀번호 / 계속 / 다시 만나서 반가워요"
- **의존성**: 사용자 manual = Clerk dashboard application name 변경 1건 (1분, dev instance, key 갱신 불요)
- **테스트**: Curious + Casual 페르소나 재실행 sub-agent 안 sign-in/up flow PASS (영어 0건 + accounts.dev redirect 0건). **"Development mode" 배지 = dev env 정상 표시, fix 대상 X**.
- **검증**: `curl -L http://localhost:3100/sign-in` 응답 URL → `localhost:3100/sign-in` 유지 (`accounts.dev` 부재). HTML 응답 안 koKR 라벨 ("로그인" / "이메일") 검증.

> **BL-320 "Development mode" 배지** = Clerk dev instance 의 의도된 SaaS feature. dev key 사용 시 항상 표시 = production deploy + production key 전환 시 자동 해소. **Sprint 62 Beta production deploy 시점에 별도 BL-261 (Clerk custom domain + production instance) 영역에서 묶음 처리**. 로컬 dev 환경 fix 무의미.

### T-4 BL-312 OpenAPI production env-gate · 1h

- **대상**: `backend/src/main.py` FastAPI initialization
- **변경**:
  ```python
  ENVIRONMENT = settings.environment  # "development" | "staging" | "production"
  app = FastAPI(
      title="QuantBridge",
      docs_url="/docs" if ENVIRONMENT != "production" else None,
      redoc_url="/redoc" if ENVIRONMENT != "production" else None,
      openapi_url="/openapi.json" if ENVIRONMENT != "production" else None,
  )
  ```
- **테스트**: `tests/main/test_openapi_gating.py` — production env 시 `/openapi.json` → 404
- **검증**: dev = 200 / production = 404 (env override 로 unit test 안 simulate)

### T-5 BL-311 BE 보안 헤더 middleware · 3h

- **대상**: `backend/src/main.py` 미들웨어 신규 + (옵션) `backend/src/middleware/security_headers.py`
- **변경**:
  ```python
  @app.middleware("http")
  async def add_security_headers(request: Request, call_next):
      response = await call_next(request)
      response.headers["X-Content-Type-Options"] = "nosniff"
      response.headers["X-Frame-Options"] = "DENY"
      response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"  # HTTPS prod 만
      response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
      response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
      if "server" in response.headers:
          del response.headers["server"]  # uvicorn version leak strip
      return response
  ```
- **테스트**: `tests/main/test_security_headers.py` — 모든 응답에 5 헤더 + server 헤더 부재 assertion
- **검증**: `curl -i http://localhost:8100/api/v1/strategies` → 5 헤더 모두 존재 + `server: uvicorn` 부재

### T-6 BL-310 healthz `/livez` 분리 · 2h

- **대상**: `backend/src/health/router.py`
- **변경**:
  - `_CELERY_TIMEOUT_S` → env-driven `HEALTHZ_CELERY_TIMEOUT_S` (default `8.0`)
  - `/livez` 신규 endpoint = liveness (broker check 없이 process up 만 확인) → K8s liveness probe 용
  - `/healthz` 유지 = readiness (db + redis + celery 3-dep) → K8s readiness probe 용
- **테스트**: `tests/health/test_livez.py` + `test_healthz_timeout_override.py`
- **검증**: `curl http://localhost:8100/livez` 200 (db down 상관 없음) / `/healthz` celery 정상 시 200

### T-7 BL-327 KPI tooltip · 4h

- **대상**: `frontend/src/components/backtests/detail/KpiCard.tsx` (또는 비슷한 위치)
- **변경**:
  - Radix Tooltip 활용 (이미 shadcn 안 있을 가능성 높음, 없으면 npm install)
  - 5 KPI 라벨 각각 `?` 아이콘 + 1줄 설명:
    - 총 수익률: "백테스트 기간 동안의 누적 손익 비율"
    - 샤프 비율: "변동성 대비 초과수익. 1 이상 양호"
    - 최대 낙폭 (Max Drawdown): "고점 대비 최대 손실 폭"
    - Profit Factor: "총 이익 ÷ 총 손실. 1.5 이상 양호"
    - 승률 · 거래수: "이익 거래 비율 + 전체 거래 횟수"
  - `aria-describedby` 로 screen reader 호환
- **테스트**: e2e 안 tooltip 가시성 + a11y axe 위반 0건
- **검증**: Casual 페르소나 재실행 시 용어 해독률 +10%p 이상

### T-8 BL-322 + BL-323 Hero copy 정합 + Optimizer 메뉴 · 3h

- **대상**:
  - `frontend/src/app/page.tsx` (landing hero) — 카피 "TradingView 전략을 업로드하면" → "Pine Script 코드를 붙여넣으면" (파일/URL 업로드 "곧 지원" 동안 사실 기반)
  - `frontend/src/components/layout/Sidebar.tsx` — `/optimizer` 메뉴 추가 (현재 sidebar 6 항목 + Optimizer 7번째). 이미 `/optimizer` 페이지 존재 (Sprint 54-56 구축, BL-235 N-dim viz 만 BL).
- **테스트**: hero copy 변경 후 Curious 회귀 재실행 시 "Hero copy GAP" finding 미발생
- **검증**: 사이드바 클릭 `/optimizer` 진입 + 카피 일치성 manual review

---

## 4. 검증 기준

### 신규 테스트 (T-1 ~ T-8 각각 1건 이상)

- 합 8-10 신규 test (BE ≈ 4 + FE ≈ 5)
- 모두 PASS 의무 + CI 통과

### 회귀

- BE 전체 (148 ~ 160 추정) PASS
- FE 전체 (707 ~ 720 추정) PASS
- ruff + mypy + tsc + lint clean

### dogfooding (사용자 manual + sub-agent 후속)

- 본 PR 머지 후 Multi-Agent QA 재실행 (4 페르소나 Standard depth, ~3h)
- Composite 6.08 → **7.5+** 의무 (Beta 4-AND gate (a) 진입 조건)
- Critical = 0 의무 (gate (b))
- High ≤ 3 의무 (gate (c))

### 메트릭

- Mobile 점수 3.8 → **6.5+** 회복 (Mobile 페르소나 재실행)
- Casual 용어 해독률 40% → **55%+** (Casual 페르소나 재실행, KPI tooltip 효과)
- Curious 도입 결정 Maybe → **Yes (조건부)** (Clerk production 효과)

---

## 5. 위험 + 완화

| 위험                                                               | 완화                                                                                                                                                  |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clerk Embedded 전환 시 routing 충돌 가능성                         | `[[...sign-in]]` catch-all 라우트 유지 + `<SignIn />` 컴포넌트 prop (`afterSignInUrl`, `signUpUrl`) 명시. dev key 그대로 사용 → external dependency 0 |
| Mobile P0 fix (T-1/2) 가 desktop 회귀 유발                         | Playwright e2e 데스크톱 1440x900 + 모바일 375x667 양쪽 assertion 의무                                                                                 |
| BE 보안 헤더 (T-5) middleware 가 기존 CORS middleware 와 순서 충돌 | FastAPI middleware 등록 순서 명시 + integration test (`tests/main/test_cors.py` 회귀 확인)                                                            |
| `@clerk/localizations` 의 `koKR` 일부 라벨 미지원                  | Clerk dashboard 의 custom labels 로 fallback. Sprint 62 polish 이연 OK                                                                                |
| 신규 헤더 (HSTS) 가 localhost dev 환경에서 영향                    | Production-only 분기 (`if settings.environment == "production"`)                                                                                      |

---

## 6. 자의 결정 라벨

- **Sprint Type**: B (risk-critical fix-first) — Sprint 60 와 동일 패턴
- **Worker pattern**: 단일 worker (Sprint 60 대비 8 BL ≈ 9-12h 실측 = 1 day, multi-worker 분리 ROI 없음)
- **G.0 codex consult**: 권고 ★★★★ (Sprint 60 패턴 = G.0 master plan validation 직후 본 sprint 진입). T-3 (Clerk env wiring) + T-5 (보안 헤더 middleware 순서) 가 G.0 surface area
- **G.4 final gate**: 의무. 본 sprint 종료 = Multi-Agent QA 재실행 PASS 의무
- **Sprint 62 분기**: Multi-Agent QA 재실행 결과 = (a) gate PASS / Critical 0 / High ≤ 3 시 Beta 본격 진입 의지 결정. FAIL 시 fix-first Sprint 62

---

## 7. 예상 일정

| Phase                                             | 시간                                             | 산출                                                                |
| ------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------- |
| Sprint kickoff + codex G.0 master plan validation | 1h                                               | LESSON-040 prereq spike + plan revision                             |
| T-1/2 Mobile P0 (병렬 의존성 0)                   | 4h                                               | BL-340 + BL-339 fix                                                 |
| T-3 Clerk dev surface fix (로컬, dev key 그대로)  | 사용자 manual 1분 (dashboard app name) + 코드 3h | BL-319/321/328 묶음 fix (BL-320 = Sprint 62 production deploy 이연) |
| T-4/5/6 BE 보안 (병렬 의존성 0)                   | 6h                                               | BL-310/311/312 fix                                                  |
| T-7/8 UX 핵심 (병렬 의존성 0)                     | 7h                                               | BL-322/323/327 fix                                                  |
| codex G.4 + Multi-Agent QA 재실행 + 보고서 작성   | 3h                                               | Composite 측정 + Sprint 62 분기 결정                                |
| **합**                                            | **≈ 24h**                                        | **3 day single worker, Sprint 60 단축 패턴 적용 시 실측 ≈ 8-12h**   |

목표 완료일: **2026-05-19 ~ 2026-05-21** (단일 worker single day 1.5-3 day)

---

## 8. 사용자 manual 의존 작업 체크리스트

### Sprint 61 진입 의무 (로컬 dev 환경, 외부 의존 0)

- [ ] (T-3 manual 1분) Clerk dashboard → Application → Settings → Application name: `quant-bridge` → **QuantBridge** 변경. **dev instance 안에서, dev key 그대로**. 별도 발급 불요.
- [ ] (Sprint 종료) Multi-Agent QA 재실행 (`docs/qa/2026-05-19~21/` 생성) — 본 plan 의 검증 기준 합격 판정 의무
- [ ] (Sprint 종료) Beta 4-AND gate (d) 본인 의지 결정 — Day 7 NPS + 본 QA 재실행 결과 cross-reference

### Sprint 62 Beta production deploy 시점 의무 (외부 의존 = DNS + Clerk production)

- [ ] Clerk dashboard production instance 발급 (현재 dev = `stunning-chipmunk-35.accounts.dev`)
- [ ] DNS CNAME 설정 — `auth.quantbridge.io` (또는 본인 도메인) → Clerk verification CNAME
- [ ] `frontend/.env.production` `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` production key (`pk_live_...`)
- [ ] `backend/.env.production` `CLERK_SECRET_KEY` production key (`sk_live_...`)
- [ ] 결과: BL-320 "Development mode" 배지 자동 해소 + 기존 BL-261 deferred 영역 동시 처리

---

## 9. 핵심 파일 경로

| 파일                                                                       | 역할                                                                      |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `docs/qa/2026-05-17/integrated-report.html`                                | 베이스라인 (Composite 6.08, 37 BL)                                        |
| `frontend/src/app/(dashboard)/trading/page.tsx`                            | T-1 대상                                                                  |
| `frontend/src/components/layout/UserButton.tsx` 또는 wrapper               | T-2 대상                                                                  |
| `frontend/src/app/layout.tsx`                                              | T-3 ClerkProvider                                                         |
| `backend/src/main.py`                                                      | T-4 + T-5                                                                 |
| `backend/src/health/router.py`                                             | T-6                                                                       |
| `frontend/src/components/backtests/detail/KpiCard.tsx` (추정 경로)         | T-7                                                                       |
| `frontend/src/app/page.tsx` + `frontend/src/components/layout/Sidebar.tsx` | T-8                                                                       |
| `.ai/common/global.md` §7.1                                                | Sprint kickoff Type B 첫 step = baseline 재측정 (본 plan 자체가 baseline) |

---

🟢 **Sprint 61 plan 작성 완료** — 8 BL fix-first, ≈ 23h scope, Composite 6.08 → 7.5+ 목표
