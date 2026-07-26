# AI 기반 1인 풀스택 개발 방법론

> 신규 프로젝트에 바로 적용 가능한 6 Stage 프레임워크.
> Stage 1~2는 프로젝트 초반 1회. Stage 3~6은 2주 Sprint로 반복.
>
> Gstack + Superpowers 등 특정 도구를 사용하는 경우
> `methodology-tooled.md`를 참조하세요.

---

## 전체 흐름

```
[Stage 1] 기획 + 아키텍처 → [Stage 2] 디자인
  ↓
[Stage 3] Sprint 계획 → [Stage 4] 구현 → [Stage 5] 검증 + 배포 → [Stage 6] 학습
  ↓                                                                    ↓
  └──────────────── Stage 3로 돌아감 (다음 Sprint) ←──────────────────┘
```

---

## Stage 1: 기획 + 아키텍처 — "뭘 만들고, 어떤 구조로?"

### Phase A: 기획 (뭘 만들지)

**도구:** 제품 비전 수립 도구 (예: Gstack /office-hours, BMAD discovery)

1. 6개 강제 질문: 수요 증거, 현재 해결법, 구체적 사용자, 가장 좁은 쐐기, 관찰, 미래 적합성
2. 전제(Premises) 확인 → 3가지 접근 방안 비교 → 선택
3. 디자인 문서 생성 → `docs/00_project/`

**선택적:** 스코프 검증 도구 (예: Gstack /plan-ceo-review, /autoplan)

**산출물:** 디자인 문서 (문제, 수요 증거, 타겟 유저, 성공 기준) — 타겟 유저·핵심 가치·성공 기준 확정 시 Phase B 진입

### Phase B: 아키텍처 (어떤 구조로)

**도구:** 아키텍처 리뷰 도구 (예: Gstack /plan-eng-review) + 직접 문서 작성

1. 아키텍처 방향 검증 (리뷰 도구) — 상세 문서 작성 전에 먼저
2. 기술 스택 결정 → `docs/dev-log/001-tech-stack.md` (ADR)
3. 데이터 모델 설계 → `docs/04_architecture/erd.md` (전체 Phase 고려)
4. API 경계 설계 → `docs/03_api/endpoints.md` (FE mock API와 1:1 대응)
5. 파이프라인 설계 → `docs/04_architecture/` (데이터 흐름, 비동기 패턴)

**핵심:** 아키텍처는 전체 Phase 커버. 실행 계획은 Sprint 직전에만 상세화.

**산출물:** ADR, ERD, API 명세, 아키텍처 문서 — 기술 스택 ADR + ERD + API 명세 완료 시 통과

---

## Stage 2: 디자인 — "어떻게 보일 것인가?"

**도구:** 디자인 시스템 생성 도구 + UI 프로토타이핑 도구 (예: /design-consultation, Stitch MCP, Pencil MCP)

1. 디자인 시스템 정의 → DESIGN.md (색상, 타이포, 간격, 모션, 분위기)
2. UI 프로토타이핑 도구 → DESIGN.md 임포트 → 핵심 화면 생성 → 실시간 수정 반복
3. 커스텀 컴포넌트만 정밀 편집 (기존 UI 킷에 없는 것)

**사용 비율:** 일반 화면 80% 프로토타이핑, 커스텀 20% 정밀 편집

**산출물:** DESIGN.md, 화면별 스크린샷, 디자인 토큰 — 핵심 화면 3개 이상 완료 시 통과

---

## Stage 3: Sprint 계획 — "이번 2주에 뭘 할 것인가?"

**도구:** 설계 탐색 + 계획 수립 (예: Superpowers brainstorming → writing-plans)

1. Stage 1 산출물(ADR, ERD, API 명세)이 있으면 먼저 참조하여 기존 설계와의 정합성을 확인한다
2. Vertical Slice 선정 ("FE+BE 관통하는 핵심 흐름은?")
3. 설계 탐색 (필수) — 기능 단위 설계 탐색
4. 계획 수립 — 구체적 파일, 순서, 의존성
5. [중간 규모+] 별도 서브에이전트에서 계획 리뷰
6. 병렬화 판단 — 독립 작업은 git worktree로 분리

**산출물:** Sprint 작업 목록 (우선순위 + 의존성) — 모든 task에 파일 경로 + 검증 기준 포함 시 통과

---

## Stage 4: 구현 — "코드 작성"

**도구:** TDD 프레임워크 (예: Superpowers TDD) → 코드 정리 도구 (예: /simplify) → 브라우저 검증

1. TDD — 테스트 먼저 → Red → Green → Refactor
2. 코드 정리 — TDD 잔여물 정리 (코드량 5~15% 감소)
3. 브라우저 검증 — FE 변경 시 즉시 확인
4. 프로젝트 코딩 규칙 자동 적용 (`.ai/rules/` 참조)

**모델 전략:**

| 작업 | 모델 |
|------|------|
| 아키텍처, 새 기능, 디버깅 | Opus |
| 단순 수정, 문서 | Sonnet |
| 파일 탐색 | Haiku |

### 병렬 실행 운영 원칙

작업 규모에 따라 적절한 병렬화 기법을 선택한다.

**공통 분배 기준:** 파일 경계가 겹치지 않는 작업끼리 분리한다.
- 좋은 분리: `feature/auth` (auth/) vs `feature/dashboard` (dashboard/) — 파일 겹침 없음
- 나쁜 분리: `feature/auth-ui` vs `feature/auth-api` — 공유 타입 파일에서 충돌

#### 기법 A: 서브에이전트 (소규모 — 같은 기능 내 분할)

메인 에이전트 내부에서 서브에이전트를 spawn하여 병렬 처리한다.

- **적합:** 3개 이하 파일 동시 수정, 코드베이스 탐색, 독립적 리서치
- **장점:** 경량, 빠름, 추가 도구 불필요
- **한계:** 서브에이전트는 도구 제한 있음, 사람이 직접 개입 불가

#### 기법 B: 터미널 멀티플렉서 (중~대규모 — 독립 기능 병렬)

터미널 멀티플렉서(tmux, cmux 등)로 독립 에이전트 세션을 여러 개 운영한다.

- **적합:** 2개 이상 독립 기능 동시 개발, Sprint 단위 병렬화
- **장점:** 각 에이전트가 full 컨텍스트, 사람이 언제든 세션에 개입 가능
- **한계:** 토큰 비용 N배, 세션 간 직접 통신 불가 (사람이 중계)

#### 세션 구성 (기법 B 기준, 권장 3-5개)

| 세션 | 역할 | 비고 |
|------|------|------|
| MAIN | 계획, 통합, PR 생성 | main 브랜치 |
| FEAT-1~N | 기능별 독립 구현 | 각각 별도 worktree |
| REVIEW | 완료된 코드의 독립 리뷰 | 구현 세션과 분리하여 편향 방지 |

**운영 흐름:**
1. MAIN에서 Sprint 계획 수립, 작업 분배
2. 기능별 worktree 생성 → 각 세션에서 독립 에이전트 실행
3. 사람은 다른 작업 진행 또는 주기적으로 세션 확인
4. 완료된 기능은 REVIEW 세션에서 독립 리뷰
5. MAIN에서 병합

### 막혔을 때 탈출 패턴

| 신호 | 대응 |
|------|------|
| 동일 에러 3회 반복 | 새 세션에서 에러 메시지만 전달하여 재시작 |
| 세션 컨텍스트 포화 | 새 세션 시작 + 진행 상황 요약 인계 |
| 접근 방식 자체가 잘못된 느낌 | Stage 3로 돌아가서 계획 재작성 |
| 탐색에 컨텍스트를 많이 소비한 후 구현 전환 | 탐색 결과를 요약 → 새 세션에서 요약만 전달하여 구현 |

**산출물:** 모든 task 테스트 통과 + 코드 정리 완료 + FE 브라우저 검증 시 통과

---

## Stage 5: 검증 + 배포 — "제대로 동작하고, 사용자에게 전달"

### 5a: 리뷰

1. **독립 리뷰 세션** — 고위험 변경(인증, 결제, DB 스키마)은 구현과 별도 세션에서 리뷰한다.
   새 세션은 구현 컨텍스트가 없으므로 확증 편향 없이 코드를 평가한다.
2. 코드 리뷰 (리뷰 도구 또는 수동)

### 5b: QA

1. Sprint 말 통합 QA (목표: Health score 8+ 또는 자체 기준)
2. 라이브 UI 비주얼 감사
3. 버그 발견 시: 체계적 디버깅 (재현→가설→추적→수정)

### 5c: Ship

1. PR 생성 — 테스트 + 리뷰 + VERSION/CHANGELOG
2. 보안 감사 (배포 전 1회)

### 5d: Deploy + Monitor

1. 배포 전: migration/rollback 계획 확인, secrets 감사
2. 배포
   - MVP/소규모: 직접 배포 (카나리 불필요)
   - 프로덕션/다수 사용자: 단계적 롤아웃 (카나리/블루-그린)
3. 배포 후: 헬스체크 + 모니터링
4. (선택) 성능 기준선 (성능 민감 기능 후)

**산출물:** QA 통과 + PR 머지 + 헬스체크 통과 시 완료

---

## Stage 6: 학습 — "뭘 배웠는가?"

**도구:** 교훈 기록 + 회고 도구 (예: lessons.md, Gstack /retro)

1. 실수 즉시 → `.ai/project/lessons.md` 기록
2. Sprint 말 → 회고 (커밋 분석 + lessons.md 업데이트)
3. 3회 반복 패턴 → `.ai/stacks/` 규칙 승격
4. 정기 감사 → 모델 개선으로 불필요해진 규칙 삭제

**승격 경로:** lessons.md → .ai/project/ → .ai/stacks/ → .ai/common/ → 삭제

### Sprint 전환 체크리스트

Stage 6 완료 후 Stage 3로 돌아갈 때:
1. lessons.md 반영 확인
2. 회고 개선점을 다음 Sprint 제약조건에 반영
3. 이전 Sprint에서 스킵한 이슈 중 이번에 처리할 것 선별
4. 이전 Sprint에서 새로 발견된 요구사항이 있으면 Stage 1 재방문 검토

---

## 신규 프로젝트 시작 체크리스트

```
□ ai-rules 복사 (README.md "가져온 후 할 일" 참조) + .ai/rules/ 심링크 설정
□ docs/ 스타터 복사: cp .ai/templates/docs/TODO.md docs/TODO.md
□ lessons.md 초기화: cp .ai/templates/lessons-starter.md .ai/project/lessons.md
□ PostToolUse/Stop 훅 설정 (.ai/templates/settings.json.example 참조)
```

위 셋업 완료 후, AI 에이전트와 함께 아래 순서로 진행:

```
□ 제품 비전 수립
  → 프롬프트: "이 프로젝트의 타겟 유저, 핵심 차별점, MVP 범위를 정의해줘"
  → 산출물: docs/00_project/vision.md
□ AGENTS.md "현재 컨텍스트" 채우기 (프로젝트명, 설명, 스택, 도메인)
□ 기술 스택 ADR → docs/dev-log/001-tech-stack.md
□ ERD 설계 (전체 Phase 고려) → docs/04_architecture/erd.md
□ API 명세 (FE mock과 1:1 대응) → docs/03_api/endpoints.md
□ (선택) 디자인 시스템 → DESIGN.md
□ PRD Sprint 분해 → docs/01_requirements/
□ Sprint 1 시작 → Stage 3~6 반복
```

---

## MCP 관리

| 세션 | 활성 MCP | 비활성 |
|------|---------|--------|
| 코딩 | GitHub만 | 디자인 도구 |
| 디자인 | UI 프로토타이핑 + GitHub | — |
| 디버깅 | GitHub | 디자인 도구 |

---

## 핵심 원칙

1. **아키텍처는 전체, 실행은 Sprint 단위** — 나중에 DB 스키마 바꾸는 게 가장 비싼 실수
2. **Vertical Slice** — Phase 순서 대신 FE+BE 관통
3. **코드 생성은 AI 에이전트** — 디자인 도구는 "시각적 결정"에만
4. **설계 탐색 필수** — 매 기능 구현 전 설계 탐색
5. **TDD → 정리 → 검증 → 배포** — 품질 파이프라인 빠짐없이
6. **lessons.md** — 실수를 자산으로, 3회 반복 시 규칙 승격
7. **막히면 세션을 버려라** — 오염된 컨텍스트보다 새 세션 + 요약 인계가 빠르다
