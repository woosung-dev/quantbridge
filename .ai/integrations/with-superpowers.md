# superpowers와 함께 사용하기

> [superpowers](https://github.com/obra/superpowers) — TDD 기반 에이전틱 스킬 프레임워크.
> "코드 생성기"가 아닌 "훈련된 소프트웨어 엔지니어"처럼 동작하도록 프로세스를 강제.

## 설치

```bash
# 1. 마켓플레이스 등록
/plugin marketplace add obra/superpowers-marketplace

# 2. 플러그인 설치
/plugin install superpowers@superpowers-marketplace

# 3. 업데이트
/plugin update superpowers
```

요구사항: Claude Code 2.0.13 이상

## superpowers가 하는 일

session-start 훅으로 자동 주입되어, 아래 워크플로우를 **강제**합니다:

```
Brainstorm → Write Plan → Execute Plan → Test(RED) → Implement(GREEN) → Review → Finish Branch
```

## 스킬 목록 (12개)

### 핵심 워크플로우

| 스킬 | 역할 |
|------|------|
| `brainstorming` | 구현 전 소크라테스식 설계 정교화 |
| `writing-plans` | 상세 구현 계획 (파일 경로, 순서, 검증 기준) |
| `executing-plans` | 체크포인트 포함 배치 실행 |
| `test-driven-development` | RED → GREEN → REFACTOR 강제 |
| `verification-before-completion` | 완료 주장 전 실제 검증 강제 |

### 병렬·협업

| 스킬 | 역할 |
|------|------|
| `dispatching-parallel-agents` | 독립 서브에이전트 병렬 실행 |
| `subagent-driven-development` | 2단계 리뷰 + 빠른 반복 |
| `using-git-worktrees` | 격리된 worktree 브랜치 작업 |
| `finishing-a-development-branch` | 병합/PR/유지/폐기 옵션 제시 |

### 품질·디버깅

| 스킬 | 역할 |
|------|------|
| `systematic-debugging` | 4단계 근본 원인 분석 (재현→가설→추적→수정) |
| `requesting-code-review` | 자동 코드 리뷰 체크리스트 |
| `receiving-code-review` | 피드백 대응 가이드 (맹목적 수용 방지) |

### 메타

| 스킬 | 역할 |
|------|------|
| `writing-skills` | 커스텀 스킬 생성 (프로젝트 고유 프로세스를 스킬화) |

## ai-rules와의 관계

| 영역 | ai-rules | superpowers | 우선 |
|------|----------|-------------|------|
| 개발 워크플로우 | AGENTS.md §4 / global.md §1 | brainstorming → writing-plans → executing-plans | **superpowers** (자동 오버라이드) |
| Plan Before Code | AGENTS.md §3 | writing-plans 스킬 | **superpowers** |
| 코딩 규칙 | 스택별 상세 규칙 | 없음 | **ai-rules 전담** |
| 코드 리뷰 | 없음 | requesting/receiving-code-review | superpowers 추가 |
| 디버깅 | 없음 | systematic-debugging | superpowers 추가 |
| 자기개선 | lessons.md 승격 루프 | writing-skills (커스텀 스킬 생성) | 시너지 — lessons에서 반복 패턴을 스킬로 승격 |

superpowers는 `<EXTREMELY_IMPORTANT>` 태그로 주입되므로,
AGENTS.md의 워크플로우보다 **자동으로 우선권**을 가집니다.
ai-rules의 워크플로우를 삭제할 필요 없이 그대로 두면 됩니다.

## 조정이 필요한 부분

### Git 워크플로우

superpowers는 **git worktree** 기반 브랜치 전략을 사용합니다.
ai-rules의 Git Safety Protocol(커밋/푸쉬 전 사용자 승인)은 worktree에서도 동일하게 적용하세요.

### 문서화

superpowers의 `writing-plans` 스킬이 계획을 작성하지만,
ai-rules의 `docs/` 디렉토리 구조(AGENTS.md §4)는 별도로 유지하세요.
계획 문서를 `docs/reference/`에 저장하면 두 시스템이 자연스럽게 공존합니다.

### 커스텀 스킬과 자기개선 루프

superpowers의 `writing-skills` 스킬로 프로젝트 고유 프로세스를 스킬화할 수 있습니다.
ai-rules의 자기개선 루프(lessons.md → 규칙 승격)와 결합하면:

```
실수 반복 → lessons.md 기록 → 3회 반복 시 → superpowers 커스텀 스킬로 승격
```

## 사용 시기

### 잘 맞는 경우
- 복잡한 기능 구현 (여러 모듈, 의존성)
- 높은 품질 요구 (TDD 필수)
- 장기 유지보수 코드베이스

### 과도한 경우
- 빠른 프로토타이핑, 일회용 스크립트
- 단순 문서 수정, 설정 변경

> methodology-tooled.md의 "도구는 점진적으로" 원칙: 필요가 증명될 때까지 모든 스킬을 활성화하지 마세요.

## 요약

- **설치만 하면 됩니다.** ai-rules 파일 수정 불필요.
- superpowers가 워크플로우를 오버라이드하고, ai-rules는 코딩 컨벤션을 담당합니다.
- lessons.md의 반복 패턴을 커스텀 스킬로 승격하면 두 시스템이 시너지를 냅니다.
