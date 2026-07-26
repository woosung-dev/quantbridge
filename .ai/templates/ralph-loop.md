# Ralph Loop 가이드

> Stage 5 구현 기법 C — 무한 루프 기반 자율 구현.
> AI 에이전트를 무한 반복 실행하여 사람이 자리를 비워도 자율적으로 코드를 완성한다.
>
> 기존 병렬 실행 기법(서브에이전트, cmux)과 상호 보완적으로 사용.

---

## 개념

### Ralph Loop이란?

AI 코딩 에이전트(Claude Code)를 **무한 루프로 반복 실행**하여,
매 반복마다 작업 목록(`fix_plan.md`)에서 하나의 태스크를 수행하고 커밋하는 자율 구현 기법이다.

```bash
# 가장 단순한 형태
while :; do cat PROMPT.md | claude --print ; done
```

### 이름 유래

심슨 가족의 캐릭터 **"랄프 위검(Ralph Wiggum)"**에서 따왔다.
어리석지만 끈질기고 낙관적인 캐릭터처럼, AI가 에러를 만나도 포기하지 않고 반복 시도하는 모습을 표현.
창시자 제프리 헌틀리(Geoffrey Huntley)는 이를 **"순진한 지속성(Naive Persistence)"**이라 정의했다.

### 핵심 메커니즘 3가지

| 요소 | 역할 |
|------|------|
| **피드백 루프** | 실패 에러가 다음 반복에서 자동 수정됨 |
| **테스트 백프레셔** | 유닛 테스트가 "정답지" — 무분별한 코드 방지 |
| **컨텍스트 초기화** | 매 반복 백지 시작 → 컨텍스트 오염 없음. 진행상황은 git에 저장 |

### 기존 기법과 비교

| 기법 | 컨텍스트 | 인간 개입 | 적합 규모 | 자동화 |
|------|----------|----------|----------|--------|
| **A. 서브에이전트** | 공유 | 불가 | 소규모 (3파일 이하) | 반자동 |
| **B. cmux** | 독립 (수동 관리) | 수시 가능 | 중~대규모 | 수동 |
| **C. Ralph Loop** | 독립 (자동 갱신) | 불필요 | 반복적 대규모 | **완전 자동** |

**선택 기준:**
- 서브에이전트: 빠르게 3개 이하 파일 병렬 수정
- cmux: 2+ 독립 기능을 사람이 감독하며 개발
- Ralph Loop: 10개 이상 동질적 작업을 무인으로 자동 처리

---

## 핵심 파일 구조

프로젝트 루트에 아래 파일들을 준비한다:

```
프로젝트/
├── PROMPT.md          ← 루프 제어 명령 (매 반복 cat으로 주입)
├── fix_plan.md        ← 우선순위 작업 목록 (에이전트가 읽고 [x] 표시)
├── AGENT.md           ← 빌드/테스트 명령어 참조 (이미 있으면 재사용)
├── specs/             ← 기능 명세 (fix_plan.md에서 참조)
│   ├── SCR-001.md
│   └── API-012.md
├── scripts/ralph.sh   ← 런처 스크립트 (안전장치 포함)
└── .ai/rules/         ← 코딩 규칙 (기존 ai-rules)
```

| 파일 | 템플릿 | 설명 |
|------|--------|------|
| `PROMPT.md` | `.ai/templates/ralph-prompt.md` 복사 | 매 반복 주입되는 지시문 |
| `fix_plan.md` | `.ai/templates/ralph-fix-plan.md` 참고 | Stage 4에서 생성하는 작업 목록 |
| `AGENT.md` | 프로젝트에 맞게 직접 작성 | 빌드/테스트/린트 명령어 |
| `ralph.sh` | `scripts/ralph.sh` 복사 | 안전장치 포함 런처 |

---

## 전제 조건

### 1. TDD (필수)

테스트가 Ralph Loop의 **guardrail**이다. 테스트 없이 루프를 돌리면 AI가 올바른 방향으로 가는지 검증할 수 없다.

- **이상적:** 루프 시작 전 테스트가 모두 존재 (RED 상태 OK)
- **현실적:** `fix_plan.md` 상단에 테스트 작성 태스크를 먼저 배치

```markdown
# fix_plan.md 예시 — 테스트 먼저
- [ ] `tests/auth/login.test.ts` — 로그인 유닛 테스트 작성 (RED)
- [ ] `src/auth/login.ts` — 로그인 로직 구현 (GREEN)
- [ ] `tests/auth/signup.test.ts` — 회원가입 유닛 테스트 작성 (RED)
- [ ] `src/auth/signup.ts` — 회원가입 로직 구현 (GREEN)
```

### 2. Git 깨끗한 상태

루프 시작 전 uncommitted changes가 없어야 한다.
`ralph.sh`가 pre-flight에서 자동 검증한다.

### 3. 코딩 규칙 설정 완료

`.ai/rules/`가 프로젝트에 맞게 설정되어 있어야 한다.
PROMPT.md에서 `.ai/rules/` 참조를 지시하므로, 규칙이 없으면 코드 품질을 보장할 수 없다.

---

## 로컬 실행 (4단계)

### Step 1: PROMPT.md 작성

```bash
cp .ai/templates/ralph-prompt.md PROMPT.md
# 프로젝트에 맞게 수정 (테스트 명령어, 규칙 경로 등)
```

### Step 2: fix_plan.md 작성

Stage 4 Sprint 계획의 산출물이다. `.ai/templates/ralph-fix-plan.md`를 참고하여 작성.

**작성 원칙:**
- 1 태스크 = 1 atomic 단위 (한 반복에서 완료 가능한 크기)
- 의존성 순서대로 배치 (위에서 아래로)
- 파일 경로 + 테스트 파일 명시
- 구체적 지시 (에이전트가 해석 가능하게)

### Step 3: AGENT.md 작성

빌드, 테스트, 린트 명령어를 정리한다:

```markdown
# AGENT.md

## 빌드
npm run build

## 테스트
npm run test

## 린트
npm run lint

## 타입 체크
npx tsc --noEmit
```

### Step 4: ralph.sh 실행

```bash
# 기본 실행 (최대 50회 반복)
./scripts/ralph.sh

# 옵션 지정
./scripts/ralph.sh --max-iterations 30 --model sonnet

# 허용 도구 제한 (보안 강화)
./scripts/ralph.sh --allowed-tools "Edit,Write,Bash(read-only),Read,Glob,Grep"
```

실행 후 노트북을 열어두면 자율적으로 진행된다.
`RALPH_DONE` 파일이 생성되면 모든 작업이 완료된 것이다.

---

## 클라우드 실행

로컬이 기본이지만, 장시간 무인 실행이 필요하면 클라우드를 활용할 수 있다.

### 옵션 1: 원격 서버 (screen/tmux)

로컬과 동일하되 서버에서 실행한다. 가장 단순한 클라우드 방식.

```bash
# 서버 접속
ssh my-server

# screen 세션 생성
screen -S ralph

# ralph.sh 실행
cd /path/to/project
./scripts/ralph.sh --max-iterations 100

# screen 분리 (Ctrl+A, D) → 서버 접속 종료해도 계속 실행
```

### 옵션 2: GitHub Actions

CI/CD 파이프라인에서 Ralph Loop을 실행한다.

```yaml
# .github/workflows/ralph-loop.yml
name: Ralph Loop
on:
  workflow_dispatch:
    inputs:
      max_iterations:
        description: '최대 반복 횟수'
        default: '30'

jobs:
  ralph:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          prompt_file: PROMPT.md
          max_turns: ${{ github.event.inputs.max_iterations }}
          allowed_tools: "Edit,Write,Bash,Read,Glob,Grep"
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### 옵션 3: Claude Code /schedule

크론 기반 반복 실행. 주기적으로 fix_plan.md를 확인하고 미완료 작업을 처리.

```bash
# Claude Code 내에서
/schedule "매 30분마다 fix_plan.md 확인 후 미완료 작업 1개 처리"
```

---

## fix_plan.md 작성 가이드

### 포맷

```markdown
# fix_plan.md — Sprint N 작업 목록

## 우선순위 높음 (기반 코드)
- [ ] `src/lib/db.ts` — DB 연결 유틸 구현. 테스트: `tests/lib/db.test.ts`
- [ ] `src/lib/auth.ts` — JWT 토큰 검증. 테스트: `tests/lib/auth.test.ts`

## 우선순위 중간 (기능 코드)
- [ ] `src/api/users/route.ts` — 사용자 CRUD API. specs/API-001.md 참조. 테스트: `tests/api/users.test.ts`
- [ ] `src/components/UserList.tsx` — 사용자 목록 컴포넌트. specs/SCR-002.md 참조

## 우선순위 낮음 (정리)
- [ ] `src/types/index.ts` — 공통 타입 정의 정리
```

### 규칙

| 규칙 | 이유 |
|------|------|
| 1태스크 = 1 체크박스 | 에이전트가 1회에 1개만 처리 |
| 파일 경로 명시 | 에이전트가 즉시 작업 위치 파악 |
| 테스트 파일 명시 | TDD 강제 |
| 의존성 순서 배치 | 선행 작업 먼저 완료 |
| `[blocked]` 표시 허용 | 에이전트가 진행 불가 시 다음으로 건너뜀 |

### 에이전트의 태스크 처리 규칙

1. 위에서부터 첫 번째 `[ ]` 항목 선택
2. 구현 + 테스트 통과
3. `[x]`로 변경 + git commit
4. 모든 항목 `[x]` 또는 `[blocked]` → `RALPH_DONE` 생성

---

## 안전장치

### 런처 스크립트 내장 안전장치

| 안전장치 | 기본값 | 설명 |
|----------|--------|------|
| `--max-iterations` | 50 | 무한 루프 방지 — 최대 반복 횟수 |
| `RALPH_DONE` 감지 | 활성 | 모든 작업 완료 시 자동 종료 |
| 테스트 검증 | 활성 | 매 반복 후 테스트 실행 — 실패 시 중단 |
| `--allowed-tools` | 전체 | 허용 도구 제한으로 파괴적 작업 방지 |
| `sleep` | 2초 | API 레이트 리밋 방지 |

### 추가 권장 안전장치

- **git branch 분리:** `ralph/sprint-N` 브랜치에서 실행 → 결과 확인 후 merge
- **비용 모니터링:** Anthropic 대시보드에서 사용량 실시간 확인
- **diff 크기 제한:** 한 반복에서 너무 큰 변경이 생기면 경고

### 비상 정지

```bash
# 방법 1: 터미널에서 Ctrl+C
# 방법 2: RALPH_DONE 파일 직접 생성
touch RALPH_DONE

# 방법 3: fix_plan.md의 남은 작업을 모두 [blocked]로 변경
```

---

## 방법론 연동 (6 Stage)

Ralph Loop은 기존 방법론의 **Stage 4(구현)**에서 사용하는 기법 C이다.

```
Stage 3: Sprint 계획
  └→ fix_plan.md 생성 (Ralph Loop 입력)
       ↓
Stage 4: 구현 — 기법 C: Ralph Loop 실행
  └→ ralph.sh 실행 → 무인 자율 구현
       ↓
Stage 5: 검증 + 배포
  └→ 결과물 검증 (QA, 디자인 리뷰) → 배포
       ↓
Stage 6: 학습
  └→ lessons.md 업데이트 (루프에서 발견된 패턴)
```

### 언제 Ralph Loop을 선택하는가?

| 상황 | 추천 기법 |
|------|----------|
| 3개 이하 파일 빠른 수정 | A. 서브에이전트 |
| 2+ 독립 기능 + 사람 감독 | B. cmux |
| 10+ 동질적 작업 + 무인 실행 | **C. Ralph Loop** |
| 테스트 일괄 작성 | **C. Ralph Loop** |
| 대규모 리팩토링 (파일별 독립) | **C. Ralph Loop** |
| 복잡한 설계 판단 필요 | A 또는 B (사람 개입 필요) |

---

## 트러블슈팅

### 같은 작업을 반복한다

**원인:** fix_plan.md의 태스크 설명이 모호하여 에이전트가 완료 판단을 못함.
**해결:** 태스크에 구체적 완료 조건을 명시한다.

```markdown
# 나쁨
- [ ] 로그인 기능 구현

# 좋음
- [ ] `src/auth/login.ts` — email/password 로그인 함수 구현. bcrypt 비교. 성공 시 JWT 반환. 테스트: `tests/auth/login.test.ts` 3개 케이스 통과
```

### 테스트가 불안정하다 (flaky)

**원인:** 타이밍, 네트워크, 랜덤 데이터 의존 테스트.
**해결:** Ralph Loop 시작 전 flaky test를 제거하거나 안정화한다. 불안정한 테스트는 guardrail로서 가치가 없다.

### 커밋이 너무 잘게 쪼개진다

**원인:** fix_plan.md의 태스크 단위가 너무 작다.
**해결:** 관련 작업을 하나의 태스크로 묶는다.

```markdown
# 너무 잘게
- [ ] User 타입 정의
- [ ] User 스키마 작성
- [ ] User 테스트 작성

# 적절한 단위
- [ ] `src/models/user.ts` — User 모델 (타입 + Zod 스키마 + 테스트) 구현. 테스트: `tests/models/user.test.ts`
```

### API 비용이 너무 높다

**원인:** 반복 횟수가 많거나 Opus 모델 사용.
**해결:**
- `--model sonnet` 사용 (단순 반복 작업엔 Sonnet이면 충분)
- `--max-iterations` 줄이기
- fix_plan.md 태스크를 더 구체적으로 (에이전트가 헤매지 않게)

### 에이전트가 규칙을 안 따른다

**원인:** PROMPT.md에서 `.ai/rules/` 참조 지시가 누락.
**해결:** PROMPT.md에 규칙 읽기를 명시적으로 포함한다.

---

## 랄프톤 활용 팁

1박 2일 랄프톤에서 Ralph Loop을 최대한 활용하는 방법:

1. **오후 3시~저녁:** Stage 1~4 집중 (기획, 아키텍처, 디자인, Sprint 계획)
2. **저녁:** fix_plan.md + PROMPT.md + 테스트 작성 완료
3. **밤~다음날 아침:** Ralph Loop 실행 → 보드게임/수면
4. **오전:** Stage 6 검증 + 발표 준비

**핵심:** "인간이 설계하고, AI가 구현한다." 설계 품질이 결과물 품질을 결정한다.
