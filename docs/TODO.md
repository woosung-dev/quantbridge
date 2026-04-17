# QuantBridge — TODO

> 사람과 AI가 공동 관리하는 작업 추적 파일.
> 차단 항목은 `[blocked]` 표시, 질문은 Questions 섹션에 기록.

> **📍 제품 로드맵:** [`docs/00_project/roadmap.md`](./00_project/roadmap.md) (Horizon × Pillars)
> **📍 현재 Horizon:** H1 (0–1.5m, Stealth, 본인 dogfood). 순서: **Sprint 7c → 7b → 8a → 8b → dogfood 1~2주**. 외부 공개 없음. Build in public 주 1회.

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
- [x] .env.example POSTGRES_* 정렬 (docker-compose SSOT)

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

- [ ] Chip-style tag input (type + Enter + Backspace 제거) — 현재 comma-split. 파워 유저 마찰. Context: plan P7-6, 2~4시간
- [ ] Coachmark tour — first-visit edit 페이지의 ⌘+S/Enter 단축키 1회성 overlay. Context: plan Persona C storyboard
- [ ] Save conflict OCC — 백엔드 ETag 또는 `If-Unmodified-Since` header 도입 후 FE에서 409 Conflict 분기. Context: plan P7-10, 스키마 변경 필요
- [ ] Bottom sheet dialog (mobile <768px) — DeleteDialog가 thumb-reach 위해 하단 시트로 전환. Context: plan P6 Responsive
- [ ] Monaco Pine autocomplete — Pine v5 builtin 함수 자동완성 등록. Context: plan P7-7, full grammar 선행 필요
- [ ] Full Pine TextMate grammar — 현재 5색 Monarch → 전체 keyword + builtin + operator 완전 grammar. 3~5일. Context: plan P7-7
- [ ] Keyboard shortcut help dialog (? key) — 전역 단축키 목록 모달. Context: plan P6 a11y §2
- [ ] localStorage draft user_id scoping — Clerk session 만료 시 draft auto-clear + user_id key prefix. Context: plan P7-9

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
- **다음 (결정 대기):** Sprint 7d vs Sprint 8a-pre 우선순위 — [ADR-011](./dev-log/011-pine-execution-strategy-v4.md) 참조
  - **A (Claude 추천):** Sprint 8a-pre 먼저 — Pine 실행 전략 v4(Alert Hook Parser + 3-Track) 실측 착수. 본인 dogfood 루프 핵심
  - **B:** Sprint 7d 먼저 — OKX 멀티 거래소 + Trading Sessions (기존 맥락 유지)
- Sprint 8+ — Binance mainnet 실거래 + Kill Switch capital_base 동적 바인딩

### Sprint 7 Next Actions

- [x] Strategy CRUD UI (목록/생성 3-step/편집 3탭 + delete 409 archive fallback) — Sprint 7c ✅ 완료 (2026-04-17)
- [x] 실 CCXT 거래소 연동 (Bybit testnet Futures + Cross Margin) — Sprint 7a ✅ 완료 (2026-04-17)
- [x] `bybit_futures_max_leverage` config 값이 `OrderService.execute`에서 enforce (422 `LeverageCapExceeded`) — Sprint 7a 리뷰 합의로 완료 (2026-04-17)
- [ ] Bybit testnet Live smoke test (실 API key로 수동 주문 1건) — 사용자 테스트 대기
- [ ] Trading Sessions 도메인 확장 (세션 생성/시작/중지/kill) — Sprint 7d+
- [ ] OKX 멀티 거래소 추가 — Sprint 7d
- [x] Edit 페이지 Pine 이터레이션 UX 풍부화 (ISSUE-003 + ISSUE-004) — Sprint 7b ✅ 완료 (2026-04-17)
- [ ] Kill Switch `capital_base` 동적 바인딩 (`ExchangeAccount.fetch_balance()`) — Sprint 8+
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

#### Sprint 8a-pre — Phase -1 실측 (2주, 2026-04-18~05-01 예정)

> **목표:** v4 아키텍처 가정 실증. 실측 결과에 따라 ADR-011 amendment 가능.

- [ ] Day 1-2: PyneCore 로컬 설치 + RTB/DrFX/LuxAlgo 3종 E2E 실행
  - `strategy.exit trail_points/trail_offset` 실제 지원 여부 확인 (RTB 필수)
  - 렌더링 객체(box.get_top 등) 재참조 동작 확인
  - 실행 속도 측정 (8760 봉 기준)
- [ ] Day 3: LLM 변환 Python vs PyneCore vs TV 3-way 비교
  - 신호 배열 bar-by-bar 상대 오차 측정
  - LLM 변환 버그 3개(SL 기준점/부동소수점 ==/look-ahead) 실제 영향 수치화
  - KPI 검증: "상대 오차 <0.1% MVP" 현실성
- [ ] Day 4-5: TV 공개 스크립트 15~20개 alert 패턴 프로파일링
  - pynescript AST로 alert/alertcondition 호출 추출
  - 메시지 포맷 분류 (JSON/키워드/자유 텍스트/한국어)
  - Track S/A/M 실제 비율 확정 (20-30%/40-50%/20-30% 가정 검증)
- [ ] Day 6-7: Phase -1 findings 리포트 작성
  - `.gstack/experiments/phase-minus-1-drfx/README.md`
  - ADR-011 amendment (필요 시)
- [ ] Day 8-10: Tier-0 공통 코어 착수
  - pynescript(LGPL) 포크 → QB 파서 이식 시작

#### Sprint 8a — Tier-0 공통 코어 (3주, 05-02~22 예정)

- [ ] pynescript 포크 완료 + QB `backend/src/strategy/pine/parser.py` 대체
- [ ] AST 노드 확장: 배열 리터럴, switch, method-call, Matrix/Map/UDT, 4단계 타입 수식어
- [ ] PyneCore var/varip/rollback 런타임 이식 (Apache 2.0, NOTICE 의무)
- [ ] bar-by-bar 이벤트 루프 백테스터 (vectorbt는 지표 계산 전용으로 격리)
- [ ] 렌더링 객체 런타임 범위 A (box/label/line 좌표 저장 + getter, 차트 렌더 NOP)
- [ ] PyneCore 골든 CI 하네스 구축 (상대 오차 <0.1% MVP)
- [ ] 완료 기준: DrFX/LuxAlgo 런타임 오류 없이 완주 + PyneCore 대비 10% 이내 오차

#### Sprint 8b — Tier-1 Alert Hook Parser + Tier-3 strategy() (3주, 05-23~06-12)

- [ ] Alert Hook Parser 구현
  - AST에서 `alert()`/`alertcondition()` 호출 자동 수집
  - 메시지 분류기 (JSON → 키워드 → fallback)
  - 조건식 역추적 (시그널 변수 → 정의)
- [ ] 가상 strategy() 래퍼 자동 생성기
- [ ] 사용자 1질문 UX (Sprint 7b에서 만든 TabParse 확장)
  - "추출된 매매 로직" 섹션 추가
  - 정보성 alert 구분 (사용자 확인)
- [ ] 3-Track 라우터 (S/A/M 분류기)
- [ ] `strategy.entry/exit/close/cancel` 네이티브 구현
- [ ] `strategy.exit trail_points/trail_offset` 구현 (RTB/LuxAlgo 필수, 3~5일)
- [ ] 분할 익절 (multiple `limit=` 지원)
- [ ] 피라미딩 지원

#### Sprint 8c — Tier-2 검증 + Tier-4 Variable Explorer (2주, 06-13~26)

- [ ] PyneCore 골든 오라클 CI 완성 (상대 오차 <0.01% v1.0 달성)
- [ ] TV 수동 간헐 검증 인프라 (샘플 10개, 분기 1회)
- [ ] Variable Explorer MVP (Track M 수동 UX)
  - 변수 탐색기 + Bool 시계열 시각화
  - 매수/매도/청산 수동 매핑
  - 청산 규칙 템플릿 (ATR/R:R/반대신호/커스텀)

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

- [ ] **Sprint 7d vs Sprint 8a-pre 우선순위** — 사용자 결정 필요 (**blocker**)
  - Claude 추천: **Sprint 8a-pre 먼저** (본인 dogfood 루프에 Pine이 핵심, DrFX 실측으로 Phase -1 1/3 이미 완료)
- [ ] **PyneCore `strategy.exit trail_points` 지원 여부** — Phase -1 Day 1-2에서 검증
- [ ] **Pine 해석이 QB 진짜 차별점인가?** — H2 진입 전 외부 유저 5명 인터뷰 필요 (H1 Stealth에선 본인 dogfood로 진행)

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
