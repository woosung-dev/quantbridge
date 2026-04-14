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
| [00_project/](./00_project/) | 프로젝트 비전, 개요 | 작성 완료 |
| [01_requirements/](./01_requirements/) | 요구사항, MVP 범위 | 예정 |
| [02_domain/](./02_domain/) | 도메인 모델 | 예정 |
| [03_api/](./03_api/) | API 엔드포인트 스펙 | 예정 |
| [04_architecture/](./04_architecture/) | ERD, 시스템 아키텍처, 데이터 흐름 | 예정 |
| [05_env/](./05_env/) | 환경 설정 가이드 | 예정 |
| [06_devops/](./06_devops/) | Docker, CI/CD | 예정 |
| [07_infra/](./07_infra/) | 배포, 모니터링 | 예정 |
| [DESIGN.md](../DESIGN.md) | 디자인 시스템 (색상, 타이포, 컴포넌트) | **확정** |
| [prototypes/](./prototypes/) | Stage 2 HTML 프로토타입 (4개 화면) | **확정** |
| [dev-log/](./dev-log/) | ADR (의사결정 기록) | 활성 |
| [guides/](./guides/) | 개발 가이드 | 활성 |
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

## 주요 문서 바로가기

| 문서 | 설명 |
|------|------|
| [DESIGN.md](../DESIGN.md) | 디자인 시스템 (Stage 2 산출물) |
| [QUANTBRIDGE_PRD.md](../QUANTBRIDGE_PRD.md) | 상세 PRD |
| [AGENTS.md](../AGENTS.md) | AI 에이전트 컨텍스트 |
| [.ai/](../.ai/) | 코딩 규칙 |
| [guides/development-methodology.md](./guides/development-methodology.md) | 6-Stage 개발 방법론 + 병렬 개발 전략 |
| [dev-log/001-tech-stack.md](./dev-log/001-tech-stack.md) | ADR-001: 기술 스택 결정 |
| [dev-log/002-parallel-scaffold-strategy.md](./dev-log/002-parallel-scaffold-strategy.md) | ADR-002: 병렬 스캐폴딩 전략 |
