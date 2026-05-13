# QuantBridge — TradingView Pine Script 전략 → 백테스트·데모·라이브 트레이딩 퀀트 플랫폼

> **새 AI 세션 첫 step:** 본 파일 + `docs/TODO.md` (활성 sprint 상태) + `docs/REFACTORING-BACKLOG.md` (open BL) 3 종 읽기.
> 본 파일은 **stable orientation** 만 보존. Sprint-specific narrative 는 `docs/TODO.md`, 회고/ADR 은 `docs/dev-log/INDEX.md`.

---

## Golden Rules (Immutable)

> 어떤 상황에서도 타협 금지.

- 환경 변수·API 키·시크릿을 코드에 하드코딩 금지 (`SecretStr` 사용)
- DB 접근은 Repository layer 만 (`.ai/stacks/fastapi/backend.md` §3)
- `.env.example` 에 없는 환경 변수를 코드에서 참조 금지
- 사용자 승인 없는 `git push` / 배포 금지 (main 직접 push 영구 차단)
- LLM 생성 규칙 파일을 검토 없이 그대로 사용 금지

---

## 개인 개발 원칙

### 언어 정책

- 사고 / 계획 / 대화 / 문서 / 주석 = **한국어**
- 코드 네이밍 / 커밋 메시지 = **영어**

### 역할

- **Senior Tech Lead + System Architect** 로 행동
- 유지보수 가능한 아키텍처 / 엄격한 타입 안정성 / 명확한 문서화 최우선
- 코드 제공 시 `...` 생략 금지. **완전한 코드**.
- 복잡한 설계는 Mermaid.js, 그 외 답변은 코드 + 불릿 포인트

### AI 행동 지침

- **Plan Before Code:** 코드 작성 전 "어떤 설계 문서 참고 + 어떤 방향" 짧게 브리핑
- **Atomic Update:** 코드 수정 시 관련 문서 동일 세션 안 함께 수정
- **Think Edge Cases:** 네트워크 실패 / 타입 불일치 / 빈 응답 / 권한 오류 기본 고려
- **Fact vs Assumption:** 확인된 사실 (그대로) / 추론 (`[가정]`) / 확인 필요 (`[확인 필요]`) 명시
- **Git Safety Protocol:** 커밋 / 푸쉬 / 배포 모니터링 단계별 사용자 승인. 묶음 요청만 한 번에 진행

---

## 문서화 구조 (Plan → Docs → Review → Implement 루프)

| docs/ 위치              | 용도                     |
| ----------------------- | ------------------------ |
| `00_project/`           | 프로젝트 개요            |
| `01_requirements/`      | PRD, 기능 명세 (REQ-)    |
| `02_domain/`            | 도메인 모델, ERD (ENT-)  |
| `03_api/`               | API 명세 (API-)          |
| `04_architecture/`      | 시스템 설계              |
| `05_env/` ~ `07_infra/` | 환경 설정, CI/CD, 인프라 |
| `dev-log/`              | ADR (의사결정 기록)      |
| `guides/` · `TODO.md`   | 가이드, 활성 작업 추적   |

ID 체계: `SCR-` 화면 / `API-` API / `ENT-` 엔티티 / `REQ-` 기능 / `BL-` 백로그. 한 번 부여한 ID 재사용 금지.

---

## 현재 컨텍스트

### 프로젝트 개요

- **이름:** QuantBridge
- **기술 스택:** Next.js 16 (FE) + FastAPI (BE) — 상세는 `.ai/stacks/` 참조
- **인증:** Clerk (FE + BE JWT 검증)
- **DB:** PostgreSQL + TimescaleDB (시계열) + Redis (캐시 / Celery broker)
- **비동기 작업:** Celery + Redis (백테스트, 최적화, 데이터 수집) — prefork-safe pattern §`.ai/stacks/fastapi/backend.md` §9
- **거래소:** CCXT (Bybit / OKX / Binance)
- **시크릿:** API Key AES-256 (Fernet) 암호화

### 핵심 도메인

- **Strategy** — Pine Script 파싱, 전략 CRUD, `pine_v2` 인터프리터 (Track S/A/M)
- **Backtest** — **`pine_v2` 자체 인터프리터 SSOT** (AST + bar-by-bar 이벤트 루프). vectorbt 는 _지표 계산 전용_ 으로 강등 (ADR-011 §6/§8, Sprint 8a PR #20). 리포트 24 metric.
- **Stress Test** — Monte Carlo, Walk-Forward, 파라미터 안정성 분석
- **Optimizer** — Grid / Bayesian / Genetic 파라미터 최적화 (ADR-013)
- **Trading** — CCXT 데모·라이브 주문 실행, 리스크 관리, Kill Switch
- **Market Data** — OHLCV 수집, TimescaleDB 저장, 실시간 가격 스트림

### 활성 sprint / BL / dev-log

- **활성 sprint 상태 / 다음 분기 결정:** [`docs/TODO.md`](docs/TODO.md)
- **미해결 BL:** [`docs/REFACTORING-BACKLOG.md`](docs/REFACTORING-BACKLOG.md)
- **전체 sprint 이력:** [`docs/dev-log/INDEX.md`](docs/dev-log/INDEX.md)

---

## Operational Commands

> Makefile shortcut. 자세한 타깃은 `make help`. 두 모드:
>
> - 기본: `make up` / `make be` / `make fe` → 3000 / 8000 / 5432 / 6379
> - 격리: `make up-isolated` / `make be-isolated` / `make fe-isolated` → 3100 / 8100 / 5433 / 6380 (다른 웹앱 병렬 시)

```bash
# Frontend (Next.js 16)
cd frontend && pnpm dev && pnpm test && pnpm tsc --noEmit && pnpm lint

# Backend (FastAPI)
cd backend && uvicorn src.main:app --reload --port 8000 && pytest -v && ruff check . && mypy src/
cd backend && alembic upgrade head && alembic revision --autogenerate -m "description"

# Infrastructure
docker compose up -d                          # 또는 make up
docker compose logs -f backend

# Celery
cd backend && celery -A src.tasks worker --loglevel=info --concurrency=4
cd backend && celery -A src.tasks beat --loglevel=info
```

---

## 스택 규칙 참조

> `.ai/rules/` 는 심볼릭 허브. 원본은 `.ai/common/`, `.ai/stacks/`, `.ai/project/`.

| 파일                         | 내용                                                                                             | 적용         |
| ---------------------------- | ------------------------------------------------------------------------------------------------ | ------------ |
| `.ai/rules/global.md`        | 워크플로우, 문서화, Git, 환경변수, 메타-방법론 영구 규칙 §7 (LESSON-037~040/063 승격)            | **전체**     |
| `.ai/rules/typescript.md`    | TypeScript Strict, 네이밍 컨벤션                                                                 | **전체**     |
| `.ai/rules/nextjs-shared.md` | Next.js 공통 (Zod v4, shadcn, 반응형)                                                            | **Frontend** |
| `.ai/rules/frontend.md`      | Next.js 16 FE-only (FastAPI BE 조합) + 차용 패턴 3 종 (Server/Client / error.tsx / ActionResult) | **Frontend** |
| `.ai/rules/backend.md`       | FastAPI + SQLModel + Celery prefork-safe                                                         | **Backend**  |
| `.ai/project/lessons.md`     | 학습 기록 (실수 → 규칙 승격 path)                                                                | **활성**     |

---

## QuantBridge 고유 규칙 (도메인 특화)

- 금융 숫자는 `Decimal` 사용 (float 금지). 합산: `Decimal(str(a)) + Decimal(str(b))` — float 공간 합산 후 변환 금지 (Sprint 4 D8 교훈)
- 백테스트 / 최적화 / 스트레스 테스트는 반드시 Celery 비동기. API 핸들러 직접 실행 금지
- Celery prefork-safe: `create_async_engine()` / vectorbt 등 무거운 객체는 module import 시점 호출 금지. Lazy init 함수로 worker 자식 fork 후 생성. Worker pool=prefork 고정 (Sprint 4 D3 교훈)
- 거래소 API Key 는 AES-256 (Fernet) 암호화 저장 (평문 금지)
- OHLCV 데이터는 TimescaleDB hypertable 에 저장
- 실시간 데이터는 WebSocket + Zustand 캐시 (React Query 와 분리)
- Pine Script → Python 변환 시 `exec()` / `eval()` 절대 금지 — 인터프리터 패턴 (`pine_v2`) 또는 RestrictedPython sandbox 강제 (ADR-003)
- Pine Script 미지원 함수 1 개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지 (잘못된 결과 방지) (ADR-003)
