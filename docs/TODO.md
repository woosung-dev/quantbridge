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
- **다음:** Sprint 7 — 실거래소 연동 + Trading Sessions 확장

### Sprint 7 Next Actions

- [x] 실 CCXT 거래소 연동 (Bybit testnet Futures + Cross Margin) — Sprint 7a ✅ 완료 (2026-04-17)
- [x] `bybit_futures_max_leverage` config 값이 `OrderService.execute`에서 enforce (422 `LeverageCapExceeded`) — Sprint 7a 리뷰 합의로 완료 (2026-04-17)
- [ ] Bybit testnet Live smoke test (실 API key로 수동 주문 1건) — 사용자 테스트 대기
- [ ] Trading Sessions 도메인 확장 (세션 생성/시작/중지/kill) — Sprint 7b+
- [ ] OKX 멀티 거래소 추가 — Sprint 7b
- [ ] Kill Switch `capital_base` 동적 바인딩 (`ExchangeAccount.fetch_balance()`) — Sprint 8+
- [ ] WebSocket 실시간 주문 상태 스트리밍
- [ ] CSO-5: Frontend dev CVEs 해소
- [ ] Rate limiting middleware (per-user, per-endpoint)
- [ ] Prometheus/Grafana 계측 (CCXT 호출 + 주문 처리 latency)
- [ ] Bybit v5 `set_margin_mode`/`set_leverage` "not modified" error handling (codes 110026, 34036) — Sprint 8+ mainnet 준비 (BybitFuturesProvider 반복 주문 시 legitimate error를 idempotent no-op로 처리)
- [ ] `trading.orders.margin_mode` DB-level `CHECK (margin_mode IN ('cross','isolated') OR margin_mode IS NULL)` — Sprint 8+ mainnet 전, DB-string↔DTO-Literal 경계 불변식 하드닝 (ADR-007 §구현 노트 참조)

## Blocked

_(없음)_

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
