Reading additional input from stdin...
OpenAI Codex v0.122.0 (research preview)

---

workdir: /Users/woosung/project/agy-project/quant-bridge
model: gpt-5.4
provider: openai
approval: never
sandbox: read-only
reasoning effort: medium
reasoning summaries: none
session id: 019db608-dd25-73e3-b3a9-ceee8db36dd7

---

user
You are an adversarial code reviewer evaluating Worker 3 (W3) of QuantBridge Sprint X1+X3.

## Inputs

- Plan: /Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md
- Diff (vs stage/x1-x3-indicator-ui): /tmp/w3-diff.txt
- Worker self-review: /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md

## Context

Goal: remove "width(-1)" recharts ResponsiveContainer warning in EquityChart. User memory rule LESSON-004: useEffect dep array MUST NOT contain RQ/Zustand/unstable refs — primitive only. eslint-disable react-hooks/\* forbidden.

## 7 Questions (answer EACH explicitly)

1. Acceptance Criteria 정량 (5 items in plan §2 quantitative) actually met? Cite test counts and tsc/lint exit codes from worker report.
2. Spurious PASS scenarios? E.g., does the test actually catch a regression if mount gate is removed? Worker claims it does — verify by reading the test diff.
3. TDD evidence: did test fail FIRST before implementation, then pass? Or were they written together?
4. Regression surface: any side-effects on existing FE tests? Other components importing EquityChart?
5. Edge cases (empty data, SSR pre-hydration, large points, resize-after-render, ResizeObserver missing) covered?
6. **CRITICAL — LESSON-004 compliance**: useEffect dep array — list every dep, prove none is RQ/Zustand/unstable function ref. Check for eslint-disable react-hooks/\*.
7. Final verdict: GO | GO_WITH_FIX | MAJOR_REVISION | NO_GO + confidence 1-10

Be specific — cite file:line for any issues.
codex
요청 범위는 W3 변경에 대한 적대적 리뷰입니다. 먼저 지시된 컨텍스트 파일들과 실제 diff, 관련 구현/테스트 파일을 읽어서 7개 질문을 근거 중심으로 검증하겠습니다.
exec
/bin/zsh -lc "if test -f docs/README.md; then sed -n '1,220p' docs/README.md; fi" in /Users/woosung/project/agy-project/quant-bridge
exec
/bin/zsh -lc "pwd && test -f AGENTS.md && sed -n '1,220p' AGENTS.md" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:

# QuantBridge — 문서 인덱스

> TradingView Pine Script → 백테스트 → 데모/라이브 트레이딩 플랫폼

## 기술 스택

| 영역            | 기술                                                                        |
| --------------- | --------------------------------------------------------------------------- |
| Frontend        | Next.js 16, TypeScript, Tailwind CSS v4, shadcn/ui v4, React Query, Zustand |
| Backend         | FastAPI, Python 3.11+, SQLModel, Pydantic V2, Celery                        |
| Auth            | Clerk (Frontend + Backend JWT 검증)                                         |
| Database        | PostgreSQL + TimescaleDB + Redis                                            |
| Backtest Engine | vectorbt, pandas-ta, Optuna                                                 |
| Exchange        | CCXT (Bybit, Binance, OKX)                                                  |
| Infra           | Docker Compose (dev)                                                        |

## 문서 구조

| 디렉토리                               | 내용                                   | 상태     |
| -------------------------------------- | -------------------------------------- | -------- |
| [00_project/](./00_project/)           | 프로젝트 비전, 개요                    | ✅ 완료  |
| [01_requirements/](./01_requirements/) | 요구사항 개요, REQ 카탈로그, Pine 분석 | ✅ 완료  |
| [02_domain/](./02_domain/)             | 도메인 개요, 엔티티, 상태 머신         | ✅ 완료  |
| [03_api/](./03_api/)                   | API 엔드포인트 스펙                    | ✅ 활성  |
| [04_architecture/](./04_architecture/) | ERD, 시스템 아키텍처, 데이터 흐름      | ✅ 완료  |
| [05_env/](./05_env/)                   | 로컬 셋업, 환경 변수, Clerk 가이드     | ✅ 완료  |
| [06_devops/](./06_devops/)             | Docker Compose, CI/CD, Pre-commit      | ✅ 완료  |
| [07_infra/](./07_infra/)               | 배포·Observability·Runbook (draft)     | 📝 Draft |
| [DESIGN.md](../DESIGN.md)              | 디자인 시스템 (색상, 타이포, 컴포넌트) | ✅ 확정  |
| [prototypes/](./prototypes/)           | Stage 2 HTML 프로토타입 (12개 화면)    | ✅ 확정  |
| [dev-log/](./dev-log/)                 | ADR (의사결정 기록)                    | 활성     |
| [guides/](./guides/)                   | 개발 가이드, Sprint 킥오프 템플릿      | 활성     |
| [TODO.md](./TODO.md)                   | 작업 추적                              | 활성     |

## 빠른 시작

```bash
# 1. 인프라 실행
docker compose up -d

# 2. Frontend
cd frontend && pnpm install && pnpm dev

# 3. Backend
cd backend && uv sync && uvicorn src.main:app --reload
```

## 핵심 의사결정 (gstack 스킬 확정)

> 아래 결정은 `/office-hours` + `/autoplan` (Codex+Claude 듀얼 검증) 으로 확정됨.
> **규칙 변경 전 반드시 ADR 확인 및 보안/아키텍처 재검토 필요.**

- **제품 프레이밍:** QuantBridge = TradingView Trust Layer (범용 퀀트 ❌)
  MVP 핵심 화면: Import → Verify → Verdict
  타겟: 파트타임 크립토 트레이더, $1K~$50K, Python 없음
  `[/office-hours 2026-04-13]`

- **Pine 런타임 + 파서 범위:** [ADR-003](./dev-log/003-pine-runtime-safety-and-parser-scope.md)
  - `exec()`/`eval()` 금지 → 인터프리터 패턴
  - 미지원 함수 1개라도 있으면 전체 "Unsupported" (부분 실행 금지)
  - Celery zombie task 복구 인프라 필수 (on_failure + Beat cleanup + cancel)
  - TV 상위 50개 전략 분류 선행 (80%+ 커버리지 가정 폐기)
    `[/autoplan 2026-04-13, Codex+Claude 듀얼 검증]`

## 주요 문서 바로가기

| 문서                                                                                                         | 설명                                    |
| ------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| [DESIGN.md](../DESIGN.md)                                                                                    | 디자인 시스템 (Stage 2 산출물)          |
| [QUANTBRIDGE_PRD.md](../QUANTBRIDGE_PRD.md)                                                                  | 상세 PRD                                |
| [AGENTS.md](../AGENTS.md)                                                                                    | AI 에이전트 컨텍스트                    |
| [.ai/](../.ai/)                                                                                              | 코딩 규칙                               |
| [01_requirements/requirements-overview.md](./01_requirements/requirements-overview.md)                       | 요구사항 개요 + REQ 인덱스              |
| [01_requirements/req-catalog.md](./01_requirements/req-catalog.md)                                           | REQ-### 상세 카탈로그                   |
| [02_domain/domain-overview.md](./02_domain/domain-overview.md)                                               | 8 도메인 경계 + 책임 매트릭스           |
| [02_domain/entities.md](./02_domain/entities.md)                                                             | ENT-### 엔티티 카탈로그                 |
| [02_domain/state-machines.md](./02_domain/state-machines.md)                                                 | 도메인 상태 전이도                      |
| [04_architecture/system-architecture.md](./04_architecture/system-architecture.md)                           | C4 다이어그램 + 인증/에러 경계          |
| [04_architecture/data-flow.md](./04_architecture/data-flow.md)                                               | 도메인별 시퀀스 다이어그램              |
| [05_env/local-setup.md](./05_env/local-setup.md)                                                             | 로컬 개발 환경 5분 셋업                 |
| [05_env/env-vars.md](./05_env/env-vars.md)                                                                   | 환경 변수 의미·획득법 카탈로그          |
| [05_env/clerk-setup.md](./05_env/clerk-setup.md)                                                             | Clerk 외부 의존성 셋업                  |
| [06_devops/docker-compose-guide.md](./06_devops/docker-compose-guide.md)                                     | Compose 운영 가이드                     |
| [06_devops/ci-cd.md](./06_devops/ci-cd.md)                                                                   | CI 잡 그래프 + 게이트                   |
| [06_devops/pre-commit.md](./06_devops/pre-commit.md)                                                         | husky + lint-staged 가이드              |
| [07_infra/deployment-plan.md](./07_infra/deployment-plan.md)                                                 | 배포 옵션 비교 (draft)                  |
| [07_infra/observability-plan.md](./07_infra/observability-plan.md)                                           | Observability 계획 (draft)              |
| [07_infra/runbook.md](./07_infra/runbook.md)                                                                 | 운영 Runbook (draft)                    |
| [guides/development-methodology.md](./guides/development-methodology.md)                                     | 6-Stage 개발 방법론 + 병렬 개발 전략    |
| [guides/sprint-kickoff-template.md](./guides/sprint-kickoff-template.md)                                     | Sprint 킥오프 프롬프트 템플릿           |
| [dev-log/001-tech-stack.md](./dev-log/001-tech-stack.md)                                                     | ADR-001: 기술 스택 결정                 |
| [dev-log/002-parallel-scaffold-strategy.md](./dev-log/002-parallel-scaffold-strategy.md)                     | ADR-002: 병렬 스캐폴딩 전략             |
| [dev-log/003-pine-runtime-safety-and-parser-scope.md](./dev-log/003-pine-runtime-safety-and-parser-scope.md) | ADR-003: Pine 런타임 안전성 + 파서 범위 |
| [dev-log/004-pine-parser-approach-selection.md](./dev-log/004-pine-parser-approach-selection.md)             | ADR-004: Pine 파서 접근법 선택          |

succeeded in 0ms:
/Users/woosung/project/agy-project/quant-bridge

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
- **다음:** TabParse FE 1질문 UX (별도 세션, FE 따라잡기) · Sprint 7d (OKX + Trading Sessions) H1 내 · pine_v2 H2 심화 (local history ring, valuewhen cap, user function 호출 사이트 stdlib state isolation)

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

exec
/bin/zsh -lc "sed -n '1,240p' docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:

# W3 — EquityChart `width(-1)` Warning 제거

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 3 / 5
> **Branch:** `stage/x1-x3-indicator-ui`
> **TDD Mode:** **test + impl 동시 허용** — pure UI 렌더링 (no hooks/state/effect 로직 변경)

---

## 1. Context

QuantBridge 는 Next.js 16 FE + FastAPI BE 의 퀀트 플랫폼. backtest 상세 페이지 (`/backtests/[id]`) 는 `recharts` 기반 `EquityChart` 를 사용한다.

**현재 공백**: 브라우저 콘솔에 `Warning: width(-1) and height(256) ... ResponsiveContainer` 가 뜬다. 원인은 `ResponsiveContainer` 가 부모 `div` 의 width=0 상태에서 첫 렌더링되는 시점. 이후 resize 로 복구되나 경고가 남음.

**사용자 memory 제약 (LESSON-004)**: useEffect + RQ/Zustand unstable dep 금지. ResizeObserver 사용 시 stable ref 로 한정.

---

## 2. Acceptance Criteria

### 정량

- [ ] Playwright 시나리오: `/backtests/<id>` 로 직접 navigate → 첫 페인트 시점부터 console warning "width(-1)" **0건**
- [ ] FE vitest: `EquityChart` 렌더링 테스트 ≥ 1건 (mount 후 컨테이너 width 0 가정에서 crash 없음)
- [ ] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` 모두 clean
- [ ] 기존 equity 데이터 렌더링 회귀 0 (기존 테스트 PASS)

### 정성

- [ ] ResponsiveContainer 를 감싸는 wrapper 에 **명시적 width** (예: `w-full` + inline `style={{ width: "100%" }}`) 또는 mount 후 조건부 렌더링
- [ ] useEffect 의존 배열에 RQ/Zustand 불안정 참조 금지 — primitive dep 만
- [ ] shadcn/ui v4 + Tailwind v4 관례 유지 (inline style 은 최소화, className 우선)

---

## 3. File Structure

**수정:**

- `frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx` — ResponsiveContainer 안정화

**신규:**

- `frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx` — mount 테스트

---

## 4. TDD Tasks

### T1. Failing test (mount 시 crash/warning 가드)

**Step 1 — vitest 테스트 생성:**

```tsx
// frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { EquityPoint } from "@/features/backtest/schemas";
import { EquityChart } from "../equity-chart";

const POINTS: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
  { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
];

describe("EquityChart", () => {
  it("renders empty state when no points", () => {
    render(<EquityChart points={[]} />);
    expect(screen.getByText(/Equity 데이터가 없습니다/)).toBeInTheDocument();
  });

  it("mounts without recharts width(-1) warning", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<EquityChart points={POINTS} />);

    const w = warnSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    const e = errSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    expect(w || e).toBe(false);

    warnSpy.mockRestore();
    errSpy.mockRestore();
  });
});
```

**Step 2 — 실패 확인 (warning 여부는 환경 의존적이므로 최소한 render crash 없음을 검증):**

```bash
cd frontend && pnpm test -- --run equity-chart.test
```

Expected: 가능하면 FAIL 또는 render crash; 적어도 smoke 형태로 돌아감 (완전 FAIL 이 아니어도 mount 보장).

### T2. ResponsiveContainer 안정화 구현

**Step 3 — `equity-chart.tsx` 수정** (핵심 아이디어: min-width inline + 부모 컨테이너에 `w-full` 보장 + mount gate):

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { EquityPoint } from "@/features/backtest/schemas";
import {
  downsampleEquity,
  formatCurrency,
  formatDate,
} from "@/features/backtest/utils";

interface EquityChartProps {
  points: readonly EquityPoint[];
  maxPoints?: number;
}

interface ChartDatum {
  ts: number;
  value: number;
  label: string;
}

export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
  const data = useMemo<ChartDatum[]>(() => {
    const sampled = downsampleEquity(points, maxPoints);
    return sampled.map((p) => ({
      ts: new Date(p.timestamp).getTime(),
      value: p.value,
      label: formatDate(p.timestamp),
    }));
  }, [points, maxPoints]);

  // mount gate — ResponsiveContainer 가 width=0 로 첫 렌더링되는 것을 회피.
  // CSR only 환경에서만 실제 차트 마운트.
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []); // primitive-only dep array — LESSON-004 준수

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Equity 데이터가 없습니다
      </div>
    );
  }

  if (!isMounted) {
    return <div className="h-64 w-full" aria-busy="true" />;
  }

  return (
    <div className="h-64 w-full" style={{ minWidth: 0 }}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart
          data={data}
          margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={32} />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => formatCurrency(v, 0)}
            width={80}
          />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? formatCurrency(value) : String(value)
            }
            labelFormatter={(label) => (label == null ? "" : String(label))}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="currentColor"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**근거:**

- `useState(false) + useEffect(() => setIsMounted(true), [])` 패턴은 Next.js SSR hydration 이후에만 ResponsiveContainer 를 mount → 첫 페인트 시 width=0 회피
- primitive-only dep `[]` → LESSON-004 위반 없음
- `minWidth={0}` (recharts prop) 는 defensive 하게 추가
- `aria-busy="true"` placeholder 는 동일 크기 (`h-64 w-full`) 를 유지해 layout shift 방지

**Step 4 — 녹색 확인:**

```bash
cd frontend && pnpm test -- --run equity-chart.test
cd frontend && pnpm tsc --noEmit
cd frontend && pnpm lint
```

Expected: 모두 clean.

### T3. Playwright live smoke (선택 — 조건 충족 시)

FE worker 환경에서 dev 서버 mount 가능하면:

```bash
cd frontend && pnpm dev &
# 백그라운드 3~5초 대기 후
# Playwright MCP 로 navigate → console 모니터
```

Worker 환경에서 `pnpm dev` 가 안 되면 이 step 스킵 가능. Phase 4 합류 단계에서 orchestrator 가 Playwright 로 최종 검증.

### T4. Worker-side codex review 1-pass

```bash
codex exec --sandbox read-only "Review git diff for equity-chart width(-1) fix. Check: (1) useEffect dep array is primitive-only per LESSON-004, (2) no RQ/Zustand unstable ref in dep, (3) SSR-safe (no window access before mount), (4) layout shift minimized (placeholder same size), (5) recharts ResponsiveContainer usage idiomatic."
```

출력 → `docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md`.

### T5. Stage push

exec
/bin/zsh -lc "sed -n '1,260p' .claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md" in /Users/woosung/project/agy-project/quant-bridge
exec
/bin/zsh -lc "sed -n '1,260p' /tmp/w3-diff.txt" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:

# W3 — Codex Self-Review (EquityChart width(-1) fix)

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 3 / 5
> **Plan:** [docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md](../plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md)
> **Reviewer:** `codex-cli 0.122.0` (sandbox=read-only)

---

## 1. Scope

- 대상 파일:
  - `frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx` (구현)
  - `frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx` (신규 테스트)
- 체크 항목:
  1. `useEffect` dep primitive-only (LESSON-004 준수)
  2. `eslint-disable react-hooks/*` 사용 없음
  3. SSR-safe (no window/document top-level, `ResizeObserver` typeof 가드)
  4. layout shift 최소화 (`h-64 w-full` placeholder 동일 크기)
  5. recharts `ResponsiveContainer` 사용 idiomatic + width 측정 gate
  6. 테스트가 jsdom 에서 실제로 `width(-1)` 회귀를 catch 가능한지

---

## 2. Review 1-pass (GO_WITH_FIX)

**요약:** 구현은 문제 없음. 테스트의 회귀 탐지력이 부족 — mount gate 를 제거해도 테스트가 실패하지 않을 가능성. DOM-level (`.recharts-responsive-container` 존재 여부) 검증과 width≥1 분기 검증을 추가할 것.

**지적사항:**

1. `console.warn/error` 스파이에 `width(-1)` 문자열이 없다는 검증만으로는 회귀 탐지력이 약함. 현재 환경에서 경고가 발생하지 않는다는 사실만 확인.
2. `width<1` / `width≥1` 분기를 DOM 레벨에서 검증하지 않음.

---

## 3. 수정 적용

테스트를 3개로 확장:

1. **empty state** — 기존 유지 (`points=[]` → "Equity 데이터가 없습니다").
2. **width=0 분기 (jsdom 기본)** — `ResizeObserver` 삭제 + `getBoundingClientRect` width=0 상황에서:
   - `.recharts-responsive-container` 가 DOM 에 **없어야** 함
   - `[aria-busy="true"]` placeholder 가 **존재해야** 함
   - console.warn/error 에서 `width(-1)` 문자열 **0건**
3. **width≥1 분기 (ResizeObserver mock)** — MockResizeObserver 로 width=800 callback 발화:
   - 콜백 직전: `.recharts-responsive-container` 없음
   - `roInstances[0].cb([{ contentRect: { width: 800 } }])` + `act()` 후: `.recharts-responsive-container` 존재
   - placeholder `[aria-busy="true"]` 사라짐
   - jsdom 내부 layout 부재로 인한 ResponsiveContainer 자체 warning 은 본 테스트 범위 밖 (Phase 4 Playwright 가 담당) — 주석 명시

---

## 4. Review 2-pass (GO)

**판정:** `GO` / **신뢰도:** `8/10`

**Codex 원문 요약:**

- (1) 회귀 탐지력: mount gate 제거 시 테스트 b (width=0 경로) 가 실패함. 탐지력 충분.
- (2) width-0 / width≥1 분기: 상태 분기 기준 양쪽 모두 검증됨. 다만 `equity-chart.tsx:67` 의 "초기 `getBoundingClientRect().width >= 1` fast path" 자체는 별도 검증 없음 (minor).
- (3) LESSON-004 / unused-import lint: 리스크 없음. `useEffect` dep `[]` 안정적, import 모두 사용 중.

**남은 minor:** initial-width fast-path (line 67-71) 의 단위 테스트는 없음. `getBoundingClientRect` mock 이 필요해 테스트 복잡도가 증가하는 대비 효익이 낮아 **skip 결정**. ResizeObserver 분기가 fast-path 와 같은 `setHasWidth(true)` 를 호출하므로 mount 후 동작은 등가.

---

## 5. 수동 검증 결과

```bash
$ cd frontend && pnpm test -- --run equity-chart.test
  ✓ src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx (3 tests) 21ms
  Test Files  1 passed (1)
      Tests  3 passed (3)

$ cd frontend && pnpm test -- --run
  Test Files  24 passed (24)
      Tests  140 passed (140)

$ cd frontend && pnpm tsc --noEmit
  exit=0

$ cd frontend && pnpm lint
  exit=0  (0 errors / 0 warnings)
```

---

## 6. AC 체크리스트 (plan §2)

### 정량

- [x] FE vitest: `EquityChart` 렌더링 테스트 ≥ 1건 (mount 후 컨테이너 width 0 가정에서 crash 없음) → **3건**
- [x] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` 모두 clean → **clean**
- [x] 기존 equity 데이터 렌더링 회귀 0 (기존 테스트 PASS) → **139/139 기존 + 3 신규 = 140 PASS**
- [ ] Playwright 시나리오: `/backtests/<id>` navigate → 첫 페인트부터 console "width(-1)" 0건 → **Phase 4 orchestrator 담당 (worker 환경 미실행)**

### 정성

- [x] ResponsiveContainer 를 감싸는 wrapper 에 명시적 width (`w-full` + `style={{ minWidth: 0 }}`) 및 mount gate
- [x] useEffect 의존 배열에 RQ/Zustand 불안정 참조 금지 — **`[]` primitive-only**
- [x] shadcn/ui v4 + Tailwind v4 관례 유지 (inline style `minWidth: 0` 만 recharts 요구로 사용)

---

## 7. Edge Case 커버 (plan §5)

| Edge case                               | 처리                                                                                                      |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `data.length === 0`                     | 기존 "Equity 데이터가 없습니다" 분기 유지 + `render(<EquityChart points={[]} />)` 테스트                  |
| SSR pre-hydration                       | `useEffect` 내부에서만 측정/mount → server 에선 placeholder 렌더. `ResizeObserver` typeof 가드로 SSR 안전 |
| props.points 변경 (resize 후 re-render) | `data` useMemo dep `[points, maxPoints]` 유지 — 기존 로직 회귀 없음                                       |
| 매우 큰 points (maxPoints=1000 초과)    | `downsampleEquity` 로직 그대로 유지                                                                       |

---

## 8. LESSON-004 self-check

**useEffect dep array 증명:**

```tsx
// equity-chart.tsx:60-92
useEffect(() => {
  const node = wrapperRef.current; // ref (stable)
  if (node === null) return;
  // ... initialWidth + ResizeObserver 로직 ...
}, []); // ← primitive-only: 빈 배열
```

- **dep:** `[]` — React Query / Zustand / RHF / Zod 결과 객체 사용 없음
- **클로저 캡처:** `wrapperRef` (ref, stable), `setHasWidth` (React state setter, stable)
- **eslint:** `react-hooks/exhaustive-deps` 경고 없음 (ref/setter 는 캡처해도 안전)
- **eslint-disable:** 사용 없음

---

## 9. jsdom warning catch 가능성 명시

**T1 의 초기 의도:** `console.warn` 에서 `width(-1)` 문자열을 catch.

**실측 결과 (debug 테스트로 확인):**

```text
[w0] ["The width(-1) and height(-1) of chart should be greater than 0, ..."]
```

→ **jsdom 에서도 recharts `ResponsiveContainer` + `LineChart` 체인은 `width(-1)` warning 을 실제로 emit**. 즉 `console.warn` spy 로 catch 가능.

**최종 테스트는 두 계층으로 회귀 검출:**

1. **DOM-level**: mount gate 가 작동하면 `.recharts-responsive-container` 가 width=0 경로에서 mount 되지 않음 → 가장 강력한 가드
2. **Console-level**: 그 결과로 `width(-1)` warning 문자열 0건 — plan 에서 요구한 spy 검증

**mount branch (width≥1) 에서는** ResponsiveContainer 내부 layout 자체 측정이 jsdom 에선 불가하여 별도 `width(-1)` 및 `width(0)` warning 을 발생. 이는 jsdom 한계이며 실제 브라우저에선 발생하지 않음. Phase 4 Playwright live smoke 에서 orchestrator 가 최종 검증.

---

## 10. 최종 판정

**GO** / **신뢰도 8/10** (Codex review 2-pass 기준)

- 구현: mount gate 패턴으로 width=0 경로 차단, LESSON-004 준수
- 테스트: 3건 (empty / width=0 분기 / width≥1 분기) → 회귀 탐지력 충분
- lint / tsc / 전체 vitest: all clean
- 남은 1 항목: Playwright live smoke (Phase 4 orchestrator 담당)

succeeded in 0ms:
diff --git a/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx b/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx
new file mode 100644
index 0000000..d508b18
--- /dev/null
+++ b/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx
@@ -0,0 +1,122 @@
+import { act, render, screen } from "@testing-library/react";
+import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

- +import type { EquityPoint } from "@/features/backtest/schemas";
  +import { EquityChart } from "../equity-chart";
- +// 테스트 데이터: 3 포인트 equity curve
  +const POINTS: EquityPoint[] = [
- { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
- { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
- { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
  +];
- +// jsdom 의 ResizeObserver mock — observer 콜백을 테스트에서 직접 발화시키기 위함.
  +type RoCallback = (entries: Array<{ contentRect: { width: number } }>) => void;
  +let roInstances: Array<{ cb: RoCallback; targets: Element[]; disconnect: () => void }> = [];
- +class MockResizeObserver {
- cb: RoCallback;
- targets: Element[] = [];
- constructor(cb: RoCallback) {
- this.cb = cb;
- roInstances.push({
-      cb,
-      targets: this.targets,
-      disconnect: () => {
-        this.targets = [];
-      },
- });
- }
- observe(target: Element) {
- this.targets.push(target);
- }
- unobserve() {}
- disconnect() {
- this.targets = [];
- }
  +}
- +describe("EquityChart", () => {
- beforeEach(() => {
- roInstances = [];
- // 기본은 ResizeObserver 미정의 (jsdom 기본 동작 — width 0 으로 차트 미마운트)
- delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
- });
-
- afterEach(() => {
- delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
- });
-
- it("renders empty state when no points", () => {
- render(<EquityChart points={[]} />);
- expect(screen.getByText(/Equity 데이터가 없습니다/)).toBeInTheDocument();
- });
-
- it("does not mount ResponsiveContainer when wrapper width is 0 (no width(-1) warning)", () => {
- // jsdom 기본: getBoundingClientRect width === 0 + ResizeObserver 미정의
- // → 차트가 mount 되어선 안 되고 placeholder 만 렌더.
- const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
- const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
-
- const { container } = render(<EquityChart points={POINTS} />);
-
- // Recharts ResponsiveContainer 는 div.recharts-responsive-container 로 mount.
- // 측정 전 placeholder 단계에서는 이 노드가 존재하지 않아야 함.
- expect(
-      container.querySelector(".recharts-responsive-container"),
- ).toBeNull();
- // 동일 크기 placeholder 가 렌더되어 layout shift 가 없어야 함.
- expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
-
- // width(-1) 회귀 경고 0건 확인 (recharts 가 emit 하는 정확한 문자열).
- const hasWarn = warnSpy.mock.calls.some((args) =>
-      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
- );
- const hasErr = errSpy.mock.calls.some((args) =>
-      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
- );
- expect(hasWarn).toBe(false);
- expect(hasErr).toBe(false);
-
- warnSpy.mockRestore();
- errSpy.mockRestore();
- });
-
- it("mounts ResponsiveContainer when ResizeObserver reports width >= 1", () => {
- // ResizeObserver 가 width 800 을 발화하는 환경 — 실제 브라우저 분기를 등가로 검증.
- (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
-      MockResizeObserver;
-
- // 주의: jsdom 은 layout 엔진이 없어 ResponsiveContainer 자체 내부 측정에서
- // 별도 width(-1) warning 을 발생시킬 수 있음 (이 테스트의 책임 밖).
- // 본 테스트는 "wrapper width 측정 후 차트 mount 분기로 정확히 진입한다" 만 검증.
- // 실제 브라우저 환경에서의 warning 0건 확인은 Phase 4 Playwright live smoke 가 담당.
- const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
- const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
-
- const { container } = render(<EquityChart points={POINTS} />);
-
- // 1차 측정 시점에는 jsdom rect.width === 0 → 차트 미마운트.
- expect(
-      container.querySelector(".recharts-responsive-container"),
- ).toBeNull();
- // wrapper 가 ResizeObserver 에 등록되어야 함.
- expect(roInstances).toHaveLength(1);
-
- // ResizeObserver 콜백을 width=800 으로 발화 → setHasWidth(true) → 차트 mount.
- act(() => {
-      roInstances[0]!.cb([{ contentRect: { width: 800 } }]);
- });
-
- // 차트가 mount 되어야 함 (mount 분기 진입 확인).
- expect(
-      container.querySelector(".recharts-responsive-container"),
- ).not.toBeNull();
- // placeholder 는 사라져야 함.
- expect(container.querySelector('[aria-busy="true"]')).toBeNull();
-
- warnSpy.mockRestore();
- errSpy.mockRestore();
- });
  +});
  diff --git a/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx b/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx
  index 1af91a1..986d62a 100644
  --- a/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx
  +++ b/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx
  @@ -1,6 +1,6 @@
  "use client";

-import { useMemo } from "react";
+import { useEffect, useMemo, useRef, useState } from "react";
import {
CartesianGrid,
Line,
@@ -29,6 +29,20 @@ interface ChartDatum {
label: string;
}

+/\*\*

- - EquityChart — backtest 의 equity curve 를 line chart 로 렌더.
- -
- - width(-1) warning 회피 전략:
- - - 부모 div 의 실제 width 를 ResizeObserver 로 측정.
- - - width 가 1 이상으로 측정되기 전까지는 ResponsiveContainer 를 mount 하지 않고
- - 동일 크기의 placeholder 만 렌더링 → recharts 가 width=-1 로 자식 차트에 전달하는 것을 차단.
- - - jsdom 환경: ResizeObserver 가 inert 라 width 가 0 으로 유지 → 차트 미마운트 → warning 0건.
- - - 브라우저 환경: layout 측정 후 ResizeObserver 가 width 를 발화 → 정상 mount.
- -
- - LESSON-004 준수:
- - - useEffect dep 에 RQ/Zustand 결과 객체나 unstable function ref 사용 금지.
- - - 본 컴포넌트는 ref + setter 만 클로저 캡처하고 dep array 는 `[]` (primitive 등가).
- \*/
  export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
  const data = useMemo<ChartDatum[]>(() => {
  const sampled = downsampleEquity(points, maxPoints);
  @@ -39,6 +53,44 @@ export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
  }));
  }, [points, maxPoints]);

- // 부모 wrapper 의 실측 width — 0 이면 차트 미마운트.
- const wrapperRef = useRef<HTMLDivElement | null>(null);
- const [hasWidth, setHasWidth] = useState(false);
-
- useEffect(() => {
- const node = wrapperRef.current;
- if (node === null) {
-      return;
- }
-
- // 1차: 즉시 측정 (CSR 환경에서 layout 이 이미 완료된 경우)
- const initialWidth = node.getBoundingClientRect().width;
- if (initialWidth >= 1) {
-      setHasWidth(true);
-      return;
- }
-
- // 2차: ResizeObserver 로 width 측정 후 한 번만 발화.
- // jsdom 에서는 ResizeObserver 가 미정의이거나 inert → catch 로 안전하게 빠짐.
- if (typeof ResizeObserver === "undefined") {
-      return;
- }
-
- const observer = new ResizeObserver((entries) => {
-      for (const entry of entries) {
-        if (entry.contentRect.width >= 1) {
-          setHasWidth(true);
-          observer.disconnect();
-          break;
-        }
-      }
- });
- observer.observe(node);
- return () => {
-      observer.disconnect();
- };
- }, []); // primitive-only dep array — LESSON-004 준수
- if (data.length === 0) {
  return (
  <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
  @@ -48,39 +100,44 @@ export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
  }
  return (

* <div className="h-64 w-full">
*      <ResponsiveContainer width="100%" height="100%">
*        <LineChart
*          data={data}
*          margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
*        >
*          <CartesianGrid strokeDasharray="3 3" vertical={false} />
*          <XAxis
*            dataKey="label"
*            tick={{ fontSize: 11 }}
*            minTickGap={32}
*          />
*          <YAxis
*            tick={{ fontSize: 11 }}
*            tickFormatter={(v: number) => formatCurrency(v, 0)}
*            width={80}
*          />
*          <Tooltip
*            formatter={(value) =>
*              typeof value === "number" ? formatCurrency(value) : String(value)
*            }
*            labelFormatter={(label) => (label == null ? "" : String(label))}
*          />
*          <Line
*            type="monotone"
*            dataKey="value"
*            stroke="currentColor"
*            strokeWidth={1.5}
*            dot={false}
*            isAnimationActive={false}
*          />
*        </LineChart>
*      </ResponsiveContainer>

- <div ref={wrapperRef} className="h-64 w-full" style={{ minWidth: 0 }}>
-      {hasWidth ? (
-        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
-          <LineChart
-            data={data}
-            margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
-          >
-            <CartesianGrid strokeDasharray="3 3" vertical={false} />
-            <XAxis
-              dataKey="label"
-              tick={{ fontSize: 11 }}
-              minTickGap={32}
-            />
-            <YAxis
-              tick={{ fontSize: 11 }}
-              tickFormatter={(v: number) => formatCurrency(v, 0)}
-              width={80}

codex
이제 실제 워크트리의 파일 내용을 줄 번호 기준으로 확인합니다. 테스트가 정말 회귀를 잡는지, `EquityChart` 사용처가 어디까지 퍼져 있는지, `eslint-disable react-hooks/*`가 숨어 있지 않은지 보겠습니다.
exec
/bin/zsh -lc "nl -ba 'frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx' | sed -n '1,220p'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
1 "use client";
2
3 import { useMemo } from "react";
4 import {
5 CartesianGrid,
6 Line,
7 LineChart,
8 ResponsiveContainer,
9 Tooltip,
10 XAxis,
11 YAxis,
12 } from "recharts";
13
14 import type { EquityPoint } from "@/features/backtest/schemas";
15 import {
16 downsampleEquity,
17 formatCurrency,
18 formatDate,
19 } from "@/features/backtest/utils";
20
21 interface EquityChartProps {
22 points: readonly EquityPoint[];
23 maxPoints?: number;
24 }
25
26 interface ChartDatum {
27 ts: number;
28 value: number;
29 label: string;
30 }
31
32 export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
33 const data = useMemo<ChartDatum[]>(() => {
34 const sampled = downsampleEquity(points, maxPoints);
35 return sampled.map((p) => ({
36 ts: new Date(p.timestamp).getTime(),
37 value: p.value,
38 label: formatDate(p.timestamp),
39 }));
40 }, [points, maxPoints]);
41
42 if (data.length === 0) {
43 return (
44 <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
45 Equity 데이터가 없습니다
46 </div>
47 );
48 }
49
50 return (
51 <div className="h-64 w-full">
52 <ResponsiveContainer width="100%" height="100%">
53 <LineChart
54 data={data}
55 margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
56 >
57 <CartesianGrid strokeDasharray="3 3" vertical={false} />
58 <XAxis
59 dataKey="label"
60 tick={{ fontSize: 11 }}
61 minTickGap={32}
62 />
63 <YAxis
64 tick={{ fontSize: 11 }}
65 tickFormatter={(v: number) => formatCurrency(v, 0)}
66 width={80}
67 />
68 <Tooltip
69 formatter={(value) =>
70 typeof value === "number" ? formatCurrency(value) : String(value)
71 }
72 labelFormatter={(label) => (label == null ? "" : String(label))}
73 />
74 <Line
75 type="monotone"
76 dataKey="value"
77 stroke="currentColor"
78 strokeWidth={1.5}
79 dot={false}
80 isAnimationActive={false}
81 />
82 </LineChart>
83 </ResponsiveContainer>
84 </div>
85 );
86 }

exec
/bin/zsh -lc "nl -ba 'frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx' | sed -n '1,240p'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
nl: frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx: No such file or directory

exec
/bin/zsh -lc 'rg -n "EquityChart|eslint-disable._react-hooks|react-hooks/exhaustive-deps" frontend/src -S' in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
frontend/src/features/strategy/edit-store.ts:10:// useEffect 가 무한 루프 또는 react-hooks/exhaustive-deps 위반을 유발한다 (LESSON-004).
frontend/src/app/(dashboard)/strategies/[id]/edit/\_components/editor-view.tsx:72: /_ eslint-disable react-hooks/set-state-in-effect \*/
frontend/src/app/(dashboard)/backtests/\_components/backtest-detail-view.tsx:23:import { EquityChart } from "./equity-chart";
frontend/src/app/(dashboard)/backtests/\_components/backtest-detail-view.tsx:142: <EquityChart points={bt.equity_curve} />
frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:21:interface EquityChartProps {
frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:32:export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {

exec
/bin/zsh -lc "rg -n \"ResizeObserver|getBoundingClientRect|responsive-container|aria-busy\" frontend/src frontend/test frontend -g '"'!node_modules'"' -S" in /Users/woosung/project/agy-project/quant-bridge
exited 2 in 0ms:
rg: frontend/test: No such file or directory (os error 2)

codex
메인 워크트리에는 W3 수정이 아직 없고, 실제 변경은 worker worktree/diff 기준입니다. 따라서 line reference는 worker worktree의 실제 파일과 diff를 기준으로 잡겠습니다.
exec
/bin/zsh -lc "nl -ba '.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx' | sed -n '1,260p'" in /Users/woosung/project/agy-project/quant-bridge
exec
/bin/zsh -lc "nl -ba '.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx' | sed -n '1,240p'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
1 import { act, render, screen } from "@testing-library/react";
2 import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
3
4 import type { EquityPoint } from "@/features/backtest/schemas";
5 import { EquityChart } from "../equity-chart";
6
7 // 테스트 데이터: 3 포인트 equity curve
8 const POINTS: EquityPoint[] = [
9 { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
10 { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
11 { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
12 ];
13
14 // jsdom 의 ResizeObserver mock — observer 콜백을 테스트에서 직접 발화시키기 위함.
15 type RoCallback = (entries: Array<{ contentRect: { width: number } }>) => void;
16 let roInstances: Array<{ cb: RoCallback; targets: Element[]; disconnect: () => void }> = [];
17
18 class MockResizeObserver {
19 cb: RoCallback;
20 targets: Element[] = [];
21 constructor(cb: RoCallback) {
22 this.cb = cb;
23 roInstances.push({
24 cb,
25 targets: this.targets,
26 disconnect: () => {
27 this.targets = [];
28 },
29 });
30 }
31 observe(target: Element) {
32 this.targets.push(target);
33 }
34 unobserve() {}
35 disconnect() {
36 this.targets = [];
37 }
38 }
39
40 describe("EquityChart", () => {
41 beforeEach(() => {
42 roInstances = [];
43 // 기본은 ResizeObserver 미정의 (jsdom 기본 동작 — width 0 으로 차트 미마운트)
44 delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
45 });
46
47 afterEach(() => {
48 delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
49 });
50
51 it("renders empty state when no points", () => {
52 render(<EquityChart points={[]} />);
53 expect(screen.getByText(/Equity 데이터가 없습니다/)).toBeInTheDocument();
54 });
55
56 it("does not mount ResponsiveContainer when wrapper width is 0 (no width(-1) warning)", () => {
57 // jsdom 기본: getBoundingClientRect width === 0 + ResizeObserver 미정의
58 // → 차트가 mount 되어선 안 되고 placeholder 만 렌더.
59 const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
60 const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
61
62 const { container } = render(<EquityChart points={POINTS} />);
63
64 // Recharts ResponsiveContainer 는 div.recharts-responsive-container 로 mount.
65 // 측정 전 placeholder 단계에서는 이 노드가 존재하지 않아야 함.
66 expect(
67 container.querySelector(".recharts-responsive-container"),
68 ).toBeNull();
69 // 동일 크기 placeholder 가 렌더되어 layout shift 가 없어야 함.
70 expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
71
72 // width(-1) 회귀 경고 0건 확인 (recharts 가 emit 하는 정확한 문자열).
73 const hasWarn = warnSpy.mock.calls.some((args) =>
74 args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
75 );
76 const hasErr = errSpy.mock.calls.some((args) =>
77 args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
78 );
79 expect(hasWarn).toBe(false);
80 expect(hasErr).toBe(false);
81
82 warnSpy.mockRestore();
83 errSpy.mockRestore();
84 });
85
86 it("mounts ResponsiveContainer when ResizeObserver reports width >= 1", () => {
87 // ResizeObserver 가 width 800 을 발화하는 환경 — 실제 브라우저 분기를 등가로 검증.
88 (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
89 MockResizeObserver;
90
91 // 주의: jsdom 은 layout 엔진이 없어 ResponsiveContainer 자체 내부 측정에서
92 // 별도 width(-1) warning 을 발생시킬 수 있음 (이 테스트의 책임 밖).
93 // 본 테스트는 "wrapper width 측정 후 차트 mount 분기로 정확히 진입한다" 만 검증.
94 // 실제 브라우저 환경에서의 warning 0건 확인은 Phase 4 Playwright live smoke 가 담당.
95 const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
96 const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
97
98 const { container } = render(<EquityChart points={POINTS} />);
99
100 // 1차 측정 시점에는 jsdom rect.width === 0 → 차트 미마운트.
101 expect(
102 container.querySelector(".recharts-responsive-container"),
103 ).toBeNull();
104 // wrapper 가 ResizeObserver 에 등록되어야 함.
105 expect(roInstances).toHaveLength(1);
106
107 // ResizeObserver 콜백을 width=800 으로 발화 → setHasWidth(true) → 차트 mount.
108 act(() => {
109 roInstances[0]!.cb([{ contentRect: { width: 800 } }]);
110 });
111
112 // 차트가 mount 되어야 함 (mount 분기 진입 확인).
113 expect(
114 container.querySelector(".recharts-responsive-container"),
115 ).not.toBeNull();
116 // placeholder 는 사라져야 함.
117 expect(container.querySelector('[aria-busy="true"]')).toBeNull();
118
119 warnSpy.mockRestore();
120 errSpy.mockRestore();
121 });
122 });

succeeded in 0ms:
1 "use client";
2
3 import { useEffect, useMemo, useRef, useState } from "react";
4 import {
5 CartesianGrid,
6 Line,
7 LineChart,
8 ResponsiveContainer,
9 Tooltip,
10 XAxis,
11 YAxis,
12 } from "recharts";
13
14 import type { EquityPoint } from "@/features/backtest/schemas";
15 import {
16 downsampleEquity,
17 formatCurrency,
18 formatDate,
19 } from "@/features/backtest/utils";
20
21 interface EquityChartProps {
22 points: readonly EquityPoint[];
23 maxPoints?: number;
24 }
25
26 interface ChartDatum {
27 ts: number;
28 value: number;
29 label: string;
30 }
31
32 /\*_
33 _ EquityChart — backtest 의 equity curve 를 line chart 로 렌더.
34 _
35 _ width(-1) warning 회피 전략:
36 _ - 부모 div 의 실제 width 를 ResizeObserver 로 측정.
37 _ - width 가 1 이상으로 측정되기 전까지는 ResponsiveContainer 를 mount 하지 않고
38 _ 동일 크기의 placeholder 만 렌더링 → recharts 가 width=-1 로 자식 차트에 전달하는 것을 차단.
39 _ - jsdom 환경: ResizeObserver 가 inert 라 width 가 0 으로 유지 → 차트 미마운트 → warning 0건.
40 _ - 브라우저 환경: layout 측정 후 ResizeObserver 가 width 를 발화 → 정상 mount.
41 _
42 _ LESSON-004 준수:
43 _ - useEffect dep 에 RQ/Zustand 결과 객체나 unstable function ref 사용 금지.
44 _ - 본 컴포넌트는 ref + setter 만 클로저 캡처하고 dep array 는 `[]` (primitive 등가).
45 _/
46 export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
47 const data = useMemo<ChartDatum[]>(() => {
48 const sampled = downsampleEquity(points, maxPoints);
49 return sampled.map((p) => ({
50 ts: new Date(p.timestamp).getTime(),
51 value: p.value,
52 label: formatDate(p.timestamp),
53 }));
54 }, [points, maxPoints]);
55
56 // 부모 wrapper 의 실측 width — 0 이면 차트 미마운트.
57 const wrapperRef = useRef<HTMLDivElement | null>(null);
58 const [hasWidth, setHasWidth] = useState(false);
59
60 useEffect(() => {
61 const node = wrapperRef.current;
62 if (node === null) {
63 return;
64 }
65
66 // 1차: 즉시 측정 (CSR 환경에서 layout 이 이미 완료된 경우)
67 const initialWidth = node.getBoundingClientRect().width;
68 if (initialWidth >= 1) {
69 setHasWidth(true);
70 return;
71 }
72
73 // 2차: ResizeObserver 로 width 측정 후 한 번만 발화.
74 // jsdom 에서는 ResizeObserver 가 미정의이거나 inert → catch 로 안전하게 빠짐.
75 if (typeof ResizeObserver === "undefined") {
76 return;
77 }
78
79 const observer = new ResizeObserver((entries) => {
80 for (const entry of entries) {
81 if (entry.contentRect.width >= 1) {
82 setHasWidth(true);
83 observer.disconnect();
84 break;
85 }
86 }
87 });
88 observer.observe(node);
89 return () => {
90 observer.disconnect();
91 };
92 }, []); // primitive-only dep array — LESSON-004 준수
93
94 if (data.length === 0) {
95 return (
96 <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
97 Equity 데이터가 없습니다
98 </div>
99 );
100 }
101
102 return (
103 <div ref={wrapperRef} className="h-64 w-full" style={{ minWidth: 0 }}>
104 {hasWidth ? (
105 <ResponsiveContainer width="100%" height="100%" minWidth={0}>
106 <LineChart
107 data={data}
108 margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
109 >
110 <CartesianGrid strokeDasharray="3 3" vertical={false} />
111 <XAxis
112 dataKey="label"
113 tick={{ fontSize: 11 }}
114 minTickGap={32}
115 />
116 <YAxis
117 tick={{ fontSize: 11 }}
118 tickFormatter={(v: number) => formatCurrency(v, 0)}
119 width={80}
120 />
121 <Tooltip
122 formatter={(value) =>
123 typeof value === "number" ? formatCurrency(value) : String(value)
124 }
125 labelFormatter={(label) => (label == null ? "" : String(label))}
126 />
127 <Line
128 type="monotone"
129 dataKey="value"
130 stroke="currentColor"
131 strokeWidth={1.5}
132 dot={false}
133 isAnimationActive={false}
134 />
135 </LineChart>
136 </ResponsiveContainer>
137 ) : (
138 // 측정 전 placeholder — h-64 w-full 동일 크기로 layout shift 방지
139 <div className="h-full w-full" aria-busy="true" />
140 )}
141 </div>
142 );
143 }

exec
/bin/zsh -lc "nl -ba '.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/backtest-detail-view.tsx' | sed -n '120,170p'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
120 ) : null}
121
122 {effectiveStatus === "completed" && !bt.metrics ? (
123 <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
124 결과를 불러오는 중…
125 </p>
126 ) : null}
127
128 {effectiveStatus === "completed" && bt.metrics ? (
129 <Tabs defaultValue="overview">
130 <TabsList>
131 <TabsTrigger value="overview">개요</TabsTrigger>
132 <TabsTrigger value="metrics">성과 지표</TabsTrigger>
133 <TabsTrigger value="analysis">거래 분석</TabsTrigger>
134 <TabsTrigger value="trades">거래 목록</TabsTrigger>
135 </TabsList>
136
137 <TabsContent value="overview" className="mt-4 space-y-4">
138 <MetricsCards metrics={bt.metrics} />
139 {bt.equity_curve && bt.equity_curve.length > 0 && (
140 <section className="rounded-xl border bg-card p-4">
141 <h2 className="mb-2 text-sm font-medium">Equity Curve</h2>
142 <EquityChart points={bt.equity_curve} />
143 </section>
144 )}
145 </TabsContent>
146
147 <TabsContent value="metrics" className="mt-4">
148 <MetricsDetail metrics={bt.metrics} />
149 </TabsContent>
150
151 <TabsContent value="analysis" className="mt-4">
152 <TradeAnalysis metrics={bt.metrics} />
153 </TabsContent>
154
155 <TabsContent value="trades" className="mt-4">
156 {trades.isLoading ? (
157 <p className="text-sm text-muted-foreground">
158 거래 불러오는 중…
159 </p>
160 ) : trades.isError ? (
161 <p className="text-sm text-destructive">
162 거래 기록 로드 실패: {trades.error?.message}
163 </p>
164 ) : (
165 <TradeTable trades={trades.data?.items ?? []} />
166 )}
167 </TabsContent>
168 </Tabs>
169 ) : null}
170 </div>

exec
/bin/zsh -lc "rg -n \"EquityChart|eslint-disable._react-hooks|react-hooks/exhaustive-deps|ResizeObserver|getBoundingClientRect|aria-busy|recharts-responsive-container\" '.claude/worktrees/agent-a3916c29/frontend/src' -S" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:5:import { EquityChart } from "../equity-chart";
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:14:// jsdom 의 ResizeObserver mock — observer 콜백을 테스트에서 직접 발화시키기 위함.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:18:class MockResizeObserver {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:40:describe("EquityChart", () => {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:43: // 기본은 ResizeObserver 미정의 (jsdom 기본 동작 — width 0 으로 차트 미마운트)
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:44: delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:48: delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:52: render(<EquityChart points={[]} />);
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:57: // jsdom 기본: getBoundingClientRect width === 0 + ResizeObserver 미정의
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:62: const { container } = render(<EquityChart points={POINTS} />);
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:64: // Recharts ResponsiveContainer 는 div.recharts-responsive-container 로 mount.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:67: container.querySelector(".recharts-responsive-container"),
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:70: expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:86: it("mounts ResponsiveContainer when ResizeObserver reports width >= 1", () => {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:87: // ResizeObserver 가 width 800 을 발화하는 환경 — 실제 브라우저 분기를 등가로 검증.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:88: (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:89: MockResizeObserver;
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:98: const { container } = render(<EquityChart points={POINTS} />);
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:102: container.querySelector(".recharts-responsive-container"),
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:104: // wrapper 가 ResizeObserver 에 등록되어야 함.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:107: // ResizeObserver 콜백을 width=800 으로 발화 → setHasWidth(true) → 차트 mount.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:114: container.querySelector(".recharts-responsive-container"),
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:117: expect(container.querySelector('[aria-busy="true"]')).toBeNull();
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/backtest-detail-view.tsx:23:import { EquityChart } from "./equity-chart";
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/backtest-detail-view.tsx:142: <EquityChart points={bt.equity_curve} />
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:21:interface EquityChartProps {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:33: _ EquityChart — backtest 의 equity curve 를 line chart 로 렌더.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:36: _ - 부모 div 의 실제 width 를 ResizeObserver 로 측정.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:39: _ - jsdom 환경: ResizeObserver 가 inert 라 width 가 0 으로 유지 → 차트 미마운트 → warning 0건.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:40: _ - 브라우저 환경: layout 측정 후 ResizeObserver 가 width 를 발화 → 정상 mount.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:46:export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:67: const initialWidth = node.getBoundingClientRect().width;
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:73: // 2차: ResizeObserver 로 width 측정 후 한 번만 발화.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:74: // jsdom 에서는 ResizeObserver 가 미정의이거나 inert → catch 로 안전하게 빠짐.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:75: if (typeof ResizeObserver === "undefined") {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:79: const observer = new ResizeObserver((entries) => {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:139: <div className="h-full w-full" aria-busy="true" />
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/edit-store.ts:10:// useEffect 가 무한 루프 또는 react-hooks/exhaustive-deps 위반을 유발한다 (LESSON-004).
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/\_components/editor-view.tsx:72: /_ eslint-disable react-hooks/set-state-in-effect \*/

codex
TDD 여부는 self-report만으로는 판단이 약합니다. 커밋/파일 히스토리에서 fail-first 증거가 있는지 추가로 확인하겠습니다.
exec
/bin/zsh -lc "git -C '.claude/worktrees/agent-a3916c29' log --oneline --decorate -n 8" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ytYo9oEx' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-o2ihmNHB' (errno=Operation not permitted)
acfa9b1 (HEAD -> feat/x1x3-w3-equity-chart-fix) fix(backtest): EquityChart width(-1) warning via ResizeObserver mount gate (W3)
840f9a9 (origin/stage/x1-x3-indicator-ui, worktree-agent-a2493f6f, stage/x1-x3-indicator-ui) docs(plans): Sprint X1+X3 5 worker plans + review/report dirs
aad44e2 (origin/main, origin/HEAD, worktree-agent-a5bc9ad0, worktree-agent-a3916c29, worktree-agent-a0d2ef2b, w4/trade-analysis-breakdown, main) fix(dogfood): FE detail refetch on terminal + pine math stdlib 확장 (#57)
8374ecc chore(infra): OHLCV_PROVIDER 기본값 fixture → timescale (#56)
bf5c5ed fix(pine_v2): opposite-direction auto-flip + 7 extended metrics (dogfood 정확성) (#55)
a89bf99 merge: pine_v2 migration + when= fix (PR #52 + #54)
72789a9 (origin/stage/pine-v2-migration) fix(pine_v2): strategy.close/close_all 의 when= kwarg 지원 (#54)
cdc4eac fix(worker): funding/dogfood_report 에 PR #51 asyncio loop fix 패턴 적용 (#53)

exec
/bin/zsh -lc "git -C '.claude/worktrees/agent-a3916c29' log --oneline --follow -- 'frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-4NuDRFC1' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-mYL1haKQ' (errno=Operation not permitted)
acfa9b1 fix(backtest): EquityChart width(-1) warning via ResizeObserver mount gate (W3)
f307f60 feat(sprint-fe04): Backtest UI MVP (form · polling · equity chart · trade table) (#26)

exec
/bin/zsh -lc "git -C '.claude/worktrees/agent-a3916c29' status --short" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-B1BnadNC' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-QrAfMJrP' (errno=Operation not permitted)

exec
/bin/zsh -lc "git -C '.claude/worktrees/agent-a3916c29' log --oneline --follow -- 'frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-MdWYfeMK' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-jHLJzqat' (errno=Operation not permitted)
acfa9b1 fix(backtest): EquityChart width(-1) warning via ResizeObserver mount gate (W3)

codex
회귀 표면을 좁히기 위해 `EquityChart` 주변 테스트와 import fan-out도 확인합니다. 실제로 영향 범위가 단일 사용처인지 보겠습니다.
exec
/bin/zsh -lc "rg -n \"backtest-detail-view|equity-chart|BacktestDetailView|Equity Curve\" '.claude/worktrees/agent-a3916c29/frontend/src' -g '_test.tsx' -S" in /Users/woosung/project/agy-project/quant-bridge
exec
/bin/zsh -lc "find '.claude/worktrees/agent-a3916c29/frontend/src' -path '_**tests**\*' -maxdepth 12 | sed -n '1,200p'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:5:import { EquityChart } from "../equity-chart";

succeeded in 0ms:
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/backtest-form.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/cumulative-pnl.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/\_components/**tests**
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/\_components/**tests**/parse-dialog.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/\_components/**tests**/editor-view.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/\_components/**tests**/delete-dialog.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/\_components/**tests**/parse-dialog-steps.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/backtest/**tests**
.claude/worktrees/agent-a3916c29/frontend/src/features/backtest/**tests**/schemas.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/backtest/**tests**/utils.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/backtest/**tests**/query-keys.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/backtest/**tests**/status-meta.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/trading/**tests**
.claude/worktrees/agent-a3916c29/frontend/src/features/trading/**tests**/ExchangeAccountsPanel.empty.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/features/trading/**tests**/query-keys.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/trading/**tests**/RegisterExchangeAccountDialog.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/features/trading/**tests**/OrdersPanel.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/features/trading/**tests**/OrdersPanel.empty.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/components/**tests**
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/components/**tests**/tag-input.test.tsx
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/**tests**
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/**tests**/edit-store.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/**tests**/query-keys.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/**tests**/draft.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/**tests**/parse-preview-schema.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/features/strategy/**tests**/pine-lexicon.test.ts
.claude/worktrees/agent-a3916c29/frontend/src/components/**tests**
.claude/worktrees/agent-a3916c29/frontend/src/components/**tests**/shortcut-help-dialog.test.tsx

exec
/bin/zsh -lc "sed -n '1,220p' '.claude/worktrees/agent-a3916c29/frontend/package.json'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
{
"name": "quantbridge-frontend",
"version": "0.1.0",
"private": true,
"scripts": {
"dev": "next dev",
"dev:webpack": "next dev",
"build": "next build",
"start": "next start",
"lint": "eslint .",
"format": "prettier --write .",
"format:check": "prettier --check .",
"typecheck": "tsc --noEmit",
"test": "vitest run",
"test:watch": "vitest",
"e2e": "playwright test",
"e2e:install": "playwright install --with-deps chromium"
},
"dependencies": {
"@base-ui/react": "^1.4.0",
"@clerk/nextjs": "^6.0.0",
"@hookform/resolvers": "^3.10.0",
"@monaco-editor/react": "^4.7.0",
"@tanstack/react-query": "^5.59.0",
"@tanstack/react-query-devtools": "^5.59.0",
"class-variance-authority": "^0.7.1",
"clsx": "^2.1.1",
"lucide-react": "^0.468.0",
"next": "^16.2.4",
"next-themes": "^0.4.6",
"radix-ui": "^1.4.3",
"react": "^19.0.0",
"react-dom": "^19.0.0",
"react-hook-form": "^7.72.1",
"recharts": "^3.8.1",
"shadcn": "^4.3.0",
"sonner": "^2.0.7",
"tailwind-merge": "^2.6.1",
"tw-animate-css": "^1.4.0",
"zod": "^4.3.6",
"zustand": "^5.0.0"
},
"devDependencies": {
"@playwright/test": "^1.59.1",
"@tailwindcss/postcss": "^4.0.0",
"@tanstack/eslint-plugin-query": "^5.99.0",
"@testing-library/jest-dom": "^6.5.0",
"@testing-library/react": "^16.0.0",
"@types/node": "^22.0.0",
"@types/react": "^19.0.0",
"@types/react-dom": "^19.0.0",
"@vitejs/plugin-react": "^4.3.0",
"eslint": "^9.0.0",
"eslint-config-next": "^16.0.0",
"eslint-config-prettier": "^9.1.0",
"eslint-plugin-react-compiler": "19.1.0-rc.2",
"eslint-plugin-react-hooks": "^7.1.1",
"jsdom": "^25.0.0",
"postcss": "^8.4.0",
"prettier": "^3.3.0",
"prettier-plugin-tailwindcss": "^0.6.0",
"tailwindcss": "^4.0.0",
"typescript": "^5.6.0",
"vitest": "^2.1.0"
},
"packageManager": "pnpm@9.12.0",
"engines": {
"node": ">=20.0.0"
}
}
exec
/bin/zsh -lc "rg -n \"setupTests|vitest.setup|ResizeObserver\" '.claude/worktrees/agent-a3916c29/frontend' -g '"'!_node_modules_'"' -S" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:14:// jsdom 의 ResizeObserver mock — observer 콜백을 테스트에서 직접 발화시키기 위함.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:18:class MockResizeObserver {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:43: // 기본은 ResizeObserver 미정의 (jsdom 기본 동작 — width 0 으로 차트 미마운트)
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:44: delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:48: delete (globalThis as unknown as { ResizeObserver?: unknown }).ResizeObserver;
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:57: // jsdom 기본: getBoundingClientRect width === 0 + ResizeObserver 미정의
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:86: it("mounts ResponsiveContainer when ResizeObserver reports width >= 1", () => {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:87: // ResizeObserver 가 width 800 을 발화하는 환경 — 실제 브라우저 분기를 등가로 검증.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:88: (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:89: MockResizeObserver;
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:104: // wrapper 가 ResizeObserver 에 등록되어야 함.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/**tests**/equity-chart.test.tsx:107: // ResizeObserver 콜백을 width=800 으로 발화 → setHasWidth(true) → 차트 mount.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:36: _ - 부모 div 의 실제 width 를 ResizeObserver 로 측정.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:39: _ - jsdom 환경: ResizeObserver 가 inert 라 width 가 0 으로 유지 → 차트 미마운트 → warning 0건.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:40: \* - 브라우저 환경: layout 측정 후 ResizeObserver 가 width 를 발화 → 정상 mount.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:73: // 2차: ResizeObserver 로 width 측정 후 한 번만 발화.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:74: // jsdom 에서는 ResizeObserver 가 미정의이거나 inert → catch 로 안전하게 빠짐.
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:75: if (typeof ResizeObserver === "undefined") {
.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/\_components/equity-chart.tsx:79: const observer = new ResizeObserver((entries) => {

codex
이 시점에서 핵심 리스크는 세 가지입니다: Playwright AC 미충족, fail-first TDD 증거 부재, `ResizeObserver` 미지원 시 영구 placeholder 가능성입니다. 문서 line reference까지 맞추기 위해 계획서와 self-review에도 줄 번호를 붙여 보겠습니다.
exec
/bin/zsh -lc "nl -ba 'docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md' | sed -n '1,220p'" in /Users/woosung/project/agy-project/quant-bridge
exec
/bin/zsh -lc "nl -ba '.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md' | sed -n '1,260p'" in /Users/woosung/project/agy-project/quant-bridge
succeeded in 0ms:
1 # W3 — EquityChart `width(-1)` Warning 제거
2
3 > **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 3 / 5
4 > **Branch:** `stage/x1-x3-indicator-ui`
5 > **TDD Mode:** **test + impl 동시 허용** — pure UI 렌더링 (no hooks/state/effect 로직 변경)
6
7 ---
8
9 ## 1. Context
10
11 QuantBridge 는 Next.js 16 FE + FastAPI BE 의 퀀트 플랫폼. backtest 상세 페이지 (`/backtests/[id]`) 는 `recharts` 기반 `EquityChart` 를 사용한다.
12
13 **현재 공백**: 브라우저 콘솔에 `Warning: width(-1) and height(256) ... ResponsiveContainer` 가 뜬다. 원인은 `ResponsiveContainer` 가 부모 `div` 의 width=0 상태에서 첫 렌더링되는 시점. 이후 resize 로 복구되나 경고가 남음.
14
15 **사용자 memory 제약 (LESSON-004)**: useEffect + RQ/Zustand unstable dep 금지. ResizeObserver 사용 시 stable ref 로 한정.
16
17 ---
18
19 ## 2. Acceptance Criteria
20
21 ### 정량
22
23 - [ ] Playwright 시나리오: `/backtests/<id>` 로 직접 navigate → 첫 페인트 시점부터 console warning "width(-1)" **0건**
24 - [ ] FE vitest: `EquityChart` 렌더링 테스트 ≥ 1건 (mount 후 컨테이너 width 0 가정에서 crash 없음)
25 - [ ] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` 모두 clean
26 - [ ] 기존 equity 데이터 렌더링 회귀 0 (기존 테스트 PASS)
27
28 ### 정성
29
30 - [ ] ResponsiveContainer 를 감싸는 wrapper 에 **명시적 width** (예: `w-full` + inline `style={{ width: "100%" }}`) 또는 mount 후 조건부 렌더링
31 - [ ] useEffect 의존 배열에 RQ/Zustand 불안정 참조 금지 — primitive dep 만
32 - [ ] shadcn/ui v4 + Tailwind v4 관례 유지 (inline style 은 최소화, className 우선)
33
34 ---
35
36 ## 3. File Structure
37
38 **수정:**
39
40 - `frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx` — ResponsiveContainer 안정화
41
42 **신규:**
43
44 - `frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx` — mount 테스트
45
46 ---
47
48 ## 4. TDD Tasks
49
50 ### T1. Failing test (mount 시 crash/warning 가드)
51
52 **Step 1 — vitest 테스트 생성:**
53
54 `tsx
    55	// frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx
    56	import { render, screen } from "@testing-library/react";
    57	import { describe, expect, it, vi } from "vitest";
    58	
    59	import type { EquityPoint } from "@/features/backtest/schemas";
    60	import { EquityChart } from "../equity-chart";
    61	
    62	const POINTS: EquityPoint[] = [
    63	  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
    64	  { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
    65	  { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
    66	];
    67	
    68	describe("EquityChart", () => {
    69	  it("renders empty state when no points", () => {
    70	    render(<EquityChart points={[]} />);
    71	    expect(screen.getByText(/Equity 데이터가 없습니다/)).toBeInTheDocument();
    72	  });
    73	
    74	  it("mounts without recharts width(-1) warning", () => {
    75	    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    76	    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    77	
    78	    render(<EquityChart points={POINTS} />);
    79	
    80	    const w = warnSpy.mock.calls.some((args) =>
    81	      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    82	    );
    83	    const e = errSpy.mock.calls.some((args) =>
    84	      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    85	    );
    86	    expect(w || e).toBe(false);
    87	
    88	    warnSpy.mockRestore();
    89	    errSpy.mockRestore();
    90	  });
    91	});
    92	`
93
94 **Step 2 — 실패 확인 (warning 여부는 환경 의존적이므로 최소한 render crash 없음을 검증):**
95
96 `bash
    97	cd frontend && pnpm test -- --run equity-chart.test
    98	`
99
100 Expected: 가능하면 FAIL 또는 render crash; 적어도 smoke 형태로 돌아감 (완전 FAIL 이 아니어도 mount 보장).
101
102 ### T2. ResponsiveContainer 안정화 구현
103
104 **Step 3 — `equity-chart.tsx` 수정** (핵심 아이디어: min-width inline + 부모 컨테이너에 `w-full` 보장 + mount gate):
105
106 `tsx
   107	"use client";
   108	
   109	import { useEffect, useMemo, useState } from "react";
   110	import {
   111	  CartesianGrid,
   112	  Line,
   113	  LineChart,
   114	  ResponsiveContainer,
   115	  Tooltip,
   116	  XAxis,
   117	  YAxis,
   118	} from "recharts";
   119	
   120	import type { EquityPoint } from "@/features/backtest/schemas";
   121	import {
   122	  downsampleEquity,
   123	  formatCurrency,
   124	  formatDate,
   125	} from "@/features/backtest/utils";
   126	
   127	interface EquityChartProps {
   128	  points: readonly EquityPoint[];
   129	  maxPoints?: number;
   130	}
   131	
   132	interface ChartDatum {
   133	  ts: number;
   134	  value: number;
   135	  label: string;
   136	}
   137	
   138	export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
   139	  const data = useMemo<ChartDatum[]>(() => {
   140	    const sampled = downsampleEquity(points, maxPoints);
   141	    return sampled.map((p) => ({
   142	      ts: new Date(p.timestamp).getTime(),
   143	      value: p.value,
   144	      label: formatDate(p.timestamp),
   145	    }));
   146	  }, [points, maxPoints]);
   147	
   148	  // mount gate — ResponsiveContainer 가 width=0 로 첫 렌더링되는 것을 회피.
   149	  // CSR only 환경에서만 실제 차트 마운트.
   150	  const [isMounted, setIsMounted] = useState(false);
   151	  useEffect(() => {
   152	    setIsMounted(true);
   153	  }, []); // primitive-only dep array — LESSON-004 준수
   154	
   155	  if (data.length === 0) {
   156	    return (
   157	      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
   158	        Equity 데이터가 없습니다
   159	      </div>
   160	    );
   161	  }
   162	
   163	  if (!isMounted) {
   164	    return <div className="h-64 w-full" aria-busy="true" />;
   165	  }
   166	
   167	  return (
   168	    <div className="h-64 w-full" style={{ minWidth: 0 }}>
   169	      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
   170	        <LineChart
   171	          data={data}
   172	          margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
   173	        >
   174	          <CartesianGrid strokeDasharray="3 3" vertical={false} />
   175	          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={32} />
   176	          <YAxis
   177	            tick={{ fontSize: 11 }}
   178	            tickFormatter={(v: number) => formatCurrency(v, 0)}
   179	            width={80}
   180	          />
   181	          <Tooltip
   182	            formatter={(value) =>
   183	              typeof value === "number" ? formatCurrency(value) : String(value)
   184	            }
   185	            labelFormatter={(label) => (label == null ? "" : String(label))}
   186	          />
   187	          <Line
   188	            type="monotone"
   189	            dataKey="value"
   190	            stroke="currentColor"
   191	            strokeWidth={1.5}
   192	            dot={false}
   193	            isAnimationActive={false}
   194	          />
   195	        </LineChart>
   196	      </ResponsiveContainer>
   197	    </div>
   198	  );
   199	}
   200	`
201
202 **근거:**
203
204 - `useState(false) + useEffect(() => setIsMounted(true), [])` 패턴은 Next.js SSR hydration 이후에만 ResponsiveContainer 를 mount → 첫 페인트 시 width=0 회피
205 - primitive-only dep `[]` → LESSON-004 위반 없음
206 - `minWidth={0}` (recharts prop) 는 defensive 하게 추가
207 - `aria-busy="true"` placeholder 는 동일 크기 (`h-64 w-full`) 를 유지해 layout shift 방지
208
209 **Step 4 — 녹색 확인:**
210
211 `bash
   212	cd frontend && pnpm test -- --run equity-chart.test
   213	cd frontend && pnpm tsc --noEmit
   214	cd frontend && pnpm lint
   215	`
216
217 Expected: 모두 clean.
218
219 ### T3. Playwright live smoke (선택 — 조건 충족 시)
220

succeeded in 0ms:
1 # W3 — Codex Self-Review (EquityChart width(-1) fix)
2
3 > **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 3 / 5
4 > **Plan:** [docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md](../plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md)
5 > **Reviewer:** `codex-cli 0.122.0` (sandbox=read-only)
6
7 ---
8
9 ## 1. Scope
10
11 - 대상 파일:
12 - `frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx` (구현)
13 - `frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx` (신규 테스트)
14 - 체크 항목:
15 1. `useEffect` dep primitive-only (LESSON-004 준수)
16 2. `eslint-disable react-hooks/*` 사용 없음
17 3. SSR-safe (no window/document top-level, `ResizeObserver` typeof 가드)
18 4. layout shift 최소화 (`h-64 w-full` placeholder 동일 크기)
19 5. recharts `ResponsiveContainer` 사용 idiomatic + width 측정 gate
20 6. 테스트가 jsdom 에서 실제로 `width(-1)` 회귀를 catch 가능한지
21
22 ---
23
24 ## 2. Review 1-pass (GO_WITH_FIX)
25
26 **요약:** 구현은 문제 없음. 테스트의 회귀 탐지력이 부족 — mount gate 를 제거해도 테스트가 실패하지 않을 가능성. DOM-level (`.recharts-responsive-container` 존재 여부) 검증과 width≥1 분기 검증을 추가할 것.
27
28 **지적사항:**
29
30 1. `console.warn/error` 스파이에 `width(-1)` 문자열이 없다는 검증만으로는 회귀 탐지력이 약함. 현재 환경에서 경고가 발생하지 않는다는 사실만 확인.
31 2. `width<1` / `width≥1` 분기를 DOM 레벨에서 검증하지 않음.
32
33 ---
34
35 ## 3. 수정 적용
36
37 테스트를 3개로 확장:
38
39 1. **empty state** — 기존 유지 (`points=[]` → "Equity 데이터가 없습니다").
40 2. **width=0 분기 (jsdom 기본)** — `ResizeObserver` 삭제 + `getBoundingClientRect` width=0 상황에서:
41 - `.recharts-responsive-container` 가 DOM 에 **없어야** 함
42 - `[aria-busy="true"]` placeholder 가 **존재해야** 함
43 - console.warn/error 에서 `width(-1)` 문자열 **0건**
44 3. **width≥1 분기 (ResizeObserver mock)** — MockResizeObserver 로 width=800 callback 발화:
45 - 콜백 직전: `.recharts-responsive-container` 없음
46 - `roInstances[0].cb([{ contentRect: { width: 800 } }])` + `act()` 후: `.recharts-responsive-container` 존재
47 - placeholder `[aria-busy="true"]` 사라짐
48 - jsdom 내부 layout 부재로 인한 ResponsiveContainer 자체 warning 은 본 테스트 범위 밖 (Phase 4 Playwright 가 담당) — 주석 명시
49
50 ---
51
52 ## 4. Review 2-pass (GO)
53
54 **판정:** `GO` / **신뢰도:** `8/10`
55
56 **Codex 원문 요약:**
57
58 - (1) 회귀 탐지력: mount gate 제거 시 테스트 b (width=0 경로) 가 실패함. 탐지력 충분.
59 - (2) width-0 / width≥1 분기: 상태 분기 기준 양쪽 모두 검증됨. 다만 `equity-chart.tsx:67` 의 "초기 `getBoundingClientRect().width >= 1` fast path" 자체는 별도 검증 없음 (minor).
60 - (3) LESSON-004 / unused-import lint: 리스크 없음. `useEffect` dep `[]` 안정적, import 모두 사용 중.
61
62 **남은 minor:** initial-width fast-path (line 67-71) 의 단위 테스트는 없음. `getBoundingClientRect` mock 이 필요해 테스트 복잡도가 증가하는 대비 효익이 낮아 **skip 결정**. ResizeObserver 분기가 fast-path 와 같은 `setHasWidth(true)` 를 호출하므로 mount 후 동작은 등가.
63
64 ---
65
66 ## 5. 수동 검증 결과
67
68 `bash
    69	$ cd frontend && pnpm test -- --run equity-chart.test
    70	  ✓ src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx (3 tests) 21ms
    71	  Test Files  1 passed (1)
    72	      Tests  3 passed (3)
    73	
    74	$ cd frontend && pnpm test -- --run
    75	  Test Files  24 passed (24)
    76	      Tests  140 passed (140)
    77	
    78	$ cd frontend && pnpm tsc --noEmit
    79	  exit=0
    80	
    81	$ cd frontend && pnpm lint
    82	  exit=0  (0 errors / 0 warnings)
    83	`
84
85 ---
86
87 ## 6. AC 체크리스트 (plan §2)
88
89 ### 정량
90
91 - [x] FE vitest: `EquityChart` 렌더링 테스트 ≥ 1건 (mount 후 컨테이너 width 0 가정에서 crash 없음) → **3건**
92 - [x] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` 모두 clean → **clean**
93 - [x] 기존 equity 데이터 렌더링 회귀 0 (기존 테스트 PASS) → **139/139 기존 + 3 신규 = 140 PASS**
94 - [ ] Playwright 시나리오: `/backtests/<id>` navigate → 첫 페인트부터 console "width(-1)" 0건 → **Phase 4 orchestrator 담당 (worker 환경 미실행)**
95
96 ### 정성
97
98 - [x] ResponsiveContainer 를 감싸는 wrapper 에 명시적 width (`w-full` + `style={{ minWidth: 0 }}`) 및 mount gate
99 - [x] useEffect 의존 배열에 RQ/Zustand 불안정 참조 금지 — **`[]` primitive-only**
100 - [x] shadcn/ui v4 + Tailwind v4 관례 유지 (inline style `minWidth: 0` 만 recharts 요구로 사용)
101
102 ---
103
104 ## 7. Edge Case 커버 (plan §5)
105
106 | Edge case | 처리 |
107 | --------------------------------------- | --------------------------------------------------------------------------------------------------------- |
108 | `data.length === 0` | 기존 "Equity 데이터가 없습니다" 분기 유지 + `render(<EquityChart points={[]} />)` 테스트 |
109 | SSR pre-hydration | `useEffect` 내부에서만 측정/mount → server 에선 placeholder 렌더. `ResizeObserver` typeof 가드로 SSR 안전 |
110 | props.points 변경 (resize 후 re-render) | `data` useMemo dep `[points, maxPoints]` 유지 — 기존 로직 회귀 없음 |
111 | 매우 큰 points (maxPoints=1000 초과) | `downsampleEquity` 로직 그대로 유지 |
112
113 ---
114
115 ## 8. LESSON-004 self-check
116
117 **useEffect dep array 증명:**
118
119 `tsx
   120	// equity-chart.tsx:60-92
   121	useEffect(() => {
   122	  const node = wrapperRef.current; // ref (stable)
   123	  if (node === null) return;
   124	  // ... initialWidth + ResizeObserver 로직 ...
   125	}, []); // ← primitive-only: 빈 배열
   126	`
127
128 - **dep:** `[]` — React Query / Zustand / RHF / Zod 결과 객체 사용 없음
129 - **클로저 캡처:** `wrapperRef` (ref, stable), `setHasWidth` (React state setter, stable)
130 - **eslint:** `react-hooks/exhaustive-deps` 경고 없음 (ref/setter 는 캡처해도 안전)
131 - **eslint-disable:** 사용 없음
132
133 ---
134
135 ## 9. jsdom warning catch 가능성 명시
136
137 **T1 의 초기 의도:** `console.warn` 에서 `width(-1)` 문자열을 catch.
138
139 **실측 결과 (debug 테스트로 확인):**
140
141 `text
   142	[w0] ["The width(-1) and height(-1) of chart should be greater than 0, ..."]
   143	`
144
145 → **jsdom 에서도 recharts `ResponsiveContainer` + `LineChart` 체인은 `width(-1)` warning 을 실제로 emit**. 즉 `console.warn` spy 로 catch 가능.
146
147 **최종 테스트는 두 계층으로 회귀 검출:**
148
149 1. **DOM-level**: mount gate 가 작동하면 `.recharts-responsive-container` 가 width=0 경로에서 mount 되지 않음 → 가장 강력한 가드
150 2. **Console-level**: 그 결과로 `width(-1)` warning 문자열 0건 — plan 에서 요구한 spy 검증
151
152 **mount branch (width≥1) 에서는** ResponsiveContainer 내부 layout 자체 측정이 jsdom 에선 불가하여 별도 `width(-1)` 및 `width(0)` warning 을 발생. 이는 jsdom 한계이며 실제 브라우저에선 발생하지 않음. Phase 4 Playwright live smoke 에서 orchestrator 가 최종 검증.
153
154 ---
155
156 ## 10. 최종 판정
157
158 **GO** / **신뢰도 8/10** (Codex review 2-pass 기준)
159
160 - 구현: mount gate 패턴으로 width=0 경로 차단, LESSON-004 준수
161 - 테스트: 3건 (empty / width=0 분기 / width≥1 분기) → 회귀 탐지력 충분
162 - lint / tsc / 전체 vitest: all clean
163 - 남은 1 항목: Playwright live smoke (Phase 4 orchestrator 담당)

codex
**Findings**

1. `GO`는 아닙니다. plan의 정량 AC는 전부 충족되지 않았습니다. Playwright의 “첫 페인트부터 `width(-1)` warning 0건” 항목이 plan에 명시돼 있는데 [plan](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md:23) 실제 self-review에서는 미실행으로 남아 있습니다 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:91). 따라서 “최종 acceptance 완료” 판정은 불가합니다.

2. `ResizeObserver`가 없는 환경에서 초기 width가 0이면 차트가 영구 placeholder에 머뭅니다. [equity-chart.tsx](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:67>)에서 초기 폭이 0이면 RO 경로로 넘어가고, [75-77](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:75>)에서 `ResizeObserver`가 없으면 그대로 `return`합니다. 결과적으로 [137-139](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:137>)의 `aria-busy` placeholder만 남습니다. edge-case 미커버가 아니라 실제 기능 저하입니다.

3. fail-first TDD 증거는 없습니다. plan 자체가 `test + impl 동시 허용`으로 열어두고 있고 [plan](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md:5), git history도 단일 커밋 `acfa9b1` 하나뿐입니다. self-review 역시 post-fix green run만 기록합니다 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:66). “먼저 실패했다”는 근거는 없습니다.

**7 Answers**

1. Acceptance Criteria 정량 충족 여부  
   아니오, 전량 충족은 아닙니다. [사실] plan §2 정량 항목은 사용자가 말한 5개가 아니라 4개입니다 [plan](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md:21).  
   충족:

- `equity-chart.test.tsx`: `3 tests passed` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:69)
- 전체 FE vitest: `24 passed`, `140 passed` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:74)
- `pnpm tsc --noEmit`: `exit=0` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:78)
- `pnpm lint`: `exit=0`, `0 errors / 0 warnings` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:81)  
  미충족:
- Playwright first-paint warning 0건: 미실행 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:94)

2. Spurious PASS 시나리오 존재 여부  
   주요 회귀인 “mount gate 제거”는 테스트가 잡습니다. [test](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx:56>)는 width=0 경로에서 `.recharts-responsive-container`가 없어야 하고 [66-68], placeholder가 있어야 하며 [70], warning도 없어야 한다고 봅니다 [73-80]. gate를 제거하면 첫 `render()` 직후 컨테이너 존재 assertion이 바로 깨집니다.  
   다만 blind spot은 있습니다:

- initial fast-path `getBoundingClientRect().width >= 1` 자체는 직접 검증하지 않습니다 [equity-chart.tsx](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:67>)
- `ResizeObserver` 없는데 초기 width는 양수인 케이스도 테스트하지 않습니다

3. TDD evidence  
   없습니다. [사실] 단일 커밋 `acfa9b1`에 구현과 테스트가 함께 들어가 있고, worker report에는 fail-first 로그가 없습니다. [가정] 실제로는 함께 작성했을 가능성이 높습니다. 최소한 “먼저 실패 후 수정”을 입증할 증거는 없습니다.

4. Regression surface  
   영향 표면은 작습니다. `EquityChart` 실제 사용처는 [backtest-detail-view.tsx](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx:139>) 한 곳뿐입니다. 전체 FE suite는 24 files / 140 tests로 green입니다 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:74).  
   하지만 통합 테스트는 없습니다. `BacktestDetailView` 수준에서 placeholder→chart 전환이나 실제 `/backtests/[id]` 렌더 흐름을 검증하는 테스트는 보이지 않습니다.

5. Edge cases 커버 여부

- empty data: 커버됨. 구현 [94-99](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:94>), 테스트 [51-54](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx:51>)
- SSR pre-hydration: 대체로 안전. 측정은 effect 내부뿐이고 top-level browser API 접근이 없습니다 [60-92](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:60>). 다만 실제 브라우저 first-paint warning 0건은 Playwright 미실행이라 미증명입니다.
- large points: 별도 신규 커버 없음. 기존 `downsampleEquity` 경로 유지뿐입니다 [47-54](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:47>).
- resize-after-render: 커버됨. RO callback으로 mount 전환을 검증합니다 [86-117](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx:86>)
- `ResizeObserver` missing: 미커버이자 실제 취약점입니다. 초기 width 0이면 영구 placeholder입니다 [75-77](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:75>)

6. LESSON-004 compliance  
   준수합니다.

- `useEffect` dep array: 정확히 `[]` 하나입니다 [92](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:92>)
- effect 내부 캡처:
  - `wrapperRef` → React ref, stable [57](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:57>)
  - `setHasWidth` → React state setter, stable [58](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:58>)
  - `ResizeObserver` → global API, RQ/Zustand ref 아님 [75](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:75>)
- RQ/Zustand/unstable function ref dep: 없음
- `eslint-disable react-hooks/*`: W3 변경 파일들에는 없음. repo 전체에는 unrelated 기존 disable이 [editor-view.tsx:72](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/_components/editor-view.tsx:72>)에 있으나 W3 범위 밖입니다.

7. Final verdict  
   `GO_WITH_FIX`, confidence `8/10`.

이유는 간단합니다. 핵심 회귀 방지는 대체로 맞고 LESSON-004도 지켰습니다. 하지만 1) plan의 핵심 정량 AC인 Playwright first-paint 검증이 비어 있고, 2) `ResizeObserver` 미지원 + initial width 0 경로에서 차트가 영구 미표시되는 edge defect가 남아 있어 `GO`는 과합니다.
tokens used
49,065
**Findings**

1. `GO`는 아닙니다. plan의 정량 AC는 전부 충족되지 않았습니다. Playwright의 “첫 페인트부터 `width(-1)` warning 0건” 항목이 plan에 명시돼 있는데 [plan](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md:23) 실제 self-review에서는 미실행으로 남아 있습니다 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:91). 따라서 “최종 acceptance 완료” 판정은 불가합니다.

2. `ResizeObserver`가 없는 환경에서 초기 width가 0이면 차트가 영구 placeholder에 머뭅니다. [equity-chart.tsx](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:67>)에서 초기 폭이 0이면 RO 경로로 넘어가고, [75-77](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:75>)에서 `ResizeObserver`가 없으면 그대로 `return`합니다. 결과적으로 [137-139](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:137>)의 `aria-busy` placeholder만 남습니다. edge-case 미커버가 아니라 실제 기능 저하입니다.

3. fail-first TDD 증거는 없습니다. plan 자체가 `test + impl 동시 허용`으로 열어두고 있고 [plan](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md:5), git history도 단일 커밋 `acfa9b1` 하나뿐입니다. self-review 역시 post-fix green run만 기록합니다 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:66). “먼저 실패했다”는 근거는 없습니다.

**7 Answers**

1. Acceptance Criteria 정량 충족 여부  
   아니오, 전량 충족은 아닙니다. [사실] plan §2 정량 항목은 사용자가 말한 5개가 아니라 4개입니다 [plan](/Users/woosung/project/agy-project/quant-bridge/docs/superpowers/plans/2026-04-23-x1x3-w3-equity-chart-width-fix.md:21).  
   충족:

- `equity-chart.test.tsx`: `3 tests passed` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:69)
- 전체 FE vitest: `24 passed`, `140 passed` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:74)
- `pnpm tsc --noEmit`: `exit=0` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:78)
- `pnpm lint`: `exit=0`, `0 errors / 0 warnings` [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:81)  
  미충족:
- Playwright first-paint warning 0건: 미실행 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:94)

2. Spurious PASS 시나리오 존재 여부  
   주요 회귀인 “mount gate 제거”는 테스트가 잡습니다. [test](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx:56>)는 width=0 경로에서 `.recharts-responsive-container`가 없어야 하고 [66-68], placeholder가 있어야 하며 [70], warning도 없어야 한다고 봅니다 [73-80]. gate를 제거하면 첫 `render()` 직후 컨테이너 존재 assertion이 바로 깨집니다.  
   다만 blind spot은 있습니다:

- initial fast-path `getBoundingClientRect().width >= 1` 자체는 직접 검증하지 않습니다 [equity-chart.tsx](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:67>)
- `ResizeObserver` 없는데 초기 width는 양수인 케이스도 테스트하지 않습니다

3. TDD evidence  
   없습니다. [사실] 단일 커밋 `acfa9b1`에 구현과 테스트가 함께 들어가 있고, worker report에는 fail-first 로그가 없습니다. [가정] 실제로는 함께 작성했을 가능성이 높습니다. 최소한 “먼저 실패 후 수정”을 입증할 증거는 없습니다.

4. Regression surface  
   영향 표면은 작습니다. `EquityChart` 실제 사용처는 [backtest-detail-view.tsx](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx:139>) 한 곳뿐입니다. 전체 FE suite는 24 files / 140 tests로 green입니다 [self-review](/Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md:74).  
   하지만 통합 테스트는 없습니다. `BacktestDetailView` 수준에서 placeholder→chart 전환이나 실제 `/backtests/[id]` 렌더 흐름을 검증하는 테스트는 보이지 않습니다.

5. Edge cases 커버 여부

- empty data: 커버됨. 구현 [94-99](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:94>), 테스트 [51-54](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx:51>)
- SSR pre-hydration: 대체로 안전. 측정은 effect 내부뿐이고 top-level browser API 접근이 없습니다 [60-92](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:60>). 다만 실제 브라우저 first-paint warning 0건은 Playwright 미실행이라 미증명입니다.
- large points: 별도 신규 커버 없음. 기존 `downsampleEquity` 경로 유지뿐입니다 [47-54](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:47>).
- resize-after-render: 커버됨. RO callback으로 mount 전환을 검증합니다 [86-117](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx:86>)
- `ResizeObserver` missing: 미커버이자 실제 취약점입니다. 초기 width 0이면 영구 placeholder입니다 [75-77](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:75>)

6. LESSON-004 compliance  
   준수합니다.

- `useEffect` dep array: 정확히 `[]` 하나입니다 [92](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:92>)
- effect 내부 캡처:
  - `wrapperRef` → React ref, stable [57](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:57>)
  - `setHasWidth` → React state setter, stable [58](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:58>)
  - `ResizeObserver` → global API, RQ/Zustand ref 아님 [75](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx:75>)
- RQ/Zustand/unstable function ref dep: 없음
- `eslint-disable react-hooks/*`: W3 변경 파일들에는 없음. repo 전체에는 unrelated 기존 disable이 [editor-view.tsx:72](</Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/agent-a3916c29/frontend/src/app/(dashboard)/strategies/[id]/edit/_components/editor-view.tsx:72>)에 있으나 W3 범위 밖입니다.

7. Final verdict  
   `GO_WITH_FIX`, confidence `8/10`.

이유는 간단합니다. 핵심 회귀 방지는 대체로 맞고 LESSON-004도 지켰습니다. 하지만 1) plan의 핵심 정량 AC인 Playwright first-paint 검증이 비어 있고, 2) `ResizeObserver` 미지원 + initial width 0 경로에서 차트가 영구 미표시되는 edge defect가 남아 있어 `GO`는 과합니다.
