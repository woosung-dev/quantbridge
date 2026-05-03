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
- **H2 Sprint 15 Track Watchdog 완료 (2026-05-01, stage/h2-sprint15):** BL-001 submitted watchdog + BL-002 Day 2 stuck pending cleanup 합본. main 대비 4 commits 예정 (Phase A.1 / A.2 / A.3 / G.2 fix). **BE 1216 passed (+31)** / 18 skip / 0 fail. ruff 0 / mypy 0.
  - **Phase A.1**: `OrderStatusFetch` dataclass (4-state) + `ExchangeProvider.fetch_order` Protocol + 4 provider (Bybit Demo / Futures / OKX / Fixture) + `_map_ccxt_status_for_fetch` + `_bybit_fetch_order_impl` 공유 + `_build_order_status_fetch` 정규화. 10 TDD.
  - **Phase A.2**: `_async_fetch_order_status` (state guard / decrypt / provider.fetch_order / 4-state 분기) + `fetch_order_status_task` (Celery bind=True max_retries=3, backoff 15s→30s→60s) + `_try_watchdog_alert_throttled` (Redis SET NX EX 3600) + `_build_watchdog_retry_kwargs` (G.2 P1 #1 fix — args=[order_id] 명시 override) + `_async_execute` submitted 분기 enqueue. 11 TDD.
  - **Phase A.3**: `OrderRepository.list_stuck_pending/submitted/submission_interrupted` (G.0 P1 #3 — exchange_order_id IS NULL 분리) + `scan_stuck_orders_task` (5min beat, pending → execute_order_task 재dispatch / submitted+id → fetch_order_status_task / submitted+null → throttled alert). 7 TDD.
  - **codex G.0 P1 모두 fix**: #1 (qb_active_orders rowcount=1 winner-only dec), #2 (Redis throttle alert), #3 (NULL exchange_order_id 별도 list). G.2 P1 #1+#2 즉시 fix. #3 (WS state_handler:176 unconditional dec) → BL-027 분리 (Sprint 16+ 이관, watchdog 가 worse 만들지 않음 확인).
  - **신규 BL 등록**: BL-027 (WS unconditional dec) · BL-028 (force-reject-stuck.py manual cleanup) · BL-029 (CCXT rate limit Redis throttle middleware). 50 → 53 BL.
  - dev-log: [`2026-05-01-sprint15-watchdog.md`](docs/dev-log/2026-05-01-sprint15-watchdog.md). 사용자 라이브 dogfood Day 4 시나리오 5.2/5.3 + self-assessment ≥7 시 H1→H2 gate 통과 + BL-005 (1~2주 dogfood) trigger 도래.
  - 브랜치: `stage/h2-sprint15` — 사용자 수동 stage→main PR. 다음 prompt: [`~/.claude/plans/h2-sprint-16-prompt.md`](~/.claude/plans/h2-sprint-16-prompt.md) (Path A self-assessment ≥7 = Beta 오픈 번들 BL-070~072 / Path B = 발견 Pain + BL-027/BL-010).
- **H2 Sprint 16 완료 (2026-05-01, stage/h2-sprint16):** Path B Option A — Phase 0 라이브 검증 가이드 + Phase A BL-027 (3 path commit-then-dec winner-only) + Phase B BL-010 (4 도메인 commit-spy backfill). main 대비 2 commits. **BE +26 신규 tests** (Phase A 15 + Phase B 11) 100% PASS / ruff 0 / mypy 0. **codex G.0 P1 #1+#2 모두 plan 보정 + 구현. G.2 P1 critical 0건 confirm**.
  - **Phase A (BL-027 + tasks/trading dec winner-only)**: codex G.0 iter 1 의 P1 #1 (silent corruption — `_apply_transition` dec 가 commit 전 발화) + P1 #2 (scope 누락 — `tasks/trading.py:165/200/253` 의 `_async_execute` rejected 분기 rowcount 무시) 모두 fix. Sprint 15 watchdog `tasks/trading.py:458` 표준 패턴 (rows==1 → commit → dec) 3 path (state_handler / reconciliation / tasks/trading) 통일. 신규 15 tests. 커밋 `a3d4a20`.
  - **Phase B (BL-010 commit-spy 4 도메인)**: codex G.0 audit 결과 5 도메인 (Strategy/Backtest/Waitlist/Optimizer/StressTest) 모두 commit 호출 OK = **broken bug 0건 confirmed**. spy 추가만으로 회귀 방어. Optimizer 는 H1 미구현 (스캐폴드만) → 별도 BL. 신규 11 spy. autouse `_reset_rate_limiter` override (Redis 우회). 커밋 `beacc89`.
  - **codex 게이트**: G.0 (medium, 426k tokens, iter 1) — P1 #1+#2 plan 보정 + Phase B 0건 confirm. G.2 (high, 515k tokens, iter 1) — 6 break vector (silent rollback / SQLAlchemy lazy flush / 변수 shadowing / spy false negative / pytest fixture / OrderState fallthrough) 모두 P1 critical 0건 confirm.
  - **Phase 0 라이브 검증 (사용자 직접)**: dev-log skeleton 작성 — 시나리오 5.2 (Day 2 stuck pending 자동 reconcile) + 5.3 (의도적 stale submitted fake id retry/giveup) + self-assessment 갱신. self-assessment 결과 = Sprint 17 Path 분기 (≥7 → Path A Beta 오픈, 5-6 → Path B 잔존 Pain, ≤4 → emergency).
  - **BL status**: BL-027 ✅ Resolved · BL-010 ✅ Resolved (Optimizer 제외, H1 구현 시 별도 BL). 53 → 53 BL (P1 잔여 16, P2 잔여 2).
  - dev-log: [`2026-05-01-sprint16-phase0-live-and-backfill.md`](docs/dev-log/2026-05-01-sprint16-phase0-live-and-backfill.md). 라이브 self-assessment 사용자 input 대기.
  - 브랜치: `stage/h2-sprint16` — 사용자 수동 stage→main PR. 다음 prompt: [`~/.claude/plans/h2-sprint-17-prompt.md`](~/.claude/plans/h2-sprint-17-prompt.md) (Path A/B/C 분기 명시).
- **H2 Sprint 25 완료 (2026-05-03, stage/h2-sprint25 — main `aed201f` PR #96 머지 후 cascade):** Hybrid (Frontend E2E Playwright + Backend test 강화 + codex G.0/G.2). **BL-110a/112/113/114/115 ✅ Resolved** (5건). main 대비 ~25 file 변경. **BE 1401 passed / 39 skipped / 0 failed**. **FE 251 passed**. ruff 0 / mypy 0 (147 src) / tsc 0 / lint 0.
  - **Track 1 Frontend E2E**: Clerk `clerkSetup() + clerk.signIn()` 공식 패턴 + projects 분리 (setup/chromium smoke/chromium-authed authed `--workers=1`) + mock route `/api/v1/` 전수 (codex iter 2 P2 #4 — 기존 `/api/v1/trading/...` wrong path 정정) + `page.on('request')` leak guard observability. trading-ui 5 시나리오 활성화 + dogfood-flow 3 시나리오 신규 (Strategy create / Backtest 422 inline / TestOrderDialog KS bypass disabled).
  - **Track 2 Backend test 강화**: BL-112 (scenario2 실 backtest, `make_trending_ohlcv` 8 segments × 25 bars + EMA 3/8 cross + precondition num_trades >= 3 보장), BL-113 (scenario3 OrderService.execute 정확한 args `session=/repo=/dispatcher=FakeOrderDispatcher/kill_switch=NoopKillSwitch/exchange_service=` + uuid4 idempotency_key per test + dispatch_snapshot 자동 채움 검증), BL-110a (in-process lease integration test 7개 — acquire / duplicate / 격리 / extend True / extend False → lost_event.set / extend Exception → lost_event.set / __aexit__ DEL — autouse pool reset fixture 로 pytest-asyncio per-test loop 충돌 회피), BL-114 (pytest-json-report importlib detect + `_build_summary(...json_report=None)` backward compat + plugin 부재 graceful fallback), BL-115 (`html.escape` 전수 적용 + `<script>` 주입 회귀 unit test 3개).
  - **Track 3 codex Generator-Evaluator**: G.0 iter 1 (617k tokens) → plan v2 surgery 28건 → G.0 iter 2 NOT READY (1.28M tokens) → plan v3 surgery 21건 (Clerk auth wrong / BL-112 코드 실측 refuted / OrderService param 이름 / heartbeat exception path / pytest CLI behavior / mock URL prefix). G.2 challenge (992k tokens, high reasoning) → **P1 4건 즉시 fix**: (1) `global.setup.ts` env 검증 순서 (clerkSetup 후 검증), (2) `_ws_lease.py:_heartbeat_loop` extend Exception path 추가 (split-brain 차단, 신규 회귀 test 1개), (3) dogfood-flow Backtest 422 시나리오 submit + alert assert 추가, (4) dogfood-flow TestOrderDialog KS active 시 submit disabled assert 추가. P2 12건 + P3 2건 = BL-117~129 신규 등록 (Sprint 26+ 이관). 누적 ~3M tokens.
  - **Edge Cases 19**: plan v3 §5.5 + dev-log §3 영구 기록 (사용자 명시 요구). High risk 3건 (Clerk infra / Clerk API drift / OHLCV trade count 변동) 모두 fail loud + 검증 가능.
  - **신규 BL 14건 등록**: BL-110b (real Celery prefork SIGTERM, M 4-6h), BL-116 (CI workflow_dispatch authed E2E), BL-117 (Clerk emailAddress 방식), BL-118 (baseURL 통합), BL-119 (URL predicate), BL-120 (leak guard fail-on-leak), BL-121 (production guard host allowlist), BL-122 (uv-aware plugin detect), BL-123 (mkstemp fd leak), BL-124 (subprocess timeout), BL-125 (report timestamp), BL-126 (FakeOrderDispatcher edge case), BL-127 (xdist 격리), BL-128 (trading-ui scenario 3 KS disabled assert), BL-129 (ANSI HTML).
  - **LESSON 후보**: L-S25-1 (plan fixture 가설 refute 코드 실측 의무) · L-S25-2 (Clerk clerkSetup+clerk.signIn 둘 다 의무) · L-S25-3 (pytest plugin detect first) · L-S25-4 (prefork SIGTERM ≠ multiprocessing.Process) · L-S25-5 (heartbeat lost_event falsy + Exception 두 path 모두 set) · L-S25-6 (codex G.0 iter 2 재호출 의무 — 사용자 명시 요구) · L-S25-7 (pytest-asyncio + redis-py per-test pool reset fixture 의무).
  - dev-log: [`2026-05-03-sprint25-hybrid.md`](docs/dev-log/2026-05-03-sprint25-hybrid.md). plan: `~/.claude/plans/claude-plans-h2-sprint-25-prompt-md-snappy-bee.md` (v3 + Edge Cases 19). codex G.0 session: `019ded09-8442-7c63-8193-2e671f9f8601` / G.2 session: `019ded42-b486-7db2-9283-10c692b10dbe`.
  - **사용자 협조 1 step pending**: `frontend/.env.local` 4 키 (CLERK_PUBLISHABLE_KEY/SECRET_KEY/E2E_CLERK_USER_EMAIL/PASSWORD) 채워진 후 `pnpm e2e:authed` 실 검증. 그동안 backend service-direct 자동 가드 + run_auto_dogfood.py 6/6 PASS 가 회귀 baseline.
  - 브랜치: `stage/h2-sprint25` — 사용자 수동 stage→main PR. 다음 prompt: `~/.claude/plans/h2-sprint-26-prompt.md` (Path A Beta 오픈 / Path B G.2 P2 hardening / Path C BL-110b 분기).
- **H2 Sprint 24b 완료 (2026-05-03, stage/h2-sprint24b — main 에서 새 cascade):** Track 1 Backend E2E 자동 dogfood (BL 직접 처리 0건, 순수 자동 회귀 가드). Sprint 22+23+24a main 머지 (PR #95) 후 cascade.
  - **신규**: `backend/tests/integration/test_auto_dogfood.py` 6 시나리오 — strategy/webhook_secret atomic / backtest engine smoke / order dispatch_snapshot (Sprint 22+23) / snapshot drift detection (Sprint 23 G.2 P1 #1) / multi-account dispatch (Sprint 24a BL-011/012) / summary parser smoke
  - **신규**: `backend/scripts/run_auto_dogfood.py` entry script — `subprocess.run(["uv", "run", "pytest", "--run-integration", ...])` (codex G.0 P2 #3) + 별도 summary HTML/JSON (`docs/reports/auto-dogfood/<date>.{json,html}`, codex G.0 P1 #5 — `dogfood_report._async_generate()` 와 분리)
  - **검증**: 6 시나리오 100% PASS + ruff 0 / mypy 0 (147 src). 전체 회귀 별도 보고.
  - **의의**: 매 sprint 끝 자동 회귀 가드. 사용자 dogfood (BL-005) 와 병렬 시 Pain 사전 감지.
  - dev-log: [`2026-05-03-sprint24b-auto-dogfood.md`](docs/dev-log/2026-05-03-sprint24b-auto-dogfood.md). 브랜치: `stage/h2-sprint24b` (main `9066dce` 에서 새 cascade).
- **H2 Sprint 24a 완료 (2026-05-03, stage/h2-sprint22 cascade):** **BL-011/012/013/016 ✅ Resolved** (4건, Track 2 WebSocket 안정화). Sprint 24 의 Track 2 만 본 sprint, Track 1 (자동 dogfood) 은 Sprint 24b 후속 cascade.
  - **Phase A**: BL-011 Redis lease + heartbeat (`_ws_lease.py`, `acquired=False` → None wrap codex G.0 P1 #1) + BL-012 prefork 복귀 (docker-compose `--pool=prefork --concurrency=2` + `worker_process_shutdown` 에 `signal_all_stop_events()` 호출 codex G.0 P1 #2 + reconcile lease 기반 codex P2 #1). 13 신규 tests.
  - **Phase B**: BL-013 auth circuit breaker (`_ws_circuit_breaker.py`, `ws:auth:failures` 600s sliding window + `ws:auth:blocked` 3600s, `BybitAuthError` 즉시 block / network 3회 누적 block, codex G.0 P1 #3) + BL-016 first_connect race (task layer TimeoutError catch + record_network_failure, supervisor 손대지 않음 codex G.0 P1 #4). 10 신규 tests.
  - **Phase B.5 codex G.2 P1 즉시 fix**: split-brain (heartbeat 실패 시 lease 만료 → 다른 worker 재획득) — WsLease 에 lost_event 주입 + `_stream_main` 이 stop_event + lost_event 동시 wait. 기존 test_websocket_task_routing 마이그레이션 (acquire_ws_lease mock).
  - **codex 게이트**: G.0 (medium, ~50k tokens) FIX FIRST → P1 5 + P2 4 plan v2 / G.2 (high, ~99k tokens) FIX FIRST → P1 2 즉시 fix + P2 4 → BL-108/109/110/111 신규
  - **자동 검증**: ruff 0 / mypy 0 (147 src). 신규 ~24 tests + 1 마이그레이션. 회귀 결과 별도 보고.
  - **신규 BL 4건**: BL-108 INCR+EXPIRE Lua wrap / BL-109 first_connect timeout test 강화 / BL-110 prefork SIGTERM integration test / BL-111 circuit reset admin/CLI. **합계**: 67 → **67 BL** (4 Resolved + 4 신규).
  - dev-log: [`2026-05-03-sprint24a-ws-stability.md`](docs/dev-log/2026-05-03-sprint24a-ws-stability.md). 브랜치: `stage/h2-sprint22` cascade.
- **H2 Sprint 23 C-3 묶음 완료 (2026-05-03, stage/h2-sprint22 cascade):** **BL-098/099/101/102/103 ✅ Resolved** (5건) — dogfood 늦추는 동안 Pine coverage parity + BL-091 follow-up. Sprint 22+23 sequential, 단일 PR. self-assessment 9/10 유지 목표.
  - **Phase A**: BL-099 vline NOP (1줄) + BL-098 strategy.exit NOP (codex G.0 P1 #1+#2 회피 — close-fallback 은 Pine semantic 위반 + wrong-id 위험) + BL-101 Makefile up-isolated-build 신규 타깃 + BL-103 main.py:lifespan deprecation warning (app_env staging/production 조건). 신규 7 tests.
  - **Phase B BL-102 Order dispatch snapshot**: Order.dispatch_snapshot JSONB + Alembic 20260503_0001 (격리 stack upgrade/downgrade ✅) + OrderService.\_execute_inner snapshot 채움 (codex G.0 P1 #3 — exchange_service.\_repo.get_by_id 재사용) + \_parse_order_dispatch_snapshot 엄격 parser (codex G.0 P1 #4 — isinstance(bool) 강제, KeyError/ValueError → None) + \_provider_from_order_snapshot_or_fallback helper + qb_order_snapshot_fallback_total{reason} Counter. 신규 23 tests.
  - **Phase B.5 codex G.2 P1 즉시 fix**:
    - **G.2 P1 #1 (security critical)**: snapshot vs current account `(exchange, mode)` mismatch 시 `UnsupportedExchangeError` raise — snapshot=demo + account=live 시 BybitDemoProvider 선택되지만 creds=live 로 silent live endpoint 호출 위험 차단. metric reason="drift". 3 drift tests.
    - **G.2 P1 #2**: `v2_adapter._stub_parse_outcome(warnings=)` 추가 + ok-path 가 `state.warnings` 전달 → BacktestOutcome.parse.warnings 노출. strategy.exit NOP silent success 차단.
  - **codex 게이트**: G.0 (medium, ~70k tokens) FIX FIRST → P1 4건 + P2 5건 plan v2 surgery / G.2 (high, ~94k tokens) FIX FIRST → P1 2건 즉시 fix (Phase B.5) + P2 4건 → BL-104/105/106 신규
  - **자동 검증**: ruff 0 / mypy 0 (145 src). 1차 회귀 1346 → 2차 1372 + 1 fail (test_order_rejected_metric exchange_stub 마이그레이션 누락) → 3차 보정. 신규 ~30 tests + 21 monkeypatch (Sprint 22 영향) 모두 회귀 0.
  - **신규 BL 3건 (Sprint 24+)**: BL-104 (strategy.exit full PendingExitOrder + warnings dedupe, P2 M) / BL-105 (OrderService account fetch in transaction + AccountNotFound, P2 S) / BL-106 (Alembic IF NOT EXISTS TOCTOU 회피, P3 S). **합계 변동**: 68 → **66 BL** (5 Resolved + 3 신규)
  - dev-log: [`2026-05-03-sprint23-c3-bundle.md`](docs/dev-log/2026-05-03-sprint23-c3-bundle.md). 브랜치: `stage/h2-sprint22` (Sprint 22+23 cascade, 단일 PR)
- **H2 Sprint 22 완료 (2026-05-03, stage/h2-sprint22):** **BL-091 ✅ Resolved** — Sprint 20 hot-fix 의 architectural proper fix. **ExchangeAccount.mode dynamic dispatch** = `(account.exchange, account.mode, has_leverage)` 3-tuple. self-assessment 9/10 유지 목표.
  - **Phase A.1**: `UnsupportedExchangeError(ProviderError)` (`exceptions.py`) — ProviderError subclass = `_execute_with_session:214` `except ProviderError` 자동 catch → graceful rejected.
  - **Phase A.2**: `BybitLiveProvider` stub 신규 (`providers.py:701-`) — `create_order` / `cancel_order` / `fetch_order` 3 메서드 모두 ProviderError("BL-003 mainnet runbook 완료 후 활성화") raise. Protocol 만족 (codex G.0 P1 #3).
  - **Phase A.3 (코어)**: `tasks/trading.py` — module-level `_exchange_provider` global + `_get_exchange_provider()` lazy singleton 제거. `_has_leverage(submit_or_order)` (None or 0 → spot, isinstance 가드, codex G.2 P2 #2 type guard) + `_provider_for_account_and_leverage(exchange, mode, has_leverage)` 본체 + `_build_exchange_provider(account, submit)` public 추가. 호출처 line 257 (create_order) + line 502 (fetch_order) 변경.
  - **Phase A.4**: `core/config.py:82` exchange_provider DEPRECATED 마킹 (필드 유지, dispatch path 미사용). `docker-compose.yml` worker+beat `EXCHANGE_PROVIDER` env 제거. `.env.example` (root + backend) + `runbook.md` + `bybit-mainnet-checklist.md` 4 docs deprecation 주석 sync (G.2 P2 #4).
  - **Phase A.5**: `tests/tasks/test_provider_dispatch.py` 신규 — 31 tests (TestProviderDispatchHappyPath 3 + Unsupported 4 + BybitLiveStub 4 + HasLeverageHelper 8 inc. string/bool/Decimal G.2 P2 #2 4 신규 + BuildExchangeProvider 3 + E2E rejected verifier 2 + narrow_fixture_guard 5 parametrize).
  - **Phase A.6**: 21건 monkeypatch 자동 마이그레이션 (Python regex script) — `_exchange_provider` setattr 19건 + `settings.exchange_provider` setattr 2건 → `_provider_for_account_and_leverage` lambda + 2건 줄 삭제. `test_build_exchange_provider_dispatches_bybit_futures` 함수 본문 ExchangeAccount fixture 직접 호출 패턴.
  - **Phase B.4**: `tests/trading/test_account_mode_immutable.py` audit — `/exchange-accounts` route 의 PUT/PATCH 부재 회귀 가드. codex G.2 P2 #1 fix 로 정확한 prefix 매칭.
  - **codex 게이트**: G.0 (medium, ~52k tokens, iter 1) → FIX FIRST. P1 5건 (live/stub 충돌 / UnsupportedExchangeError graceful catch 누락 / Protocol cancel_order 누락 / EXCHANGE_PROVIDER 정책 모순 / account.mode race) + P2 5건 모두 plan v2 surgery 반영. G.2 (high, ~84k tokens, iter 1) → **PASS (P1 0건)**. P2 5건 중 #1+#2+#4 즉시 fix, #3+#5 BL-102/BL-103 신규 등록.
  - **자동 검증**: **1342 passed / 27 skipped / 0 failed** (3분 12초, 격리 stack 5433/6380). Sprint 21 baseline 1185 → +28 신규 + 21 monkeypatch 회귀 0 fail. ruff 0 / mypy 0 (145 src files).
  - **신규 BL 2건 (Sprint 23+)**: BL-102 Order 에 dispatch (exchange, mode, has_leverage) snapshot 저장 (P2 M, G.2 P2 #3) / BL-103 EXCHANGE_PROVIDER non-default startup warning 또는 필드 제거 (P3 S, G.2 P2 #5). **합계 변동**: 67 → **68 BL** (BL-091 ✅ Resolved + 2 신규).
  - **dogfood Day 2-7 트리거**: `make up-isolated` 재기동 + worker `EXCHANGE_PROVIDER` env 부재 라이브 확인 → TestOrderDialog 발송 → `exchange_order_id` 가 `bybit-...` 형식 + Bybit Demo 대시보드 reflects 확인. 사용자 직접 1-2주 dogfood 병렬.
  - dev-log: [`2026-05-03-sprint22-bl091-architectural.md`](docs/dev-log/2026-05-03-sprint22-bl091-architectural.md). 브랜치: `stage/h2-sprint22` — 사용자 수동 stage→main PR.
  - **방법론 LESSON-020 후보**: ExitPlanMode 직전 codex G.0 누락 → 사용자 명시 지적 후 재발견. memory `feedback_codex_g0_pattern.md` 강화 (3회 반복 시 영구 규칙 승격 후보).
- **H2 Sprint 19 완료 (2026-05-02, stage/h2-sprint18 sequential):** Path C technical debt — **BL-081/083/084/085 ✅ Resolved** (4건). Sprint 18 G.2 잔존 P2 + 신규 audit/integration test. self-assessment 9/10 유지. dogfood 진입 전 회귀 방어 자동화.
  - **Path 결정**: 사용자 분기 = Path C (★★★★★ 같은 세션 적합도 최고). Path B (1-2주 dogfood) Sprint 20 / Path A (Beta 오픈) 향후.
  - **BL-081**: `qb_pending_alerts` Prometheus Gauge + `track_pending_alert(task)` idempotent helper (set membership 검사로 drain + done_callback 중복 dec 방어). `kill_switch.py:225` migration. 5 tests.
  - **BL-083**: `tests/test_migrations.py` 4 fail → 0. `_resolved_test_db_url()` (TEST_DATABASE_URL > DATABASE_URL > default) + `_to_psycopg2_url()` helper (`make_url` 기반).
  - **BL-084**: AST audit `test_no_module_level_loop_bound_state.py` — module-level `asyncio.<Semaphore|Lock|Event|Queue|Condition|...>` 차단 gate. import alias + AnnAssign 지원. Allowlist 1개 (`_SEND_SEMAPHORE`). 4 tests.
  - **BL-085**: `tests/tasks/test_prefork_smoke_integration.py` — `@pytest.mark.integration` + `--run-integration` flag. DSN guard (`make_url().database.endswith("_test")`) + `_no_op_apply_async` (3개 task `apply_async/delay` no-op). 5 tests. Sprint 18 라이브 30/30 의 CI 자동화.
  - **codex G.0 (medium, 366k tokens, iter 1)**: HIGH → FIX FIRST. P1 4건 모두 plan 반영. test_migrations conftest 우회 / scanner real DB hit / pytest_collection_modifyitems early return / done_callback 중복 dec.
  - **codex G.2 (high, 397k tokens, iter 1)**: HIGH → FIX. P1 #1 reconcile_ws_streams `run_bybit_private_stream.delay()` 미patch → 추가. P1 #2 DSN substring guard 약점 → `make_url().database` 정확 검증. False alarms 8/10 vector. P2 1건 흡수 (system-architecture.md `qb_pending_alerts` 추가) / 4건 Sprint 20 이관.
  - **자동 검증**: 신규 14 tests + 기존 회귀 = **1278 passed / 0 failed / 27 skipped** (Sprint 18 1269 → Sprint 19 1278). ruff 0 / mypy 0 (145 src). 라이브 scan_stuck_orders x3 = **3/3 succeeded / 0 raised** (Sprint 18 30/30 패턴 유지).
  - **신규 BL 5건 (Sprint 20+)**: BL-086 AST factory detection / BL-087 audit glob / BL-088 drain helper / BL-089 Grafana alert wire-up / BL-090 tests/db_url.py 분리. **합계**: 59 → 64 BL.
  - dev-log: [`2026-05-02-sprint19-technical-debt.md`](docs/dev-log/2026-05-02-sprint19-technical-debt.md). 브랜치: `stage/h2-sprint18` (Sprint 18 + 19 sequential, 단일 PR). 다음 prompt: `~/.claude/plans/h2-sprint-20-prompt.md` (Path B 본인 dogfood ★★★★★).
- **H2 Sprint 18 완료 (2026-05-02, stage/h2-sprint18):** **BL-080 ✅ Resolved** — Option C persistent worker loop (`_WORKER_LOOP.run_until_complete`) 채택. Sprint 17 1/3 → Sprint 18 30/30 (same ForkPoolWorker-2). self-assessment **5/10 → 9/10**. **H1→H2 gate (≥7) 통과**.
  - **Phase A multi-candidate diagnostic (Iron Law)**: codex G.0 가 `_SEND_SEMAPHORE` smoking gun REFUTED. 라이브 재현 → control `backtest.reclaim_stale` 3/3 success / failing `scan_stuck_orders` 1/3 success / 2 fail. Stack trace `BaseProtocol._on_waiter_completed` 가리킴 = **asyncpg connection 의 transport waiter 가 1st task asyncio.run() loop 에 stale bound**. candidate 1/2/4 collapse, **candidate 5 (task-specific query 패턴 + asyncpg connection state leakage)** 확정.
  - **Phase B Option C 구현 (TDD)**: `backend/src/tasks/_worker_loop.py` 신규 — `init/shutdown/run_in_worker_loop` (running-loop guard + asyncgens drain). `worker_process_init` hook init + `worker_process_shutdown` hook 신규 shutdown (codex G.0 P1 #4). `_on_worker_ready` master 만 → asyncio.run 유지 (P1 #5). 9개 task entry point 변경 (orphan_scanner / trading × 2 / websocket_task × 2 / backtest × 2 / funding / dogfood_report / stress_test_tasks). `worker_max_tasks_per_child` 1 → 250 (codex G.2 P2 #1 보수).
  - **Phase C conftest fix (codex G.0 P1 #7)**: `TEST_DATABASE_URL` / `TEST_REDIS_LOCK_URL` env 우선순위 + 격리 stack 5433/6380 매핑. **Sprint 16/17 의 296 errors → 0**. 1269 passed / 4 failed (alembic test psycopg2 sync 5432 hardcoded — Sprint 18 무관, BL-083 이관) / 18 skipped.
  - **codex G.0 (high, 824k tokens, iter 1)**: Hypothesis REFUTED + 7 P1 + 5 P2 모두 plan v2 반영. asyncio.Semaphore binding 동작 정정 (uncontended 미bind, contended path만 bind). Celery `include=[...]` master process import 로 모든 child sys.modules 적재 = backtest import-diff 가설 약화.
  - **codex G.2 challenge (high, 487k tokens, iter 1)**: HIGH risk → FIX FIRST. P1 #1 (`_on_worker_shutdown` race — ws_stream solo running 중 `run_in_worker_loop` RuntimeError) 즉시 fix (`_WORKER_LOOP.is_running()` 검사 후 cleanup skip). P2 #3 `shutdown_asyncgens` + `shutdown_default_executor` 추가. P3 #1 `coro.close()` 추가. False alarms 9/14 vector.
  - **라이브 검증**: 30 dispatched mixed tasks (10 cycles × 3 task types) → **30/30 succeeded by single ForkPoolWorker-2 / 0 raised**. Sprint 17 의 1/3 fail 패턴 완전 차단.
  - **자동 검증**: 신규 12 worker_loop tests + 1269 전체 회귀 PASS / ruff 0 / mypy 0 (10 src/tasks files).
  - **신규 BL 5건 (Sprint 19 이관)**: BL-081 `_PENDING_ALERTS` gauge / BL-082 1h soak gate / BL-083 alembic test psycopg2 호환 / BL-084 AST audit / BL-085 prefork integration test. **합계 변동**: 54 → 59 BL (BL-080 ✅ Resolved + 5 신규).
  - dev-log: [`2026-05-02-sprint18-bl080-architectural.md`](docs/dev-log/2026-05-02-sprint18-bl080-architectural.md).
  - 브랜치: `stage/h2-sprint18` — 사용자 수동 stage→main PR. 다음 prompt: `~/.claude/plans/h2-sprint-19-prompt.md` (Beta 오픈 번들 + BL-005 dogfood + BL-081/082).
- **H2 Sprint 17 부분 진전 (2026-05-02, stage/h2-sprint17):** Path C emergency — Phase 0 라이브 검증으로 Sprint 15 watchdog 100% silent fail (141/141) + Sprint 12 reconcile 50% intermittent fail (18/35) 발견. self-assessment **2/10 → 5/10 (+3)**. H1→H2 gate (≥7) 미통과 — **Sprint 18 BL-080 root architectural fix 후 재평가**.
  - **Root cause (systematic-debugging Phase 1+2)**: module-level cached AsyncEngine + Celery prefork worker 의 `asyncio.run()` 새 loop = SQLAlchemy/asyncpg connection pool loop binding mismatch. funding.py:26-31 PR #51 reference 정확. Pattern Diff: control task `backtest.reclaim_stale` 6h 34/34 success (per-call engine pattern) vs scan/reconcile/trading module-level singleton fail.
  - **Phase A**: `orphan_scanner.py` module-level `_worker_engine` / `_sessionmaker_cache` 제거 + `create_worker_engine_and_sm()` 도입 (backtest.py:31 mirror) + `_async_scan_stuck_orders()` per-call engine + finally `engine.dispose()`. 신규 4 tests + 회귀 fix 7 monkeypatch.
  - **Phase B**: `websocket_task.py` `from src.common.database import async_session_factory` 제거 + per-call engine + `_stream_main()` outer try/finally `engine.dispose()` (long-running stream lifetime hold + BaseException 통과). 신규 8 tests (+4 BaseException: BybitAuthError / Exception / CancelledError / KeyboardInterrupt). codex G.0 P1 #3 fix.
  - **Phase C** (codex G.0 P1 #1 격상, 사용자 wedge 확장 채택): `tasks/trading.py` 동일 module-level singleton 제거 + `_async_execute` / `_async_fetch_order_status` per-call engine + finally dispose. `_execute_with_session` / `_fetch_order_status_with_session` helper 분리. 신규 7 tests + 회귀 fix 16 monkeypatch (test_celery_task 5 + test_fetch_order_status_task 11). dogfood Day 5 broker side effect ↔ DB 분기 silent fail 차단.
  - **자동 검증**: 신규 19 tests 100% PASS / ruff 0 / mypy 0 (9 source files). 전체 1235 tests 중 957 passed / 4 failed / 296 errors / 18 skipped. 4 failed + 296 errors = **`InvalidPasswordError` (DB 인증) — Sprint 16 dev-log §3.3 동일 pre-existing infra 문제**, 본 sprint 무관.
  - **codex 게이트**: G.0 (medium, iter cap 2, session `019de440-...`) — P1 #1+#2+#3 발견 + master plan v2.1 보정 (Phase C 옵션→필수, Phase D 신규, Phase B test scope 확장). 219k tokens. iter 2 codex resume empty 응답 (시간 절약 위해 skip). G.2 challenge skip — 시간 제약 + 잔존 P1 codex 가 G.0 에서 예측 (asyncio.run 두 번 연속 fail).
  - **라이브 재검증 (격리 docker post-restart)**: **1st task succeeded (0.11s)** — Phase 0 의 100% silent fail 대비 진전. **2nd/3rd task fail** — RuntimeError "attached to a different loop" / InterfaceError "another operation is in progress" 재발. **잔존 P1 critical** — systematic-debugging Phase 4.5 architectural problem confirmed (3+ fixes 후 다른 module-level state 가 stale).
  - **Phase C+ mitigation**: `worker_max_tasks_per_child=1` celery_app.py 추가. 효과 부분적 — 같은 child 가 broker prefetch 로 multi-task 처리 후 종료.
  - **신규 BL 등록**: **BL-080** scan/reconcile/trading prefork-safe **architectural fix** (asyncpg/SQLAlchemy module-level state reset). Sprint 18 우선. trigger: self-assessment 5 → ≥7. est L (1-2일). Question: backtest.reclaim_stale 정상 / 우리 task fail diff 정밀 분석 필요.
  - **합계 변동**: 53 → 54 BL (BL-080 신규).
  - dev-log: [`2026-05-02-sprint17-prefork-fix.md`](docs/dev-log/2026-05-02-sprint17-prefork-fix.md). 사용자 stage→main PR + Sprint 18 BL-080 root fix 우선.
  - 브랜치: `stage/h2-sprint17` — 사용자 수동 stage→main PR. 다음 prompt: `~/.claude/plans/h2-sprint-18-prompt.md` (BL-080 architectural fix 명시).
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
