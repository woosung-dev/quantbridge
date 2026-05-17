# QA Sentinel 재측정 — Sprint 61 fix-first 효과 검증

**일자**: 2026-05-17 (Sprint 61 머지 후, PR #288 main @`26b7486`)
**환경**: Isolated mode (FE :3100 / BE :8100, uvicorn local + docker quantbridge-worker)
**페르소나**: QA Sentinel (Standard ~50분 실측)
**Pre baseline**: 2026-05-17 QA Sentinel 7.45/10 (Critical 0 / High 4 / Med 2 / Low 1)

---

## Sprint 61 fix 효과 (직접 검증)

| BL     | T-  | Sprint 61 변경                                                     | 검증 결과                                                                                                                                                                                                                                                                                                                                                                                                                                           | Confidence |
| ------ | --- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| BL-310 | T-6 | /livez 분리 + `_get_celery_timeout_s()` env override (default 8.0) | `/livez 200 PASS` (1.4ms) / `/healthz 503 (celery_workers=0 + timeout 8.0s)` — **partial**. dev 환경에서 uvicorn local ↔ docker worker broker URL 불일치 가능성 + 8s 부족 시나리오 그대로                                                                                                                                                                                                                                                           | H          |
| BL-311 | T-5 | 5 보안 헤더 middleware + `server` strip + HSTS prod                | X-Frame-Options=DENY / X-Content-Type-Options=nosniff / Referrer-Policy / Permissions-Policy 4종 **PASS**. **`server: uvicorn` 여전 leak FAIL** — `SecurityHeadersMiddleware.dispatch` 에서 `del response.headers["server"]` 실행하지만 uvicorn transport layer 가 middleware 응답 직후 다시 부착. **신규 BL-347 후보 P2**                                                                                                                          | H          |
| BL-312 | T-4 | OpenAPI / Swagger UI / Redoc production env-gate                   | dev: `/openapi.json 200 + /docs 200 + /redoc 200` PASS. production env-override 시 404 (test `test_main_openapi_gating.py` 9 case PASS, source 검증)                                                                                                                                                                                                                                                                                                | H          |
| BL-319 | T-3 | ClerkProvider `signInUrl="/sign-in"` + `signUpUrl="/sign-up"`      | `/sign-in 200` + `/sign-up 200` 직접 access PASS. **그러나 protected route (`/backtests` / `/trading` / `/strategies` / `/optimizer`) 307 → `https://stunning-chipmunk-35.accounts.dev/sign-in?redirect_url=...` 여전** — **PARTIAL FAIL**. `proxy.ts` clerkMiddleware `auth.protect()` 는 ClerkProvider props 가 아닌 **`NEXT_PUBLIC_CLERK_SIGN_IN_URL` env 를 우선 사용** → `.env.local` 에 누락 (`pk_test_...` 만 설정). **신규 BL-348 후보 P1** | H          |
| BL-321 | T-3 | Clerk application name 변경                                        | 사용자 manual 영역 (dashboard 외부 수동 1분). pending                                                                                                                                                                                                                                                                                                                                                                                               | M          |
| BL-322 | T-8 | Hero copy 정합 ("Pine Script 코드를 붙여넣으면")                   | `landing-hero.tsx:47` 반영 PASS. HTML curl 확인 = "Pine Script 코드를 붙여넣으면" 노출                                                                                                                                                                                                                                                                                                                                                              | H          |
| BL-323 | T-8 | Optimizer 메뉴 추가                                                | `dashboard-nav-list.tsx:33` `{ href: "/optimizer", label: "최적화", disabled: false }` PASS                                                                                                                                                                                                                                                                                                                                                         | H          |
| BL-327 | T-7 | 5 KPI tooltip + ? button                                           | `metrics-cards.tsx:128-131` `aria-label` + `title` + `data-testid="kpi-info-${key}"` 5건 PASS. 신규 test `metrics-cards-kpi-info.test.tsx` 5 case 존재                                                                                                                                                                                                                                                                                              | H          |
| BL-328 | T-3 | ClerkProvider `localization={koKR}`                                | `app-providers.tsx:2,16` `import { koKR } from "@clerk/localizations"` + props 적용 PASS. 실 화면 한국어 form 검증 = Curious/Casual 페르소나 영역                                                                                                                                                                                                                                                                                                   | H          |
| BL-339 | T-2 | 터치 타겟 ≥44pt (UserButton + chips + Disclaimer)                  | `dashboard-header.tsx:40,61,66,67` `size-11` + `min-h-11 min-w-11` 적용 PASS. `mobile-nav.tsx:51` `size-11` PASS. `legal-notice-banner.tsx:11` `min-h-11 px-2 py-2.5` PASS                                                                                                                                                                                                                                                                          | H          |
| BL-340 | T-1 | Trading horizontal overflow `min-w-0` fix                          | `dashboard-shell.tsx:54,60` `flex min-w-0 flex-1 flex-col` + `main className="min-w-0 flex-1"` PASS. `trading-dash-hero.tsx:114` DashKpi `min-w-0 overflow-hidden` 보완 PASS                                                                                                                                                                                                                                                                        | H          |

**Summary**: PASS 8 / PARTIAL 2 (BL-310 healthz, BL-319 protected route) / FAIL 1 (BL-311 server strip) / pending manual 1 (BL-321)

---

## 회귀 (Sprint 60 P0 fix 11종)

| BL         | 검증 영역                    | 결과                                                                   |
| ---------- | ---------------------------- | ---------------------------------------------------------------------- |
| BL-244     | Optimizer slowapi × Pydantic | `/api/v1/optimizer/runs/*` endpoint resolve PASS (openapi.json 5 path) |
| BL-265     | UI 내부 sprint/BL/ADR 노출   | landing / backtests curl 0 match PASS                                  |
| BL-270     | 가짜 marketing copy          | "Pine Script 코드를 붙여넣으면" 정직화 카피 PASS                       |
| BL-271     | 가짜 testimonial             | landing curl 0 match PASS                                              |
| BL-273     | Disclaimer marketing         | `legal-notice-banner.tsx` 존재 + 링크 min-h-11 PASS                    |
| BL-280     | vectorbt UI 노출             | curl 0 match PASS                                                      |
| BL-285     | 모바일 햄버거 dead           | `dashboard-header.tsx:22` `setMobileNavOpen` 토글 PASS                 |
| BL-300     | UserButton 0x0               | `dashboard-header.tsx:66-67` `size-11` wrapper PASS                    |
| BL-303     | 내부 sprint/BL 노출          | 0 match PASS                                                           |
| BL-305     | 모바일 UserButton wrapper    | `min-h-11 min-w-11` PASS                                               |
| BL-308/309 | trading deepen audit         | docs only, code 0 touch — N/A                                          |

**회귀 11/11 PASS** ✅

---

## 신규 BL (BL-347~)

### BL-347 [Medium] [H] BE `server: uvicorn` header leak (T-5 partial regression)

**Severity**: Medium (info-disclosure / OWASP A05)
**Confidence**: High (실측 curl)
**영역**: backend/src/common/security_headers.py

**증상**: `curl -I http://localhost:8100/livez` 응답 헤더에 `server: uvicorn` 여전 노출. Sprint 61 T-5 의 strip 의도와 mismatch.

**원인**: `SecurityHeadersMiddleware.dispatch()` 의 `del response.headers["server"]` 는 Starlette middleware layer 응답에만 적용. uvicorn 의 `--no-server-header` flag 또는 ASGI lifespan-level strip 가 필요. middleware 만으로는 transport 단 부착을 차단 못함.

**재현**:

```bash
curl -sI http://localhost:8100/livez | grep -i ^server
# server: uvicorn  ← leak
```

**기대**: server 헤더 부재 또는 generic 값 (e.g. `server: api`).

**fix 옵션**:

- (a) uvicorn 부팅 옵션 `--no-server-header` (uvicorn 0.30+ 지원)
- (b) `gunicorn -k uvicorn.workers.UvicornWorker --server_header False` (production)
- (c) reverse proxy (nginx/Caddy) `proxy_hide_header server` (가장 확실)

**Sprint 61 영향**: test `test_main_security_headers.py` 의 server strip case 가 TestClient mock 환경에서만 PASS, 실 uvicorn 부팅 환경에서 실패 — test fixture 와 prod 환경 gap.

---

### BL-348 [High] [H] Clerk protected route → `accounts.dev` redirect (T-3 partial)

**Severity**: High (auth flow stuck — 기능 정상 작동하나 dev surface leak)
**Confidence**: High (실측 4 route curl)
**영역**: frontend/.env.local + frontend/src/proxy.ts

**증상**: 익명 user 가 `/backtests` / `/trading` / `/strategies` / `/optimizer` 접근 시:

```
HTTP 307
location: https://stunning-chipmunk-35.accounts.dev/sign-in?redirect_url=http://localhost:3100/backtests
```

Sprint 61 T-3 의도 = 자체 도메인 `/sign-in` redirect. 실제 = Clerk dev instance `accounts.dev` 로 fallback.

**원인 분석**: Sprint 61 BL-319 fix 는 `app-providers.tsx` 의 ClerkProvider props 만 변경:

```tsx
<ClerkProvider signInUrl="/sign-in" signUpUrl="/sign-up" />
```

그러나 `proxy.ts` 의 `clerkMiddleware` `auth.protect()` 는 server-side 에서 실행 → **ClerkProvider props 무시**. Clerk SDK 는 `NEXT_PUBLIC_CLERK_SIGN_IN_URL` env 를 우선 참조하는데 `.env.local` 에 누락:

```
$ grep CLERK frontend/.env.local
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
# NEXT_PUBLIC_CLERK_SIGN_IN_URL 부재
# NEXT_PUBLIC_CLERK_SIGN_UP_URL 부재
```

**재현**:

```bash
curl -sI http://localhost:3100/backtests | grep -i ^location
# location: https://stunning-chipmunk-35.accounts.dev/sign-in?...
```

**기대**: `location: http://localhost:3100/sign-in?redirect_url=...`

**fix**: `frontend/.env.local` 에 2 줄 추가:

```
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
```

**검증**:

- `/sign-in` 직접 access = 200 PASS (route 존재)
- `app/(auth)/sign-in/[[...sign-in]]/page.tsx` 존재 확인
- 즉 route 구현은 완료, env 누락만 issue

**Sprint 61 영향**: BL-319 fix 본질 partial. T-3 plan 에서 env override 누락. Day 7 Beta gate 영향 = dev surface "accounts.dev" 노출 = 신규 user trust 저하.

---

### BL-349 [Medium] [H] BE healthz timeout 8.0s 부족 (T-6 partial)

**Severity**: Medium (readiness probe false negative)
**Confidence**: High (실측)
**영역**: backend/src/health/router.py `_get_celery_timeout_s()`

**증상**: `/healthz` 8s timeout 만료 → 503:

```json
{
  "db": "ok",
  "redis": "ok",
  "celery_workers": 0,
  "errors": { "celery": "timeout after 8.0s" }
}
```

**원인**: dev 환경에서 uvicorn local (port 8100) 가 docker `quantbridge-worker` (별도 network) 와 broker round-trip 시도. Redis URL 환경 차이 + worker timeout cold-start > 8s 가능. 즉 fix 의 mechanism 은 정상 (env override 수용), 실용적 default 가 부족.

**fix 옵션**:

- (a) `HEALTHZ_CELERY_TIMEOUT_S=15` env 설정 권장 + .env.example 명시
- (b) docker-compose dev override 에 자동 주입
- (c) cold-start 후 첫 health check skip (warmup grace period)

**Sprint 61 영향**: T-6 의 env override mechanism 은 정상 작동 (test 4 PASS). 단 default 8.0 이 dev 환경에서 부족 → BL 등재만, production 검증 별도.

---

## Summary

- **점수: 7.8 / 10** (가중치: 보안 0.3 × 8.0 + 회귀 0.3 × 10 + 기능 0.2 × 7.0 + 일관성 0.2 × 6.5 = 2.4 + 3.0 + 1.4 + 1.3 = **8.1** → conservative 7.8)
- **Pre 7.45 → Post 7.8. △ +0.35**
- Sprint 61 fix 효과: **PASS 8 / PARTIAL 3 (BL-310/311/319) / pending manual 1 (BL-321)**
- 회귀 (Sprint 60 P0): **11/11 PASS** ✅
- Critical 0 / High 1 (BL-348) / Medium 2 (BL-347, BL-349) — Pre 7건 → Post 신규 3건
- Beta 진입 차단: **BL-348** (protected route accounts.dev redirect — 신규 user trust 직격). BL-347/349 는 production 검증 후 결정 가능

### Sprint 62 권고

| 우선순위 | 항목                                                         | 예상 |
| -------- | ------------------------------------------------------------ | ---- |
| P0       | BL-348 `.env.local` 2줄 추가 + 재검증                        | 5분  |
| P1       | BL-347 uvicorn `--no-server-header` 또는 reverse proxy       | 30분 |
| P2       | BL-349 `HEALTHZ_CELERY_TIMEOUT_S=15` env + .env.example 갱신 | 15분 |

총 ~50분 = Type C hotfix 1 PR. Day 7 Beta gate 영향 직접.
