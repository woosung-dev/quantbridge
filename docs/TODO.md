# QuantBridge — TODO

> 사람과 AI가 공동 관리하는 작업 추적 파일.
> 차단 항목은 `[blocked]` 표시, 질문은 Questions 섹션에 기록.

---

## Next Actions

### Stage 1: 계획 + 아키텍처 ✅ 완료

- [x] /office-hours 완료 (2026-04-13, Trust Layer 프레이밍 확정)
- [x] /autoplan 완료 (2026-04-13, CEO+Design+Eng 리뷰, Codex+Claude 듀얼 검증)
  - 4개 critical 인사이트 → CLAUDE.md + ADR-003 + lessons.md에 증류 완료
- [x] DESIGN.md 작성 — /design-consultation + ui-ux-pro-max (8개 변형 비교 → Final 확정)

### Phase 0: 병렬 스캐폴딩 (autoplan과 동시 진행)

**Session 1 — Root Infrastructure (main):** ✅ 완료 (2026-04-15)
- [x] 초기 커밋 (planning docs + config)
- [x] docker-compose.yml (TimescaleDB 단일 인스턴스 + Redis)
- [x] .github/workflows/ci.yml (changes-aware, frontend/backend 분리 + 요약 잡)
- [x] .husky/pre-commit + root package.json (husky + lint-staged)
- [x] .editorconfig + .gitignore 보강
- [x] .env.example POSTGRES_* 정렬 (docker-compose SSOT)

**Session 2 — Backend Scaffold (feat/backend-scaffold 워크트리):** ✅ 완료
- [x] FastAPI 프로젝트 초기화 (uv + pyproject.toml)
- [x] 3-Layer 디렉토리 구조 (src/core, common, auth, 7개 도메인)
- [x] Alembic async migration 인프라
- [x] pytest + pytest-asyncio 테스트 인프라 (health 엔드포인트 검증 1건 통과)
- [x] ruff.toml + mypy.ini 개발 도구 (ruff/mypy/pytest 모두 clean)

**Session 3 — Frontend Scaffold (feat/frontend-scaffold 워크트리):** ✅ 완료
- [x] Next.js 16 프로젝트 초기화 (pnpm)
- [x] FSD Lite 디렉토리 구조 (app, components, features, lib)
- [x] Clerk 인증 (ClerkProvider + proxy.ts)
- [x] shadcn/ui v4 기본 컴포넌트
- [x] ESLint + Prettier + vitest 개발 도구

**머지 완료 (2026-04-15):** d82de8b (backend) + 059eca9 (frontend) on main

### Phase 0 완료 후

- [ ] 3개 워크트리 머지 (main ← backend ← frontend)
- [ ] `docker compose up && pnpm dev && uvicorn` 동작 확인
- [ ] Stage 3 첫 스프린트 계획 시작

### 미완성 문서 (Stage 2 이후 채울 예정)

- [ ] docs/01_requirements/ — 상세 요구사항
- [ ] docs/02_domain/ — 도메인 모델 상세
- [ ] docs/05_env/ — 환경 설정 가이드
- [ ] docs/06_devops/ — Docker, CI/CD 상세
- [ ] docs/07_infra/ — 배포, 모니터링

## In Progress

_(현재 진행 중 없음 — Phase 0 대기 상태)_

## Blocked

_(없음)_

## Questions

- [ ] DB 호스팅: Self-hosted PostgreSQL vs Neon Serverless — TimescaleDB 요구사항 때문에 self-hosted가 유리하나 최종 결정 필요
- [ ] 배포 전략: Vercel + Cloud Run vs Docker + K8s — MVP 단계 결정 필요
- [ ] Socket.IO vs 순수 FastAPI WebSocket — 실시간 데이터 전송 방식 결정 필요

### Stage 2: 디자인 ✅ 완료 (Tier 1 Phase 1 MVP 커버)

- [x] DESIGN.md 작성 (디자인 시스템 + App Shell 패턴 §10)
- [x] 00-landing.html (랜딩 페이지, 플로팅 다크 쇼케이스)
- [x] 01-strategy-editor.html (전략 편집, Monaco 스타일)
- [x] 02-backtest-report.html (백테스트 결과 리포트)
- [x] 03-trading-dashboard.html (트레이딩 대시보드, Full Dark)
- [x] 04-login.html (로그인/가입, Split-screen)
- [x] 05-onboarding.html (4단계 온보딩 위저드)
- [x] 06-strategies-list.html (전략 목록, 카드 그리드)
- [x] 07-strategy-create.html (전략 생성 3-step 위저드)
- [x] 08-backtest-setup.html (백테스트 설정 폼)
- [x] 09-backtests-list.html (백테스트 목록 테이블)
- [x] 10-trades-detail.html (거래 내역 상세)
- [x] 11-error-pages.html (404/500/503)

**Tier 2~3 (Phase 2~4 + 공통):** 필요 시 추가 진행 (PRD 확정 후 권장)

## Completed

- [x] ADR-003 작성 — Pine 런타임 안전성 + 파서 범위 (/autoplan 인사이트 증류)
- [x] /autoplan 인사이트 증류 — CLAUDE.md 보안 규칙 2개 + lessons.md LESSON-001/002/003
- [x] Stage 2 완료 — DESIGN.md + 12개 프로토타입 (docs/prototypes/)
- [x] DESIGN.md 확정 — 8개 디자인 변형 비교, 실제 렌더링 검증, Final 91.0점
- [x] PRD 초안 작성 (QUANTBRIDGE_PRD.md)
- [x] .ai/ 규칙 셋업 (ai-rules 클론)
- [x] AGENTS.md 커스터마이징
- [x] PRD vs .ai/ spec 차이 분석 완료
- [x] 개발 워크플로우 정의 (6-Stage Methodology)
- [x] docs/dev-log/001-tech-stack.md (ADR-001) 작성
- [x] docs/04_architecture/erd.md (DB 스키마) 작성
- [x] docs/03_api/endpoints.md (API 명세) 작성
- [x] .env.example 작성
- [x] docs/guides/development-methodology.md 작성
- [x] docs/dev-log/002-parallel-scaffold-strategy.md (ADR-002) 작성
