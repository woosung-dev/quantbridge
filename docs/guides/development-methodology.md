# QuantBridge — 개발 방법론

> **상태:** 확정
> **일자:** 2026-04-13

---

## 전체 흐름

```
[1회성 단계]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stage 1: 계획 + 아키텍처
  ├── /office-hours (제품 방향 검증)
  ├── /autoplan (CEO/디자인/엔지니어링/DX 리뷰)
  └── Assignment: TV 전략 50개 분류 (Go/No-Go 판단)

Stage 2: 디자인
  ├── /design-consultation → DESIGN.md (디자인 시스템)
  └── 핵심 화면 3개 프로토타입

[반복 단계 — 2주 스프린트 사이클]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ┌──────────────────────────────────┐
  │ Stage 3: 스프린트 계획             │
  │   brainstorming → writing-plans  │
  │            ↓                     │
  │ Stage 4: 구현                     │
  │   TDD → /simplify → /browse     │
  │            ↓                     │
  │ Stage 5: 검증 + 배포              │
  │   /review → /qa → /ship         │
  │            ↓                     │
  │ Stage 6: 학습                     │
  │   /retro → lessons.md 업데이트    │
  │            ↓                     │
  └──── 다음 스프린트로 ─────────────┘
```

---

## Stage 상세

### Stage 1: 계획 + 아키텍처 (1회성)

| 단계 | 도구 | 산출물 |
|------|------|--------|
| 제품 방향 검증 | `/office-hours` | 핵심 가치 명확화, 타겟 사용자 확정 |
| 종합 리뷰 | `/autoplan` | 확정된 플랜 (CEO/디자인/엔지니어링/DX 관점) |
| 시장 검증 | Assignment | TV 전략 50개 분류 → Go/Adjust/Pivot 판단 |

**주의:** Assignment 결과가 **Pivot**이면 Stage 2 방향이 완전히 바뀔 수 있음.

### Stage 2: 디자인 (1회성)

| 단계 | 도구 | 산출물 |
|------|------|--------|
| 디자인 시스템 | `/design-consultation` | DESIGN.md (색상, 타이포, 다크 테마) |
| 화면 프로토타입 | 수동/Figma | 핵심 화면 3개 (전략 편집, 백테스트 결과, 트레이딩 대시보드) |

**이후 스프린트에서는** 확정된 디자인 시스템을 재사용.

### Stage 3: 스프린트 계획 (매 스프린트)

| 단계 | 도구 | 산출물 |
|------|------|--------|
| 브레인스토밍 | `brainstorming` | 요구사항 탐색, 설계 방향 |
| 플랜 작성 | `writing-plans` | 구현 계획서 (파일별 변경사항, 테스트 항목) |

### Stage 4: 구현 (매 스프린트)

| 단계 | 도구 | 산출물 |
|------|------|--------|
| TDD 사이클 | `test-driven-development` | RED → GREEN → REFACTOR |
| 코드 정리 | `/simplify` | 중복 제거, 품질 향상 |
| UI 검증 | `/browse` | 브라우저 테스트, 스크린샷 |

### Stage 5: 검증 + 배포 (매 스프린트 — 빠뜨리기 쉬움)

| 단계 | 도구 | 산출물 |
|------|------|--------|
| 코드 리뷰 | `/review` | PR 리뷰 리포트 |
| QA 테스트 | `/qa` | 버그 리포트 + 수정 |
| 배포 | `/ship` | PR 생성, 버전 범프, CHANGELOG |

**빠뜨리면:** 코드 리뷰 없이 머지, QA 없이 배포 → 버그 누적

### Stage 6: 학습 (매 스프린트 — 빠뜨리기 쉬움)

| 단계 | 도구 | 산출물 |
|------|------|--------|
| 회고 | `/retro` | 스프린트 분석 리포트 |
| 교훈 기록 | 수동 | `.ai/project/lessons.md` 업데이트 |

**빠뜨리면:** 같은 실수 반복, 규칙 승격 안 됨

---

## 보안 게이트

| 시점 | 도구 | 목적 |
|------|------|------|
| Phase 3 (데모 트레이딩) 진입 전 | `/cso` | 거래소 API Key 암호화, Clerk 토큰 처리, OWASP 점검 |

---

## 병렬 개발 전략

> Git Worktree를 활용한 멀티 에이전트 병렬 개발. 상세: `docs/dev-log/002-parallel-scaffold-strategy.md`

### 원칙

1. **파일 소유권 분리** — 각 워크트리가 수정하는 파일 집합이 겹치지 않아야 함
2. **짧은 수명** — 워크트리는 가능한 빨리 main에 머지
3. **공유 인프라 우선** — scaffold/auth/DB 공통 모듈이 먼저 존재해야 도메인 병렬화 가능

### 3-Phase 파이프라인

```
Phase 0 (순차)           Phase 1 (병렬 2~3)          Phase 2 (병렬 3~4)
─────────────           ──────────────────          ──────────────────
초기 커밋                BE 핵심 도메인               BE 고급 도메인
scaffold                FE 핵심 페이지               FE 고급 UI
docker-compose          Market Data 수집            WebSocket/실시간
auth + common
```

### 워크트리 사용법

```bash
# 독립 브랜치에서 작업 시작
claude --worktree feat/backend-scaffold

# 완료 후 main에 머지
git checkout main
git merge feat/backend-scaffold
```
