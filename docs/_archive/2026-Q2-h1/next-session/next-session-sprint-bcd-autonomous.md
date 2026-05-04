# 자율 orchestration — Sprint 7d + FE-03 + FE-04 (B → C → D 3 독립 PR 연쇄)

> 새 Claude Code 세션에서 아래 "--- PROMPT START ---" 블록을 붙여넣거나, 단 한 줄:
> `docs/next-session-sprint-bcd-autonomous.md 읽고 그대로 실행해줘`

> **세션 시작 시 반드시 `--permission-mode bypassPermissions` 또는 `/permissions` 에서 `approvalMode=auto` 확인** — 승인 프롬프트 없이 연쇄 실행에 필요.

---

## 내부 참고

Sprint FE-02(2026-04-19, PR #25) 이후 사용자가 "B+C+D 3개 스프린트를 새 세션에서 쭉 자동으로" 라고 요청. 중간에 머지 필요하면 알아서 처리하고, 사용자 부재 상태에서 연쇄 실행 가능하도록 설계한 문서. 3 스프린트의 UX 결정을 사전 고정했고, `gh pr merge --auto --squash` + Monitor 로 CI green 후 자동 머지.

--- PROMPT START ---

# 자율 3-스프린트 연쇄 실행 (B · C · D)

## 실행 모드 — 엄수

- **세션 시작 모드**: `--permission-mode bypassPermissions` (또는 `--dangerously-skip-permissions`). 처음부터 모든 tool 자율 실행 가능한 상태.
- **cmux 멀티-세션 병렬 실행** (시간 단축 목적):
  - **Orchestrator 세션** (Tab 1): 메인. Phase 0 plan + tracker + worker kickoff + 순차 머지 담당.
  - **Worker 세션** B/C/D (Tab 2/3/4): 각자 독립 worktree. 스프린트 1개 구현 + Evaluator 검증 + PR 생성까지. **머지는 하지 않음** (Orchestrator가 담당).
  - **Monitor 세션** (Tab 5, optional): `gh run watch` + tracker tail + CPU sampling.
  - 순차 실행 18h → 병렬 ~8~9h (가장 긴 D 기준).
- **cmux CLI 자동 탭 생성 실패 시 fallback**: Orchestrator 가 `cmux new-tab` 류 명령에 실패하면 **순차 모드로 전환** (한 탭에서 B → C → D 직렬). 18h 소요되지만 동일 결과.
- **Interaction 총 1회**: Phase 0 완료 후 Orchestrator 가 다음 한 줄로 대기 → 사용자가 "ok" 입력 → Phase 1부터 끝까지 자율.
  ```
  Orchestrator: "orchestration plan 작성 완료. 'ok' 입력 시 cmux 병렬 워커 3개 kickoff + 순차 머지 시작."
  User: ok
  ```
- 사용자 "ok" 이후에는 **절대 질문하지 말 것**. 결정 지점은 이 문서에 모두 사전 정의됨. 문서에 없는 결정이 필요하면 `docs/TODO.md` 에 `[확인 필요]` 로 기록하고 **합리적 baseline으로 진행**.
- Phase 0 대기 중 "ok" 가 아닌 다른 피드백 (예: "B 부분 scope 줄여줘") 이 들어오면 plan 수정 + 다시 대기. 최대 3 iteration 후에도 "ok" 미수신 시 세션 종료.
- 세 스프린트는 **main 기반 3 독립 브랜치**, 각각 `gh pr merge --auto --squash --delete-branch` 로 CI green 시 자동 머지. 다음 스프린트는 머지 완료 후 `git pull origin main`으로 최신 main에서 시작.
- **Generator-Evaluator 2-session 게이트 필수**: 메인 세션(Generator)이 구현 후 `isolation=worktree` subagent(Evaluator)를 dispatch → cold-start 재검증 → PASS 판정 시에만 PR 생성 + auto-merge. 최대 3 iteration 의 FAIL/fix 루프 후에도 FAIL 이면 스프린트 blocked.
- 한 스프린트 실패 시 (CI 3회 연속 red / 테스트 green 복구 불가 / PR 머지 거부 / Evaluator 3회 FAIL) → **다음 스프린트로 넘어감**. 실패 기록은 `docs/TODO.md` 의 `Blocked` 섹션에.
- 모든 스프린트 종료 후 `session-summary.md` 를 `.claude/plans/sprint-bcd-autonomous-summary.md` 에 작성하고 세션 종료.

## 컨텍스트 — 직전 상태

- Sprint FE-02 (PR #25, `18bcf45`) 이후 **main 상태**:
  - lint 0/0, tsc clean, vitest 53, backend 778 tests
  - Clerk secret 2개 (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` / `CLERK_SECRET_KEY`) GitHub repo secret 등록됨
  - ESLint `react-compiler` + `@tanstack/query/exhaustive-deps` error level
  - queryKey factory: `strategyKeys.list(userId, query)` / `tradingKeys.orders(userId, limit)` 패턴 — 새 hook 추가 시 동일 패턴 **엄수**
  - queryFn은 모듈-level `makeXxxFetcher` factory 호출식으로 감싸서 ESLint rule AST CallExpression skip 특성 활용 (**LESSON-005**)
  - debouncer 패턴: `useRef` + sync useEffect(deps 없음) (**LESSON-006**)
- 메모리 참조: `project_sprint_fe02_complete.md`, `feedback_effect_ref_loop.md`, `feedback_option_star_ratings.md`

## 전체 플로우 (Generator-Evaluator 2-session 패턴)

메인 세션이 **Generator**(구현 담당), 각 스프린트 종료 직전 `isolation=worktree` subagent 로
**Evaluator**(독립 검증 담당)를 dispatch 한다. Evaluator 는 **콜드 스타트 fresh context** 에서
Generator 의 결과물을 cold checkout → fresh install → lint/test/build/policy 재검증 + 플랜 대비
scope 달성 여부 판정. Evaluator PASS 일 때만 PR 생성 + auto-merge.

```
Orchestrator Tab 1 (bypassPermissions)
  → docs/next-session-sprint-bcd-autonomous.md 로드
  → 메모리 조회 (fe02_complete + feedback_*)
  │
  ├─ Phase 0: Orchestration plan + text-gate 승인
  │   ↓ /Users/woosung/.claude/plans/bcd-orchestration/tracker.md 작성
  │   ↓ signal directory 초기화 (.claude/plans/bcd-orchestration/signals/{b,c,d}.status)
  │   ↓ 3 worker worktree 미리 생성 (`.claude/worktrees/feat+sprint{7d,fe03,fe04}`)
  │   ↓ Orchestrator: "plan 작성 완료. 'ok' 입력 시 cmux 병렬 워커 kickoff."
  │   ↓ User: "ok"  ← 유일한 interaction
  │   ↓ 사용자 자리 비움
  │
  ├─ Phase 1: cmux worker 탭 3개 kickoff (병렬)
  │   ↓ Orchestrator tries:
  │     cmux new-tab sprint-b "cd <worktree> && claude --permission-mode bypassPermissions < worker-b.prompt"
  │     cmux new-tab sprint-c "..."
  │     cmux new-tab sprint-d "..."
  │   ↓ cmux CLI 실패 시 → 순차 fallback (아래 Sequential Mode)
  │
  │   ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
  │   │ Tab 2: Worker B    │ │ Tab 3: Worker C    │ │ Tab 4: Worker D    │
  │   │ Sprint 7d (BE)     │ │ FE-03 (edit lift)  │ │ FE-04 (backtest)   │
  │   │                    │ │                    │ │                    │
  │   │ writing-plans      │ │ writing-plans      │ │ writing-plans      │
  │   │ executing-plans    │ │ executing-plans    │ │ executing-plans    │
  │   │ self-verify        │ │ self-verify        │ │ self-verify        │
  │   │ Evaluator subagent │ │ Evaluator subagent │ │ Evaluator subagent │
  │   │ (FAIL ↔ fix, ≤3)   │ │ ...                │ │ ...                │
  │   │ PR 생성 (머지 X)    │ │ PR 생성 (머지 X)    │ │ PR 생성 (머지 X)    │
  │   │ signals/b.status=  │ │ signals/c.status=  │ │ signals/d.status=  │
  │   │   pr_ready + PR#   │ │   pr_ready + PR#   │ │   pr_ready + PR#   │
  │   └────────────────────┘ └────────────────────┘ └────────────────────┘
  │
  ├─ Phase 2: Orchestrator sequential merge (병렬 완료 기다리며 B→C→D 순서 고정)
  │   ↓ Monitor B signal: pr_ready → gh pr merge B --squash (CI green 대기)
  │   ↓ 머지 완료 후 tracker 업데이트 → main pull
  │   ↓ Monitor C signal: pr_ready → rebase C onto main if needed → merge C
  │   ↓ Monitor D signal: pr_ready → rebase D onto main if needed → merge D
  │   ↓ worker 탭은 PR 머지 후 자동 종료 (또는 orchestrator 가 kill)
  │
  └─ Phase 3: Session summary + 메모리 업데이트 + cleanup

------------------------------------------------------------------
Sequential fallback (cmux CLI 불가 시)
  Orchestrator Tab 1 에서 B → C → D 순차 실행 + 머지 (원래 설계)
  총 18h. Worker/Orchestrator 분리 없음.
------------------------------------------------------------------
```

## 공통 절차 (모든 스프린트 반복)

각 스프린트는 아래 템플릿을 정확히 따른다.

### 1) 브랜치 + 워크트리

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git worktree add .claude/worktrees/<branch-suffix> -b <branch-name>
cd .claude/worktrees/<branch-suffix>
pnpm install --frozen-lockfile  # 루트 husky
cd frontend && pnpm install --frozen-lockfile && cd -
# BE 스프린트면 backend/uv sync
```

### 2) 플랜 작성

`docs/superpowers/plans/2026-04-19-<sprint-slug>.md` (superpowers:writing-plans 스킬 사용)

### 3) 실행

`superpowers:executing-plans` 또는 직접 구현. TDD 패턴 권장 (`superpowers:test-driven-development`).

### 4) Generator self-verification — **verification-before-completion 엄수**

```bash
# FE 스프린트
cd frontend
pnpm lint                # 0 errors 0 warnings
pnpm tsc --noEmit        # clean
pnpm test -- --run       # green
pnpm build               # 로컬 (.env.local 의 Clerk dev key 재사용)
# Live smoke 자동화 (아래 §Live smoke 자동화 프록시 참조)

# BE 스프린트
cd backend
uv run ruff check .
uv run mypy src/
uv run pytest -v
```

### 4.5) Evaluator review (Generator-Evaluator 2-session 패턴) — **필수 게이트**

Generator 는 self-verification 후 바로 push 하지 **말 것**. 먼저 Evaluator subagent 를 dispatch 하여
콜드 스타트 재검증. PASS 판정이 나와야 PR 을 생성한다.

```bash
# 1) Generator: 현재까지의 변경을 branch에 commit + local only push (원격 push 안 함)
cd .claude/worktrees/<branch-suffix>
git add -A && git commit -m "..."  # 또는 이미 commit 된 상태

# 2) Evaluator dispatch (main 세션의 Agent tool + isolation=worktree)
#    — 프롬프트 템플릿은 §Evaluator subagent 프롬프트 참조
#    — Evaluator 는 fresh clone 받아 cold-start 재검증
#    — PASS/FAIL 판정 + 구체 근거 리포트 반환
```

Evaluator 가 **FAIL** 이면: 리포트의 `actionable_issues` 를 Generator 가 읽고 수정 → 4단계 self-verification
→ Evaluator 재dispatch. **최대 3 iteration**. 3회 실패 시 스프린트 blocked, 다음 스프린트로 넘어감.

Evaluator 가 **PASS** 인 경우에만 아래 5) 진행.

### 5) Commit → Push → PR

commit 메시지는 프로젝트 컨벤션 (`feat(...)`, `refactor(...)`, `docs(...)`) 준수. Co-authored-by 포함.

### 6) PR 자동 머지 세팅

```bash
gh pr create --title "<conv>: <sprint>" --body "$(cat <<'EOF'
## Summary
<요약>

## Test plan
- [x] lint / tsc / test / build 로컬 green
- [ ] CI green (frontend + backend + e2e + ci summary)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
PR_NUMBER=$(gh pr view --json number -q .number)
gh pr merge $PR_NUMBER --auto --squash --delete-branch
```

### 7) CI green 대기 + 머지 확인 (Monitor)

```bash
# Monitor 도구 사용 — 사용자 부재 시에도 alert
until out=$(gh pr view $PR_NUMBER --json state,mergedAt -q '.state' 2>/dev/null) \
  && [[ "$out" == "MERGED" || "$out" == "CLOSED" ]] \
  && echo "pr=$PR_NUMBER state=$out"; do sleep 30; done
```

- MERGED: 다음 스프린트 진행
- CLOSED (머지 안 된 close — CI red 등 자동 머지 불가 시 수동 close 필요한 케이스): 스프린트를 **실패 기록**하고 다음으로 넘어감

### 8) main 최신화 후 워크트리 정리

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git checkout main && git pull origin main
git worktree remove --force .claude/worktrees/<branch-suffix>
git branch -D <branch-name> 2>/dev/null || true
```

## Evaluator subagent 프롬프트 (Generator-Evaluator 패턴)

각 스프린트의 self-verification 후 Generator(메인 세션)가 아래 템플릿으로 **독립 Evaluator subagent** 를
dispatch 한다. **절대 주 세션에서 직접 검증을 반복하지 말 것** — Evaluator 의 가치는 "다른 context,
다른 working tree, fresh install" 에서 재현성을 증명하는 것이다.

### Dispatch 방법

메인 세션에서 `Agent` 도구 호출:

- `subagent_type`: `"superpowers:code-reviewer"` (최우선 선호 — 있는 경우) 또는 `"general-purpose"`
- `isolation`: `"worktree"` (필수 — 독립 worktree 로 cold-start 보장)
- `run_in_background`: `false` (결과를 기다려야 PASS/FAIL 판정 가능)

### Evaluator 프롬프트 템플릿 (그대로 복붙)

````
당신은 Sprint <X> 의 **Evaluator**(독립 검증자)입니다. 당신은 Generator(메인 세션)의 구현 결과물을
**콜드 스타트 fresh context** 에서 재현·검증합니다. Generator 의 주장을 신뢰하지 마세요 — 스스로 실행해
증거를 모으고 PASS/FAIL 을 판정합니다.

## 컨텍스트

- 프로젝트: /Users/woosung/project/agy-project/quant-bridge (Next.js 16 + FastAPI + Clerk)
- 스프린트: <B = Sprint 7d OKX + Trading Sessions / C = Sprint FE-03 Edit lift-up / D = Sprint FE-04 Backtest UI MVP>
- Generator 브랜치: `<branch-name>`
- 원본 플랜: `docs/superpowers/plans/<plan-file>.md`
- 스프린트 scope 정의: `docs/next-session-sprint-bcd-autonomous.md` 의 `# Sprint <X>` 섹션
- 준수 규칙: `.ai/project/lessons.md` LESSON-004/005/006/007, `.ai/rules/frontend.md` · `backend.md`

## 당신의 임무 (5단계)

### 1. 콜드 체크아웃
당신은 `isolation=worktree` 로 이미 독립 worktree 에서 시작되었습니다. 다음을 수행:
```bash
git fetch origin
git checkout <branch-name>
# 이미 checkout 된 상태면 skip
cd <repo-root>

# 루트 + frontend + backend 모두 fresh install
pnpm install --frozen-lockfile
cd frontend && pnpm install --frozen-lockfile && cd -
cd backend && uv sync --all-extras --dev && cd -
````

### 2. 재현성 검증 (가장 중요)

FE 스프린트 (C/D):

```bash
cd frontend
pnpm lint 2>&1 | tail -30     # 0 errors 0 warnings
pnpm tsc --noEmit 2>&1 | tail -20
pnpm test -- --run 2>&1 | tail -40
pnpm build 2>&1 | tail -30    # .env.local 세팅 필요 — 메인 repo 에서 cp
```

BE 스프린트 (B):

```bash
cd backend
uv run ruff check . 2>&1 | tail -20
uv run mypy src/ 2>&1 | tail -20
uv run pytest -v 2>&1 | tail -60
```

각 단계 결과를 리포트에 **그대로 인용** (요약 금지). 하나라도 실패하면 **즉시 FAIL**.

### 3. Scope 달성 심사

`docs/next-session-sprint-bcd-autonomous.md` 의 `# Sprint <X>` scope 항목을 **각각 체크리스트로 돌며**
실제 코드에서 확인:

- 파일 경로 존재 여부 (`Glob`)
- 주요 기능 점유부 (`Grep`)
- 테스트 존재 + 의미 있는 assertion (flaky or trivial 아닌가)
- 플랜 (`docs/superpowers/plans/<plan>.md`) 의 각 단계 달성도

항목별로 ✅ / ⚠️ / ❌ 판정 + 근거 파일:라인. ❌ 1건 이상 → **FAIL** (단, 명시된 "scope out" 항목은 ✅).

### 4. Policy / LESSON 위반 심사 (zero-tolerance 항목)

다음 중 하나라도 발견되면 **즉시 FAIL**:

- `eslint-disable.*react-hooks/` 주석 (LESSON-004)
- `any` 사용 (TypeScript strict — `Grep` 로 `:\s*any\b` 검색, 진짜 any 만 식별)
- queryKey factory 에 `getToken` 포함 (LESSON-005)
- useQuery/useInfiniteQuery 의 `queryFn` 이 ArrowFunction 이며 userId 가 queryKey factory 첫 인자가 아님 (LESSON-005)
- render body 에서 `ref.current = ` 대입 (LESSON-006)
- 금융 숫자 (가격/수량/수익률) 에 float 사용 (LESSON 공통) — `Grep` `: float\b` 검색
- Pine Script 에 `exec(`/`eval(` (LESSON 공통)
- Commit 메시지 conventional 위반 (feat/fix/refactor/docs/chore/test 외)
- 시크릿 커밋 (`gitleaks` 기본 패턴 — `pk_live`, `sk_live`, AWS key, `-----BEGIN`)
- 환경 변수 하드코딩 (`.env.example` 에 없는 변수 코드 내 직접 사용)

### 5. 최종 판정 리포트 (JSON 블록 포함)

마지막에 **정확히 아래 포맷**으로 결과를 출력하세요. Generator 가 기계적으로 파싱합니다.

```json-report
{
  "sprint": "<B|C|D>",
  "verdict": "PASS|FAIL",
  "reproducibility": {
    "lint": "<pass|fail — 1줄 근거>",
    "typecheck": "<pass|fail — 1줄 근거>",
    "test": "<pass|fail N/M — 1줄 근거>",
    "build": "<pass|fail|skipped — 1줄 근거>"
  },
  "scope_checklist": [
    {"item": "<scope 1>", "status": "✅|⚠️|❌", "evidence": "<file:line 또는 test name>"}
  ],
  "policy_violations": [
    {"rule": "LESSON-<NNN>|any|secret|...", "location": "<file:line>", "severity": "error|warn"}
  ],
  "actionable_issues": [
    "Generator 가 고쳐야 할 항목을 명령형 1문장으로. FAIL 이면 반드시 1건 이상. PASS 면 빈 배열."
  ],
  "notes": "<자유 서술, 200자 이내>"
}
```

JSON 블록 외에 **감상평이나 사족 없이** 최대 300 tokens 이내로 요약한 본문도 함께 제공.

## 엄수

- 당신의 판정은 Generator 가 기계적으로 읽음. verdict 는 반드시 "PASS" 또는 "FAIL" 대문자 그대로.
- Generator 를 칭찬하거나 격려할 필요 없음. 증거와 판정만.
- fresh install 시 네트워크 에러 / lockfile 충돌은 **3회 재시도** 후에도 지속되면 "reproducibility.\*:fail — install 단계" 로 보고 → FAIL.
- 당신은 코드를 수정하지 **않습니다**. 검증만.

```

### Evaluator 결과 파싱 + 다음 동작 (Generator 측)

Generator(메인 세션)는 Evaluator 리포트의 `json-report` 블록을 읽고:

- `verdict == "PASS"` → PR 생성 + `gh pr merge --auto --squash --delete-branch` 진행 (절차 5~8)
- `verdict == "FAIL"` 이면:
  - `actionable_issues` 각 항목을 순차 적용 (파일 수정 → self-verify 다시 → 새 commit)
  - Evaluator 재dispatch
  - **최대 3 iteration**. 3회째에도 FAIL 이면 스프린트 blocked, `docs/TODO.md` 에 기록, 다음 스프린트로 진행
- 리포트 파싱 실패 (JSON 블록 없음 / 포맷 깨짐) → Evaluator 1회 재dispatch 후에도 같으면 FAIL 처리

### Evaluator 재사용 시 context 관리

같은 Evaluator agent 를 iteration 2/3 에서 재사용하지 말고 **매 iteration 새 subagent dispatch**
(cold context 보장 — 이전 판정의 anchoring 배제). 새 worktree 가 매번 생성되므로 부담 없음.

---

## cmux 병렬 orchestration — 구체 구조

### Signal directory (Orchestrator ↔ Worker IPC)

`.claude/plans/bcd-orchestration/signals/` 파일 시스템 기반 state machine.

```

.claude/plans/bcd-orchestration/
tracker.md # 전체 상태 (인간 가독 + Orchestrator 정답지)
signals/
b.status # pending | running | evaluator_review | pr_ready | merged | blocked
b.pr # PR 번호 (pr_ready 진입 시 기록)
b.iteration # Evaluator iteration 카운트 (0~3)
c.status / c.pr / c.iteration
d.status / d.pr / d.iteration
prompts/
worker-b.prompt # Worker Tab 2 에 주입할 프롬프트 (Phase 0 에서 생성)
worker-c.prompt
worker-d.prompt
logs/
b.log / c.log / d.log

```

- Worker 는 **자기 sprint의 signal 파일에만 write**. 다른 sprint signal 읽기는 허용 (crossover 방지 위해).
- Orchestrator 는 **모든 signal 파일을 read/write**. `gh pr merge` 만 orchestrator 담당.
- 각 파일은 원자적 write (tmpfile + rename) 권장. bash: `echo "pr_ready" > b.status.tmp && mv b.status.tmp b.status`.

### Worker 프롬프트 템플릿 (Phase 0에서 생성)

각 worker tab 은 독립 Claude 세션이므로 self-contained prompt 필요. 아래는 `worker-b.prompt` 예시 (C/D는 sprint scope 만 치환):

```

당신은 Sprint 7d 의 Worker 입니다. 독립 cmux 탭의 Claude 세션.

## 컨텍스트

- worktree: /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/feat+sprint7d
- branch: feat/sprint7d-okx-trading-sessions
- signal dir: /Users/woosung/project/agy-project/quant-bridge/.claude/plans/bcd-orchestration/signals/
- sprint scope: `docs/next-session-sprint-bcd-autonomous.md` 의 "# Sprint 7d (B)" 섹션 그대로
- 엄수 규칙: 같은 문서 "공통 엄수 제약" 섹션
- Evaluator 프로토콜: 같은 문서 "Evaluator subagent 프롬프트" 섹션

## 당신의 임무

1. signals/b.status 를 "running" 으로 설정
2. worktree 로 이동 + install (pnpm / uv)
3. writing-plans → executing-plans → self-verification
4. signals/b.status = "evaluator_review"
5. Evaluator subagent dispatch (isolation=worktree). 최대 3 iteration 의 FAIL ↔ fix loop.
6. Evaluator PASS 시 PR 생성. signals/b.status = "pr_ready" + signals/b.pr = <PR번호>.
7. 종료. **머지하지 말 것** — Orchestrator 담당.
8. 모든 실패 케이스 (Evaluator 3회 FAIL / CI red / build 실패 / dispatch 실패) → signals/b.status = "blocked" 후 종료.

## 로그

모든 stdout/stderr을 logs/b.log 에 tee. Orchestrator 가 tail 로 관찰.

## 세션 종료

임무 완료 (pr_ready / blocked) 시 한 줄 요약 출력 후 세션 종료 (`exit` 또는 Ctrl+D).

````

### Orchestrator 폴링 루프 (Phase 2)

Orchestrator 는 "ok" 후 worker 3개 kickoff, 그 다음 Monitor 도구로 signal 폴링:

```bash
# 순차 머지 루프 — B 완료될 때까지 C/D 머지 대기 (하지만 C/D의 코드 작성은 병렬 진행됨)
for sprint in b c d; do
  # 이 sprint 의 pr_ready 또는 blocked 까지 대기
  until status=$(cat .claude/plans/bcd-orchestration/signals/$sprint.status 2>/dev/null) \
    && [[ "$status" == "pr_ready" || "$status" == "blocked" ]]; do sleep 30; done

  if [[ "$status" == "blocked" ]]; then
    echo "[$sprint] blocked — skip merge"
    continue
  fi

  pr=$(cat .claude/plans/bcd-orchestration/signals/$sprint.pr)
  # 머지 전 main 최신화 (이전 sprint 머지 반영)
  git -C <main-repo> pull origin main

  # PR 이 main 보다 뒤처져 있으면 rebase 지시
  gh pr view $pr --json mergeStateStatus -q .mergeStateStatus
  # BEHIND 면 rebase, CONFLICTING 이면 blocked

  gh pr merge $pr --squash --delete-branch --auto
  # CI green 대기
  until merged=$(gh pr view $pr --json state -q .state) && [[ "$merged" == "MERGED" || "$merged" == "CLOSED" ]]; do sleep 30; done

  echo "$merged" > .claude/plans/bcd-orchestration/signals/$sprint.status
done
````

### cmux kickoff (Phase 1) — 실패 시 fallback

```bash
# 시도 순서: cmux → tmux → sequential
if command -v cmux >/dev/null 2>&1; then
  cmux new-tab "sprint-b" "cd $WORK_B && claude --permission-mode bypassPermissions --print-session-id" < prompts/worker-b.prompt
  cmux new-tab "sprint-c" "..."
  cmux new-tab "sprint-d" "..."
  PARALLEL_MODE=cmux
elif command -v tmux >/dev/null 2>&1; then
  tmux new-window -n sprint-b "..."
  # ... 유사
  PARALLEL_MODE=tmux
else
  echo "⚠️ No multiplexer found — switching to sequential mode"
  PARALLEL_MODE=sequential
  # Phase 1/2 가 아닌 기존 "순차 실행" 루프로 전환
fi
```

실제 cmux CLI 명령이 위와 다를 수 있음 → Orchestrator 가 첫 worker 탭 시도 후 **5분 내 `b.status == running`** 로 업데이트되는지 확인. 안 되면 sequential fallback.

### Worker 탭 정리

각 worker 는 임무 완료 시 스스로 exit. Orchestrator 는 Phase 3 cleanup 에서 잔여 cmux 탭을 `cmux kill-session` (또는 `tmux kill-window`) 으로 정리.

---

## Progress Tracker (`.claude/plans/bcd-orchestration/tracker.md`)

Phase 0 에서 생성되며, 각 스프린트 완료/실패 시 Orchestrator 가 직접 업데이트. 세션이 context limit
으로 중간에 죽어도 이 파일을 읽으면 "어디까지 진행했는지" 복원 가능 — 재개 시 signal 파일 + tracker
병합으로 이어서 실행.

### 초기 스키마 (Phase 0 에서 작성)

```markdown
# BCD Orchestration Tracker

**Session started:** <ISO timestamp>
**Base main:** <sha — Phase 0 시작 시 main HEAD>
**Active sprint:** none

## Sprints

### B. Sprint 7d (OKX + Trading Sessions)

- **Status:** pending | in_progress | evaluator_review | pr_open | merged | blocked
- **Branch:** feat/sprint7d-okx-trading-sessions
- **Worktree:** .claude/worktrees/feat+sprint7d
- **PR:** (none)
- **Evaluator iterations:** 0/3
- **Merged commit:** (none)
- **Notes:** (이상 / 실패 원인)

### C. Sprint FE-03 (Edit page state lift-up)

(동일 구조)

### D. Sprint FE-04 (Backtest UI MVP)

(동일 구조)

## Global timeline

- Phase 0 complete at <ts>
- Sprint B start at <ts> / end at <ts> / verdict <merged|blocked>
- Sprint C start at <ts> / end at <ts> / verdict ...
- Sprint D start at <ts> / end at <ts> / verdict ...
- Session summary at <ts>

## Resume protocol

세션이 중간에 죽으면 재개 시:

1. 이 파일 먼저 읽음
2. `Active sprint` 의 `Status` 에 따라 다음 단계 결정:
   - `in_progress` → 해당 스프린트 worktree 에 들어가서 self-verification 부터 재시작
   - `evaluator_review` → Evaluator subagent 재dispatch (새 iteration)
   - `pr_open` → `gh pr view` + Monitor 로 CI 상태 재확인 → merged 되면 다음 스프린트로
   - `blocked` → 다음 스프린트로 skip
3. 현재 main 이 tracker 의 `Base main` 보다 앞서 있으면 `git pull` 후 재개
```

### 업데이트 타이밍 (메인 세션 엄수)

- Phase 0 끝 → Initial tracker 작성
- 각 스프린트 시작 시 `Active sprint` + `Status: in_progress` + `start at` 기록
- Generator self-verification 통과 → `Status: evaluator_review`
- Evaluator PASS → PR 생성 직전 `Status: pr_open` + `PR:` 링크
- CI green + auto-merge 완료 → `Status: merged` + `Merged commit:`
- 실패 판정 시 `Status: blocked` + `Notes:` 사유
- 모든 스프린트 종료 → `Active sprint: none` + Session summary 생성

### 무결성 규칙

- Tracker 는 커밋하지 않는다 (local-only, `.claude/plans/` 는 gitignored)
- 각 업데이트는 **edit 바로 직후 파일 저장 + flush 보장** — Edit 도구가 atomic 이므로 OK
- tracker 읽기/쓰기 실패는 치명적이지 않다 — 기록이 깨지면 git log 로 재구성

---

## Live smoke 자동화 프록시

사용자 부재 상태라 Activity Monitor 사용 불가. 대신:

```bash
cd frontend && pnpm dev &
DEV_PID=$!
sleep 20  # 초기 Ready 대기

# Playwright MCP로 주요 페이지 navigate + CPU 샘플링
# 60초간 10초 간격으로 next-server CPU 측정
for i in 1 2 3 4 5 6; do
  CPU=$(ps -p $(lsof -i :3000 -sTCP:LISTEN -t) -o %cpu= 2>/dev/null | tr -d ' ')
  echo "[$i] next-server CPU=${CPU}%"
  sleep 10
done

# 기준: 어떤 샘플이든 CPU > 80% 면 render storm 의심 → 즉시 스프린트 실패 처리
# dev server 반드시 종료
kill $DEV_PID 2>/dev/null
pkill -f "next-server" 2>/dev/null
```

추가: Playwright MCP `browser_navigate` + `browser_console_messages level=error` 로 console 에러 0건 + `browser_evaluate` 로 `performance.getEntriesByType('resource').length < 50` 검증.

## Cleanup (매 스프린트 후 필수)

```bash
# orphan dev server 방지 (LESSON-007)
lsof -i :3000 -sTCP:LISTEN -t 2>/dev/null | xargs -r kill -9
pkill -f "next-server" 2>/dev/null
pgrep -f "mcp-chrome" | xargs -r kill 2>/dev/null
```

## 공통 엄수 제약 (모든 스프린트)

- **ESLint `react-hooks/*` disable 절대 금지** (LESSON-004)
- **queryKey factory: `strategyKeys.list(userId, ...)` 패턴, queryFn은 `makeXxxFetcher(...)` CallExpression** (LESSON-005)
- **`ref.current = v` render 중 대입 금지 → sync useEffect(deps 없음)** (LESSON-006)
- **금융 숫자는 `Decimal`, float 금지, `Decimal(str(a)) + Decimal(str(b))` 패턴**
- **Celery prefork-safe — 모듈 import 시점 무거운 객체 생성 금지**
- **Pine Script는 `exec()`/`eval()` 금지 — 인터프리터 패턴**
- **미지원 Pine 함수 1개라도 있으면 전체 Unsupported 반환**
- TypeScript strict, `any` 금지
- 선택지 2개↑ 제시 금지 (자율 실행 — 이 문서의 baseline 그대로 진행)

---

# Sprint 7d (B) — OKX + Trading Sessions

## Scope (사전 fix)

1. **OKX 어댑터 추가** — CCXT 기반, Bybit 어댑터(`backend/src/adapters/exchanges/bybit.py`) 패턴 그대로 복제
   - 파일: `backend/src/adapters/exchanges/okx.py` (신규)
   - 파일: `backend/src/adapters/exchanges/factory.py` 수정 (OKX 등록)
   - Sandbox / demo mode만 (live 금지)
   - Futures 제외 (spot only) — futures는 후속 스프린트
   - 인증: API Key + Secret + Passphrase (OKX 특이사항 — AES-256 암호화 대상에 passphrase 포함)
2. **Trading Sessions 필터** — 전략 실행 시 특정 시장 세션에만 진입하도록 시간대 마스크
   - 표준 세션 3개 (UTC 기준, DB에 seed):
     - `asia`: 00:00–07:00 (Asia/Tokyo 09:00-16:00)
     - `london`: 08:00–16:00 (Europe/London 08:00-16:00)
     - `ny`: 13:30–20:00 (America/New_York 09:30-16:00)
   - `Strategy` 모델에 `trading_sessions: list[str]` 컬럼 추가 (nullable, 비어있으면 24h)
   - Backtest 엔진/Executor에서 bar timestamp 의 UTC hour 로 필터링
3. **DB migration** — alembic으로 `exchange_accounts.passphrase_encrypted` + `strategies.trading_sessions` 컬럼 추가
4. **Test**:
   - OKX 어댑터 unit test (CCXT sandbox mocking)
   - Trading sessions 필터 unit test (9시/14시/22시 UTC 시점별 entry 허용/차단)
   - Integration: strategy 생성 시 trading_sessions 저장 확인

## 브랜치

`feat/sprint7d-okx-trading-sessions` · worktree `.claude/worktrees/feat+sprint7d`

## 제약

- **OKX 실제 API 키 요구하지 않음** (CCXT sandbox). live trading 테스트는 후속 스프린트.
- `exchange_accounts` 테이블의 passphrase는 기존 `api_key_encrypted`/`api_secret_encrypted` 와 같은 AES-256 암호화 레이어 재사용
- 기존 Bybit pytest가 **green 유지** 필수 (회귀 없음)

## PR 형식

- title: `feat(sprint7d): OKX 어댑터 + Trading Sessions 필터`
- 예상 commit 4~6개 (migration / adapter / sessions filter / tests / 최종 통합)

---

# Sprint FE-03 (C) — Edit page 편집 버퍼 state lift-up

## Scope (사전 fix)

### 문제 정의 (직전 상태)

- `/strategies/[id]/edit` 페이지의 TabCode (Monaco editor) 와 TabParse (대화형 Dialog) 가 **각자 독립된 local state 로 pineSource 를 들고 있음**
- TabCode 에서 편집해도 TabParse 는 mount 시점의 서버 값으로 파싱 → 사용자 편집 미반영
- "저장" 버튼이 없음 — 편집이 persist 되지 않음

### 해결 (사전 fix)

1. **Zustand 도메인 store 도입** — `frontend/src/features/strategy/edit-store.ts`
   - 프로젝트 convention (Sprint 7c 이후 Zustand 도메인 store 패턴) 따름
   - 상태: `pineSource: string`, `isDirty: boolean`, `lastSavedAt: Date | null`, `serverSnapshot: string` (서버에서 가져온 원본)
   - 액션: `setPineSource(s)`, `resetDirty()`, `markSaved(savedAt, server)`, `loadServerSnapshot(s)`
   - `isDirty` 는 computed: `pineSource !== serverSnapshot`
2. **TabCode** — Monaco onChange → store.setPineSource 로 lift-up
3. **TabParse** — store.pineSource 를 구독, 500ms debounce 후 `usePreviewParse(pineSource)` 재호출 (기존 useQuery 패턴 유지)
4. **Save 버튼** — 페이지 header 우측 sticky, `isDirty` 시 enabled, 클릭 시 `useUpdateStrategy` mutation 호출 → onSuccess 시 `markSaved` + toast
5. **Unload 경고** — `isDirty` true 상태에서 탭 닫기/라우트 이동 시 `beforeunload` 이벤트로 "저장 안 된 변경사항" 경고

### 엄수

- Zustand selector 는 **scalar selector 사용** (`useEditStore(s => s.pineSource)` — 객체 selector 금지)
- TabParse 의 재파싱은 usePreviewParse queryKey 가 이미 `pineSource` 포함 → Zustand pineSource 가 변하면 React Query 자동 재파싱
- **useEffect dep 에 Zustand 전체 store 넣지 말 것** (LESSON-004)
- TabCode 에 Monaco onChange → setPineSource 직접 연결 (debounce는 `usePreviewParse` 쪽에서 처리, 상태는 즉시 업데이트)

## 브랜치

`feat/sprint-fe03-edit-lift-up` · worktree `.claude/worktrees/feat+sprint-fe03`

## Test

- Zustand store unit test (setPineSource / dirty / markSaved)
- TabCode → store 연결 (vitest + @testing-library)
- TabParse → store 구독 확인
- Save 버튼 disable/enable 상태 머신 테스트
- Integration: edit 페이지 mount → loadServerSnapshot → 편집 → dirty → save → dirty false

## 예상 commit 5~7개

---

# Sprint FE-04 (D) — Backtest UI MVP (baseline fix)

## Scope (사전 fix)

> BE API는 이미 ready (Sprint 4 완료). MVP 최소 기능만 엄격히 제한. office-hours 생략.

### UI 범위 (fix된 baseline)

1. **Trigger form** — `/backtests/new`
   - Strategy 선택 (드롭다운, `useStrategies` 재사용)
   - Symbol (예: BTC/USDT)
   - Timeframe (1m / 5m / 15m / 1h / 4h / 1d)
   - Start date / End date (2개 date picker)
   - Initial capital (USDT, default 10000)
   - Submit → `POST /api/v1/backtests` → status polling 화면으로 navigate
2. **Status polling 화면** — `/backtests/[id]`
   - 실행 중일 때: 진행률 스피너 + "Pending → Running → Completed" 상태 표시
   - `useBacktestStatus(id)` — 30초 간격 (LESSON-004 교훈 대로 ≥30s, error 시 refetchInterval false)
   - Completed 시 결과 화면으로 자동 전환
3. **결과 화면** — 같은 `/backtests/[id]` (Completed 시 표시)
   - **Metrics 카드 4개**: Sharpe ratio · Max drawdown · Win rate · Total trades
   - **Equity curve** — recharts `LineChart`, X축 timestamp / Y축 equity value. x axis date 포맷 YYYY-MM-DD
   - **Trade table** — shadcn DataTable 최소 (컬럼: open_time · close_time · symbol · side · pnl · pnl_pct)
   - **Error 시**: error message + retry 버튼
4. **목록 화면** — `/backtests`
   - 기존 실행된 backtest 리스트 (최근순 20개)
   - 컬럼: strategy_name · symbol · timeframe · status · sharpe · created_at
   - 행 클릭 → `/backtests/[id]` 로 이동

### 기술 결정 (baseline)

- **차트 라이브러리**: `recharts` (Tailwind v4 / shadcn 공식 호환 경로). 설치: `pnpm add recharts`. 대안 라이브러리 검토 없이 이걸로 진행.
- **실시간 진행률**: WebSocket 미도입. 30초 React Query polling 으로 충분 (MVP)
- **차트 데이터 volume**: 백테스트 결과 OHLCV 가 많을 수 있으므로 equity curve 는 **다운샘플링** (1000 포인트 상한)
- **트레이드 테이블**: 페이지네이션 없음 (MVP, 상한 200 row). 이후 스프린트에서 infinite scroll 고려
- **API types**: 기존 `backend/src/api/backtest.py` 응답 스키마를 `frontend/src/features/backtest/schemas.ts` 로 Zod 변환 (BE에서 이미 반환하는 JSON 그대로)

### 파일 구조

```
frontend/src/features/backtest/
  api.ts                 # apiFetch 래퍼
  hooks.ts               # useBacktests / useBacktest / useCreateBacktest (userId factory 패턴)
  query-keys.ts          # backtestKeys.list(userId) / backtestKeys.detail(userId, id)
  schemas.ts             # Zod
  types.ts
  __tests__/*.test.ts

frontend/src/app/(dashboard)/backtests/
  page.tsx               # 목록
  new/page.tsx           # form
  [id]/page.tsx          # status polling + 결과
  _components/
    backtest-form.tsx
    equity-chart.tsx
    trade-table.tsx
    metrics-cards.tsx
    status-badge.tsx
```

### 엄수 (LESSON-004/005/006)

- `backtestKeys.list(userId)` — factory 시그니처에 userId 첫 인자
- `queryFn: makeListFetcher(userId, getToken)` — 모듈-level factory
- `useRef` + sync useEffect 패턴 (필요 시)
- Polling useQuery `refetchInterval: (q) => q.state.status === 'error' ? false : 30_000`

## 브랜치

`feat/sprint-fe04-backtest-ui-mvp` · worktree `.claude/worktrees/feat+sprint-fe04`

## Test

- hooks unit test (factory 시그니처 / userId identity)
- backtest-form validation (symbol/dates/capital)
- status polling 상태 머신 (pending → running → completed / error)
- equity chart 다운샘플링 함수
- trade table 렌더링 smoke
- Integration: create → polling → completed transition

## 예상 commit 8~12개 (scope 큼)

---

## 실패 대응 매트릭스

| 조건                                                         | 동작                                                                                                                                   |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `pnpm lint` 실패                                             | 최대 3회 자동 fix 시도 후 실패 시 PR 생성하지 않고 다음 스프린트로                                                                     |
| `pnpm tsc --noEmit` 실패                                     | 최대 3회 자동 fix 시도 후 실패 시 다음 스프린트                                                                                        |
| `pnpm test` 실패                                             | 실패 테스트 개별 조사 후 최대 3회 fix. 지속 실패 시 다음 스프린트                                                                      |
| `pnpm build` 실패                                            | 원인 확인 (env / type / import cycle). 3회 시도 후 다음 스프린트                                                                       |
| `uv run pytest` 실패                                         | 동일 패턴                                                                                                                              |
| Live smoke CPU > 80%                                         | 즉시 스프린트 실패 처리 (LESSON-004 재발 방지), 다음 스프린트로                                                                        |
| PR 생성 실패                                                 | `git push` 다시 시도 1회, 그래도 실패 시 다음 스프린트                                                                                 |
| CI red 반복                                                  | `gh run rerun --failed` 1회, 그래도 red 면 PR `--auto` 취소 → close → 다음 스프린트                                                    |
| `--auto --squash --delete-branch` 머지 거부 (permission)     | 실패 기록 후 다음 스프린트                                                                                                             |
| **Evaluator FAIL 3회 연속** (Generator-Evaluator loop)       | 스프린트 blocked, PR 생성 안 함, 다음 스프린트로                                                                                       |
| **Evaluator 리포트 파싱 실패 2회** (JSON 블록 깨짐)          | 스프린트 blocked, 다음으로                                                                                                             |
| **Evaluator subagent dispatch 실패** (worktree 생성 불가 등) | general-purpose 로 fallback 1회, 그래도 실패 시 Generator self-verification 만으로 진행하되 PR body 에 "Evaluator bypass: <사유>" 명시 |

실패 기록 위치: `docs/TODO.md` 의 `Blocked` 섹션

## 최종 단계 — Session summary

세 스프린트 종료 후:

1. **최종 main 상태 확인**
   ```bash
   git checkout main && git pull origin main
   git log --oneline -10
   ```
2. **세 스프린트 중 머지된 것 목록 집계**
3. **`/Users/woosung/.claude/plans/sprint-bcd-autonomous-summary.md`** 작성:
   - 각 스프린트 결과 (머지 / blocked)
   - 머지된 PR URL
   - 실패 사례와 조치
   - 발견한 새 LESSON 후보 (있다면)
4. **메모리 업데이트**:
   - `project_sprint_7d_complete.md` · `project_sprint_fe03_complete.md` · `project_sprint_fe04_complete.md` (머지된 스프린트만)
   - `MEMORY.md` 인덱스에 라인 추가
5. **Cleanup**:
   - 모든 worktree 제거
   - orphan dev server / mcp-chrome 정리 (LESSON-007)
6. **세션 종료 메시지**: "B/C/D 자율 실행 완료. 최종 main 상태 `<hash>`. 머지 <n>/3 건. 상세 요약 `.claude/plans/sprint-bcd-autonomous-summary.md`."

## 예상 타임라인

- 순차 실행 시: B ~6h · C ~4h · D ~8h = **~18시간** (CI 대기 포함)
- 사용자 부재 상태에서 수면 중 진행 → 깨어났을 때 최대 3 PR 머지 완료
- CI 실패 / 머지 거부 시 해당 스프린트만 blocked, 나머지 진행

## 한 줄 실행 (cmux Orchestrator + 병렬 Worker 3개)

### 1. Orchestrator 탭 시작

```bash
cd /Users/woosung/project/agy-project/quant-bridge
claude --permission-mode bypassPermissions
# 또는 cmux에서: cmux new-tab "orchestrator" "claude --dangerously-skip-permissions"
```

### 2. 첫 프롬프트 (Orchestrator 탭)

```
docs/next-session-sprint-bcd-autonomous.md 읽고 그대로 실행해줘.
cmux 병렬 모드로 B/C/D 워커 kickoff + Orchestrator 가 순차 머지 담당.
```

### 3. Orchestrator 동작

1. 문서 + 메모리 로드
2. `/Users/woosung/.claude/plans/bcd-orchestration/` 디렉토리 + tracker.md + signals/ + prompts/ + logs/ 생성
3. 3 worker worktree 미리 생성
4. `"plan 작성 완료. cmux 병렬 모드 준비됨. 'ok' 입력 시 worker 3개 kickoff + 순차 머지 시작."` 한 줄 → 사용자 응답 대기

### 4. 사용자 응답

```
ok
```

### 5. 이후 자동 흐름

- Orchestrator 가 `cmux new-tab sprint-{b,c,d}` 로 worker 탭 3개 동시 kickoff (실패 시 sequential fallback)
- Worker 는 각자 구현 + Evaluator 검증 + PR 생성 (머지 X)
- Orchestrator 가 signal 폴링 + B → C → D 순서로 `gh pr merge --squash --delete-branch` 순차 머지
- 모든 sprint 종료 시 summary + 메모리 + cleanup + Orchestrator 세션 종료 ("B/C/D 실행 완료" 한 줄 출력)

**Interaction 총 1회** (`"ok"` 텍스트). 이후 자리 비우기 → 깨어나면 tracker.md + summary.md 로 결과 확인.

### 선택: Monitor 탭 (Tab 5)

```bash
cmux new-tab "monitor" "watch -n 10 'cat .claude/plans/bcd-orchestration/signals/*.status && echo --- && gh pr list --state open'"
```

CI / PR / signal 상태를 실시간 관찰. 사용자가 깨어났을 때 즉시 상황 파악.

--- PROMPT END ---

## 사용 방법

1. **세션 종료 후 휴식**. 사용자가 자리 비운 사이 실행되도록 설계됨.
2. 새 Claude Code 세션을 `--permission-mode bypassPermissions` 또는 `/auto` 로 시작.
3. 위 한 줄 프롬프트 입력.
4. 세션 깨어나면 `.claude/plans/sprint-bcd-autonomous-summary.md` 로 결과 확인.

## 주의 — 사용자 부재 시 유의점

- **LESSON-004 live smoke 는 완전 자동 대체 불가**. Playwright MCP CPU 샘플링 + console error 체크가 최선. 수동 Activity Monitor 5분 관찰의 발견력은 낮아짐.
- **Clerk 로그인이 필요한 E2E 는 CI `e2e` job에서 sign-in redirect 만 smoke**. 실제 로그인 상태 테스트는 세션 내에서 불가.
- **Backtest 실행은 Celery worker 필요** — CI 에서는 skip, 로컬에서도 `docker compose up` 필요 가능. D의 unit / integration test 는 Celery mock 사용.
- `gh pr merge --auto` 는 **repo 에 "Allow auto-merge" 설정이 켜져 있어야** 작동. 설정 안 되어 있으면 첫 스프린트 시점에 실패 기록 후 수동 PR 유지.
- 세션이 중간에 죽을 수 있음 (context limit 등). 그런 경우 다시 한 줄 프롬프트로 재개 — 문서가 멱등적 (git status 로 진행 상황 복원 가능).

## 참조

- Sprint FE-02 완료: `project_sprint_fe02_complete.md`
- LESSON-004/005/006: `.ai/project/lessons.md`
- 메모리 인덱스: `MEMORY.md`
- 기존 prompt 예시: `docs/next-session-after-fe-01-prompt.md` (FE-01→FE-02 전환)
