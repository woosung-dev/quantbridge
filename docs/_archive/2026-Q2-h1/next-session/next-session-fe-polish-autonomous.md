# 자율 병렬 orchestration — FE Polish 3 독립 PR (Bundle 1, Option C Staging Branch)

> **트리거 프롬프트 (새 세션 첫 메시지):**
>
> ```
> /autonomous-parallel-sprints
> docs/next-session-fe-polish-autonomous.md 읽고 그대로 실행해줘. Bundle 1 (FE Polish 3 병렬). Option C (Staging Branch — stage/fe-polish 생성 후 3 워커 PR base=A, Orchestrator 로컬 squash merge → push, 사용자가 A→main 수동). 사용자 interaction 은 'ok' 한 번만.
> ```

> **세션 시작 모드**: `--permission-mode bypassPermissions` (또는 `/permissions` → `approvalMode=auto`)

---

## 내부 참고

Sprint FE-04 + 7d 머지 (2026-04-19 `06f10f0`) 이후 자율 병렬 스킬 첫 본격 검증. H1 Stealth 마감 전 FE 사용성 폴리시 3건 병렬 실행. **Option C (Staging Branch) 도입** — main 을 Claude 가 직접 touch 안 하고 `stage/fe-polish` 에 3 머지 누적 후 사용자가 A→main 만 수동. `gh pr merge` deny 조작 없음.

--- PROMPT START ---

# 자율 3-스프린트 연쇄 실행 (FE-A · FE-B · FE-C, Option C)

## 실행 모드 — 엄수

- **세션 시작 모드**: `claude --allow-dangerously-skip-permissions --dangerously-skip-permissions` (2.1.114+ 확인됨)
- **cmux 병렬 모드**:
  - Orchestrator (Tab 1): Phase 0 scaffolding + staging branch 생성 + worker kickoff + 로컬 머지
  - Worker FE-A/B/C (Tab 2/3/4): 각자 독립 worktree (**base = stage/fe-polish**). 구현 + Evaluator + PR 생성까지 (**머지 금지**)
- **사용자 interaction 1회**: Phase 0 완료 후 `"ok"` → Phase 1~3 자율.
- **Staging Branch 머지 전략 (Option C)**:
  - Phase 0 에서 `git checkout -b stage/fe-polish main && git push -u origin stage/fe-polish`
  - 3 worker worktree 는 `stage/fe-polish` 기준 분기 (main 기준 아님)
  - Worker PR 은 `--base stage/fe-polish` 로 생성 (main 아님)
  - Orchestrator Phase 2: **로컬 `git merge --squash` + `git push origin stage/fe-polish`** (`gh pr merge` 미사용 → settings.json deny 조작 없음!)
  - Phase 3 최종 보고에 **사용자가 수행할 A→main 머지 명령 3개** 명시 (수동, 사용자 터미널)

## 컨텍스트 — 직전 상태 (main `06f10f0`)

- Sprint FE-04 + FE-03 + 7d 머지 완료 (2026-04-19 새벽)
- lint 0/0, tsc clean, vitest 59+ FE tests, backend 823 tests
- ESLint `react-compiler` + `@tanstack/query/exhaustive-deps` error level
- queryKey factory: `strategyKeys.list(userId, query)` + `makeXxxFetcher` CallExpression 패턴 (LESSON-005)
- 메모리 참조: `project_sprint_{fe01..fe04,7d,bcd_parallel_execution}_complete.md`, `feedback_*.md`, `feedback_merge_strategy_b_default.md` (→ 본 문서는 C 로 승격)

## 사전 Probe 5단계 (Iron Law)

Orchestrator 는 Phase 0 시작 **전** 자동 수행:

```bash
bash ~/.claude/skills/autonomous-parallel-sprints/scripts/preflight-probe.sh \
  /Users/woosung/project/agy-project/quant-bridge
```

기대 결과: **[1~4] 전부 통과**. `gh pr merge*` DENY 감지는 **무시해도 됨** — Option C 는 `gh pr merge` 미사용.

**추가 사전 작업 (Blocker #5 예방 — Worker 신호 전환 재프롬프트 방지)**: `.claude/settings.local.json` 의 `allow` 배열에 아래 광역 패턴이 없으면 Edit 으로 추가:

```json
"Bash(echo * > *.status)",
"Bash(echo * > *.iteration)",
"Bash(echo * > *.pr)",
"Bash(echo * > /Users/woosung/project/agy-project/quant-bridge/.claude/plans/*)",
"Bash(tee -a /Users/woosung/project/agy-project/quant-bridge/.claude/plans/*)",
"Bash(git merge --squash *)",
"Bash(git push origin stage/*)"
```

JSON 유효성: `python3 -m json.tool .claude/settings.local.json`.

## 공통 엄수 제약 (전 스프린트)

- **LESSON-004**: `react-hooks/*` eslint-disable 금지
- **LESSON-005**: queryKey factory `xxxKeys.list(userId, ...)` + `makeXxxFetcher` CallExpression
- **LESSON-006**: render body `ref.current = v` 금지 → sync useEffect(deps 없음)
- **LESSON-007**: dev server/mcp-chrome orphan 정리
- TypeScript strict, `any` 금지
- `.ai/stacks/nextjs-shared.md §4` 반응형 규칙 (모바일 <768px overflow-x-auto wrapper)
- Interaction 금지 (자율 실행). 머지 금지 (Worker).

---

# Sprint FE-A — Landing `/` + `/dashboard` 일관성 (ISSUE-002 · ISSUE-009)

## Scope (사전 fix)

### 1) `/` (`frontend/src/app/page.tsx`) — Landing

- 서버 컴포넌트 유지, `auth()` (Clerk) 로 로그인 상태 체크
  - `userId` 있음 → `redirect("/strategies")`
  - `userId` 없음 → Landing UI 표시
- 미인증 UI 개선:
  - "Stage 0 scaffold" 배지 제거
  - Hero copy (한 줄) + "시작하기" 버튼 (Clerk sign-in 링크, `<SignInButton>` 또는 `/sign-in` 라우트)
  - shadcn `Button` 사용, DESIGN.md 토큰 준수

### 2) `/dashboard` (`frontend/src/app/(dashboard)/dashboard/page.tsx`) — 불일치 해소

- scaffold placeholder 제거 후 `redirect("/strategies")` 로 변경.

## 브랜치

`feat/fe-a-landing-dashboard` · worktree `.claude/worktrees/feat+fe-a` · **base = stage/fe-polish**

## Test

- `pnpm lint` / `pnpm tsc --noEmit` / `pnpm test -- --run` 전부 green
- `pnpm build` green
- Live smoke (Playwright MCP): `/` 미인증 → "시작하기" 버튼 / 인증 → /strategies redirect / `/dashboard` → /strategies redirect. Console error 0, CPU < 80%

## PR

- `--base stage/fe-polish --head feat/fe-a-landing-dashboard`
- title: `feat(fe-a): Landing CTA + /dashboard redirect (ISSUE-002/009)`
- 예상 commit: 3~4개

---

# Sprint FE-B — `/trading` 모바일 + 빈 상태 (ISSUE-005 · ISSUE-006)

## Scope (사전 fix)

### 1) 모바일 overflow 수정 (ISSUE-005)

- Recent Orders (6컬럼) + Exchange Accounts (4컬럼) 375px 찌그러짐 → `overflow-x-auto` wrapper
- 375px / 768px / 1024px 3 뷰포트 검증

### 2) 빈 상태 copy + CTA (ISSUE-006)

- "Recent Orders (0)" 헤더만 있는 상태 → Empty state 컴포넌트
  - 문구: "아직 주문이 없습니다. 전략을 실행하면 여기에 표시됩니다."
  - CTA: "전략 보기" (→ `/strategies`)
- Exchange Accounts 빈 상태 동일 패턴

### 파일

- `frontend/src/app/(dashboard)/trading/page.tsx`
- `frontend/src/features/trading/components/*.tsx`

## 브랜치

`feat/fe-b-trading-mobile-empty` · worktree `.claude/worktrees/feat+fe-b` · **base = stage/fe-polish**

## Test

- 위와 동일 lint/tsc/test/build
- Live smoke: `/trading` 375px 가로 스크롤만 / 빈 상태 copy+CTA / console error 0

## PR

- `--base stage/fe-polish --head feat/fe-b-trading-mobile-empty`
- title: `feat(fe-b): /trading 모바일 overflow + 빈 상태 UX (ISSUE-005/006)`
- 예상 commit: 3~5개

---

# Sprint FE-C — 전역 UX 2건 (단축키 help + draft scoping)

## Scope (사전 fix)

### 1) Keyboard shortcut help dialog

- `?` key 전역 감지 (input/textarea focus 시 제외)
- shadcn `Dialog` modal
- 단축키 목록:
  - `⌘+S` — 저장 (edit 페이지)
  - `⌘+Enter` — 파싱 실행 (edit 페이지)
  - `?` — 이 도움말
  - `Esc` — 닫기
- 위치: `frontend/src/components/shortcut-help-dialog.tsx` (신규), `app/(dashboard)/layout.tsx` 에서 마운트

### 2) localStorage draft `user_id` scoping

- 현재 `localStorage["strategy-draft"]` → `localStorage["strategy-draft:${userId}"]` 로 변경
- Clerk `userId` 변화 시 이전 user draft 자동 삭제
- 파일: `frontend/src/app/(dashboard)/strategies/new/` 내 draft 훅 (grep 으로 찾아 수정)

## 브랜치

`feat/fe-c-shortcut-help-draft-scope` · worktree `.claude/worktrees/feat+fe-c` · **base = stage/fe-polish**

## Test

- lint/tsc/test/build green
- 새 unit test: shortcut dialog `?` open/close / input focus 시 `?` 무시 / draft scoping (userId 전환 시 이전 draft 삭제)
- Live smoke: `?` → 모달 / `Esc` → 닫힘 / sign-out → 다른 계정 → draft 미노출

## PR

- `--base stage/fe-polish --head feat/fe-c-shortcut-help-draft-scope`
- title: `feat(fe-c): 단축키 help dialog + draft userId scoping`
- 예상 commit: 4~6개

---

## Phase 0 절차 (Orchestrator)

1. `preflight-probe.sh` 실행 → 통과 확인
2. `.claude/settings.local.json` 광역 allow 패턴 확인/추가 (`git merge --squash *` + `git push origin stage/*` 포함)
3. **Staging branch 생성**:
   ```bash
   cd /Users/woosung/project/agy-project/quant-bridge
   git checkout main && git pull origin main
   git checkout -b stage/fe-polish
   git push -u origin stage/fe-polish
   ```
4. `.claude/plans/fe-polish-orchestration/` 생성 (tracker · signals · prompts · logs)
5. Worker worktree 3개 **stage/fe-polish 기준** 생성:
   ```bash
   git worktree add .claude/worktrees/feat+fe-a -b feat/fe-a-landing-dashboard stage/fe-polish
   git worktree add .claude/worktrees/feat+fe-b -b feat/fe-b-trading-mobile-empty stage/fe-polish
   git worktree add .claude/worktrees/feat+fe-c -b feat/fe-c-shortcut-help-draft-scope stage/fe-polish
   ```
6. 한 줄 출력: `"plan 작성 완료. Probe OK. stage/fe-polish 생성됨. 'ok' 입력 시 worker 3개 kickoff + staging 자동 머지 시작."`

## 워커 프롬프트 참조

`~/.claude/skills/autonomous-parallel-sprints/templates/worker-prompt.md` + 2026-04-19 B/C/D 세션의 `worker-b.prompt` base. **base 브랜치만 main → stage/fe-polish 로 치환**.

### Worker 프롬프트 핵심 차이 (Option C 전용)

- `gh pr create` 시 `--base stage/fe-polish` 명시
- branch 기준점: 워크트리 이미 stage/fe-polish 기준으로 만들어져 있음

## Phase 2 — Orchestrator 자동 머지 to stage/fe-polish (Option C 핵심)

각 워커 `pr_ready` 도달 시 순차:

```bash
cd /Users/woosung/project/agy-project/quant-bridge   # 메인 repo worktree
git fetch origin feat/fe-a-landing-dashboard
git checkout stage/fe-polish
git pull origin stage/fe-polish                      # 다른 머지가 먼저 반영됐을 수 있음
git merge --squash origin/feat/fe-a-landing-dashboard
git commit -m "feat(fe-a): Landing CTA + /dashboard redirect (ISSUE-002/009)"
git push origin stage/fe-polish

# PR 닫기 (이미 squash-merge 로 통합되었으므로)
gh pr close <pr_a> --comment "Merged via local squash into stage/fe-polish"
git push origin --delete feat/fe-a-landing-dashboard
```

N=3 반복 (fe-a, fe-b, fe-c). Conflict 발생 시 해당 PR `blocked` 기록 + 사용자 수동 resolve 요청. 각 머지 후 `git push origin stage/fe-polish` 로 원격 CI 돌림.

## Phase 3 — Cleanup + A→main 머지 안내 (사용자 수동)

자동 cleanup:

- 워커 worktree 3개 제거 · 로컬 branch 삭제 (stage/fe-polish 는 유지)
- cmux ws close · orphan 정리
- 메모리 3파일 + MEMORY.md 인덱스
- `.claude/plans/fe-polish-autonomous-summary.md` 최종화

**사용자에게 최종 보고 (A→main 머지 가이드 포함)**:

```
FE Polish 3 건 staging 머지 완료. main 은 여전히 06f10f0 (자동화 touch 없음).
stage/fe-polish 커밋: <SHA1> <SHA2> <SHA3> (CI 상태: ...)

다음 단계 — 사용자 수동 (2~3분):
cd /Users/woosung/project/agy-project/quant-bridge
gh pr create --base main --head stage/fe-polish \
  --title "chore: FE Polish 3건 통합 머지 (ISSUE-002/005/006/009 + shortcut help + draft scoping)" \
  --body "포함: fe-a (Landing/dashboard) + fe-b (trading mobile/empty) + fe-c (shortcut/draft). 각 sprint 는 stage/fe-polish 에 squash merge 됨."

# CI green 확인 후:
gh pr merge <new_pr_number> --squash --delete-branch
git checkout main && git pull origin main
```

**Rollback 명령 (만약 A 가 마음에 안 들면)**:

```
git branch -D stage/fe-polish
git push origin --delete stage/fe-polish
```

## 실패 대응 매트릭스

| 조건                          | 동작                                           |
| ----------------------------- | ---------------------------------------------- |
| lint/tsc/test 실패            | 3회 fix 후에도 실패 시 blocked                 |
| Live smoke CPU > 80%          | 즉시 blocked (LESSON-004 재발 방지)            |
| Evaluator 3회 FAIL            | blocked                                        |
| Probe 실패                    | kickoff 금지, 원인 제시                        |
| `git merge --squash` conflict | 해당 PR `blocked` + 사용자 수동 resolve 가이드 |
| staging CI red                | 보고서에 CI 상태 명시, 사용자 A→main 판단 맡김 |

## Session summary (Phase 3 끝)

`.claude/plans/fe-polish-autonomous-summary.md` — 3 staging 머지 결과 · commit SHA · 소요 · Evaluator iteration · **A→main 수동 머지 명령** · rollback 명령.

--- PROMPT END ---

## 사용 방법

1. 새 Claude Code 세션을 `claude --permission-mode bypassPermissions` 로 시작
2. 맨 위 트리거 프롬프트 3줄 붙여넣기
3. Probe 통과 + Phase 0 (stage 브랜치 + worktree + scaffolding) 결과 확인 → `"ok"` 입력
4. 자리 비움 (~60분)
5. 깨어나서 summary 확인 + A→main 머지 명령 3개 수동 실행 (터미널, 2~3분)

## 예상 타임라인

- Probe + Phase 0: ~10분
- Phase 1 kickoff + 워커 실행: ~30~45분
- Phase 2 로컬 squash merge × 3 + staging CI: ~10~15분
- Phase 3 cleanup + 보고: ~5분
- **Claude 자율 실행 합계**: ~55~75분 (사용자 개입 `"ok"` 1회)
- **사용자 A→main 머지**: 2~3분 (새 세션 아닌 그냥 터미널)
