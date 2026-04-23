# QuantBridge — TODO

> 사람과 AI가 공동 관리하는 작업 추적 파일.
> 차단 항목은 `[blocked]` 표시, 질문은 Questions 섹션에 기록.

> **📍 제품 로드맵:** [`docs/00_project/roadmap.md`](./00_project/roadmap.md) (Horizon × Pillars)
> **📍 현재 Horizon:** H1 (0–1.5m, Stealth, 본인 dogfood). 진행: 7c → 7b → 8a → 8b → 8c → 7d → FE-01~04 → FE Polish Bundle 1/2 → Exchange Account Dialog ✅ → X1+X3 (5 워커 L2 Deep Parallel) ✅ → Y1 (Pre-flight Coverage Analyzer, PR #61) ✅ → **Path β (문서 선행 + Tier-2 Trust Layer CI + dogfood) 진행 중**. **남은 게이트: Bybit demo dogfood 3~4주 + Path β Gate-2** → H2 진입. (Kill Switch capital_base 동적 바인딩은 이미 완료됨 — 2026-04-22 확인)

> **🚀 현재 세션 작업:** Path β Stage 0 (문서 선행) — 2026-04-23. ADR-013 Trust Layer CI + 누락 회고 ADR-014/015/016/017 + Trust Layer 요구사항/아키텍처 + dogfood 체크리스트. Gate-0 검증 후 Stage 1/2 진행.

---

## Next Actions

### Stage 1: 계획 + 아키텍처 ✅ 완료

- [x] /office-hours 완료 (2026-04-13, Trust Layer 프레이밍 확정)
- [x] /autoplan 완료 (2026-04-13, CEO+Design+Eng 리뷰, Codex+Claude 듀얼 검증)
  - 4개 critical 인사이트 → CLAUDE.md + ADR-003 + lessons.md에 증류 완료
- [x] DESIGN.md 작성 — /design-consultation + ui-ux-pro-max (8개 변형 비교 → Final 확정)

### Phase 0: 병렬 스캐폴딩 (autoplan과 동시 진행)

**Session 1 — Root Infrastructure (main):** ✅ 완료 (2026-04-15)

- [x] 초기 커밋 (planning docs + config)
- [x] docker-compose.yml (TimescaleDB 단일 인스턴스 + Redis)
- [x] .github/workflows/ci.yml (changes-aware, frontend/backend 분리 + 요약 잡)
- [x] .husky/pre-commit + root package.json (husky + lint-staged)
- [x] .editorconfig + .gitignore 보강
- [x] .env.example POSTGRES\_\* 정렬 (docker-compose SSOT)

**Session 2 — Backend Scaffold (feat/backend-scaffold 워크트리):** ✅ 완료

- [x] FastAPI 프로젝트 초기화 (uv + pyproject.toml)
- [x] 3-Layer 디렉토리 구조 (src/core, common, auth, 7개 도메인)
- [x] Alembic async migration 인프라
- [x] pytest + pytest-asyncio 테스트 인프라 (health 엔드포인트 검증 1건 통과)
- [x] ruff.toml + mypy.ini 개발 도구 (ruff/mypy/pytest 모두 clean)

**Session 3 — Frontend Scaffold (feat/frontend-scaffold 워크트리):** ✅ 완료

- [x] Next.js 16 프로젝트 초기화 (pnpm)
- [x] FSD Lite 디렉토리 구조 (app, components, features, lib)
- [x] Clerk 인증 (ClerkProvider + proxy.ts)
- [x] shadcn/ui v4 기본 컴포넌트
- [x] ESLint + Prettier + vitest 개발 도구

**머지 완료 (2026-04-15):** d82de8b (backend) + 059eca9 (frontend) on main

### Phase 0 완료 후

- [x] 3개 워크트리 머지 (main ← backend ← frontend)
- [x] `docker compose up && pnpm dev && uvicorn` 동작 확인
- [x] Stage 3 첫 스프린트 계획 시작

### Stage 3 / Sprint 1 — Pine Parser MVP ✅ 완료 (2026-04-15, merge `e433a45`)

- [x] Pine v4/v5 파서 + 인터프리터 MVP
- [x] Ground zero EMA Cross v4/v5 golden 통과
- [x] `parse_and_run(source, ohlcv) -> ParseOutcome` 공개 API

### Stage 3 / Sprint 2 — vectorbt Engine + SignalResult Fill ✅ 완료 (2026-04-15)

- [x] `strategy.exit(stop=, limit=)` 해금 + SignalResult 브래킷 필드 채움
- [x] `strategy.short` / pyramiding / `qty_percent` / non-literal `qty` 명시적 Unsupported
- [x] `src/backtest/engine/` — types/adapter/metrics/public `run_backtest()` 구현
- [x] vectorbt 0.28.5 의존성 추가 (spec은 0.26 이었으나 numpy 2.x 호환 문제로 상향)
- [x] Ground zero EMA Cross v4/v5 backtest snapshot 추가
- [x] 합성 브래킷 골든 `ema_cross_atr_sltp_v5` 통과
- [x] 테스트 201 → 230 passing

### Stage 3 / Sprint 3 — Strategy API + Clerk 실배선 ✅ 완료 (2026-04-15)

- [x] Strategy 도메인 CRUD (6 엔드포인트) + /strategies/parse 미리보기
- [x] Clerk JWT 실검증 + User 모델 + /auth/me
- [x] Clerk Webhook (Svix 서명 검증) + user.created/updated/deleted 3 이벤트
- [x] Alembic 첫 migration + round-trip 테스트
- [x] pytest conftest (DB savepoint 격리 + FastAPI AsyncClient)
- [x] S3-01 gate propagation + S3-02 duplicate strategy.exit warning
- [x] AppException.code 추가 (spec §4.4 error code 구조)
- [x] 테스트 289 passing (230 → 289, 신규 59건)

### Stage 3 / Sprint 4 — Celery + Backtest API ✅ 완료 (2026-04-16)

- [x] S3-04 `_price_to_sl_ratio` 음수 ratio → ValueError (Pine semantics 정합 + golden 회귀 없음)
- [x] S3-03 (stretch) engine fault injection 테스트 — 91% 유지, 미커버 4영역 Sprint 5 이관 (spec §10.2)
- [x] `RawTrade` DTO + `BacktestResult.trades` + `extract_trades()` — Decimal-first fees 합산
- [x] `run_backtest()`가 trades 반환
- [x] Config Settings: `backtest_stale_threshold_seconds` + `ohlcv_fixture_root`
- [x] `Backtest` + `BacktestTrade` SQLModel (6-state enum, JSONB metrics/equity_curve, FK 정책)
- [x] Alembic migration `add_backtests_and_backtest_trades_tables` + round-trip 통과
- [x] JSONB serializers (Decimal → str, naive UTC → ISO 8601 Z)
- [x] Backtest + Strategy 예외 (`StrategyHasBacktests` 포함)
- [x] `TaskDispatcher` Protocol + Celery/Noop/Fake 3 impls
- [x] OHLCVProvider Protocol + FixtureProvider + BTCUSDT_1h fixture (8760 rows)
- [x] `BacktestRepository` CRUD + 조건부 UPDATE + reclaim_stale (running + cancelling 둘 다 커버)
- [x] Pydantic V2 schemas (9 DTOs, Decimal str, period validator)
- [x] Celery `celery_app.py` + `@worker_ready` stale reclaim hook
- [x] `tasks/backtest.py` run_backtest_task + `_execute` + `reclaim_stale_running` (prefork-safe lazy engine)
- [x] `BacktestService` 8 methods + 3-guard cancel 로직 (§5.1) + transient `CANCELLING` 처리
- [x] `StrategyService.delete()` cross-domain — 선조회 + `IntegrityError → StrategyHasBacktests` 번역 + `rollback()` 추가
- [x] Router 7 REST endpoints + main.py 등록
- [x] API E2E tests: submit/list/detail + cancel/delete/trades/progress (23 신규)
- [x] L4 로컬 smoke 3건 완료 (S1 ✅ / S2 ✅ / S3 ⚠️partial — spec §10.1 기록)
- [x] endpoints.md 갱신 (cancel 추가 + task_id → backtest_id)
- [x] 테스트: 289 → **368 pass**
- [x] CI: ruff / mypy / pytest / alembic upgrade 모두 green

**PR:** https://github.com/woosung-dev/quantbridge/pull/3 (Draft)

### Sprint 5 Stage B — Option A: Infra Hardening + market_data 도메인 (코드 작업)

> Sprint 4 spec §10.5/§11.2 명시 path. plan: [`superpowers/plans/2026-04-16-sprint5-stage-b.md`](./superpowers/plans/2026-04-16-sprint5-stage-b.md), spec: [`superpowers/specs/2026-04-16-sprint5-stage-b-design.md`](./superpowers/specs/2026-04-16-sprint5-stage-b-design.md).

#### M1 — DateTime tz-aware + bar_index Fix + Metadata Diff ✅ 완료 (2026-04-16, PR #6 `514ab84`)

- [x] AwareDateTime TypeDecorator 신규 (`backend/src/common/datetime_types.py`) + ORM 가드
- [x] 3개 도메인 모델 `_utcnow()` 제거 + `datetime.now(UTC)` 일원화
- [x] Alembic migration `convert_datetime_to_timestamptz` (11개 컬럼, period_start/end 포함)
- [x] Pydantic `AwareDatetime` 적용 (Backtest/Strategy/Auth schemas + period validator)
- [x] Engine `trades.py` `_resolve_bar_index` helper + 중복 timestamp 회귀 테스트
- [x] `serializers._parse_utc_iso` naive 반환 production 버그 fix (M1 Task 8 catch)
- [x] utcnow() 코드베이스 전수 audit + Celery task datetime 인자 점검
- [x] datetime 비교 패턴 tz-aware 통일 (21 failures + 3 collection errors 회귀 fix)
- [x] metadata diff 회귀 테스트 (SQLModel.metadata vs alembic upgrade schema)
- [x] 테스트: 368 → **380 pass** / ruff clean / mypy clean / CI green
- [x] [ADR-005](./dev-log/005-datetime-tz-aware.md) 작성

#### M2 — market_data Infrastructure (T11~T18) ✅ 완료 (2026-04-16, PR #6)

- [x] T11: ccxt 4.5.49 + tenacity 9.1.4 의존성 추가
- [x] T12: Docker init SQL — TimescaleDB extension + `ts` schema (manual + future fresh setup)
- [x] T13: `market_data/constants.py` (Timeframe Literal + TIMEFRAME_SECONDS + normalize_symbol)
- [x] T14: OHLCV Hypertable 모델 (Numeric(18,8) + composite PK + `ts` schema + AwareDateTime)
- [x] T15: Alembic migration `create_ohlcv_hypertable` (7-day chunk + idempotent extension/schema)
- [x] T16: OHLCVRepository (get_range + insert_bulk ON CONFLICT + find_gaps generate_series + advisory_lock)
- [x] T17: Advisory lock 동시성 테스트 (pg_try_advisory_xact_lock 결정적 probe)
- [x] T18: M2 milestone push + CI green (391 tests)
- [x] metadata diff 회귀 테스트 multi-schema 지원 (ts.ohlcv 같은 non-public schema drift 감지)

#### M3 — CCXT + TimescaleProvider + Backtest 통합 (T19~T28) ✅ 완료 (2026-04-16, PR #6)

- [x] T19: Config — `ohlcv_provider` Literal flag + `timescale_url` 제거
- [x] T20: CCXTProvider — pagination + tenacity 재시도 + closed bar 필터
- [x] T21: TimescaleProvider — cache → CCXT fallback + advisory lock
- [x] T22: FastAPI Lifespan — CCXTProvider singleton (timescale 경로만 init)
- [x] T23: Celery Worker CCXTProvider lazy singleton + worker_shutdown close (prefork-safe)
- [x] T24: `get_ohlcv_provider` DI — config flag 분기 (HTTP)
- [x] T25: Backtest dependencies + worker provider 조립 통합
- [x] T26: conftest `_force_fixture_provider` autouse — CCXT 외부 호출 차단
- [x] T27: Backtest E2E with TimescaleProvider (mock CCXT) — cache miss → fetch → hit 검증
- [x] T28: M3 milestone push + CI green (400 tests)

#### M4 — Beat Schedule + Docker-compose Worker + Sprint 3 Drift (T29~T33) ✅ 완료 (2026-04-16, PR #6)

- [x] T29: Celery Beat schedule — `backtest.reclaim_stale` 5분 주기 (worker_ready hook과 이중 안전망)
- [x] T30: Backend Dockerfile (uv 기반, api/worker/beat 공용)
- [x] T31: docker-compose backend-worker + backend-beat 통합 — 4 services UP 검증
- [x] T32: Strategy pagination drift fix — limit/offset 표준화 + page deprecated fallback
- [x] T33: M4 final push + PR ready + TODO/CLAUDE.md 동기화

### Sprint 5+ 이관 (Sprint 4 spec §10.5 참조)

> M1 완료로 일부 항목 해소됨. 잔여 항목은 M2~M4 또는 Sprint 6+로 이관.

- [x] **S3-05:** `_utcnow()` → AwareDateTime + TIMESTAMPTZ 복원 ← M1 완료 (ADR-005)
- [x] Engine `trades.py` bar_index TypeError fix ← M1 완료 (`_resolve_bar_index` helper)
- [x] Stale cancelling 주기적 reclaim beat task ← M4 T29 완료 (5분 주기)
- [ ] Idempotency-Key 지원 (`POST /backtests`) → Sprint 6+ 이관
- [ ] Real broker integration 테스트 인프라 (pytest-celery) → Sprint 7+ (Trading 도메인 시점)
- [x] OHLCV 실데이터 수집 (CCXT + TimescaleDB hypertable) ← M2/M3 완료
- [ ] conftest Alembic-based 전환 → 부분 해소 (metadata diff 회귀로 drift 감지 추가). 완전 전환은 미정
- [x] Sprint 3 Strategy router pagination drift (`page/limit` → `limit/offset`) ← M4 T32 완료
- [x] docker-compose에 worker 서비스 추가 ← M4 T31 완료 (worker + beat)
- [ ] FE Strategy delete UX (archive 유도) → Sprint 6+ FE 라인
- [ ] Task 14/15/19/21 Minor improvements (Sprint 4 spec §10.5) → 보류

### Sprint 6+ Open Issues (Stage B 이후)

- [ ] Idempotency-Key 지원 (`POST /backtests`)
- [ ] Real broker integration 테스트 인프라 (pytest-celery)
- [ ] CCXT 호출 계측 (Prometheus/logfire)
- [ ] 초기 backfill Celery task 분리 (대용량 OHLCV 백필)
- [ ] TimescaleDB compression / retention policy
- [ ] Multi-worker split-brain Redis lock (현재는 PG advisory만)
- [ ] FE Strategy delete UX (archive 유도)
- [ ] Sprint 4 spec §10.5 Minor: BacktestRepository session.refresh, exists_for_strategy EXISTS, fixture 통합
- [ ] conftest 완전 Alembic 전환 (현재는 metadata.create_all + 회귀 diff로 부분 보강)

### Sprint 8+ 후보

- [ ] Strategy template gallery (`/templates`) — Sprint 7c에서 placeholder만 처리
- [ ] Strategy clone + share — Sprint 7c에서 드롭다운만 disabled (design review P7-4)
- [ ] Backtest run from /strategies/[id]/edit — `/backtest?strategy_id=` 연결 (Sprint 7b/7d 후보)
- [ ] FE component test infra (Vitest + @testing-library/react) — Sprint 7c 이관
- [ ] FE E2E test infra (Playwright + @clerk/testing) — Sprint 7c 수동 smoke만 돌렸으나 자동화 안 됨. Clerk Dashboard testing token 발급 + Playwright fixture 구축. 9 시나리오 spec은 plan §5.7에 기록됨 (재사용). Context: 2026-04-17 Playwright MCP smoke 경험

### Sprint 7c 이후 FE Design Debt (design review 2026-04-17 기록)

- [x] Chip-style tag input (type + Enter + Backspace 제거) — Sprint FE-D ✅ 완료 (2026-04-20, PR #33, 118 tests)
- [ ] Coachmark tour — first-visit edit 페이지의 ⌘+S/Enter 단축키 1회성 overlay. Context: plan Persona C storyboard
- [ ] Save conflict OCC — 백엔드 ETag 또는 `If-Unmodified-Since` header 도입 후 FE에서 409 Conflict 분기. Context: plan P7-10, 스키마 변경 필요
- [x] Bottom sheet dialog (mobile <768px) — Sprint FE-E ✅ 완료 (2026-04-20, PR #34, 124 tests)
- [ ] Monaco Pine autocomplete — Pine v5 builtin 함수 자동완성 등록. Context: plan P7-7, full grammar 선행 필요
- [ ] Full Pine TextMate grammar — 현재 5색 Monarch → 전체 keyword + builtin + operator 완전 grammar. 3~5일. Context: plan P7-7
- [x] Keyboard shortcut help dialog (? key) — Sprint FE-C ✅ 완료 (2026-04-19, PR #31)
- [x] localStorage draft user_id scoping — Sprint FE-C ✅ 완료 (2026-04-19, PR #31)

### /qa Quick tier findings (2026-04-17 — 상세 `.gstack/qa-reports/qa-report-localhost-2026-04-17.md`)

- [x] **ISSUE-001 (CRITICAL) — `/trading` App Shell 누락** → `src/app/trading/` → `src/app/(dashboard)/trading/` 이동으로 해소 (commit `5bb0223`). 사이드바·유저메뉴·nav 복구
- [x] **ISSUE-002 (Medium) — Landing `/` CTA/네비 없음** → Sprint FE-A ✅ 완료 (2026-04-19, PR #30 via stage/fe-polish #32)
- [x] **ISSUE-003 (Medium) — Edit 코드 탭 우측 패널 misleading empty state** → Sprint 7b ✅ 완료 (2026-04-17)
- [x] **ISSUE-004 (Medium) — 파싱 결과 탭 정보량 부족** → Sprint 7b + FE-01 ✅ 완료 (2026-04-17~19)
- [x] **ISSUE-005 (Medium) — `/trading` 모바일 테이블 overflow** → Sprint FE-B ✅ 완료 (2026-04-19, PR #29)
- [x] **ISSUE-006 (Medium) — `/trading` 빈 상태 copy 없음** → Sprint FE-B ✅ 완료 (2026-04-19, PR #29)
- [ ] **ISSUE-007 (Low) — Clerk `@clerk/ui` 미사용 경고.** ClerkProvider에 `ui={ui}` 전달 시 구조적 CSS pin 제거. Clerk 버전 호환성 확인 후
- [x] **ISSUE-009 (Low) — `/dashboard` scaffold vs 사이드바 disabled 불일치** → Sprint FE-A ✅ 완료 (2026-04-19, PR #30 via #32)

### Sprint 6 — Trading 데모 MVP ✅ 완료 (2026-04-16)

**6-Step 방법론 전체 완료. T1~T23 구현 + CSO 체크리스트 해소.**

- [x] Step 1 /office-hours → `docs/01_requirements/trading-demo.md` (design doc APPROVED, spec review 2 iterations)
- [x] Step 2 /brainstorming → `docs/superpowers/specs/2026-04-16-trading-demo-design.md` (5 기술 결정 Q1~Q5)
- [x] Step 3 /writing-plans → `docs/superpowers/plans/2026-04-16-trading-demo.md` (T1~T23, 5381 라인)
- [x] Step 4 /autoplan → 41 findings / 5 critical fixes plan 반영 (ADR-006)
- [x] Step 5 /cso → 6 security findings / CSO-1 plan 반영 (`docs/audit/2026-04-16-trading-demo-security.md`)
- [x] Step 6 SDD — T1~T23 전체 구현 완료 (feat/sprint6-trading-impl-v2, PR #9)

**CSO 체크리스트:**

- [x] CSO-1: EncryptionService MultiFernet (T4/T10/T11/T17 — 5회 plan drift 교정)
- [x] CSO-2: `backend/Dockerfile` `USER appuser` 추가 (T23)
- [x] CSO-3: `.github/workflows/ci.yml` 3 third-party actions SHA pin (T23)
- [x] CSO-4: `docker-compose.yml` `TRADING_ENCRYPTION_KEYS` env rename (T3)
- [x] CSO-6: Webhook router `MAX_WEBHOOK_BODY = 64 * 1024` Content-Length cap (T19)
- [ ] (Sprint 7 이연) CSO-5: Frontend dev CVEs

**구현 요약:**

- 34 commits (23 feat + 11 polish), 58 files, +5,715 lines
- 4 신규 테이블 (`trading` 스키마) + Alembic migration
- 10 REST endpoints + webhook receiver (HMAC + Idempotency-Key)
- Kill Switch 2 evaluator (CumulativeLoss + DailyLoss)
- Celery execute_order_task (prefork-safe, 3-guard transitions)
- Frontend `/trading` read-only 대시보드 (3 panels)
- Tests: backend 506 pass + frontend 7 pass (baseline 391 → 513 total)

### 미완성 문서 → ✅ 완료 (Sprint 5 Stage A, 2026-04-16)

- [x] docs/01_requirements/ — requirements-overview.md + req-catalog.md
- [x] docs/02_domain/ — domain-overview.md + entities.md + state-machines.md
- [x] docs/04_architecture/ — system-architecture.md + data-flow.md (보강)
- [x] docs/05_env/ — local-setup.md + env-vars.md + clerk-setup.md
- [x] docs/06_devops/ — docker-compose-guide.md + ci-cd.md + pre-commit.md
- [x] docs/07_infra/ — deployment-plan.md + observability-plan.md + runbook.md (draft)

## In Progress

- Sprint 5 Stage A docs sync ✅ 완료 (2026-04-16)
- Sprint 5 Stage B M1~M4 ✅ 완료 (2026-04-16, PR #6 머지)
- Sprint 6 Trading 데모 MVP ✅ 완료 (2026-04-16, PR #9 — 34 commits)
- Sprint 7a Bybit Futures + Cross Margin ✅ 완료 (2026-04-17, PR #10, 524 tests)
- Sprint 7c FE 따라잡기 (Strategy CRUD UI) ✅ 완료 (2026-04-17, 3 라우트 + Monaco Pine Monarch + shadcn/ui 12개 + sonner + Delete 409 archive fallback + design-review 7-pass 5/10→9/10)
- Sprint 7c 후속 — Next.js 16 Anti-Pattern 해소 ✅ 완료 (2026-04-17, `chore/dev-cpu-optimization` — context7 감사 P0~P7 적용)
  - [x] P0: `QueryProvider` → context7 TanStack SSR 공식 패턴 (typeof window 분기 + browser singleton)
  - [x] P1: Trading API `fetch()` → `apiFetch` + Clerk 토큰 일원화 (보안 401 누락 fix)
  - [x] P2: `strategies/page.tsx` 서버 prefetch + `HydrationBoundary` PoC (Clerk `auth()` server-side)
  - [x] P3: `step-code.tsx` useEffect deps 안정화 (`useRef` 캡슐화, ADR-010 #5 반영)
  - [x] P5: Suspense/ErrorBoundary — Next.js 규약 `loading.tsx`+`error.tsx` 라우트 레벨 (strategies + dashboard group)
  - [x] P6: `app/(dashboard)/error.tsx` 추가 (route-group 레벨 경계)
  - [x] P7: Trading FSD 구조 (`schemas.ts`/`query-keys.ts`/`hooks.ts`/`components/` 분리 + `index.ts` barrel)
  - 검증: `tsc --noEmit` ✅ / `eslint` ✅ / `vitest` 7/7 ✅
- Sprint 7b Edit UX 풍부화 ✅ 완료 (2026-04-17, `feat/sprint7b-edit-parse-ux`)
  - T1: BE `ParsePreviewResponse.functions_used` 노출 (Pydantic schema 1필드, Alembic migration 없음, Strategy 모델 불변)
  - T2–T3: FE Zod schema round-trip test + `ParsePreviewPanel`에 감지 함수 섹션(지표/전략콜/기타) + 빈 상태 copy "⌘+Enter로 첫 파싱을 실행하세요"
  - T4: `TabCode` 마운트 시 자동 `useParseStrategy` 호출 → 우측 패널 empty-state 오표시 제거 (ISSUE-003)
  - T5: `TabParse` 4-섹션 재작성 (에러 → 경고 → 감지 함수 → 메타), 실시간 스냅샷 + 저장 시점 스냅샷 구분 표시 (ISSUE-004)
  - 검증: backend 528 tests ✅ / ruff + mypy clean / frontend 9 vitest ✅ / tsc + eslint clean
- Sprint 7c 후속 — CPU 근본 원인 정정 + E2E 검증 ✅ 완료 (2026-04-17)
  - **진짜 원인 판명:** Next.js 16.2.3 Turbopack `turbo-tasks` recomputation 무한 루프 버그 — 16.2.4에서 [PR #92725](https://github.com/vercel/next.js/pull/92725) + [PR #92631](https://github.com/vercel/next.js/pull/92631) 수정. 본 세션의 ADR-010 15 anti-pattern 분석과 P0 `typedRoutes: isBuild` 회피 모두 오진에 기반 → **철회**
  - [x] `frontend/package.json`: `next@^16.2.4` 업그레이드로 근본 해결 (사용자 확인 — idle 0.0% CPU)
  - [x] `next.config.ts`: `create-next-app` 기본값으로 회귀 (reactStrictMode/typedRoutes/env 3개 필드 제거)
  - [x] 필터 URL sync (Plan §5.7 시나리오 7): `useSearchParams`+`router.replace` + 서버 `page.tsx` `searchParams` 동기화. `parse_status` / `archived` / `page` 3개 쿼리 반영
  - [x] Sprint 7c Playwright E2E 9/9 시나리오 돌림: 7 PASS, 1 PARTIAL→FIX (필터 URL sync — 본 커밋에 해소), 1 NOT TESTED (409 archive fallback — 백테스트 연결 전략 부재)
- Sprint 8a-pre Phase -1 실측 ✅ 완료 (2026-04-18, PR #18)
- Sprint 8a Tier-0 Foundation ✅ 완료 (2026-04-18, PR #20, 169 tests)
- Sprint 8b Tier-1 래퍼 + Tier-0 렌더링 + 6/6 corpus ✅ 완료 (2026-04-18, PR #21, 224 tests)
- Sprint 8c user-defined function + 3-Track dispatcher ✅ 완료 (2026-04-19, PR #22, 252 tests)
- Sprint 7d OKX + Trading Sessions ✅ 완료 (2026-04-19, PR #28, 823 tests)
- Sprint FE-01 TabParse 1질문 UX + LESSON-004 ✅ 완료 (2026-04-19, PR #23/#24, 35 FE tests)
- Sprint FE-02 FE tech debt 제로 + CI 복원 ✅ 완료 (2026-04-19, PR #25, 53 FE tests, LESSON-005/006)
- Sprint FE-03 Edit Zustand lift-up ✅ 완료 (2026-04-19, PR #27, 59 FE tests)
- Sprint FE-04 Backtest UI MVP ✅ 완료 (2026-04-19, PR #26, 86 FE tests)
- FE Polish Bundle 1 (FE-A/B/C) ✅ 완료 (2026-04-19, PR #32 merge, autonomous-parallel-sprints Option C 기본)
- FE Polish Bundle 2 (FE-D/E/F) ✅ 완료 (2026-04-20, PR #36 merge, Option C P0+P1 dogfood 4/4 달성, BUG-1/2/3 발견)
- Sprint X1+X3 (5 워커 L2 Deep Parallel + 3-way Evaluator) ✅ 완료 (2026-04-23, stage `8b1028b`, 946 BE / 167 FE tests)
- Sprint Y1 Pre-flight Pine Coverage Analyzer ✅ 완료 (2026-04-23, PR #61 merge, 961 BE / 167 FE tests, whack-a-mole 종식)
- **Path β — Documentation-First → Tier-2 Trust Layer CI (진행 중)** — 2026-04-23 Stage 0 시작
  - Stage 0 (Docs): ADR-013/014/015/016/017, trust-layer-architecture.md, trust-layer-requirements.md, dogfood-checklist.md, LESSON 승격 → Gate-0
  - Stage 1 (Design): 3-Layer Parity 스켈레톤 → Gate-1 (codex + opus 2중 blind)
  - Stage 2 (Implement): P-1/2/3 tests + baseline_metrics.json + mutation oracle + CI workflow → Gate-2
  - Dogfood 병행: Kill Switch 0 오작동 + 체결 ≥95% + sharpe 편차 <5% + UX ticket 화
- **다음:** Path β Gate-0 (Stage 0 완결성 검증, codex 단일) → Stage 1 설계 착수

### Sprint 7 Next Actions

- [x] Strategy CRUD UI (목록/생성 3-step/편집 3탭 + delete 409 archive fallback) — Sprint 7c ✅ 완료 (2026-04-17)
- [x] 실 CCXT 거래소 연동 (Bybit testnet Futures + Cross Margin) — Sprint 7a ✅ 완료 (2026-04-17)
- [x] `bybit_futures_max_leverage` config 값이 `OrderService.execute`에서 enforce (422 `LeverageCapExceeded`) — Sprint 7a 리뷰 합의로 완료 (2026-04-17)
- [ ] Bybit testnet Live smoke test (실 API key로 수동 주문 1건) — 사용자 테스트 대기 (Step 4에서 runbook/체크리스트 지원 예정)
- [x] Trading Sessions 도메인 확장 (세션 생성/시작/중지/kill) — Sprint 7d ✅ 완료 (2026-04-19, PR #28)
- [x] OKX 멀티 거래소 추가 — Sprint 7d ✅ 완료 (2026-04-19, PR #28)
- [x] Edit 페이지 Pine 이터레이션 UX 풍부화 (ISSUE-003 + ISSUE-004) — Sprint 7b ✅ 완료 (2026-04-17)
- [x] **Kill Switch `capital_base` 동적 바인딩 (`ExchangeAccount.fetch_balance()`) ✅ 이미 완료 (2026-04-22 확인)**
  - `kill_switch.py:95-99`: `CumulativeLossEvaluator` balance_provider 동적 바인딩 구현됨
  - `dependencies.py:105`: `balance_provider=exchange_service` DI 연결 완료
  - `service.py:98-131`: `fetch_balance_usdt()` CCXT 조회 + config fallback 구현됨
  - Redis TTL cache는 서비스 주석 기준 H2+ (WebSocket 스트리밍으로 대체 예정)
- [ ] WebSocket 실시간 주문 상태 스트리밍
- [ ] CSO-5: Frontend dev CVEs 해소
- [ ] Rate limiting middleware (per-user, per-endpoint)
- [ ] Prometheus/Grafana 계측 (CCXT 호출 + 주문 처리 latency)
- [ ] Bybit v5 `set_margin_mode`/`set_leverage` "not modified" error handling (codes 110026, 34036) — Sprint 8+ mainnet 준비 (BybitFuturesProvider 반복 주문 시 legitimate error를 idempotent no-op로 처리)
- [ ] `trading.orders.margin_mode` DB-level `CHECK (margin_mode IN ('cross','isolated') OR margin_mode IS NULL)` — Sprint 8+ mainnet 전, DB-string↔DTO-Literal 경계 불변식 하드닝 (ADR-007 §구현 노트 참조)

### Sprint 7c — FE 따라잡기 (Strategy CRUD UI)

> **Scope 결정 완료:** 2026-04-17 (gstack `/office-hours` session 12 + `/plan-design-review` Step 0 lite). 상세 근거·Stage 2 자산 재채택·개정 premises 전부 [`dev-log/008-sprint7c-scope-decision.md`](./dev-log/008-sprint7c-scope-decision.md) 참조.
>
> **Implementation plan 대기:** 별도 세션에서 `/superpowers:writing-plans` 호출 → `docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md` 생성 예정. 그 전까지 SDD 실행 금지. Stage 2 자산(DESIGN.md + 프로토타입 3개 + INTERACTION_SPEC)을 반드시 input으로 사용.

- [ ] **선행 Assignment (plan 작성 전 OK):** Pine 소스 1개를 현재 `curl` 방식으로 등록·Parse·백테스트까지 직접 돌리고 스텝별 초단위 시간 측정 — Sprint 7c 완료 후 before/after 정량 평가 지표
- [ ] **Step 2:** `/superpowers:writing-plans` 세션 호출하여 경량 plan (T1~Tn task 분해) 생성. Input: ADR 008 + DESIGN.md + 프로토타입 3개 + INTERACTION_SPEC
- [ ] **Step 2.5 (선택):** writing-plans 산출물을 대상으로 `/plan-design-review` 정식 7-pass 재실행하여 empty/error/responsive/a11y 세부 gap 확인
- [ ] **Step 3:** `/superpowers:subagent-driven-development`로 plan 실행 (Sprint 7b 시작 전 merge, 1~1.5주 time box)
- [ ] **라우트 구성 (ADR 개정 반영):** `/strategies`(목록) + `/strategies/new`(3-step wizard) + `/strategies/[id]/edit`(Monaco 탭 UI). Drawer 패턴 폐기
- [ ] **비스코프 확인:** 주문 생성 폼 / OrderList 상세·필터 / ExchangeAccount UI / Strategy versioning 전부 Sprint 8+에서 재평가 (Monaco는 Stage 2 결정대로 포함)

### Sprint 8 — Pine Execution Strategy v4 (Alert Hook Parser + 3-Track)

> **Architecture:** [`dev-log/011-pine-execution-strategy-v4.md`](./dev-log/011-pine-execution-strategy-v4.md) (ADR) + [`04_architecture/pine-execution-architecture.md`](./04_architecture/pine-execution-architecture.md) (구현 명세) + [`superpowers/specs/2026-04-17-pine-execution-v4-design.md`](./superpowers/specs/2026-04-17-pine-execution-v4-design.md) (세션 아카이브)
>
> **핵심 통찰 3:** (1) `alert()`은 자발적 매매 신호 선언 (2) 매매 로직은 Pine 전체의 13% 이하 (3) 실측 없는 설계 5라운드 < 실측 1번
>
> **Horizon H1 Stealth 완료 기준 (Sprint 8d 종료 시):** DrFX/LuxAlgo 3종 PyneCore 대비 상대 오차 <0.1%, `strategy.exit trail_points` 지원, 본인 dogfood TV→QB 30초 내

#### Sprint 8a-pre — Phase -1 실측 (2주, 2026-04-18~05-01)

> **상세 plan:** [`superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md`](./superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md)
> **브랜치:** `experiment/phase-minus-1-drfx` (main `d36793e` 기준)
> **작업 디렉토리:** `.gstack/experiments/phase-minus-1-drfx/` (격리)
> **원안 변경(2026-04-18):** 3-way(LLM 1개 vs PyneCore vs TV) → **N-way 5 스크립트 × 최대 7 엔진 × 8 지표** 매트릭스로 확장

##### Day 1 — 환경 + I3 DrFX PyneCore + 파서 커버리지

- [x] PR #17 `--squash` merge 완료 (`d36793e`)
- [ ] `experiment/phase-minus-1-drfx` 브랜치 + `.gstack/experiments/phase-minus-1-drfx/` 격리 디렉토리
- [ ] `uv init` + `uv add pynecore pynescript ccxt pandas numpy matplotlib`
- [ ] OpenAI / Google API 키 존재 확인 → E6/E7 skip 여부 사전 결정
- [ ] 사용자 제공 5개 `.pine` → `corpus/{s1,s2,i1,i2,i3}_*.pine`
  - S1 RTB (strategy, 쉬움) / S2 (strategy, 중간)
  - I1 (indicator, 쉬움) / I2 (indicator, 중간) / I3 DrFX Diamond Algo (indicator, 어려움)
- [ ] BTCUSDT 1H 2025-04-18 ~ 2026-04-17 고정 OHLCV CSV + SHA256
- [ ] E1 PyneCore → I3 DrFX 실행
- [ ] E2 pynescript → 5종 파싱 커버리지 리포트
- [ ] E3 현재 QB 파서 → 5종 baseline 리포트 (ADR-004 baseline)
- [ ] E4 `/tmp/drfx_test/drfx_backtest.py` 고정 CSV 재실행

##### Day 2 — LLM 매트릭스 + trail_points probe

- [ ] E5 Claude Sonnet 4.6 — I3 DrFX 변환 (Claude Code 내부)
- [ ] E6 GPT-5 / E7 Gemini 2.5 Pro — 키 존재 시 자동 호출, 부재 시 skip + 사유 기록
- [ ] 8 지표 수치 비교표 + bar-by-bar Jaccard (E1 oracle 기준)
- [ ] LLM 버그 3개 재현성 체크 (SL 기준점 / float `==` / look-ahead) 모델별 PASS/FAIL
- [ ] `strategy.exit trail_points/trail_offset` 지원 probe (DrFX or 합성 `probe_trail.pine`)
- [ ] `qty_percent` 분할 익절 probe 1건

##### Day 3 — S1/S2/I1/I2 얕은 실행 + TV 스폿체크 + 판단

- [ ] S1/S2/I1/I2 얕은 실행 (E1 + E3 중심)
- [ ] `nway_diff_matrix.csv` (5 엔진 × 5 스크립트 × 8 지표)
- [ ] 상대 오차 계산 (I3 심층 기준): `|candidate - E1| / |E1|`
- [ ] TV 수동 스폿체크 1건 (I3 1H 최근 30일, Supertrend/ATR 2~3점)
- [ ] 가정 3개 판정표 → ✅/🟡/❌
- [ ] `README.md` 상단 한 줄 권고: continue / ADR amend / abort
- [ ] 사용자 승인 → Day 4+ 이행

##### Day 4-10 (scope 밖, 참고)

- [ ] Day 4-5: TV 공개 스크립트 15~20개 alert 패턴 프로파일링 (Track S/A/M 실제 비율)
- [ ] Day 6-7: ADR-011 amendment (실측 반영)
- [ ] Day 8-10: Tier-0 pynescript 포크 착수

##### 가정 3개 (Day 3 판정 대상)

1. PyneCore가 `strategy.exit trail_points/trail_offset` 지원 (RTB/LuxAlgo 필수)
2. LLM 변환본 vs PyneCore 상대 오차 <0.1% MVP KPI 현실적
3. LLM 변환 버그 3개(SL 기준점/float ==/look-ahead)가 수익률에 실질 영향

#### Sprint 8a — Tier-0 공통 코어 (3주, 05-02~22 예정)

- [ ] pynescript 포크 완료 + QB `backend/src/strategy/pine/parser.py` 대체
- [ ] AST 노드 확장: 배열 리터럴, switch, method-call, Matrix/Map/UDT, 4단계 타입 수식어
- [ ] PyneCore var/varip/rollback 런타임 이식 (Apache 2.0, NOTICE 의무)
- [ ] bar-by-bar 이벤트 루프 백테스터 (vectorbt는 지표 계산 전용으로 격리)
- [ ] 렌더링 객체 런타임 범위 A (box/label/line 좌표 저장 + getter, 차트 렌더 NOP)
- [ ] PyneCore 골든 CI 하네스 구축 (상대 오차 <0.1% MVP)
- [ ] 완료 기준: DrFX/LuxAlgo 런타임 오류 없이 완주 + PyneCore 대비 10% 이내 오차

#### Sprint 8b — Tier-1 가상 strategy 래퍼 + Tier-0 렌더링 scope A ✅ 완료 (2026-04-18)

> **Plan:** [`docs/superpowers/plans/2026-04-18-sprint-8b-tier1-rendering.md`](./superpowers/plans/2026-04-18-sprint-8b-tier1-rendering.md)
> **브랜치:** `feat/sprint8b-tier1-rendering`. 10 tasks TDD × commit 단위로 완수.

- [x] **Tier-1 가상 strategy 래퍼 (Task 1–5)** — indicator+alertcondition → 자동 매매 경로
  - [x] `AlertHook.condition_ast` 필드 (alertcondition arg0 또는 enclosing if.test AST 보존)
  - [x] `SignalKind → VirtualAction` 매핑 테이블 (LONG/SHORT_ENTRY/EXIT 4종)
  - [x] `VirtualStrategyWrapper` edge-trigger(False→True) strategy.entry/close 디스패치
  - [x] `discrepancy=True` alert은 경고 기록 후 condition_signal 우선
  - [x] Pine v4 legacy alias (atr/ema/sma/rsi/crossover/… → ta._) + iff + math._ 확장
  - [x] i1_utbot.pine E2E 완주 (Tier-1 핵심 파일럿)
- [x] **Tier-0 렌더링 scope A (Task 6–7, 9)** — 좌표 저장 + getter만 (ADR-011 §2.0.4)
  - [x] `RenderingRegistry` + LineObject/BoxObject/LabelObject/TableObject
  - [x] `line.get_price(x)` 선형보간 + box.get_top/get_bottom + label.set_xy + table.cell
  - [x] Interpreter dispatcher (factory + handle.method 호출 모두 경유)
  - [x] Pine enum 상수 40+ (line.style\__/extend._/shape._/location._/size._/position._)
  - [x] i2_luxalgo.pine E2E 완주 — var line.new + set_xy1/xy2 + switch
- [x] **추가 stdlib (Task 8)** — switch statement + ta.stdev / ta.variance / math.abs
- [x] **산출물**
  - **209 pine_v2 tests** (기존 169 → +40 신규), **backend 전체 735 green**, ruff/mypy clean
  - 6 corpus 매트릭스 **2/6 → 6/6** (s1_pbr + s2_utbot + s3_rsid + i1_utbot + i2_luxalgo + i3_drfx)
    - s1/i1/i2: strict=True 완주 + 매매 생성 검증 (Tier-1 래퍼 또는 네이티브 strategy)
    - s2: strict=True 완주 + v4 strategy.entry(boolean direction, when=) + time/timestamp stub
    - s3/i3: strict=False 완주 (user function/request.security/valuewhen 등 H2+ 이연은 errors로 수집 후 skip)
  - H1 MVP scope 엄수 — trail_points/qty_percent/pyramiding 여전히 H2+ 이연

- [x] **다음 블록 (Sprint 8b 후속 또는 8c)**:
  - [x] user-defined function(=>) 지원 — Sprint 8c ✅ 완료 (2026-04-19, PR #22)
  - [x] 3-Track 라우터 (S/A/M 분류기) — Sprint 8c ✅ 완료 (2026-04-19, PR #22)
  - [x] 사용자 1질문 UX (TabParse 확장) — Sprint FE-01 ✅ 완료 (2026-04-19, PR #23)
  - [ ] `strategy.exit trail_points/trail_offset` (Horizon H2+, pine_v2 H2 심화 sprint)
  - [ ] 분할 익절 + 피라미딩 (Horizon H2+, pine_v2 H2 심화 sprint)
  - [ ] pine_v2 local history ring + valuewhen cap + user function stdlib state isolation (H2+)

#### Sprint 8c — Tier-2 검증 + Tier-4 Variable Explorer (2주, 06-13~26)

> **변경 (2026-04-23):** 원안 Tier-2 (PyneCore 골든) 는 Phase -1 실측에서 PyneCore CLI 가 PyneSys 상용 API 의존 확인 → **Path β 로 재정의** (3-Layer Parity P-1/2/3). PyneCore transformers/ 이식 기반 P-4 는 Path γ (~3주) 로 이연. 본 섹션의 "Variable Explorer MVP" 도 H2 이후로 재평가.

- [ ] ~~PyneCore 골든 오라클 CI 완성~~ → Path β 3-Layer Parity 로 대체 (ADR-013)
- [ ] ~~TV 수동 간헐 검증 인프라~~ → Path β 완료 후 분기 1회 샘플 10개 로 축소
- [ ] Variable Explorer MVP (Track M 수동 UX) → H2 이후 dogfood 피드백 재평가
  - 변수 탐색기 + Bool 시계열 시각화
  - 매수/매도/청산 수동 매핑
  - 청산 규칙 템플릿 (ATR/R:R/반대신호/커스텀)

### Path β — Documentation-First → Tier-2 Trust Layer CI (2026-04-23 시작)

> **ADR:** [`dev-log/013-trust-layer-ci-design.md`](./dev-log/013-trust-layer-ci-design.md) · **아키텍처:** [`04_architecture/trust-layer-architecture.md`](./04_architecture/trust-layer-architecture.md) · **SLO:** [`01_requirements/trust-layer-requirements.md`](./01_requirements/trust-layer-requirements.md)
> **플랜 파일:** `~/.claude/plans/file-users-woosung-project-agy-project-q-humming-dewdrop.md`

#### Stage 0 — 문서 선행 (진행 중, Day 1~2)

- [x] C1. ADR-010 번호 중복 해소 (010a/010b rename)
- [x] A1. `dev-log/013-trust-layer-ci-design.md` 작성
- [x] A2. `04_architecture/trust-layer-architecture.md` 작성
- [x] A3. `01_requirements/trust-layer-requirements.md` 작성
- [x] A4. `guides/dogfood-checklist.md` 작성 (기존 `07_infra/h1-testnet-dogfood-guide.md` 와 역할 분리)
- [x] B1. `dev-log/014-sprint-8b-8c-pine-v2-expansion.md` 회고 작성
- [x] B2. `dev-log/015-sprint-7d-okx-sessions.md` 회고 작성
- [x] B3. `dev-log/016-sprint-y1-coverage-analyzer.md` 회고 작성
- [x] B4. `dev-log/017-fe-polish-bundle-1-2-retro.md` 회고 작성
- [x] C3. `04_architecture/pine-execution-architecture.md` 에 Y1 + 8c 섹션 추가
- [x] C4. TODO.md 동기화 (본 PR)
- [x] C5. LESSON-004/005/006 → `.ai/stacks/nextjs/frontend.md` 승격
- [x] B5. `superpowers/reports/2026-04-23-documentation-audit.md` 회고 작성
- [x] Gate-0. **codex + opus 2중 blind evaluator PASS** (codex 8/10, opus 8.5/10, blocker 0) — 2026-04-23 완료

#### Stage 1 — Design (Day 3, Gate-0 통과 후)

- [ ] `backend/tests/strategy/pine_v2/test_trust_layer_parity.py` 스켈레톤
- [ ] `backend/tests/fixtures/pine_corpus_v2/baseline_metrics.json` 스키마
- [ ] Day 3 오픈 질문 결정: evaluator 병렬/직렬, mutation CI 포함 여부, baseline 포맷
- [ ] Gate-1: codex + opus 2중 blind 검증 (G1-A~E)

#### Stage 2a — Data-independent (commit `060725d`, PR #65 base) ✅ 완료 (2026-04-23)

- [x] `_tolerance.py` 실 구현 (4 public func + Decimal precision guard)
- [x] P-1 AST Shape edge_digest (`test_pynescript_baseline_parity.py` 확장, 12/12)
- [x] P-2 Coverage SSOT Sync (양방향 strict equality + 3 union consistency, 4/4)
- [x] `generate_corpus_ohlcv_frozen.py` + `regen_trust_layer_baseline.py` (--confirm gate)
- [x] CI `--durations=10` 모니터링 + `ruff.toml` per-file-ignores (RUF001-003)

#### Stage 2b — Execution Golden 실측 (commit `ec532ef`) ✅ 완료 (2026-04-23)

- [x] `corpus_ohlcv_frozen.parquet` 생성 (Bybit BTCUSDT 1h 2024-01~06, 4,368 bars, sha256 `1a99144813...5038`)
- [x] `baseline_metrics.json` 실값 생성 (5 runnable corpus + i3_drfx skip)
- [x] P-3 Execution Golden 실 assertion (6/6 green, 허용 오차 max(0.001 abs, 0.1% rel))
- [x] regen `--confirm` gate test 실 구현 (subprocess, 0.38s)
- [x] ADR-013 §11 Amendment 추가 (Stage 2b 완료 + Stage 2c 이연 명시)
- [x] **Gate-2 CONDITIONAL PASS**: codex 8.5/10 + opus 8/10 (blockers 0)
  - SLO 9개 중 8개 실 달성 (TL-E-1/2/3/4/6/7/8/9)
  - TL-E-5 (Mutation ≥7/8) Stage 2c 이연 — ADR-013 §10.1 Q2 "nightly only" 결정 근거

#### Stage 2c 1차 — Mutation Oracle 4/8 + Gate-2 후속 의무 ✅ 완료 (2026-04-23, PR #66 merge `115292a`)

- [x] **M-1 Mutation Oracle harness (1차)** — 8 mutation 중 M1/M2/M4/M7 4개 **감지 PASS**. in-process monkeypatch 패턴 확립 (`StdlibDispatcher.call` wrap). pine_v2 330 pass / 12 skip. M3/M5/M6/M8 은 2차 이연
- [x] **M-2 metric 범위 assert 추가** — `test_p3_baseline_metric_range_sanity` 5/5 (opus Gate-2 W-OPUS-G2-2)
- [x] **M-3 P-3 corpus 독립성 보강** — s2/i1 Track S/A 교차 + i2 0-trades + sortino/calmar null 문서 정정 (opus Gate-2 W-OPUS-G2-3)
- [x] **M-4 `generated_at` 부분 regen fix** — `--corpus` 모드 envelope 보존 + corpus 별 `updated_at` 분리 (opus Gate-2 W-OPUS-G2-4)
- [x] **Gate-3 1차 CONDITIONAL PASS** — codex 8/10 + opus 8/10. C-1 즉시 해소 (`conftest.py` `--run-mutations` 플래그 + `@pytest.mark.mutation` skip + `.github/workflows/trust-layer-nightly.yml` 18:00 UTC cron 신규)

#### Stage 2c 2차 — Mutation 8/8 + W-2/W-3 ✅ 완료 (2026-04-23, branch `feat/path-beta-stage2c-2nd`)

**Path β 완료 선언 조건 초과 달성** (SLO TL-E-5 ≥ 7/8 → 실질 8/8 green). ADR-013 §11 Amendment 행 기재.
**브랜치**: `feat/path-beta-stage2c-2nd` ← main(`115292a`). PR base=main 직접.
**세션 plan**: `~/.claude/plans/path-lucky-squid.md`. 프로젝트 plan: `docs/superpowers/plans/2026-04-23-stage2c-2nd-plan.md`.

- [x] **T1 M3** `StrategyState.entry` no-op cascade → `num_trades` drop 감지 (c1 `bfdfca4`)
- [x] **T2 M5** `fill_price + 0.005` ABS_TOL drift → `trades_digest` entry_price 필드 변경 감지 (c2 `297b121`)
- [x] **T3 M6** `StrategyState.close` 반환 `trade.pnl × Decimal("1.0001")` amplifier → `metrics.total_return` drift (c3 `005047f`)
- [x] **T4 M8** `VirtualStrategyWrapper.process_bar` duplicate fire → `num_trades` 증가 (Track A, c4 `9a0d70c`)
- [x] **T5 W-2 + W-3** M2 `test_m2_rsi_noise_drift_is_detected` rename + M4 `@pytest.mark.xfail(strict=False)` marker (c5 `cfaffbc`)
- [x] **T6 docs/memory** ADR-013 §11 완료 행 + 본 TODO sync + memory `project_path_beta_stage2c_2nd_complete.md` (진행 중)
- [ ] **Gate-4 2중 blind** — codex + opus 병렬 review pending (PR 생성 후)
- [ ] Stage 2c 완료 후 requirements.md §4.1 에 "Mutation 측정 불가 = scope-reducing" 명시화 (codex Gate-2 W-2)

**검증 실측**:

- Mutation suite: **7 passed + 1 xpassed** (M4 XPASS = 현 corpus 에서 drift 포착) = **실질 8/8 감지**, 2:31
- Backend full regression: **985 passed / 17 skipped / 0 failed**, 2:34 (mutation 외 0 regression)

#### Stage 2 — 관찰 후보 (Warning 수준, 차기 sprint 검토)

- [ ] codex Gate-2 W-3: P-3 중복 실행 (`run_backtest_v2` + `parse_and_run_v2`) → 엔진 API 통합 후 1회 호출로 축소
- [ ] opus Gate-2 W-OPUS-G2-5: CI 시간 선형 증가 대비 subset marker (`@pytest.mark.trust_layer_full`) 도입 시점

#### Dogfood (A 트랙) — Stage 2 중 병행

- [ ] Bybit testnet s1_pbr + s2_utbot 자동 집행 2주
- [ ] OKX testnet i2_luxalgo (PR #28 merge 후)
- [ ] 일일 체크리스트 (`docs/guides/dogfood-checklist.md`)
- [ ] Week 1 / Week 2 요약 (`dev-log/dogfood-week1-path-beta.md`, `dogfood-week2-path-beta.md`)
- [ ] 성공 기준: D-A 오작동 0 / D-B ≥95% / D-C sharpe 편차 <5% / D-D UX ticket 화

### Path γ/δ 후보 (Path β 완료 후)

- [ ] **Path γ — PyneCore transformers 이식** (~3주)
  - `persistent.py` / `series.py` / `security.py` / `nabool.py` 참조 이식
  - Apache 2.0 NOTICE + 원본 헤더 유지
  - `test_pynecore_reference_oracle.py` 추가 → ADR-013 amend "P-1/2/3/4 Full Tier-2"
- [ ] **Path δ — Bulk stdlib top-N** (1~2주, dogfood 피드백 기반)
  - TV 15~20 corpus 프로파일링 후 우선순위 top-N 함수 (fixnan, ta.supertrend, ta.cci, ta.mfi, ta.willr, array.from, ta.tostring 등)
  - Path β Tier-2 CI 안전망 활용
- [ ] **Coverage Analyzer AST 기반 정밀화** (Y1 follow-up, 2~3일)
  - regex → pynescript AST visitor
  - false positive/negative ↓

### LLM 활용 후보 (Trust Layer 외 UX 개선, Path β 완료 후)

> **원칙:** Trust Layer (정확성 게이트) 에는 LLM 불포함. UX 레이어에서만 활용.

- [ ] **L-1. Pine 소스 자연어 요약** (Sprint Y2 후보, ★★★★☆)
  - 전략 등록 시 자동 한국어 설명 박스 (`/strategies/{id}/explain`)
  - Read-only. 잘못돼도 백테스트/거래 영향 없음
- [ ] **L-2. Backtest 결과 해석** (Sprint Y2 후보, ★★★★☆)
  - "Sharpe 1.2 + DD 15% = 중상위권" 자연어 서술
  - FE MVP 1일 추정
- [ ] **L-3. Unused 변수/함수 프루닝 제안** (★★☆☆☆, 위험 중)
  - 의미 변경 위험. Path β Gate-2 G2-C (mutation ≥7/8) 증명 후 재검토

#### Sprint 8d — Tier-5 LLM 하이브리드 + 베타 오픈 (2주, 06-27~07-10)

- [ ] LLM 하이브리드 (Amazon Oxidizer Rule+LLM 패턴)
  - 파서 에러 자연어 수정 제안
  - 비표준 Pine → 지원 Pine 재작성 (사용자 승인 후)
  - 미지원 stdlib 초안 생성 + 골든 테스트 승격 파이프라인
- [ ] MTF 지원 (`request.security` / `security_lower_tf`)
- [ ] ToS 법적 방어 조항 추가 (invite-only DMCA, 라이선스 승계)
- [ ] 첫 베타 10명 온보딩 준비

#### Sprint 8 공통 — 기피 전략 (명시적 거부)

- ❌ PyneTS 포팅/참조 (AGPL SaaS 조항 차단)
- ❌ PyneSys SaaS 영구 구독 (vendor lock-in + 아키텍처 불일치)
- ❌ LLM 원샷 번역 주경로 (2.1~47.3% 정확도)
- ❌ 자체 ANTLR Pine v6 6~12개월 포팅 (pynescript 1~2주 포크로 대체)
- ❌ 바이트코드 VM / LLVM / MLIR / WASM (과대투자)
- ❌ 렌더링 완전 구현 (범위 B — 백테스트 무관)
- ❌ TV 헤드리스 스크래핑 (ToS 회색지대)

## Blocked

- [x] ~~Sprint 7d vs Sprint 8a-pre 우선순위~~ — 2026-04-18~19에 8a-pre → 8a → 8b → 8c → 7d 순으로 모두 해소 ✅
- [x] ~~PyneCore `strategy.exit trail_points` 지원 여부~~ — Phase -1 Day 1-2 실측 완료 (Sprint 8a-pre, PR #18) ✅
- [ ] **Pine 해석이 QB 진짜 차별점인가?** — H2 진입 전 외부 유저 5명 인터뷰 필요 (H1 Stealth에선 본인 dogfood로 진행, Step 5에서 재검토)
- [ ] **본인 Bybit Futures 실자본 1~2주 dogfood** — H1 Stealth 종료 조건. Kill Switch capital_base(Step 3) + mainnet runbook(Step 4) 완료 후 사용자 수동 실행

## H1 Stealth 종료 대기 작업 (Horizon 전환 gate)

> H1 → H2 진입 전 해소해야 할 최종 게이트. 2026-04-20 현재 세션에서 Step 3/4 착수.

- [ ] **P0: Kill Switch `capital_base` 동적 바인딩 + leverage cap 검증** (현재 세션 Step 3, 4~5h)
  - Bybit Futures balance endpoint → periodic refresh (30s)
  - leverage × capital 초과 시 hard-reject
  - pytest + PR
- [ ] **P0: Bybit mainnet dogfood 준비** (현재 세션 Step 4, 3~4h)
  - `docs/07_infra/runbook.md` 확장 (mainnet 절차, API key 로테이션, emergency kill)
  - `docs/07_infra/bybit-mainnet-checklist.md` (신규, IP whitelist/출금 권한/레버리지 1:1/소액)
  - `scripts/bybit-smoke.sh` 소액 dry-run 스크립트
- [ ] **P0: 본인 실자본 1~2주 dogfood** (사용자 수동) — H1 종료 확정 조건
- [ ] **P1: autonomous-parallel-sprints 스킬 patch (BUG-1/2/3 → LESSON-007/008/009 반영)**
  - 스킬 repo: `~/.claude/skills/autonomous-parallel-sprints/`
  - BUG-1 kickoff-worker.sh symlink → `--git-common-dir` 기반 교체
  - BUG-2 Planner SIG_ID full-id 강제
  - BUG-3 Worker plan 저장 경로 worktree-only 강제
- [ ] **P2: H2 진입 게이트 설계** (현재 세션 Step 5, 3~5h) — `/office-hours` Q4 narrowest wedge, Monte Carlo/Walk-Forward 우선순위, Beta 5~10명 온보딩 기준

_(기존 Blocked 항목 없음 유지)_

## Next Actions (P0~P7 후속)

- [ ] **P4 (zod 경로 정정):** `.ai/stacks/nextjs-shared.md §2`의 `import { z } from "zod/v4"` 규칙은 zod@4 미설치 시점의 transition 문구. zod@4.3.6 기준 `"zod"`가 곧 v4 → 규칙을 `import { z } from "zod"`로 완화 필요. (`.ai/`는 gitignored라 원본 repo에서 처리) [확인 필요]
- [ ] `.uuid()` → `z.uuid()` 전수 migration (strategy/trading 완료, 나머지 전수검사 필요)
- [ ] 나머지 대시보드 라우트(`/strategies/[id]/edit`, `/strategies/new`)에도 `loading.tsx`+`error.tsx` 라우트 규약 적용
- [ ] `strategy-list.tsx` 수동 `isLoading`/`isError` 분기 → `useSuspenseQuery`로 최종 전환 (현재는 route-level boundary로 1차 해소)
- [ ] 기타 `"use client"` 27개 중 presentational 컴포넌트 서버 컴포넌트화 (`strategy-card`, `strategy-table` 후보) — React Query hook chain 재설계 필요
- [ ] 사용자 수동 조치: `kill <dev-pid>` + `rm -rf frontend/.next frontend/tsconfig.tsbuildinfo` → `pnpm dev` 재시작 → idle CPU <20% 검증 (ADR-010 budget 대조)

## Questions

- [ ] DB 호스팅: Self-hosted vs Neon vs Fly Postgres vs TimescaleDB Cloud — TimescaleDB 필수. 상세 비교는 [`07_infra/deployment-plan.md`](./07_infra/deployment-plan.md) §4
- [ ] 배포 전략: Vercel+Cloud Run vs K8s vs Fly.io — 상세 비교는 [`07_infra/deployment-plan.md`](./07_infra/deployment-plan.md) §2
- [ ] Socket.IO vs 순수 FastAPI WebSocket — 실시간 데이터 전송 방식 결정 필요 (Sprint 7+)

### Stage 2: 디자인 ✅ 완료 (Tier 1 Phase 1 MVP 커버)

- [x] DESIGN.md 작성 (디자인 시스템 + App Shell 패턴 §10)
- [x] 00-landing.html (랜딩 페이지, 플로팅 다크 쇼케이스)
- [x] 01-strategy-editor.html (전략 편집, Monaco 스타일)
- [x] 02-backtest-report.html (백테스트 결과 리포트)
- [x] 03-trading-dashboard.html (트레이딩 대시보드, Full Dark)
- [x] 04-login.html (로그인/가입, Split-screen)
- [x] 05-onboarding.html (4단계 온보딩 위저드)
- [x] 06-strategies-list.html (전략 목록, 카드 그리드)
- [x] 07-strategy-create.html (전략 생성 3-step 위저드)
- [x] 08-backtest-setup.html (백테스트 설정 폼)
- [x] 09-backtests-list.html (백테스트 목록 테이블)
- [x] 10-trades-detail.html (거래 내역 상세)
- [x] 11-error-pages.html (404/500/503)

**Tier 2~3 (Phase 2~4 + 공통):** 필요 시 추가 진행 (PRD 확정 후 권장)

## Completed

- [x] ADR-005 작성 — DateTime tz-aware + AwareDateTime TypeDecorator (Sprint 5 Stage B M1, 2026-04-16)
- [x] ADR-003 작성 — Pine 런타임 안전성 + 파서 범위 (/autoplan 인사이트 증류)
- [x] /autoplan 인사이트 증류 — CLAUDE.md 보안 규칙 2개 + lessons.md LESSON-001/002/003
- [x] Stage 2 완료 — DESIGN.md + 12개 프로토타입 (docs/prototypes/)
- [x] DESIGN.md 확정 — 8개 디자인 변형 비교, 실제 렌더링 검증, Final 91.0점
- [x] PRD 초안 작성 (QUANTBRIDGE_PRD.md)
- [x] .ai/ 규칙 셋업 (ai-rules 클론)
- [x] AGENTS.md 커스터마이징
- [x] PRD vs .ai/ spec 차이 분석 완료
- [x] 개발 워크플로우 정의 (6-Stage Methodology)
- [x] docs/dev-log/001-tech-stack.md (ADR-001) 작성
- [x] docs/04_architecture/erd.md (DB 스키마) 작성
- [x] docs/03_api/endpoints.md (API 명세) 작성
- [x] .env.example 작성
- [x] docs/guides/development-methodology.md 작성
- [x] docs/dev-log/002-parallel-scaffold-strategy.md (ADR-002) 작성
