# Sprint 25 — Hybrid (Frontend E2E Playwright + Backend test 강화 + codex)

**날짜**: 2026-05-03 (Sprint 22+23+24a/24b main 머지 완료 직후, PR #95+#96)
**브랜치**: `stage/h2-sprint25` (main `aed201f` cascade)
**범위**: Track 1 Frontend E2E (Clerk + Playwright) + Track 2 Backend test 강화 (BL-112/113/110a/114/115) + Track 3 codex Generator-Evaluator
**상태**: ✅ 완료 (2026-05-03) — implementation + codex G.0 (iter 1+2) + G.2 challenge (P1 4 즉시 fix) + 전체 회귀 검증.

**결과 요약**: BE 1401 passed / 39 skipped / 0 failed. FE 251 passed / tsc 0 / lint 0. ruff 0 / mypy 0 (147 src). codex G.0 1.9M tokens + G.2 992k tokens 누적 ~3M, 23 P1 + 18 P2 + 6 P3 = 47 finding 모두 plan v3 또는 implementation 반영 (P1 critical 0 잔존).

> **사용자 명시 요구 반영**: 본 dev-log 는 implementation 진입 전 사전 작성 + 종료 시 실 데이터 채움.

---

## §1. 배경

dogfood Day 1-2 의 broken bug 패턴 (Sprint 6 webhook commit / Sprint 13 OrderService outer commit / Sprint 15 ExchangeAccountService 3회 재발 → LESSON-019 영구 규칙 승격) 은 **사람 dogfood 의존 발견** 이라 cycle time 길었다. Sprint 24b 의 backend service-direct 자동 가드 (test_auto_dogfood.py 6 시나리오) 도입은 진전이지만 두 결함:

1. **Frontend critical path 자동화 0%** — Strategy create / TestOrderDialog HMAC 검증 / KillSwitch 등 사용자 본인이 매일 누르는 UI flow 가 **수동 브라우저 검증 의존**
2. **scenario2/3 stub** — BL-112 (`run_backtest_v2` 미호출, import smoke 만) + BL-113 (`Order` ORM 직접 INSERT, `OrderService.execute` 우회)

본 sprint 가 두 결함 동시 해소 + Track 3 (codex Generator-Evaluator) 가 plan + 구현 양쪽 검증.

**expected outcome**:
- 사용자 dogfood Day 8+ 부터 critical UI flow 회귀 검증 자동화 (`make fe-e2e-authed` local 명령)
- BE auto_dogfood scenario2/3 가 진짜 backtest engine + OrderService.execute 호출
- prefork lease integration test in-process (BL-110a) — heartbeat extend False / lost_event / lease contention 회귀 가드
- self-assessment 9/10 유지 (Sprint 18→24 cascade)

---

## §2. Implementation 진행 상태

### Track 1 — Frontend E2E (Clerk + Playwright)

#### Phase 1.1 — dependency + ignore + env ✅

- [x] `frontend/package.json` devDependencies: `@clerk/testing` 추가
- [x] `frontend/.gitignore`: `e2e/.auth/` 추가 + `git check-ignore` 검증
- [x] `frontend/.env.example`: `CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY` + `E2E_CLERK_USER_EMAIL/PASSWORD` 4 신규 키
- [x] `git check-ignore frontend/e2e/.auth/storageState.json` 가 ignored 확인

#### Phase 1.2 — 사용자 baseline storageState ✅

- [x] 사용자가 `cd frontend && pnpm exec playwright codegen --save-storage=e2e/.auth/storageState.baseline.json http://localhost:3100/sign-in` 실행 (1회 5분)

#### Phase 1.3 — global.setup.ts + projects 분리 + fixtures ✅

- [x] `frontend/e2e/global.setup.ts` 신규 — `clerkSetup() + clerk.signIn() + protected route validation` (pathname + UI selector 둘 다)
- [x] `frontend/playwright.config.ts` projects 3개 분리 (setup / chromium / chromium-authed)
- [x] `frontend/e2e/fixtures/api-mock.ts` 신규 — `API_ROUTES` (모든 prefix `/api/v1/`) + MOCK_DEMO_ACCOUNT/MOCK_KS_EVENT_*
- [x] `frontend/e2e/fixtures/auth.ts` 신규 — storageState 만료 감지 helper
- [x] `page.on('request')` leak guard (real backend call 0 검증)

#### Phase 1.4 — Make + pnpm scripts ✅

- [x] `frontend/package.json` scripts: `e2e` / `e2e:authed --workers=1` (production guard) / `e2e:all`
- [x] `Makefile`: `fe-e2e` / `fe-e2e-authed`

#### Phase 2.1 — trading-ui.spec.ts 활성화 + mock 전수 ✅

- [x] `test.skip` 5건 제거 (line 49/77/103/123/141 → `test`)
- [x] MOCK 변수 `api-mock.ts` 에서 import (DRY)
- [x] 모든 mock route prefix `/api/v1/` (codex iter 2 P2 #4 critical)
- [x] `pnpm e2e:authed` → 5/5 PASS + leak 0

#### Phase 2.2 — dogfood-flow.spec.ts 신규 ✅

- [x] 3 시나리오 `serial mode`:
  1. Strategy create → webhook_secret plaintext 1회 표시 (Sprint 13 atomic)
  2. Backtest 시작일/종료일 빈 채 submit → 422 inline error (Sprint 13 Phase C)
  3. TestOrderDialog HMAC 발송 → 201 expected mock + KS bypass guard (Sprint 13 Phase B)
- [x] `pnpm e2e:authed` → 8/8 PASS

#### Phase 2.3 — dogfood guide 업데이트 ✅

- [x] `docs/07_infra/dogfood-day2-7-guide.md` §3 — `make fe-e2e-authed` + 만료 시 재생성 절차

### Track 2 — Backend test 강화

#### Phase 3 — BL-112 fixture + scenario2 RED → GREEN ✅

- [x] `backend/tests/fixtures/backtest_ohlcv.py` 신규 — `make_trending_ohlcv` (linspace 4 segment) + `EMA_CROSS_PINE_SOURCE`
- [x] `backend/tests/fixtures/test_backtest_ohlcv_precondition.py` 신규 — fixture 자체 `num_trades >= 3` 검증 (RED → GREEN)
- [x] `test_auto_dogfood.py:scenario2` 강한 assert: `status=='ok' + result is not None + len(equity_curve) > 0 + num_trades >= 1`

#### Phase 4 — BL-113 scenario3 OrderService ✅

- [x] `FakeOrderDispatcher` 신규 (`OrderDispatcher` Protocol 구현)
- [x] `test_auto_dogfood.py:scenario3` 가 `OrderService(session=, repo=, dispatcher=fake, kill_switch=, exchange_service=)` 명시 construction
- [x] `await service.execute(req, idempotency_key=f"{request.node.name}:{uuid4().hex}")` 호출
- [x] DB refresh 후 `order.dispatch_snapshot == {"exchange": ..., "mode": ..., "has_leverage": ...}` 검증

#### Phase 5 — BL-110a in-process lease integration test ✅

- [x] `backend/tests/tasks/test_ws_lease_integration.py` 신규 (`@pytest.mark.integration`)
- [x] 6 시나리오: lease 획득 / duplicate None / account 격리 / extend True 정상 / **extend False → lost_event.set** / `__aexit__` Redis key 부재
- [x] `monkeypatch RedisLock.extend → False` (codex iter 2 P1 #8 — exception path 가 아닌 falsy return path)
- [x] heartbeat interval 압축 (`ttl_ms=1000` → interval=333ms, real time 1-2초 검증)

#### Phase 6 — BL-114 pytest-json-report ✅

- [x] `backend/pyproject.toml` dev dep: `pytest-json-report>=1.5,<2`
- [x] `_run_pytest()` 진입 시 `importlib.util.find_spec("pytest_jsonreport")` plugin detect (codex iter 2 P1 #9)
- [x] `_build_summary(rc, stdout, stderr, json_report=None)` backward compat (scenario6 L327 호출 보존)
- [x] plugin 부재 시 graceful fallback (legacy stdout 파싱)

#### Phase 7 — BL-115 HTML escape full ✅

- [x] `run_auto_dogfood.py` 의 모든 dynamic text `html.escape` 적용 (stdout_tail / stderr_tail / table cells / header)
- [x] `backend/tests/scripts/test_run_auto_dogfood_html_escape.py` 신규 — `<script>alert(1)</script>` 주입 → escaped 검증

### Track 3 — codex Generator-Evaluator

#### G.0 (master plan 검증) — ✅ 완료

- **iter 1** (medium, 617k tokens, session `019ded09-8442-7c63-8193-2e671f9f8601`): P1 14 + P2 10 + P3 4 → plan v2 surgery 28건 모두 반영
- **iter 2** (medium, 1.28M tokens, resume from same session): plan v2 **NOT READY 판정**. P1 9 + P2 8 + P3 4 발견 (Clerk auth wrong / BL-112 코드 실측 refuted / OrderService param 이름 wrong / heartbeat exception path wrong / pytest CLI behavior wrong / mock URL prefix wrong) → plan v3 surgery 21건 모두 반영
- **iter 3 보류**: 누적 ~1.9M tokens, max 2 iter 한도 도달. iter 2 가 코드 실측 깊이 + plan v3 의 P1 모두 fix.

#### G.2 (구현 후 challenge) ✅ 완료

**session**: `019ded42-b486-7db2-9283-10c692b10dbe` (high reasoning, 992k tokens, iter 1)
**verdict**: P1 4 + P2 12 + P3 2 = 18 finding. P1 4건 모두 즉시 fix. P2/P3 신규 BL 등록 (Sprint 26+ 이관).

**P1 fix 즉시**:
1. `global.setup.ts` env 검증 순서 — `clerkSetup()` 후 검증 (`.env.local` dotenv 로딩 후) → 사용자 .env.local 사용 깨짐 회귀 방어
2. `_ws_lease.py:_heartbeat_loop` extend exception path — `extend()` 가 raise 시도 lost_event.set() 보장 (이전 falsy return 만 set → split-brain 위험). 신규 회귀 test `test_heartbeat_extend_exception_sets_lost_event` 추가
3. dogfood-flow `Backtest 422 inline` 시나리오 — submit + `data-testid=backtest-form-server-error` 또는 `role=alert` assert 추가 (페이지 heading 만 PASS-by-default 차단)
4. dogfood-flow `TestOrderDialog KS bypass` 시나리오 — KS active mock + dialog open + `button[type=submit]` disabled assert (banner 만 보고 PASS-by-default 차단)

**P2 BL 등록 (Sprint 26+ 이관, BL-117~127)**:
1. Clerk emailAddress 방식 권장 (MFA/verification 우회 회피) — BL-117
2. baseURL 통합 (config + setup) — BL-118
3. API_ROUTES URL predicate (orders-v2 false-match 차단) — BL-119
4. leak guard fail-on-leak (현재 observability only) — BL-120
5. production guard host allowlist (NODE_ENV 외) — BL-121
6. pytest-json-report uv-aware detect — BL-122
7. mkstemp fd leak — BL-123
8. subprocess timeout — BL-124
9. report 파일명 timestamp + symlink — BL-125
10. FakeOrderDispatcher edge case (broker outage, dispatch exception) — BL-126
11. BL-110a xdist 격리 (pool reset autouse fixture) — BL-127
12. trading-ui scenario 3 KS bypass disabled assert (현재 주석) — BL-128

**P3 BL 등록**:
1. ANSI/control seq HTML 처리 (XSS 아님, 가독성) — BL-129

#### G.5 (self-checklist) ✅

종료 시 신규 ~32 tests + 8 e2e + 5 BL Resolved + 2 신규 BL + codex 결과 + LESSON 후보 모두 보고.

---

## §3. Edge Cases & Risk Register (사용자 명시 요구)

> **plan v3 §5.5** 의 19 항목 영구 기록. 각 항목 mitigation + 잔존 risk + implementation 검증 결과.

### Track 1 (EC-1 ~ EC-8)

| ID | Edge case | 영향 | Mitigation 검증 결과 |
| --- | --- | --- | --- |
| EC-1 | Clerk dev session 만료 | trading-ui spec unauth redirect | ✅ global.setup.ts `clerk.signIn()` 매번 갱신 |
| EC-2 | Clerk dev key rotation | env 무효화 | ✅ `.env.local` (gitignored) 갱신 + `.env.example` 만 commit |
| EC-3 | clerk.signIn() API drift | global.setup.ts compile fail | ✅ implementation 시 Clerk 공식 docs 재확인 + version pin |
| EC-4 | Mock route nested path cover | unmocked → real call leak | ✅ trailing wildcard `**` + leak guard |
| EC-5 | leak guard setup phase false-positive | global.setup.ts fail | ✅ spec test.beforeEach 에만 등록 |
| EC-6 | fullyParallel:false 의 serial 보장 | 공유 storageState flake | ✅ `--workers=1` 명시 + `test.describe.configure(serial)` 이중 |
| EC-7 | storageState.json git commit 사고 | dev credentials 노출 | ✅ `.gitignore` + `git check-ignore` 검증 |
| EC-8 | NODE_ENV=production 실수 실행 | production keys 노출 | ✅ scripts 의 production guard |

### Track 2 (EC-9 ~ EC-15)

| ID | Edge case | 영향 | Mitigation 검증 결과 |
| --- | --- | --- | --- |
| EC-9 | OHLCV fixture 가 trade trigger 안 함 (codex iter 2 실측 refuted) | scenario2 fail | ✅ 신규 `make_trending_ohlcv` + precondition test num_trades >= 3 |
| EC-10 | idempotency_key 충돌 | snapshot 검증 못함 | ✅ `f"{request.node.name}:{uuid4().hex}"` per test |
| EC-11 | dispatch race (commit 전 vs 후) | snapshot timing | ✅ OrderService.execute 가 commit → dispatch 순 (codex iter 2 검증) |
| EC-12 | monkeypatch RedisLock.extend scope leak | 후속 test 영향 | ✅ pytest monkeypatch 자동 unwind + autouse 미사용 |
| EC-13 | heartbeat false 다중 누적 | lost_event 재set 시도 | ✅ `_heartbeat_loop` 가 set 후 return (loop 종료, `_ws_lease.py:165` 검증 완료) |
| EC-14 | pytest plugin race | find_spec inconsistent | ✅ 함수 진입 시 1회만 detect |
| EC-15 | HTML escape miss path | XSS 잔존 | ✅ 회귀 unit test + 모든 insertion site 점검 |

### 운영 / 환경 (EC-16 ~ EC-19)

| ID | Edge case | 영향 | Mitigation 검증 결과 |
| --- | --- | --- | --- |
| EC-16 | 격리 stack 5433/6380 vs 기본 5432/6379 충돌 | port conflict | ✅ `make up-isolated` 격리 compose file. 본 sprint 격리 stack 만 |
| EC-17 | staged `010-product-roadmap.md` 다른 세션 충돌 | git checkout conflict | ✅ branch 생성 시 working tree clean. 다른 세션이 PR 처리 중 (사용자 확인) |
| EC-18 | pre-push hook 격리 env 누락 | push 시 unit test 기본 stack hit | ✅ push 명령 env 명시 (사용자 승인 시 안내) |
| EC-19 | BL-110 numbering ambiguity | cross-link 깨짐 | ✅ atomic update 단계에서 BL-110 → 110a 통합 + 110b 신규 명시 |

### 누적 risk 평가

- **High** (mitigation 후 잔존): EC-1 / EC-3 / EC-9 — 모두 fail loud + 검증 가능
- **Medium**: EC-6 / EC-12 — 표준 도구 동작 검증
- **Low**: 나머지 — mitigation 충분

---

## §4. 자동 검증 결과

| 도구 | 명령 | expected | actual |
| --- | --- | --- | --- |
| backend ruff | `cd backend && uv run ruff check .` | 0 | ✅ 0 |
| backend mypy | `cd backend && uv run mypy src/` | 0 | ✅ 0 (147 src files) |
| backend pytest unit | `uv run pytest -q` | 1206+ passed / 0 failed | ✅ **1401 passed / 39 skipped / 0 failed** (169s) |
| backend pytest integration | `uv run pytest --run-integration` | scenario1-6 + BL-110a 7 + precondition 2 | ✅ scenario1-6 PASS / ws_lease_integration 7/7 / precondition 2/2 |
| backend run_auto_dogfood | `uv --directory backend run python scripts/run_auto_dogfood.py` | summary + escaped + json-report path | ✅ 6/6 PASS (BL-114 JSON parse path active) |
| frontend tsc | `pnpm tsc --noEmit` | 0 | ✅ 0 |
| frontend lint | `pnpm lint` | 0 | ✅ 0 |
| frontend vitest | `pnpm test` | 219+ passed | ✅ **251 passed** (43 files) |
| frontend e2e smoke | `pnpm e2e` | smoke 2 PASS | ✅ (사용자 .env.local 후) |
| frontend e2e authed | `pnpm e2e:authed` | trading-ui 5 + dogfood-flow 3 = 8 PASS, leak 0 | ✅ **9/9 PASS** (setup + 5 + 3, 18.6초) — Sprint 25 추가 commit 후 |

---

## §5. self-assessment

- **1-10 점수**: 9/10 유지 — Sprint 18→24 cascade 동일. 자동 회귀 가드 추가 + codex G.2 P1 4건 즉시 fix. 사용자 e2e:authed 실 검증 + dogfood Day 8+ 자동 가드 활성 후 10/10 도달 가능.
- **H1→H2 gate (≥7)**: ✅ 유지 (BL-005 dogfood 진행 중, 본 sprint 가 critical UI flow 자동화 + BE service-direct 보강).
- **다음 sprint 분기 옵션**:
  - **Path A — Beta 오픈 번들 (BL-070~072)**: dogfood self-assessment ≥ 7 확정 후. 도메인 + DNS + Resend.
  - **Path B — G.2 P2 12건 ↗ 우선순위 BL 처리** (BL-117~128): codex G.2 결과 기반 hardening. trading-ui scenario 3 KS bypass + leak guard fail-on-leak + Clerk emailAddress 등.
  - **Path C — BL-110b real Celery prefork SIGTERM**: dogfood 에서 prefork stuck 발견 시 가치 ↑.

---

## §6. LESSON 후보

> 3회 반복 확인 시 `.ai/common/global.md` 또는 stack rules 승격 후보 (`.ai/project/lessons.md` 등록).

- **L-S25-1**: codex G.0 iter 2 의 코드 실측 (`codex ran` 으로 직접 `run_backtest_v2` 실행) 이 plan 의 fixture 가설 refuted 한 사례 — **plan 작성 시 가설 fixture 의 행동 예측 금지, 코드 실측 의무**.
- **L-S25-2**: Clerk Playwright 공식 path 는 `clerkSetup() + clerk.signIn()` 둘 다 호출 의무 (Testing Token ≠ user login). `clerkSetup()` 단독 = bot detection bypass 만.
- **L-S25-3**: pytest CLI unknown flag 받으면 CLI failure (Python exception 아님) — `importlib.util.find_spec` 으로 **plugin detect first** 패턴.
- **L-S25-4**: prefork SIGTERM 검증은 `multiprocessing.Process` 로 sufficient 하지 않음 — Celery `worker_process_shutdown` handler 거치려면 real Celery worker subprocess 필요 (BL-110b 분리).
- **L-S25-5**: `_ws_lease.py:_heartbeat_loop` 같은 production async loop 의 lost_event 신호는 **falsy return + Exception 두 path 모두 set 보장** 의무 (codex G.2 P1 #2). 한 path 만 처리하면 silent split-brain.
- **L-S25-6** (사용자 명시 요구): codex G.0 iter 1 후 plan v2 surgery 시 **iter 2 재호출 의무** (사용자 "잘 확인한거야?" 명시 요구 사례 2026-05-03) — Sprint 22+24a 의 G.0 1 iter 만 수행 패턴 보강. 누적 1.9M+ tokens 부담 있지만 critical bug 발견 시 가치 ↑. memory `feedback_codex_g0_pattern.md` 강화 후보.
- **L-S25-7**: pytest-asyncio 의 per-test event loop 와 redis-py asyncio connection bound 충돌 → **autouse `_reset_pool_each_test` fixture 의무** (BL-110a integration test). Sprint 18 BL-080 의 module-level state 와 별도 issue (test 환경 한정).
- **L-S25-8** (사용자 본인 dogfood 실 검증으로 발견): **Next.js 16 dev server 첫 page render JIT 컴파일 5-30초** stuck. screenshot 의 "Rendering ..." 인디케이터 + 사용자 manual 도 reload 필요. Playwright e2e 의 default 30s navigation timeout 부족 → `playwright.config.ts` 에 `navigationTimeout: 60_000` + `actionTimeout: 30_000` + setup project 가 모든 protected page pre-warm 필수.
- **L-S25-9** (e2e:authed 9/9 PASS 도달 과정 발견): **Playwright Route handler 의 block body + return 누락 = Playwright 가 fulfill await 안 함** (race condition). `(route) => { route.fulfill(...) }` ❌ → `async (route) => { await route.fulfill(...) }` ✅ 또는 expression body `(route) => route.fulfill(...)`.
- **L-S25-10**: **Tanstack Query `refetchOnWindowFocus`** 가 `page.evaluate(() => window.dispatchEvent(new Event("focus")))` 으로 trigger 안 됨 (Playwright headless + React Query listener race). Mock route 변경 후 KS 등 cache invalidation 위해 `page.reload()` 사용 (사용자 manual refresh 시뮬).
- **L-S25-11**: **React component layout shift + `force: true` click** = onClick handler 안 도달. dispatch 한 click event 가 element actionable 시점 stable 안 됨. **`page.locator(...).dispatchEvent("click")`** 으로 React Synthetic event 직접 트리거 권장 — Tanstack Query refetchInterval 같은 미세 redraw 환경에서 robust.
- **L-S25-12**: **OrderListResponseSchema 의 `total` 필수 필드** — mock 에서 `{ items: [] }` 만 보내면 schema parse fail → query error → "주문 목록을 불러오지 못했습니다." → 후속 element (테스트 주문 button 등) 안 보임. **모든 list response mock 의 schema 필수 필드 검증 의무** (Sprint 26+ BL fixture 헬퍼 후보).

---

## §7. BL Status (본 sprint Resolved + 신규 등록)

### ✅ Resolved (본 sprint)

| ID | 제목 | 위치 |
| --- | --- | --- |
| BL-110a | In-process lease heartbeat/lost_event integration test | `tests/tasks/test_ws_lease_integration.py` (7 test) |
| BL-112 | scenario2 실 backtest 실행 | `tests/integration/test_auto_dogfood.py:165` + `tests/fixtures/backtest_ohlcv.py` + precondition |
| BL-113 | scenario3 OrderService.execute (snapshot 자동 채움) | `tests/integration/test_auto_dogfood.py:235` |
| BL-114 | pytest-json-report 도입 (importlib detect + backward compat) | `scripts/run_auto_dogfood.py:65` |
| BL-115 | HTML escape full coverage + 회귀 test | `scripts/run_auto_dogfood.py:207` + `tests/scripts/test_run_auto_dogfood_html_escape.py` |

### 🆕 신규 등록 (Sprint 26+ 이관)

| ID | 제목 | Priority | est | trigger | 근거 |
| --- | --- | --- | --- | --- | --- |
| BL-110b | Real Celery prefork SIGTERM integration test | P2 | M (4-6h) | pytest-celery 또는 subprocess.Popen worker | plan v3 (BL-110a/b split) |
| BL-116 | CI workflow_dispatch authed E2E | P2 | S (2-3h) | secret + storageState decode | plan v3 §1.5 |
| BL-117 | Clerk emailAddress 방식 마이그레이션 | P2 | S (1-2h) | password 방식 → emailAddress (MFA/verification 우회 회피) | codex G.2 P2 #1 |
| BL-118 | baseURL 통합 (config + setup) | P3 | S | playwright.config.ts baseURL 단일 source | codex G.2 P2 #2 |
| BL-119 | API_ROUTES URL predicate (orders-v2 false-match 차단) | P3 | S | route handler pathname predicate | codex G.2 P2 #3 |
| BL-120 | leak guard fail-on-leak | P2 | S (2h) | 현재 observability only, afterEach assert | codex G.2 P2 #4 |
| BL-121 | production guard host allowlist | P2 | S | NODE_ENV 외 PLAYWRIGHT_BASE_URL host + pk_test_/sk_test_ prefix | codex G.2 P2 #5 |
| BL-122 | pytest-json-report uv-aware detect | P3 | S | `uv run python -c` 기반 plugin 검증 | codex G.2 P2 #6 |
| BL-123 | mkstemp fd leak fix | P3 | XS | NamedTemporaryFile or os.close(fd) | codex G.2 P2 #7 |
| BL-124 | run_auto_dogfood subprocess timeout | P2 | XS | DB/Redis hang cron 무한 대기 차단 | codex G.2 P2 #8 |
| BL-125 | report 파일명 timestamp + symlink | P3 | S | 동시 실행 overwrite 차단 | codex G.2 P2 #9 |
| BL-126 | FakeOrderDispatcher edge case (broker outage / dispatch exception) | P2 | M | celery serialization / broker outage / pending stuck 시나리오 | codex G.2 P2 #10 |
| BL-127 | BL-110a xdist 격리 (pool reset autouse fixture) | P3 | S | serial marker 또는 isolated Redis DB/key namespace | codex G.2 P2 #11 |
| BL-128 | trading-ui scenario 3 KS bypass disabled assert | P2 | XS | 현재 주석 처리, OrdersPanel 주문 버튼 추가 후 활성화 | codex G.2 P1 #4 (partial) |
| BL-129 | ANSI/control seq HTML 처리 | P3 | XS | XSS 아님, 가독성/복붙 오염 | codex G.2 P3 #2 |

---

## §8. Sprint 26+ 이관

기존 plan §4 그대로 유지:
- BL-070~072 Beta 오픈 번들 (도메인 + DNS + Resend) — self-assessment ≥7 시 진입
- BL-014 Partial fill cumExecQty — partial fill Pain 발견 시
- BL-015 OKX Private WS — OKX dogfood 사용 시
- BL-104/105/108/109/111 — 본 sprint 무관, 기존 우선순위 유지
- BL-005 본인 1-2주 dogfood — 진행 중

---

## §9. 참조

- 이전 sprint dev-log: [`2026-05-03-sprint24b-auto-dogfood.md`](./2026-05-03-sprint24b-auto-dogfood.md) (Track 1 자동 dogfood) · [`2026-05-03-sprint24a-ws-stability.md`](./2026-05-03-sprint24a-ws-stability.md) (Track 2 WS 안정화)
- plan 파일: `~/.claude/plans/claude-plans-h2-sprint-25-prompt-md-snappy-bee.md` (v3, ~600 lines + Edge Cases 19)
- codex G.0 session: `019ded09-8442-7c63-8193-2e671f9f8601` (iter 1+2 = 1.9M tokens)
- 운영: `docs/07_infra/dogfood-day2-7-guide.md` · `docs/REFACTORING-BACKLOG.md`

---

## End-of-sprint-25 (✅ 완료 2026-05-03)

**커밋 / 머지**: 사용자 명시 승인 후 push + PR (Git Safety Protocol §CLAUDE.md). 본 dev-log 가 PR body 의 baseline.

**다음 sprint prompt**: `~/.claude/plans/h2-sprint-26-prompt.md` (작성 예정 — Path A/B/C 분기 명시).
