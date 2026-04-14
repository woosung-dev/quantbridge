# ADR-002: 병렬 스캐폴딩 전략

> **상태:** 확정
> **일자:** 2026-04-13
> **작성자:** QuantBridge 팀

---

## 컨텍스트

프로젝트가 Stage 1 (계획 + 아키텍처) 단계에서 소스 코드 0줄 상태.
다른 세션에서 `/autoplan` + `DESIGN.md` 작업이 병렬로 진행 중.
이 시간을 활용하여 프로젝트 골격을 병렬로 구축하여, autoplan 완료 즉시 Stage 3 (스프린트) 진입이 가능한 상태를 목표로 한다.

## 결정

### 3세션 병렬 스캐폴딩 (+ autoplan 세션 = 총 4세션)

```
                    ┌─── autoplan 세션 (기존) ───────────┐
                    │  main 브랜치                       │
                    │  /autoplan → DESIGN.md             │
                    │  산출물: 확정 플랜 + 디자인 시스템    │
                    └────────────────────────────────────┘

  Session 1               Session 2                Session 3
  (main 브랜치)            (워크트리)               (워크트리)
  ────────────            ────────────             ────────────
  feat: root-infra        feat/backend-scaffold    feat/frontend-scaffold

  담당 파일:              담당 파일:               담당 파일:
  ├ docker-compose.yml    └ backend/**             └ frontend/**
  ├ .github/workflows/
  ├ .husky/
  └ root 설정 파일
```

### 파일 소유권 매트릭스

| 파일/디렉토리 | Session 1 | Session 2 | Session 3 | autoplan |
|--------------|:---------:|:---------:|:---------:|:-------:|
| `docker-compose.yml` | **O** | X | X | X |
| `.github/` | **O** | X | X | X |
| `backend/` | X | **O** | X | X |
| `frontend/` | X | X | **O** | X |
| `docs/` | X | X | X | **O** |
| `DESIGN.md` | X | X | X | **O** |

**겹침: 0%** — 머지 충돌 없음 보장

### 각 세션 작업 범위

#### Session 1: Root Infrastructure (main 브랜치)

1. **초기 커밋** — 현재 planning docs 전체
2. **docker-compose.yml**
   - PostgreSQL 15 + TimescaleDB extension
   - Redis (cache + Celery broker)
   - 환경변수는 `.env` 참조
3. **CI/CD 기본 설정**
   - `.github/workflows/ci.yml` (lint + typecheck + test)
4. **Pre-commit hooks**
   - `.husky/pre-commit` (lint-staged)
5. **Root 설정**
   - `.editorconfig`
   - 루트 `.gitignore` 업데이트

#### Session 2: Backend Scaffold (feat/backend-scaffold 워크트리)

1. **FastAPI 프로젝트 초기화** (uv)
   - `pyproject.toml`: 전체 의존성
   - Python 3.11+
2. **디렉토리 구조** (3-Layer)
   ```
   backend/src/
   ├── main.py              — FastAPI app + /health
   ├── core/config.py       — pydantic-settings
   ├── common/              — database, exceptions, pagination, dependencies
   ├── auth/                — Clerk JWT 검증
   ├── strategy/            — 빈 도메인 구조
   ├── backtest/            — 빈 도메인 구조
   ├── stress_test/         — 빈 도메인 구조
   ├── optimizer/           — 빈 도메인 구조
   ├── trading/             — 빈 도메인 구조
   ├── exchange/            — 빈 도메인 구조
   └── market_data/         — 빈 도메인 구조
   ```
3. **Alembic 설정** (async migration 인프라만, 테이블 정의 제외)
4. **테스트 인프라** (pytest + pytest-asyncio + conftest.py)
5. **개발 도구** (ruff.toml, mypy.ini)

#### Session 3: Frontend Scaffold (feat/frontend-scaffold 워크트리)

1. **Next.js 16 프로젝트 초기화** (pnpm)
   - TypeScript strict, App Router, Tailwind CSS v4
2. **핵심 패키지 설치**
   - @clerk/nextjs, @tanstack/react-query, zustand
   - react-hook-form, zod, shadcn/ui v4 기본 컴포넌트
3. **디렉토리 구조** (FSD Lite)
   ```
   frontend/src/
   ├── app/                 — layout, page, (auth), (dashboard)
   ├── components/          — ui/, layout/, providers/
   ├── features/            — strategy/, backtest/, trading/, exchange/ (빈 구조)
   ├── hooks/               — use-debounce.ts
   ├── lib/                 — api-client.ts, utils.ts
   ├── store/               — ui-store.ts
   └── types/               — common.ts
   ```
4. **Clerk 미들웨어** (proxy.ts — 공개 라우트만 정의)
5. **개발 도구** (ESLint, Prettier, vitest)

### 실행 순서

```
[즉시]
  Session 1: 초기 커밋 (사용자 승인)

[초기 커밋 직후 — 3세션 동시 실행]
  Session 1: docker-compose + CI + root 설정
  Session 2: claude --worktree feat/backend-scaffold
  Session 3: claude --worktree feat/frontend-scaffold

[3세션 완료 후]
  Session 1에서 머지 조율:
    git merge feat/backend-scaffold
    git merge feat/frontend-scaffold

[autoplan + DESIGN.md 완료 후]
  → 즉시 Stage 3 (스프린트 계획) 진입 가능
```

### autoplan과의 동기화

autoplan이 ERD/API 스펙을 변경할 수 있으나, scaffold는 **빈 도메인 디렉토리 구조만** 생성하므로 영향 없음.
실제 모델/스키마 구현은 Stage 3 스프린트에서 확정된 플랜 기반으로 진행.

## 거부한 대안

| 대안 | 거부 이유 |
|------|----------|
| autoplan 완료까지 대기 | 스캐폴딩은 플랜 독립적 작업. 대기는 시간 낭비 |
| 7개 도메인별 워크트리 | `common/` 모듈 동시 수정 → 머지 충돌 불가피 |
| 풀스택 수직 슬라이스 | 공유 인프라 없이 수직 슬라이스 불가능 (코드 0줄 상태) |
| 2세션만 사용 | 가능하지만, Infra를 BE/FE 한쪽에 묶으면 작업량 불균형 |

## 결과

- 4세션 동시 실행으로 Stage 1 → Stage 3 전환 시간 최소화
- scaffold 완료 시 `docker compose up → pnpm dev → uvicorn` 즉시 동작
- 머지 충돌 0% (파일 소유권 완전 분리)
