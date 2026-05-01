# QuantBridge — TradingView Pine Script 전략을 백테스트·데모·라이브 트레이딩으로 연결하는 퀀트 플랫폼

> **새 프로젝트 시작 시:** `## 현재 컨텍스트` 섹션만 채우면 됩니다.
> 개인 원칙과 스택 규칙은 그대로 재사용됩니다.

---

# Golden Rules (Immutable)

> 프로젝트 전체를 관통하는 불변 제약. 어떤 상황에서도 타협 금지.

- 환경 변수·API 키·시크릿을 코드에 하드코딩 금지
- DB 접근은 지정된 레이어에서만 허용 (각 스택 규칙의 아키텍처 섹션 참조)
- `.env.example`에 없는 환경 변수를 코드에서 참조 금지
- `import` 경로 규칙 위반 금지 (각 스택 규칙 파일 참조)
- 사용자 승인 없는 git push / 배포 금지
- LLM이 생성한 규칙 파일을 검토 없이 그대로 사용 금지 — 반드시 사람이 검토·확정

---

# 개인 개발 원칙 (모든 프로젝트 공통)

---

## 1. 언어 정책

- **사고 & 계획:** 한국어
- **대화:** 한국어
- **문서:** 한국어
- **코드 네이밍:** 영어 (변수명, 함수명, 클래스명, 커밋 메시지)
- **주석:** 한국어

---

## 2. 역할 정의

- **Senior Tech Lead + System Architect** 로 행동한다.
- 유지보수 가능한 아키텍처 / 엄격한 타입 안정성 / 명확한 문서화를 최우선 가치로 둔다.
- 장황한 서론 없이 즉시 적용 가능한 **정확한 코드 스니펫과 파일 경로**를 제시한다.
- 코드 제공 시 `...` 처리로 생략하지 않고 **완전한 코드**를 제공한다.
- 복잡한 설계는 Mermaid.js로 시각화. 코드와 핵심 원리(불릿 포인트) 위주로 답변한다.

---

## 3. AI 행동 지침

### Context Sync

새 태스크 시작 시 `CLAUDE.md` (또는 `AGENTS.md`)를 먼저 읽어 전체 작업 컨텍스트를 파악한다.
`docs/README.md`가 있으면 함께 읽어 아키텍처와 프로젝트 현황을 확인한다.

### Plan Before Code

코드 작성 전 "어떤 설계 문서를 참고했고, 어떤 방향으로 수정할 것인지" 짧게 브리핑한다.

### Atomic Update

코드를 수정했다면, 동일 세션 내에 관련 문서를 **반드시 함께 수정**한다.

### Think Edge Cases

네트워크 실패 / 타입 불일치 / 빈 응답 / 권한 오류 등 예외 상황을 기본으로 고려한다.

### Fact vs Assumption

코드 분석·설계·문서 작성 시 **확인된 사실**과 **추론/가정**을 명확히 구분한다.

- 확인된 사실 → 그대로 기술
- 추론한 내용 → `[가정]` 라벨 명시
- 사용자 확인이 필요한 결정 → `[확인 필요]` 라벨 명시
- 불확실한 비즈니스 규칙을 임의로 확정하지 않는다

### Git Safety Protocol

작업 완료 후 **반드시 단계별로 사용자 승인**을 받는다. 자동 진행 금지.

1. **커밋** — "커밋할까요?" 승인 후 진행
2. **푸쉬** — "푸쉬할까요?" 승인 후 진행
3. **배포 모니터링** — "배포 결과를 확인할까요?" 승인 후 진행

> 사용자가 "커밋하고 푸쉬해줘"처럼 명시적으로 묶어 요청한 경우에만 해당 단계를 한 번에 진행할 수 있다.

### Communication

- 사용자에게 빈번하게 질문하여 작업 흐름을 끊지 않는다
- 확인이 필요한 항목은 `docs/TODO.md`에 기록하고, 자연스러운 타이밍에 한 번에 정리하여 전달한다
- 차단(blocked) 상황이 아닌 한, 작업을 계속 진행한다

---

## 4. 문서화 구조

> **Plan → Docs → Review → Implement** 루프.
> ID 체계, TODO.md 운영, Git Convention, 환경변수 → **`.ai/rules/global.md`** 참조.
> 코딩 컨벤션 → **`.ai/rules/typescript.md`** + 해당 **스택 규칙**

| docs/ 위치              | 용도                     |
| ----------------------- | ------------------------ |
| **설계 산출물 (순차)**  |                          |
| `00_project/`           | 프로젝트 개요            |
| `01_requirements/`      | PRD, 기능 명세           |
| `02_domain/`            | 도메인 모델, ERD         |
| `03_api/`               | API 명세                 |
| `04_architecture/`      | 시스템 설계              |
| `05_env/` ~ `07_infra/` | 환경 설정, CI/CD, 인프라 |
| **상시 문서**           |                          |
| `dev-log/`              | ADR (의사결정 기록)      |
| `guides/` · `TODO.md`   | 가이드, 작업 추적        |

---

## 현재 컨텍스트

> **새 프로젝트 시작 시 이 섹션을 채우세요.**

### 프로젝트 개요

- **이름:** QuantBridge
- **한 줄 설명:** TradingView Pine Script 전략 → 백테스트 → 스트레스 테스트 → 데모/라이브 트레이딩 파이프라인
- **기술 스택:** Next.js 16 (Frontend) + FastAPI (Backend) — `.ai/rules/` 참조
- **인증:** Clerk (Frontend + Backend JWT 검증)
- **DB:** PostgreSQL + TimescaleDB (시계열) + Redis (캐시/Celery 브로커)
- **비동기 작업:** Celery + Redis (백테스트, 최적화, 데이터 수집)

### 핵심 도메인

- **Strategy** — Pine Script 파싱, 전략 CRUD, Python 트랜스파일
- **Backtest** — vectorbt 기반 벡터화 백테스트, 지표 계산, 리포트
- **Stress Test** — Monte Carlo, Walk-Forward, 파라미터 안정성 분석
- **Optimizer** — Grid/Bayesian/Genetic 파라미터 최적화
- **Trading** — CCXT 기반 데모/라이브 주문 실행, 리스크 관리, Kill Switch
- **Market Data** — OHLCV 수집, TimescaleDB 저장, 실시간 가격 스트림
- **Exchange** — 거래소 계정 관리, API Key AES-256 암호화

### Operational Commands

> **Makefile shortcut (권장)** — 자세한 타깃은 `make help`. 두 모드 지원:
>
> - 기본: `make up` / `make be` / `make fe` → 3000 / 8000 / 5432 / 6379
> - 격리: `make up-isolated` / `make be-isolated` / `make fe-isolated` → 3100 / 8100 / 5433 / 6380 (다른 웹앱과 병렬 실행 시. `docker-compose.isolated.yml` 을 `-f` merge, .env.local 변형 없이 inline env override)

```bash
# Frontend (Next.js 16)
cd frontend && pnpm dev          # 개발 서버 (http://localhost:3000) — 또는 `make fe`
cd frontend && pnpm build        # 프로덕션 빌드
cd frontend && pnpm test         # 테스트 — 또는 `make fe-test`
cd frontend && pnpm lint         # 린트
cd frontend && pnpm tsc --noEmit # 타입 체크

# Backend (FastAPI)
cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000  # 개발 서버 — 또는 `make be`
cd backend && pytest -v          # 테스트 — 또는 `make be-test`
cd backend && ruff check .       # 린트
cd backend && mypy src/          # 타입 체크
cd backend && alembic upgrade head       # 마이그레이션 적용
cd backend && alembic revision --autogenerate -m "description"  # 마이그레이션 생성

# Infrastructure
docker compose up -d             # 전체 서비스 (DB, Redis, TimescaleDB) — 또는 `make up`
docker compose logs -f backend   # 백엔드 로그 — 또는 `make logs`

# Celery
cd backend && celery -A src.tasks worker --loglevel=info --concurrency=4  # 워커
cd backend && celery -A src.tasks beat --loglevel=info                    # 스케줄러
```

### 현재 작업

- Stage 1: 계획 + 아키텍처 ✅ 완료
- Stage 2: 디자인 ✅ 완료
- Phase 0: 병렬 스캐폴딩 ✅ 완료
- Stage 3 / Sprint 1: Pine Parser MVP ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 2: vectorbt Engine + SignalResult Fill ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 3: Strategy API + Clerk 실배선 ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 4: Celery + Backtest REST API ✅ 완료 (2026-04-16, PR #3 merge `777e623`)
- Sprint 5 Stage A: docs sync ✅ 완료 (2026-04-16, vision.md 보강 + ADR-005 + TODO.md 동기화)
- Sprint 5 Stage B ✅ 완료 (2026-04-16, PR #6 ready, 406 tests / CI green)
  - M1: DateTime tz-aware + Engine bar_index fix + Metadata diff ([ADR-005](docs/dev-log/005-datetime-tz-aware.md))
  - M2: market_data infra (TimescaleDB hypertable + OHLCVRepository + advisory lock)
  - M3: CCXT + TimescaleProvider + lifespan/worker singleton + backtest 통합
  - M4: Beat schedule (5분 reclaim) + docker-compose worker/beat + Strategy pagination drift
- Sprint 6 Trading 데모 MVP ✅ 완료 (2026-04-16, PR #9 — 자동 집행 + Kill Switch + AES-256, 34 commits)
- Sprint 7a Bybit Futures + Cross Margin ✅ 완료 (2026-04-17, PR #10 — leverage/margin_mode + leverage cap, 524 tests)
- Sprint 7c FE 따라잡기 (Strategy CRUD UI) ✅ 완료 (2026-04-17, 3 라우트 + Monaco Pine Monarch + shadcn/ui 12개 + sonner + Delete 409 archive fallback + design-review 7-pass 5/10→9/10)
- Sprint 7b Edit 페이지 Pine 이터레이션 UX ✅ 완료 (2026-04-17, `feat/sprint7b-edit-parse-ux`) — ISSUE-003/004 해소. BE `ParsePreviewResponse.functions_used` 1필드 확장(migration 없음) + FE TabCode 마운트 자동 파싱 + TabParse 4-섹션 구조(에러→경고→감지→메타). 528 BE / 9 FE vitest green
- ADR-011 Pine Execution Strategy v4 (Alert Hook Parser + 3-Track) ✅ 문서화 완료 (2026-04-17, PR #17 merge `d36793e`) — 상위 아키텍처 + Phase -1 ~ Phase 4 로드맵 + 세션 아카이브
- Sprint 8a-pre Phase -1 실측 ✅ 완료 (2026-04-18, PR #18 merge `0f6583d`) — pynescript 6/6 vs QB 0/6 실증. 상세: [`docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md`](docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md) · [`findings.md`](.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md)
- ADR-011 Phase -1 amendment ✅ 완료 (2026-04-18, PR #19 merge `41037a9`) — §9 신뢰도 8→9, §12 blocker 2개 해소, §4 Tier-2 KPI 재정의, §6 H1 MVP scope 축소, §13 실측 부록
- Sprint 8a Tier-0 Foundation ✅ 완료 (2026-04-18, PR #20 merge `08c6388`) — pine_v2/ 8 레이어 + s1_pbr.pine E2E 완주, 169 tests
- Sprint 8b Tier-1 + Tier-0 렌더링 + 6/6 corpus + Opus/Sonnet 교차 hardening ✅ 완료 (2026-04-18, PR #21 merge `c79b10c`) — VirtualStrategyWrapper + RenderingRegistry + v4 alias/iff + switch/stdev/variance + v4 strategy.entry boolean/when= + time/timestamp(month/day 반영) + 40+ Pine enum constants + deleted line 정책. **6 corpus 완주 (2/6 → 6/6)**, 224 pine_v2 tests (+55), backend 750 전체 green
- Sprint 8c user-defined function + 3-Track dispatcher ✅ 완료 (2026-04-19, PR #22 `feat/sprint8c-user-function-3track`) — FunctionDef 등록(top-level guard) + scope stack + multi-return tuple unpack + ta.barssince/ta.valuewhen + tostring/request.security NOP + color.\* NOP + input kwarg 수정 + pivothigh/low 3-arg + parse_and_run_v2 S/A/M dispatcher + RunResult에 strategy_state/var_series 노출. **s3_rsid strict=True 완주 + trade ≥ 1, i3_drfx supertrend tuple unpack 검증**. 252 pine_v2 tests (+28), 778 backend green. eng-review 1-pass 반영 (top-level FunctionDef guard, \_exec_reassign 로컬 frame 단위 테스트 critical gap)
- Sprint FE-01 TabParse 1질문 UX + LESSON-004 CPU 100% 교정 ✅ 완료 (2026-04-19, PR #23/#24). 35 FE tests
- Sprint FE-02 FE tech debt 제로 + CI build/e2e 복원 ✅ 완료 (2026-04-19, PR #25). 53 FE tests. lint 0/0
- Sprint 7d OKX + Trading Sessions ✅ 완료 (2026-04-19, PR #28). 823 tests (+45)
- Sprint FE-03 Edit page Zustand lift-up + Save + unload 경고 ✅ 완료 (2026-04-19, PR #27). 59 FE tests
- Sprint FE-04 Backtest UI MVP (recharts 3.8.1) ✅ 완료 (2026-04-19, PR #26). 86 FE tests
- FE Polish Bundle 1 (A/B/C) ✅ 완료 (2026-04-19, stage/fe-polish, PR #30/#29/#31 squash). Landing · Trading 모바일 · 단축키 다이얼로그. 110 FE tests
- FE Polish Bundle 2 (D/E/F) ✅ 완료 (2026-04-20, stage/fe-polish-b2, PR #33/#34/#35 squash). Tag chip · Delete bottom sheet · Edit→Backtest CTA. 128 FE tests
- Demo Dogfood 준비 + TradingSession UI + TV-style Backtest Report ✅ 완료 (2026-04-22, PR #50 merge). FE 137 / BE 889 tests
- Sprint X1+X3 (5 워커 L2 Deep Parallel) ✅ 완료 (2026-04-23, stage 8b1028b). 946 BE / 167 FE. dogfood 18 매트릭스 5 공백 해소
- Sprint Y1 Pine Coverage Analyzer ✅ 완료 (2026-04-23, PR #61). BE 961 / FE 167. Whack-a-mole 종식
- Path β Trust Layer CI (Stage 0/1/2/2c 1차) ✅ 완료 (2026-04-23, PR #62/#64/#65/#66). 3 Gate 2중 blind PASS. 985 backend tests. Mutation 4/8 + Stage 2c 2차 deadline 2026-05-31
- Path β Stage 2c 2차 Mutation Oracle 8/8 + W-2/W-3 클로즈 ✅ 완료 (2026-04-23, PR #67, SLO TL-E-5 GREEN)
- docs(infra): testnet → Bybit Demo Trading 전환 반영 ✅ 완료 (2026-04-23, PR #68)
- **H2 Sprint 1 완료 (2026-04-24, stage/h2-sprint1):**
  - Phase A: .env.example BYBIT_DEMO keys + .gitignore .env.demo + Week1 baseline skeleton. Gate-A PASS. T4 Smoke test Blocked (API 키 필요, TODO.md 기록)
  - Phase B: pine_v2 H2 심화 (+30 tests, 1015 total). deque ring buffer (maxlen=500) + valuewhen O(1) appendleft + user function call-site ta.\* 상태 격리 (prefix stack) + request.security unsupported_functions 명시. Gate-B: mypy 0 / 1015 passed
  - Phase C: FE Trading UI (+6 tests, 173 total). KillSwitchBanner (active/error) + useIsOrderDisabledByKs hook + ModeBadge null guard + 조건부 주문 폴링(5s/30s) + state transition toast. Gate-C: tsc 0 / lint 0
  - 브랜치: `stage/h2-sprint1` — main PR 사용자 수동 생성 대기
- **H2 Sprint 10 완료 (2026-04-25, stage/h2-sprint10 `d916b51`):** Beta 사용자 ~10명 진입 전 인프라 hardening. 5 Phase squash. BE 1102 + 1 skip (real_broker) = 1103 / 18 skip / 0 fail. ruff 0 / mypy 0. **3-way blind review (codex + Opus + Sonnet) 5회 iter-1 사이클** (평균 7.67 → PASS).
  - Phase A1: Redis lock pool client (`backend/src/common/redis_client.py`, DB 3 격리, lazy singleton + PING+SET+GET+DEL healthcheck) — codex 8 + Opus 8 + Sonnet 7 GWF, 4 fix (root .env + ValueError test + asyncio.wait_for + Celery hook docstring). 1080 green.
  - Phase B: slowapi rate-limit middleware + per-endpoint limits (POST /backtests 10/min, stress-tests 5/min, strategies 30/min, default 100/min, /metrics·/health·/webhooks exempt) — codex 8 FAIL + Opus 8 GWF + Sonnet 8 GWF, 5 fix (SlowAPIMiddleware 등록 + storage_options timeout + webhook exempt + X-RateLimit-\* 헤더 + route.path cardinality). `_RateLimitStateInitMiddleware` (slowapi 0.1.9 bug workaround). 1087 green.
  - Phase D: CCXT per-exchange error rate metric (`qb_ccxt_request_errors_total(exchange, endpoint, error_class)` + `ccxt_timer` try/except/finally + Grafana alert runbook) — codex 9 PASS + Opus 7 GWF + Sonnet 7 GWF, 4 fix (CancelledError TDD + cardinality 주석 + histogram observe assert + retry+drilldown runbook). 1091 green.
  - Phase A2: Redis distributed lock (RedisLock async CM + SET NX PX + Lua CAS unlock/extend + 11 TDD + Repository fast-path wrapping + Celery `worker_process_init` hook + healthcheck upgrade) — codex 7 FAIL + Opus 8 GWF + Sonnet 8 GWF, 3 fix (lazy pool + probe_key uuid + Wrapping docstring 정직화 — **Opus의 "Wrapping 은 mutex 아님, contention signal only" 지적을 문서화로 흡수**). Q1=gradual (Redis fast-path + PG authoritative) 유지. 1102 green.
  - Phase C: Real broker E2E infra **skeleton** (pytest-celery + real*broker marker + `--run-real-broker` flag + BYBIT_DEMO*\*\_TEST env + `nightly-real-broker.yml` cron 0 18 \* \* \* + workflow_dispatch + auto-label issue) — codex 8 FAIL + Opus 8 GWF + Sonnet 7 GWF, 4 fix (pytest-timeout dep + pipefail shell + ensureLabel helper + EXCHANGE_PROVIDER dead env). 1103 collectable. **실제 E2E 로직은 nightly 첫 실행 시 credentials + seed data 하에 작성 예정.**
  - 브랜치: `stage/h2-sprint10` — main PR 사용자 수동 생성 대기. PR body 초안 제공됨.
  - Follow-ups (Sprint 11 이관): Service-level Redis lock hold 확장 (실질 mutex) · CI lupa C ext 빌드 검증 · Sentinel/Cluster · cardinality allowlist · slowapi upgrade 후 middleware workaround 제거 · issue 중복 방지 · E2E 실제 구현
- **H2 Sprint 11 완료 (2026-04-25, stage/h2-sprint11 `e312f99`):** Beta 오픈 준비 infra 4 + Sprint 10 Follow-up 3 = 7 Phase. main 대비 12 커밋 앞섬. **BE 1130 passed** (+28) / 18 skip / 0 fail. **FE 207 passed** (+11). ruff 0 / mypy 0 / tsc 0 / eslint 0.
  - Phase A: US·EU Geo-block 3계층 — Cloudflare WAF runbook (`docs/07_infra/geo-block-setup.md`) + Next.js 16 `proxy.ts` CF-IPCountry 기반 `/not-available` redirect + Clerk webhook `public_metadata.country` 검증 (`GeoBlockedCountryError`). User.country_code String(2) 컬럼 + Alembic idempotent migration. RESTRICTED_COUNTRIES = US + EU 27 + GB. FE geo-block-banner + /not-available 안내 페이지. BE 4 TDD + FE 7 vitest.
  - Phase B: 법무 임시 템플릿 (D-5 B 안) — /disclaimer, /terms, /privacy 3 페이지 (한/영 혼용, Beta 특화 문구) + `LegalNoticeBanner` (전 페이지 상단 amber 배경 고지) + `legal-links.ts` 상수 + `docs/07_infra/legal-temporary.md` (H2 말 정식 변호사 교체 절차 $500~$1,500).
  - Phase C: Waitlist BE 도메인 (8 파일 — models/schemas/repository/service/router/dependencies/email_service/token_service) + Alembic migration (ENUM idempotent) + FE features 모듈 + `/waitlist` form 5 필드 + `/admin/waitlist` approve UI. Resend httpx wrapper + tenacity 3-retry. HMAC-SHA256 invite token (7-day TTL, exp + nonce). `@limiter.limit("5/hour")` POST + `@limiter.limit("10/minute")` GET. BE 16 TDD + FE 6 vitest. 병렬 Agent 43분. **post-merge hotfix**: `conftest.py` 에 `REDIS_LOCK_URL=redis://localhost:6379/3` 기본값 주입 (`8ef8f09`) — Agent 가 env 로 우회한 버그 해소.
  - Phase D: Onboarding 4-step wizard (welcome → strategy → backtest → result) — Zustand persist `qb-onboarding-v1` + TTL 5분 + scalar selector (LESSON-004 준수) + stepper + useBacktestProgress 재사용. Sample Pine: `ema-crossover.pine` (ta.ema 12/26 crossover/under). FE 11 tests. 병렬 Agent 8분.
  - Phase E (Sprint 10 A2 follow-up): Service-level RedisLock — real distributed mutex (Option A). `backtest/service.py::submit` 와 `trading/service.py::execute` 를 `async with RedisLock(f"idem:{domain}:{key}", ttl_ms=30_000)` 으로 감싸고 Repository wrapping 제거. **Opus 의 "Wrapping 은 mutex 아님" 지적 해소** — `redlock.py` docstring 을 "real mutex 완료" 로 업데이트. BE 6 TDD + 19 기존 idempotency 회귀 유지 (25 green).
  - Phase F (Sprint 10 B follow-up): slowapi `>=0.1.9` → `>=0.1.9,<0.2` (upper bound 명시). PyPI 조회 시 0.1.x 최신 = 0.1.9 (upgrade no-op). `_RateLimitStateInitMiddleware` workaround 는 0.1.x 전반 잔존 → 유지. major 0.2.x 는 Sprint 12+ 이관 (사용자 결정 Q3 = Minor 범위). 기존 7 rate-limit TDD green.
  - Phase G (Sprint 10 D follow-up): `error_class` allowlist — `_CCXT_ERROR_CLASSES` 28 (ccxt.base.errors) + `_BUILTIN_ERROR_CLASSES` 5 (asyncio/OS) = 33 + "Other" 버킷. `_normalize_error_class(exc)` helper. Cardinality 4×10×34 ≈ 1,360 series (10k 한도 내). 기존 dummy class (`_RateLimitExceeded` 등) 를 실제 ccxt 예외로 교체 (의도 반영). BE 2 TDD + 4 기존 ccxt_timer 회귀.
  - **방법론 실측:** Phase A+B 직접 구현 · Phase C+D 병렬 Agent (Claude usage limit 내 정상 완료, 각각 43분/8분) · Phase E+F+G 병렬 Agent 시도 **실패 (org monthly usage limit)** → 직접 구현으로 전환하여 **F (5분) → G (20분) → E (45분)** 순차 완성. 3-way blind review (codex + Opus + Sonnet) 는 Sprint 10 대비 생략 (사용자 결정 — A/B/E/F/G 단순 범위 · C/D Agent 내부 검증 충분).
  - 브랜치: `stage/h2-sprint11` — main PR 사용자 수동 생성 대기. Cloudflare WAF 수동 설정 · Resend API 키 발급 · Termly 정식 법무 교체 (H2 말) 는 후속.
- **H2 Sprint 12 완료 (2026-04-25, stage/h2-sprint12 `65bc86a`):** dogfood 가속 — Phase A (Slack alert) + Phase C (Bybit Private WebSocket + Reconciliation). main 대비 9 커밋 앞섬. **BE 1171 passed** (+41) / 18 skip / 0 fail. **FE 219 passed** (+12). ruff 0 / mypy 0 / tsc 0 / eslint 0.
  - **codex Generator-Evaluator 6 게이트 (G0~G4 + revisit) 2.6M tokens** — 24 CRITICAL 발견 + 모두 fix or 명시적 Sprint 13 이관. 사용자 명시 요청으로 본격 적용.
  - Phase A: `backend/src/common/alert.py` SlackAlertService — per-call httpx client + BoundedSemaphore(8) + 15s wait_for + tenacity 503 retry. KillSwitchService.ensure_not_gated() 의 event save 직후 alert task 발송 (G0-1: Service layer hook, Evaluator 안 X). best-effort policy — module-level `_PENDING_ALERTS` set 으로 task strong ref 보존. G2 challenge fix: HTTPError catch 누락 + wait_for 가 semaphore 안에 있어 9번째 alert 30s+ 누적 → 양쪽 fix + 회귀 테스트 2건. 11 신규 tests.
  - Phase C: `backend/src/trading/websocket/` 4 modules — BybitPrivateStream supervisor 패턴 (G4 fix #1 runtime reconnect — supervisor task 가 ConnectionClosed/heartbeat 종료 시 자동 1→30s exponential backoff), StateHandler orderLinkId UUID 우선 lookup + orphan_buffer FIFO max 1000 (G3 #2), Reconciler terminal-evidence-only transition (G3 #10) + CCXT unified status 매핑 (G4 revisit #11), BybitReconcileFetcher CCXT 어댑터.
  - Phase C-pre: OrderSubmit.client_order_id 추가 → BybitDemo/BybitFutures/Okx providers 가 `params={orderLinkId/clOrdId: str(Order.id)}` 전달. WebSocket order event 가 orderLinkId UUID 로 local DB row 매핑.
  - Celery 운영: ws_stream queue + acks_late + reject_on_worker_lost + prefetch=1 + reconcile_ws_streams 5분 beat. **G4 revisit fix #4 docker-compose ws-stream worker `--pool=solo`** — prefork 시 worker_shutdown 가 main process 만 hook → child 의 `_STOP_EVENTS` 미연결. solo 는 main 이 직접 task 실행.
  - G4 revisit fix #5 auth FD leak: supervisor finally block 이 ws.close() 보장. G4 revisit fix B: `__aenter__` 60s startup timeout.
  - 6 신규 metrics: `qb_ws_orphan_event_total` / `_buffer_size` / `qb_ws_reconcile_unknown_total` / `_skipped_total` / `qb_ws_duplicate_enqueue_total` / `qb_ws_reconnect_total`.
  - 신규 deps: `websockets>=12,<17` 명시.
  - Frontend: `useOrders` `computeOrdersRefetchInterval(orders)` helper export (5s if active, 30s idle. LESSON-004 준수). 5 신규 unit tests.
  - **dogfood 셋업 매뉴얼 (G5 self-checklist 10 항목)**: `docs/07_infra/sprint12-dogfood-checklist.md` 신규.
  - **Sprint 13 이관**: prefork+Redis lease pattern (현재 solo 우회), partial fill cumExecQty tracking, auth circuit breaker (1h TTL), Phase B Grafana Cloud, OKX Private WS, `worker_process_init/shutdown` prefork hook.
  - 브랜치: `stage/h2-sprint12` — main PR 사용자 수동 생성 대기.
- **H2 Sprint 13 완료 (2026-04-26, stage/h2-sprint13 `39eb66d`, PR #78):** Track UX — dogfood Day 1 의 Trading entry path 부재 (Pain top 1) + **Sprint 6 broken bug** (webhook_secrets DB 0건) 해소. main 대비 3 commits. **BE 1181 passed (+11)** / 18 skip / 0 fail. **FE 232 passed (+13)**. ruff 0 / mypy 0 / tsc 0 / eslint 0.
  - **Sprint 6 broken bug fix**: `WebhookSecretService.issue()` / `rotate()` 가 `_repo.commit()` 미호출이라 plaintext 반환 후 request 종료 시 rollback. dogfood Day 1 webhook_secrets 0건의 root cause. 두 메서드 commit 호출 추가 + `issue(commit=True default, commit=False option)` 옵션 분기.
  - Phase A.1 BE: `StrategyService.create()` atomic auto-issue — `secret_svc.issue(strategy.id, commit=False)` + `repo.commit()` 한 번 (strategy + webhook_secret 단일 트랜잭션). `get_strategy_service()` DI 가 `WebhookSecretRepository` 동일 session 주입. `StrategyCreateResponse(StrategyResponse)` 신규 — `webhook_secret: str | None` POST create 만, GET/list 는 `StrategyResponse` 유지. BE 6 TDD (atomic E2E 3 + Sprint 6 회귀 spy 3 = `repo.commit()` 호출 자체 mock 검증).
  - Phase A.2 FE: `webhook-secret-storage.ts` (sessionStorage TTL 30분 + strategy_id scoped + clearWebhookSecret), `useCreateStrategy onSuccess` 가 plaintext 자동 캐시 + react-query cache 에는 sanitized (no `webhook_secret`) 만, `useRotateWebhookSecret` 신규, `TabWebhook` 컴포넌트 (4번째 탭, URL + Rotate ConfirmDialog + amber card 1회 + 닫기시 즉시 remove). FE 4 vitest.
  - Phase B FE: `TestOrderDialog` — `NEXT_PUBLIC_ENABLE_TEST_ORDER='true'` production guard (env undefined 시 button 미렌더), Zod v4 + custom resolver (RHF zod v3 호환 회피), 5 필드 form, 단일 `bodyStr` direct fetch (apiFetch 우회), browser HMAC-SHA256 (Web Crypto API), 201 expected, `Idempotency-Key=crypto.randomUUID()` query. **G.4 P1 #5 fix**: KS bypass 차단 (CSS pointer-events 만으론 keyboard activation 또는 이미 열린 dialog 우회 가능 → `useIsOrderDisabledByKs()` 직접 읽고 submit button disabled + onSubmit 초입 차단). `useIsOrderDisabledByKs` hook 신규 (Sprint 12 추가됐다 가정 했지만 실제 부재). FE 6 vitest. `OrdersPanel` 'Test Order' 버튼 + KS active 시 wrapper opacity 50%.
  - Phase B BE: `test_webhook_hmac_golden.py` 신규 — golden vector hex `e4afb16c0e07eaf8ed219a072b59a47ae7619231c03cace98b376795901031e5` (BE pytest + FE vitest 양쪽 동일 fixture, **codex G.0 2차 P1 critical** 해소).
  - Phase C FE: `BacktestForm` — `useForm({ mode: "onChange" })` + `setError`/`clearErrors` 추가. `useCreateBacktest onError` 가 `status===422` 시 `setError("root.serverError")` 로 form-level inline 표시 (비-422 toast 유지). 인라인 `<p role="alert">`. FE 3 vitest.
  - codex 6 gates: **G.0 1차** (V1 P1 6 + P2 8 발견) → V2.1 patch → **G.0 2차** (P1 1=golden vector 강조 + P2 4) → **G.2 challenge** (P1 0 + P2 2: 회귀 spy + react-query cache leak) 즉시 fix → **G.4 challenge** (P1 1=KS bypass + P2 5) → P1 + P2 #6 stale 422 fix → **G.5 self-checklist** 8/10 (잔여 2 = dogfood Day 2 + docs sync).
  - **Sprint 14 이관 (G.4 P2 잔존)**: WebCrypto error 처리 / loading-error UX / `NEXT_PUBLIC_API_URL` trailing slash + production missing / response.text() size cap + JSON detail 정규화.
  - 브랜치: `stage/h2-sprint13` — PR #78 사용자 수동 stage→main. **dogfood Day 2 즉시 실행 권장** (검증 SLO: Strategy create webhook_secret 1건 + TabWebhook rotate plaintext + TestOrderDialog 201/401/422 inline + Backtest 422 inline + WS metric + self-assessment ≥ 7/10).
- **dogfood Day 2 (2026-04-26)**: Sprint 13 머지 전 local stage 검증. 5/6 시나리오 PASS + **OrderService outer commit broken bug 발견 + 즉시 hotfix** (commit `42c6575`, Sprint 6 webhook_secret 와 동일 패턴 두 군데 모두 fix). self-assessment **3→6/10 (+3 점프)** — H1→H2 gate (≥7) 1점 차 미통과. **Sprint 14 Track UX-2 우선** 권장: TabWebhook hydration fix + G.4 P2 잔존 4건 + broker 체결 검증. dev-log [`2026-04-26-dogfood-day2.md`](docs/dev-log/2026-04-26-dogfood-day2.md). 다음 prompt: [`~/.claude/plans/h2-sprint-14-prompt.md`](~/.claude/plans/h2-sprint-14-prompt.md).
- **H2 Sprint 14 완료 (2026-04-27, stage/h2-sprint14):** Track UX-2 — Day 2 발견 + Sprint 13 G.4 P2 잔존 + codex G.0 P1 3건 + 부수 발견 모두 반영. main 대비 3 commits. **BE 1185 passed (+4)** / 18 skip / 0 fail. **FE 243 passed (+11)**. ruff 0 / mypy 0 / tsc 0 / eslint 0 / pnpm build OK.
  - Phase A (`4d863df`): TabWebhook hydration race fix — `useState(() => readWebhookSecret)` initializer → **`useSyncExternalStore` 패턴** (server snapshot=null + client snapshot read + listeners notify). LESSON-004 의 react-hooks/set-state-in-effect 차단 회피 (Codex 권장 패턴). webhook-secret-storage.ts 에 `subscribeWebhookSecret`+`notify()` 추가. new/page.tsx onSuccess router.push 에 `?tab=webhook` 추가. FE 4 tests.
  - Phase B (`c1f9012`): Sprint 13 G.4 P2 4건 + helper 통합. B-1 WebCrypto try/catch + B-2 retry: 1 + ExchangeAccounts skeleton/retry + B-3 `lib/api-base.ts` 신규 `getApiBase()` (top-level throw 금지, codex G.0 P1 #3 fix) + B-4 `readErrorBody` 8KB cap. FE 11 tests (api-base 8 + WebCrypto 1 + ExchangeAccounts loading-error 2).
  - Phase C (`06dfb11`): codex G.0 P1 #1 fix — `_async_execute` receipt.status 분기. `"submitted"` 면 `attach_exchange_order_id` 만 호출 + submitted 유지 (forced filled 거짓 양성 회귀 방지). `repository.attach_exchange_order_id` 신규. BE 4 tests (filled / submitted 유지 / rejected / Sprint 13 LESSON spy commit ≥ 2).
  - **codex 5 게이트**: G.0 consult (P1 3건 — broker filled 거짓 / qb_ws_reconnect SLO / NEXT_PUBLIC_API_URL throw + 부수 EditorView tab sync 발견) + G.2 challenge (P1 1건 — submitted watchdog **Sprint 15 이관**) + G.5 self-checklist 8/10. iter cap 2 준수.
  - **Sprint 15 이관 (G.2 P1 #1)**: submitted 영구 고착 watchdog — `provider.fetch_order` + `fetch_order_status_task` Celery + orphan-submitted scanner beat. dogfood Day 3 의 Bybit Demo + WS 정상 동작 시 영향 적음.
  - dogfood Day 3 자동 검증 100% PASS (자동 가능 부분). 라이브 시나리오 6-9 + self-assessment 는 사용자 브라우저 직접 진행 필요. dev-log [`2026-04-27-dogfood-day3.md`](docs/dev-log/2026-04-27-dogfood-day3.md).
  - 브랜치: `stage/h2-sprint14` — 사용자 수동 stage→main PR. 다음 prompt: `~/.claude/plans/h2-sprint-15-prompt.md` (작성 예정).
- **H2 Sprint 15 아키텍처 cleanup 완료 (2026-04-28, stage/h2-sprint14 동일 브랜치):** Sprint 14 머지 직전 아키텍처 정합성 리뷰 → top 3 즉시 fix. main 대비 4 commits (Sprint 14 3 + 15 1 묶음). BE ruff 0 / mypy 0 (143 source files) / FE tsc 0 / lint 0.
  - **Sprint 15-A**: `ExchangeAccountService.register()` commit 누락 fix — Sprint 6 webhook_secret + Sprint 13 OrderService 와 동일 broken bug **3 번째 재발**. RED → GREEN 검증 (`AsyncMock spy: Awaited 0 → 1`). LESSON-019 추가 + `.ai/stacks/fastapi/backend.md` §트랜잭션 commit 보장 신규 섹션 승격 (3회 충족). **모든 service mutation 메서드 commit-spy 회귀 테스트 의무화**. 표준 reference: `backend/tests/trading/test_webhook_secret_commits.py` 3 spy.
  - **Sprint 15-B**: `backend/src/exchange/` dead module 8 파일 / 12 라인 삭제. 4월 15일 Phase 0 스캐폴딩 후 동결, trading/ 모듈이 거래소 책임 흡수. cross-import 0건 + main.py 미등록 확인. ADR-018 (Sprint 12 WS supervisor + Sprint 15 cleanup 묶음) 작성.
  - **Sprint 15-C**: docs sync — `system-architecture.md` §8 Observability "미적용" → 14 metrics 카탈로그 (Sprint 9~12 도입 사실 반영) + `data-flow.md` §7 "Sprint 7+ 예정" → BybitPrivateStream supervisor / StateHandler / Reconciler 실 구현 시퀀스 다이어그램 + `docs/TODO.md` 18 skip 추적표 (real_broker / mutation / golden 카테고리화).
  - **Sprint 16+ 이관 (Sprint 15 후속 dette)**: 모든 기존 service mutation 메서드 audit (commit-spy backfill) · golden expectations 재생성 (skip #1) · KIND-B/C mutation 정밀도 (xfail #16) · trust layer fixture 활성화 회귀 (#4-7, #9-15) · Sprint 14 G.2 P1 #1 submitted watchdog (Sprint 14 이관 그대로 유지).
  - 브랜치: `stage/h2-sprint14` (Sprint 14 + 15 묶음). PR 생성.
- **dogfood Day 1 (2026-04-25/26)**: Sprint 12 머지 후 첫 dogfood 시도. 인프라 fix 2건 + Backtest E2E 통과 + Trading 진입 차단 (Pain top 5). dev-log [`2026-04-25-dogfood-day1.md`](docs/dev-log/2026-04-25-dogfood-day1.md).
  - **Phase 1 인프라 fix**: backend-beat env 누락 (Sprint 12 patch 가 ws-stream만 추가, beat env 보강 미반영) + beat-data volume root ownership (Dockerfile USER appuser uid 1000 mismatch) → 2단계 fix 후 정상 부팅. backend-ws-stream 첫 가동.
  - **시나리오 1 (Backtest E2E) ✅**: dogfood-day1-ema-cross strategy 생성 + BTC/USDT 1h 1개월 backtest 7.4초 완료. 5탭 + Equity Curve 모두 렌더링. **422 root cause** = 시작일/종료일 빈 채 제출 (frontend inline error 표시 안 함).
  - **시나리오 2 (Trading) 🔴 결정적 Pain ×3**: (1) /trading 에 manual 주문 UI 없음 (2) Strategy edit 에 webhook URL/secret rotation UI 없음 (3) `trading.webhook_secrets` DB 0건 (자동 발급 안 됨). 일반 dogfood 사용자가 trading 시작 entry 자체 부재. AI 자동화 진행은 system 안전 정책 (DB raw insert / secret stdout / agent-injected secret 패턴) 으로 차단됨 — 모두 합리적.
  - **시나리오 3 (WS idle)**: active session 0 → reconcile_ws_streams beat no-op 정상. **`trading_sessions` table 자체 DB 미존재** — Sprint 12 reconcile_ws_streams 의 active session 검색 대상 재확인 필요 (Sprint 13 Phase D).
  - **시나리오 4 (KS 시뮬)** skip: webhook 경로 막힘 + service 직접 호출 trigger 막힘 → 진입 불가.
  - **본인 매일 사용 가능성 self-assessment 3/10** (Backtest 만 가능, Trading 불가). H1→H2 gate (≥7/10) 미통과.
  - **Sprint 13 Track 추천 변경**: Day 0 ★★★★★ Track A (WS 안정화) → **Day 1 후 ★★★★★ Track UX (신설)** — Trading 도메인 dogfood UX 가 prereq. Phase A (webhook 패널 + secret 자동 발급) + Phase B (테스트 주문 dialog) + Phase C (Backtest form validation) + Phase D 옵션 (trading_sessions 모델 확인). 예상 ~16h. 다음 세션 프롬프트: [`~/.claude/plans/h2-sprint-13-prompt.md`](~/.claude/plans/h2-sprint-13-prompt.md).

---

## Refactoring Backlog (deferred 작업)

> **본 섹션의 sprint history 안 "Sprint N+ 이관 / 후속 / 추후" 자연어 표현은 모두 [`docs/REFACTORING-BACKLOG.md`](docs/REFACTORING-BACKLOG.md) 의 BL-XXX ID 로 통합됐습니다 (2026-04-30).**
>
> 신규 sprint 진입 시 본 백로그 review 의무. 자연어 표현은 컨텍스트 복원성 위해 sprint 회고 안에 그대로 유지하되, 새 항목 추가 시 BL ID 부여 후 등록.

핵심 cross-link:

- **P0 — H1 종료 blocker:** [BL-001](docs/REFACTORING-BACKLOG.md#bl-001) submitted watchdog · [BL-002](docs/REFACTORING-BACKLOG.md#bl-002) Day 2 stuck pending · [BL-003](docs/REFACTORING-BACKLOG.md#bl-003) Bybit mainnet runbook · [BL-004](docs/REFACTORING-BACKLOG.md#bl-004) KillSwitch capital_base · [BL-005](docs/REFACTORING-BACKLOG.md#bl-005) 본인 1~2주 dogfood
- **P1 — Risk mitigation:** [BL-010](docs/REFACTORING-BACKLOG.md#bl-010) commit-spy 도메인 확장 (LESSON-019 backfill) · [BL-011](docs/REFACTORING-BACKLOG.md#bl-011)~[BL-016](docs/REFACTORING-BACKLOG.md#bl-016) WebSocket 안정화 6 항목 (Redis lease / prefork / auth circuit breaker / partial fill / OKX WS / first_connect race) · [BL-017](docs/REFACTORING-BACKLOG.md#bl-017)~[BL-021](docs/REFACTORING-BACKLOG.md#bl-021) Sprint 14 G.4 P2 5건
- **Beta 오픈 번들:** [BL-070](docs/REFACTORING-BACKLOG.md#bl-070)~[BL-075](docs/REFACTORING-BACKLOG.md#bl-075) (도메인 + DNS / Backend 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트)
- **정합성 audit:** [`docs/04_architecture/architecture-conformance.md`](docs/04_architecture/architecture-conformance.md) — 15 항목 영구 체크리스트 (위반 0 / OK 13 / TBD 2 = 86% 정합성, 2026-04-30)

---

## 스택 규칙 참조

> `.ai/rules/`는 심링크 허브. 원본은 `.ai/common/`, `.ai/stacks/`, `.ai/project/`에 위치.
> **Codex CLI / Gemini CLI:** 이 파일만 자동 로딩됩니다. 작업 전 아래 파일을 수동으로 읽으세요.

| 파일                         | 내용                                   | 적용                                                          |
| ---------------------------- | -------------------------------------- | ------------------------------------------------------------- |
| `.ai/rules/global.md`        | 워크플로우, 문서화 규칙, Git, 환경변수 | **전체**                                                      |
| `.ai/rules/typescript.md`    | TypeScript Strict, 네이밍 컨벤션       | **전체**                                                      |
| `.ai/rules/nextjs-shared.md` | Next.js 공통 (Zod v4, shadcn, 반응형)  | **Frontend**                                                  |
| `.ai/rules/frontend.md`      | Next.js 16 FE-only (FastAPI BE 조합)   | **Frontend**                                                  |
| `.ai/rules/backend.md`       | FastAPI + SQLModel                     | **Backend**                                                   |
| `.ai/rules/fullstack.md`     | Next.js 16 Full-Stack + Drizzle ORM    | **패턴만 차용** (ActionResult, error.tsx, Server/Client 경계) |
| ~~`.ai/rules/mobile.md`~~    | ~~Flutter~~                            | **미사용**                                                    |
| `.ai/project/lessons.md`     | 프로젝트 학습 기록 (실수 → 규칙 승격)  | **활성**                                                      |

### QuantBridge 고유 규칙 (도메인 특화)

- 금융 숫자는 `Decimal` 사용 (float 금지) — 가격, 수량, 수익률
  - **Decimal-first 합산:** `Decimal(str(a)) + Decimal(str(b))` — `Decimal(str(a + b))` 금지 (float 공간 합산 후 변환 시 precision 손실)
    `[Sprint 4 D8 교훈 → 영구 규칙]`
- 백테스트/최적화는 반드시 Celery 비동기 (API 핸들러 직접 실행 금지)
  - **Celery prefork-safe:** SQLAlchemy `create_async_engine()` / vectorbt 등 무거운 객체는 모듈 import 시점 호출 금지. Lazy init 함수로 워커 자식 프로세스 fork 후 생성. Worker pool=prefork 고정 (gevent/eventlet 비호환)
    `[Sprint 4 D3 교훈 → 영구 규칙]`
- 거래소 API Key는 AES-256 암호화 저장 (평문 금지)
- OHLCV 데이터는 TimescaleDB hypertable에 저장
- 실시간 데이터는 WebSocket + Zustand 캐시 (React Query와 분리)
- Pine Script → Python 변환 시 `exec()`/`eval()` 절대 금지 — 인터프리터 패턴 또는 RestrictedPython/sandbox 필수
  `[/autoplan 2026-04-13, Codex+Claude 듀얼 검증, 신뢰도 10/10, ADR-003 참조]`
- Pine Script 미지원 함수 1개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지 (잘못된 결과 방지)
  `[/autoplan 2026-04-13, Codex+Claude 듀얼 검증, 신뢰도 10/10, ADR-003 참조]`
