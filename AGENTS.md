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

**활성 브랜치:** `main @ 6d6a836` (Sprint 41 stage→main merge close-out)

**활성 sprint:** Sprint 42 — **지인 N=5 demo 오픈 + feedback loop**. Sprint 41 Day 7 4중 AND gate 모두 PASS (a 8/10 / b/c/d PASS) + 사용자 방향 (mainnet 보류 → demo 첫인상) 따라 demo 본격 오픈 단계 진입.

**Sprint 42 mandatory:**

- 지인 N=5 demo 오픈 (사용자 본인 + 1차 N=5 ≈ 5명, Bybit Demo Trading 사용)
- feedback 수집 채널 setup (간단한 폼 또는 직접 인터뷰, channel TBD)
- 1-2주 dogfood 결과 → Beta 본격 진입 (BL-070~075) trigger 결정

**Sprint 42 deferred:**

- BL-003 / BL-005 mainnet (사용자 결정: demo dogfood 후 별도 trigger)
- BL-190 PDF export (사용자 요청 또는 인쇄 use case 발견 시)
- BL-191 share view rate-limit (Beta 진입 시)
- BL-192 backtest status server filter (Beta 진입 시)

**Day 7 4중 AND gate (영구 기준 — Sprint 41 결과 반영):**

- (a) self-assess ≥7/10 (근거 ≥3 줄) — Sprint 41 = **8/10 PASS** (자율 병렬 cmux 5번째 실측 wall-clock ≈50분 + codex P2 2건 즉시 fix + Playwright 자동 검증 10/10 PASS + 4 트랙 fully delivered)
- (b) BL-178 production BH curve 정상. ✅ **PASS** (main 변경 X 영역)
- (c) BL-180 hand oracle 8 test all GREEN. ✅ **PASS** (main 변경 X 영역)
- (d) new P0=0 AND unresolved Sprint-caused P1=0. ✅ **PASS** (codex P2 2건 모두 fix 머지)

**직전 완료:** Sprint 41 — 외부 demo 첫인상 패키지 (4 PR / 40 files / +2615 / -166), Worker B (디자인 token) + E (UX 통일) + H (share link) + B-2 (프로토타입 App Shell + 4 페이지 layout) 자율 병렬 cmux 5번째 실측, Day 7 = 8/10 gate (a)+(b)+(c)+(d) 모두 PASS, **LESSON-048~050 신규 1/3 후보 3건** (Playwright + 인증 cookie 자동 dogfood / codex P2 즉시 fix 패턴 / sprint kickoff design source 명시 의무). 상세: [`docs/dev-log/2026-05-07-sprint41-master.md`](docs/dev-log/2026-05-07-sprint41-master.md).

**다음 분기:** Sprint 43 = **Sprint 42 결과 따라 결정**:

- **N=5 demo 1-2주 통과 + critical bug 0 + NPS ≥7** → Sprint 43 = **Beta 본격 진입 (BL-070~075 도메인+DNS / Backend 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트)**
- **demo dogfood 신규 회귀 발견** → Sprint 43 = polish iter (해당 회귀 hotfix)
- **mainnet trigger 도래** → Sprint 43 = BL-003 / BL-005 mainnet 본격 (사용자 결정 따라)

**Beta 본격 진입 (BL-070~075)** = N=5 demo 1-2주 통과 후 별도 trigger. **≠ Sprint 41 close-out 즉시 Beta 진입**.

**전체 sprint 이력:** [`docs/dev-log/INDEX.md`](docs/dev-log/INDEX.md) — 41+ 회고·ADR·dogfood 기록 인덱스

**미해결 BL:** [`docs/REFACTORING-BACKLOG.md`](docs/REFACTORING-BACKLOG.md) — Sprint 41 신규 3건 (BL-190 PDF export / BL-191 share rate-limit / BL-192 backtest status server filter). 총 **90 active BL**

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
