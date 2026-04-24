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

```bash
# Frontend (Next.js 16)
cd frontend && pnpm dev          # 개발 서버 (http://localhost:3000)
cd frontend && pnpm build        # 프로덕션 빌드
cd frontend && pnpm test         # 테스트
cd frontend && pnpm lint         # 린트
cd frontend && pnpm tsc --noEmit # 타입 체크

# Backend (FastAPI)
cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000  # 개발 서버
cd backend && pytest -v          # 테스트
cd backend && ruff check .       # 린트
cd backend && mypy src/          # 타입 체크
cd backend && alembic upgrade head       # 마이그레이션 적용
cd backend && alembic revision --autogenerate -m "description"  # 마이그레이션 생성

# Infrastructure
docker compose up -d             # 전체 서비스 (DB, Redis, TimescaleDB)
docker compose logs -f backend   # 백엔드 로그

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
