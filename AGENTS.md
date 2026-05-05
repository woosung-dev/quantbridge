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

> **운영 규칙:** 본 섹션은 **활성 sprint 1개 + 직전 완료 sprint 1개 + 다음 분기** 만 inline.
> 매 sprint 종료 시 직전 항목을 dev-log 링크로 압축. 과거 이력은 [`docs/dev-log/INDEX.md`](docs/dev-log/INDEX.md).

**활성 브랜치:** `main @ 06f5512` (Sprint 33 7 PR all merged: #141 step0 hook / #143 B BL-164 / #145 A BL-150 partial / #142 C BL-071 audit / #144 main BL-174 list-only / #146 hotfix BL-175 BH 거짓 trust 차단 / #147 hotfix BL-176 SelectWithDisplayName null skip)

**활성 sprint:** Sprint 34 진입 대기 — **dogfood Day 6 = 5/10 (regression -1.5~2)**. **Sprint 34 분기 = polish iter 2** (Beta 본격 진입 미루기). ≥7 미달 → BL-175 본격 fix / BL-177 chart marker / BL-166 / BL-176 follow-up / BL-174 detail

**직전 완료:** Sprint 33 — 6.5 양다리 균형 패키지 + dogfood Day 6 hotfix 2건 (7 PR + retro, codex G.0 P1 surgery 3건 적용, dogfood Day 5 → Day 6 = 5/10 **regression**, BUG 3건 발견 mechanism 검증)

- **codex G.0 master plan validation** (session `019df729`, medium tier, 124k tokens) — Verdict GO_WITH_FIXES + P1 surgery 3건. P1-1 hook 선행 (D 삭제 → 메인 step 0) / P1-2 BL-071 scope 재정의 (dry-run+runbook → topology gap audit + Sprint 34 unresolved gap 16건) / P1-3 scope 정직화 (필수 3 BL + stretch 3 BL, BL-150 kill criterion, Resolved → Partial). **P1 ≤1건 한도 = 잘못된 운영 규칙 (codex challenge)** — 제거, iter cap 2 만 유지
- **pre-push hook (PR #141)** main worktree (`git_dir == git_common_dir`) push reject + `QB_PRE_PUSH_BYPASS=1` 명시 우회. **자율 병렬 worker isolation 영구 차단** (Sprint 32 lesson 즉시 적용). dry-run REJECT_EXIT=1 / BYPASS_EXIT=0
- **BL-164 (PR #143)** SelectWithDisplayName helper (UI primitive, generic) — base-ui Select.Value render prop 캡슐화 + UUID/raw value 노출 자동 차단. live-session-form strategy/exchange dropdown 2개 교체. Sprint 34+ 다른 dropdown 도 동일 helper 통일 가능
- **BL-150 partial (PR #145)** live-session-detail Activity Timeline 2-pane 분리 (top entries/closes / bottom equity USDT). trading-chart.tsx wrapper 재사용 (Sprint 30 BL-157 currentColor fallback 자동 안전). React Compiler memoize 호환. **walk-forward + monte-carlo Sprint 34 defer** (lightweight-charts native bar chart 미지원). 2-3h kill criterion ~30분 여유 통과
- **BL-071 audit (PR #142)** Cloud Run topology gap audit + runbook (393 lines, 7 절). 코드 변경 0. **Sprint 34 unresolved gap 16건** (P0 8: TimescaleDB hosting / VPC Connector / IAM SA / Cloud SQL connector / Secret Manager / 도메인 / healthz / worker HTTP listener)
- **BL-174 list-only (PR #144)** LiveSessionStateView (live-session 도메인 전용, trading-empty-state pattern 복제 + variant + iconClassName). 3 state 통일 (Loading Loader2 spinner / Failed AlertCircle + error.message / Empty Plus + 기존 testid 보존). detail 분기는 Sprint 34 defer
- **BL-175 hotfix (PR #146)** dogfood Day 6 발견 — `computeBuyAndHold` 가 `initialCapital * (last_equity / first_equity)` 로 계산 → strategy line 과 거의 동일 → legend mismatch (Surface Trust ADR-019 위반). 임시 mitigation: 빈 배열 반환 → BH series 미렌더 + ChartLegend BH 항목 자동 hide. 본격 fix Sprint 34 (backend `buy_and_hold_curve` + OHLCV 가격 기반 정확 계산)
- **BL-176 hotfix (PR #147)** dogfood Day 6 발견 — `/trading` Live Sessions dropdown 조작 시 Runtime ZodError (`exchange_account_id: invalid_format`). root cause: Worker B BL-164 PR #143 `handleValueChange` 가 base-ui `null → ""` 변환 → form zod UUID schema reject. hotfix: `v=null` 시 callback skip → form prior valid value 보존
- **dual metric:** 7 PR / vitest 398 (+27) / backend pytest 1572 / mypy 0 / ruff 0 / tsc 0 / eslint 0 / **dogfood Day 6 = 5/10 (regression -1.5~2, BUG 3건 발견 효과)** / Surface fix 효과 = -1.5~2 / sprint (Sprint 32 = +1.5, Sprint 31 = +1, Sprint 30 = +0). **lesson: automated test 100% pass 와 production quality 의 격차 검증, dogfood = critical BUG 발견 mechanism 영구 의무**
- **자율 병렬 worker isolation 영구 차단 검증** — main worktree branch swap **0건** (Sprint 32 = 2건 → Sprint 33 = 0건). pre-push hook hybrid (reject + bypass env) + 메인 세션 step 0 선행 패턴 효과 검증
- 상세: [`docs/dev-log/2026-05-05-sprint33-master-retrospective.md`](docs/dev-log/2026-05-05-sprint33-master-retrospective.md)

**다음 분기:** Sprint 34 = **polish iter 2** (Day 6 = 5 regression → ≥7 도달 prereq):

1. **BL-175 본격 fix (P1)** — backend `BacktestMetrics.buy_and_hold_curve` 신규 + OHLCV 첫/끝 가격 기반 정확 계산 + frontend 자체 계산 폐기 (M 3-4h)
2. **BL-177 chart marker readability (P2)** — Sprint 32 BL-171 follow-up. zoom 영역 따라 marker count limit / cluster / text shorten / hover tooltip (M 3-4h)
3. **BL-166 uvicorn watch list (P3)** — Makefile `--reload-include "*.env*"` 추가 + 검증 (S 1-2h)
4. **BL-176 follow-up (P2)** — SelectWithDisplayName clear 동선 정합화 (form nullable schema 또는 별도 clear button — S 1-2h)
5. **BL-174 detail 분기 (P3)** — live-session-detail Empty/Failed/Loading 통일 (Sprint 33 list-only scope 외 — S 1-2h)
6. **mid-sprint dogfood 패턴 검증** — 본 sprint lesson #1 (dogfood = sprint 종료 직후 X, mid-sprint check 가 BUG 발견 + 즉시 fix cycle 가능)
7. **dogfood Day 7 재측정** → ≥7 도달 시 → Sprint 35 Beta 본격 진입 (BL-070 도메인 + BL-071 + BL-072)

**Sprint 34+ 이관 (Beta 본격 진입 결정 후):** BL-070~072 본격 / BL-073~075 캠페인+인터뷰+H2 gate / BL-005 ✅ Resolved final / BL-003 Bybit mainnet / BL-150 chart full migration / BL-166 uvicorn watch fix

**전체 sprint 이력:** [`docs/dev-log/INDEX.md`](docs/dev-log/INDEX.md) — 40+ 회고·ADR·dogfood 기록 인덱스

**미해결 BL:** [`docs/REFACTORING-BACKLOG.md`](docs/REFACTORING-BACKLOG.md) — Sprint 33 종료 시점 갱신 (Sprint 33 Resolved: BL-164 + pre-push hook 신규. Partial: BL-150 / BL-071 audit / BL-174 list-only. defer Sprint 34: BL-166 / BL-070~072 / BL-150 잔여 / BL-174 detail 분기)

**상시 활성 컨텍스트 (영구 기록 외 발견 패턴):**

- `dogfood Day N` 노트는 sprint 묶음과 별개로 dev-log 에 단독 파일로 보관
- BL-005 (본인 1-2주 dogfood) trigger 도래 후 H1→H2 gate (self-assessment ≥7) 가 재평가 기준
- `make up-isolated` (3100/8100/5433/6380) 가 다른 웹앱 병렬 시 디폴트
- **Sprint kickoff 첫 step = baseline 재측정 preflight 의무** (LESSON-037, Sprint 29 third validation 통과 — Sprint 30+ 부터 영구 적용)
- **Pine SSOT 4 invariant audit** (`tests/strategy/pine_v2/test_ssot_invariants.py`) — supported list 추가 시 4 collection 동시 갱신 의무 자동 검증
- **Surface Trust sub-pillar (Sprint 30 ADR-019)** — Backend Reliability + Risk Management + Security + **Surface Trust** (가정박스/차트/24 metric/거래목록). 측정: PRD 24 metric BE+FE 100% / config 5 가정 FE 100% / lightweight-charts 정합 / dogfood self-assess Day 3 ≥7
- **자율 병렬 sprint Agent worktree 패턴** — 충돌 회피 신규 파일 only / 통합 작업은 메인 세션 후처리 / gh CLI auto-merge --squash / `--no-verify` 1회 우회 사용자 명시 승인 패턴

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
