# QuantBridge — 문서 인덱스

> TradingView Pine Script → 백테스트 → 데모/라이브 트레이딩 플랫폼

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS v4, shadcn/ui v4, React Query, Zustand |
| Backend | FastAPI, Python 3.11+, SQLModel, Pydantic V2, Celery |
| Auth | Clerk (Frontend + Backend JWT 검증) |
| Database | PostgreSQL + TimescaleDB + Redis |
| Backtest Engine | vectorbt, pandas-ta, Optuna |
| Exchange | CCXT (Bybit, Binance, OKX) |
| Infra | Docker Compose (dev) |

## 문서 구조

| 디렉토리 | 내용 | 상태 |
|----------|------|------|
| [00_project/](./00_project/) | 프로젝트 비전, 개요 | ✅ 완료 |
| [01_requirements/](./01_requirements/) | 요구사항 개요, REQ 카탈로그, Pine 분석 | ✅ 완료 |
| [02_domain/](./02_domain/) | 도메인 개요, 엔티티, 상태 머신 | ✅ 완료 |
| [03_api/](./03_api/) | API 엔드포인트 스펙 | ✅ 활성 |
| [04_architecture/](./04_architecture/) | ERD, 시스템 아키텍처, 데이터 흐름 | ✅ 완료 |
| [05_env/](./05_env/) | 로컬 셋업, 환경 변수, Clerk 가이드 | ✅ 완료 |
| [06_devops/](./06_devops/) | Docker Compose, CI/CD, Pre-commit | ✅ 완료 |
| [07_infra/](./07_infra/) | 배포·Observability·Runbook (draft) | 📝 Draft |
| [DESIGN.md](../DESIGN.md) | 디자인 시스템 (색상, 타이포, 컴포넌트) | ✅ 확정 |
| [prototypes/](./prototypes/) | Stage 2 HTML 프로토타입 (12개 화면) | ✅ 확정 |
| [dev-log/](./dev-log/) | ADR (의사결정 기록) | 활성 |
| [guides/](./guides/) | 개발 가이드, Sprint 킥오프 템플릿 | 활성 |
| [TODO.md](./TODO.md) | 작업 추적 | 활성 |

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

| 문서 | 설명 |
|------|------|
| [DESIGN.md](../DESIGN.md) | 디자인 시스템 (Stage 2 산출물) |
| [QUANTBRIDGE_PRD.md](../QUANTBRIDGE_PRD.md) | 상세 PRD |
| [AGENTS.md](../AGENTS.md) | AI 에이전트 컨텍스트 |
| [.ai/](../.ai/) | 코딩 규칙 |
| [01_requirements/requirements-overview.md](./01_requirements/requirements-overview.md) | 요구사항 개요 + REQ 인덱스 |
| [01_requirements/req-catalog.md](./01_requirements/req-catalog.md) | REQ-### 상세 카탈로그 |
| [02_domain/domain-overview.md](./02_domain/domain-overview.md) | 8 도메인 경계 + 책임 매트릭스 |
| [02_domain/entities.md](./02_domain/entities.md) | ENT-### 엔티티 카탈로그 |
| [02_domain/state-machines.md](./02_domain/state-machines.md) | 도메인 상태 전이도 |
| [04_architecture/system-architecture.md](./04_architecture/system-architecture.md) | C4 다이어그램 + 인증/에러 경계 |
| [04_architecture/data-flow.md](./04_architecture/data-flow.md) | 도메인별 시퀀스 다이어그램 |
| [05_env/local-setup.md](./05_env/local-setup.md) | 로컬 개발 환경 5분 셋업 |
| [05_env/env-vars.md](./05_env/env-vars.md) | 환경 변수 의미·획득법 카탈로그 |
| [05_env/clerk-setup.md](./05_env/clerk-setup.md) | Clerk 외부 의존성 셋업 |
| [06_devops/docker-compose-guide.md](./06_devops/docker-compose-guide.md) | Compose 운영 가이드 |
| [06_devops/ci-cd.md](./06_devops/ci-cd.md) | CI 잡 그래프 + 게이트 |
| [06_devops/pre-commit.md](./06_devops/pre-commit.md) | husky + lint-staged 가이드 |
| [07_infra/deployment-plan.md](./07_infra/deployment-plan.md) | 배포 옵션 비교 (draft) |
| [07_infra/observability-plan.md](./07_infra/observability-plan.md) | Observability 계획 (draft) |
| [07_infra/runbook.md](./07_infra/runbook.md) | 운영 Runbook (draft) |
| [guides/development-methodology.md](./guides/development-methodology.md) | 6-Stage 개발 방법론 + 병렬 개발 전략 |
| [guides/sprint-kickoff-template.md](./guides/sprint-kickoff-template.md) | Sprint 킥오프 프롬프트 템플릿 |
| [dev-log/001-tech-stack.md](./dev-log/001-tech-stack.md) | ADR-001: 기술 스택 결정 |
| [dev-log/002-parallel-scaffold-strategy.md](./dev-log/002-parallel-scaffold-strategy.md) | ADR-002: 병렬 스캐폴딩 전략 |
| [dev-log/003-pine-runtime-safety-and-parser-scope.md](./dev-log/003-pine-runtime-safety-and-parser-scope.md) | ADR-003: Pine 런타임 안전성 + 파서 범위 |
| [dev-log/004-pine-parser-approach-selection.md](./dev-log/004-pine-parser-approach-selection.md) | ADR-004: Pine 파서 접근법 선택 |
