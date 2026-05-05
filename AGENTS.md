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

**활성 브랜치:** `main @ 27ff836` (Sprint 34 3 PR all merged: #150 BL-175 본격 fix / #149 BL-177 dense text shorten / retro PR 본 갱신)

**활성 sprint:** Sprint 35 진입 대기 — **dogfood Day 7 self-assess 결과 따라 결정** (≥7 → Beta 본격 진입 / <7 → polish iter 3). mid-dogfood Day 6.5 = PASS (Sprint 33 lesson #1 본 sprint 직접 적용 검증).

**직전 완료:** Sprint 34 — polish iter 2 (3 PR + codex G.0 P1 surgery 6건 적용, BL-175 본격 fix + BL-177 dense text shorten + BL-166 kill K-2 cancel, mid-dogfood Day 6.5 PASS + BL-178 신규 분리)

- **codex G.0 master plan validation** (session `019df7cc`, medium tier, iter cap 2, 327k tokens) — Verdict GO_WITH_FIXES + P1 surgery **6건 모두 plan 반영** (Sprint 33 lesson #2 codex P1 한도 제거 정합):
  - **P1-1** BL-175 FE wiring 누락 (R-0, plan 의 가장 큰 hole) — `equity-chart-v2.tsx` 가 `metrics` props 미수신 → backend 필드 추가만으로 silent fix failure. surgery: `EquityChartV2.buyAndHoldCurve` prop 신규 + `backtest-detail-view.tsx:160` 호출자 변환 + `computeBuyAndHold` import 제거
  - **P1-2** service.py:551-587 회귀 테스트 의무 (R-2 silent BUG) — `test_to_detail_passes_through_buy_and_hold_curve` 신규 (BacktestService.\_to_detail() JSONB → MetricsOut 1:1 검증)
  - **P1-3** BH 계산 fail-closed 정책 — invalid close (NaN/<=0) 1건이라도 → None (skip 정책 = partial silent line = 거짓 trust 영구 차단)
  - **P1-4** BL-177 scope 축소 — visible-range/crosshair/cluster = `marker-layer.tsx` 권한 외 → dense text shorten 만 / tooltip + cluster + visible-range = Sprint 35+ BL-177-A/B/C 분리
  - **P1-5** K-4 fallback 변경 — Worker A 4h 초과 시 BL-177+BL-166 즉시 defer, BL-175 만 완료
  - **P1-6** mid-dogfood numeric fixture — 주관적 "다른 곡선" 폐기, 7항목 numeric 검증 (`value[0]==initialCapital` / bar-by-bar / fail-closed scenario / legacy null / API raw + 화면 둘 다)
- **PR #150 BL-175 본격 fix** — backend `BacktestMetrics.buy_and_hold_curve: list[tuple[str, Decimal]] | None` 신규 (24 → 25 필드) + `_v2_buy_and_hold_curve` 2-stage fail-closed gate + service spread + FE wiring (P1-1) + edge case test 5건 + serializer round-trip 2건 + service detail 변환 1건. vitest 398 → 399 (+1 net) / pytest 1572 → 1580 (+8) / mypy/ruff/tsc/eslint 0/0/0/0
- **PR #149 BL-177 dense text shorten** — `deriveTradeMarkers(trades, { compact?: boolean })` API + `compact=true` 시 "L"/"S" 만 + `MARKER_LIMIT=200` cap 보존 + `equity-chart-v2.tsx` 호출부 1줄 (`trades.length > 30`). vitest +4 / tsc/eslint 0. visible-range subscription / hover tooltip / cluster = Sprint 35+ BL-177-A/B/C 분리
- **BL-166 kill K-2 cancel** (Sprint 33 lesson #7 본 sprint 직접 적용) — Makefile line 80 + 158 `--reload-include "*.env*"` 추가 후 사후 검증 (E.3) FAIL: `Reloading` log 미발생 ⚠️. 추정 root cause = `*.env*` glob pattern 이 `.env.local` (leading dot file) 미매치 또는 watchfiles default hidden file ignore. Makefile rollback + branch 폐기 (push 0) + retro 안 noop 발견 lesson 기록 + **BL-179 신규 등록** (Sprint 35+ uvicorn watchfiles `.env*` 감지 root cause + fix)
- **mid-dogfood Day 6.5 PASS** (Sprint 33 lesson #1 본 sprint 직접 적용 검증) — Playwright MCP 자동화 (Clerk JWT 발급 + backend 직접 fetch + 화면 snapshot) + 사용자 dogfood 분담. 3개 backtest (s1_pbr / s2_utbot, BTC/USDT 1h/4h, 1-3개월) numeric 검증. 검증 #6 legacy backward-compat PASS (BH null → 미렌더 + Legend hide 시각 검증) + 검증 #7 P1-3 fail-closed PASS (schema 안 `buy_and_hold_curve` 추가 + 값 null 정상). **회귀 0건 + 신규 BL 1건 분리** (BL-178 production OHLCV invalid close root cause)
- **dual metric:** 3 PR / vitest 398 → 403 (+5) / backend pytest 1572 → 1580 (+8) / mypy 0 / ruff 0 / tsc 0 / eslint 0 / **dogfood Day 6.5 PASS / Day 7 = TBD** (사용자 입력 대기) / Surface fix 효과 = R-2 차단 + P1-3 fail-closed + FE wiring 적용 (정확한 BH 표시 검증은 BL-178 의존)
- **자율 병렬 worker isolation 영구 차단 검증 (2 sprint 연속)** — main worktree branch swap **0건** (Sprint 32 = 2건 → Sprint 33 = 0건 → Sprint 34 = 0건). pre-push hook hybrid 효과 검증. Worker A 12분 (748s, 184k tokens) / Worker B 6분 (363s, 92k tokens)
- **신규 lesson 후보**: kill K-2 (BL-166) plan 가정 사후 검증 FAIL → cancel + BL 분리 패턴 정합 검증 / production OHLCV fail-closed gate (BL-178) production 환경 정상 발동 / Playwright MCP + 사용자 dogfood 분담 효율적 패턴
- 상세: [`docs/dev-log/2026-05-05-sprint34-master-retrospective.md`](docs/dev-log/2026-05-05-sprint34-master-retrospective.md)

**다음 분기:** Sprint 35 = **dogfood Day 7 self-assess 결과 따라 결정**:

- **≥7 → Beta 본격 진입**: BL-070 (도메인 + DNS) / BL-071 (Cloud Run deploy 본격, audit 16 gap 처리) / BL-072 (Resend) / BL-073~075 (캠페인 + 인터뷰 + H2 gate)
- **<7 → polish iter 3**: BL-178 (production OHLCV invalid close root cause) / BL-179 (uvicorn watchfiles `.env*` 감지) / BL-176 follow-up (SelectWithDisplayName clear) / BL-174 detail (live-session-detail Empty/Failed/Loading) / BL-177-A/B/C (visible-range / tooltip / cluster) / BL-150 잔여 (walk-forward + monte-carlo)

**전체 sprint 이력:** [`docs/dev-log/INDEX.md`](docs/dev-log/INDEX.md) — 40+ 회고·ADR·dogfood 기록 인덱스

**미해결 BL:** [`docs/REFACTORING-BACKLOG.md`](docs/REFACTORING-BACKLOG.md) — Sprint 34 종료 시점 갱신 (Sprint 34 Resolved: BL-175 + BL-177 partial. Cancel: BL-166. 신규 등록: BL-177-A/B/C / BL-178 / BL-179 = +5 net. defer Sprint 35+: BL-176 follow-up / BL-174 detail / BL-070~072 / BL-150 잔여)

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
