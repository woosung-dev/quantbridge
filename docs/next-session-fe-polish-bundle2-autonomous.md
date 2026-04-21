# 자율 병렬 orchestration — FE Polish Bundle 2 (3 독립 PR, Option C Staging Branch)

> **트리거 프롬프트 (새 세션 첫 메시지):**
>
> ```
> /autonomous-parallel-sprints
> docs/next-session-fe-polish-bundle2-autonomous.md 읽고 그대로 실행해줘. Bundle 2 (FE Polish 3 병렬 — FE-D/E/F). Option C (Staging Branch — stage/fe-polish-b2 생성 후 3 워커 PR base=A, Orchestrator 로컬 squash merge → push, 사용자가 A→main 수동). 사용자 interaction 은 'ok' 한 번만. ★ 스킬 1 P0+P1 dogfood 첫 실측 — Worker permission prompt 발생 횟수 기록.
> ```

> **세션 시작 모드**: `claude --allow-dangerously-skip-permissions --dangerously-skip-permissions` (또는 `/permissions` → `approvalMode=auto`)

---

## 내부 참고

Bundle 1 (FE-A/B/C, 2026-04-19, stage/fe-polish) 머지 완료 이후 **autonomous-parallel-sprints 스킬 1 P0+P1 dogfood 첫 실측**. Bundle 1 에서 발견된 3가지 구조적 결함 (worktree settings 상속 · sig() 헬퍼 · Planner 자동화) 패치 효과를 정량 측정.

**H1 Stealth 마감 전 FE Design Debt 3건 병렬 처리** — `docs/TODO.md` § "Sprint 7c 이후 FE Design Debt" 중 독립 실행 가능한 3건 선별.

--- PROMPT START ---

# 자율 3-스프린트 연쇄 실행 (FE-D · FE-E · FE-F, Option C, Bundle 2)

## 실행 모드 — 엄수

- **세션 시작 모드**: `claude --allow-dangerously-skip-permissions --dangerously-skip-permissions`
- **cmux 병렬 모드**:
  - Orchestrator (Tab 1): Phase 0 scaffolding + staging branch 생성 + worker kickoff + 로컬 머지
  - Worker FE-D/E/F (Tab 2/3/4): 각자 독립 worktree (**base = stage/fe-polish-b2**). 구현 + Evaluator + PR 생성까지 (**머지 금지**)
- **사용자 interaction 1회**: Phase 0 완료 후 `"ok"` → Phase 1~3 자율.
- **Staging Branch 머지 전략 (Option C)**:
  - Phase 0 에서 `git checkout -b stage/fe-polish-b2 main && git push -u origin stage/fe-polish-b2`
  - 3 worker worktree 는 `stage/fe-polish-b2` 기준 분기
  - Worker PR 은 `--base stage/fe-polish-b2` 로 생성
  - Orchestrator Phase 2: **로컬 `git merge --squash` + `git push origin stage/fe-polish-b2`** (`gh pr merge` 미사용)
  - Phase 3 최종 보고에 사용자가 수행할 A→main 머지 명령 3개 명시

## 컨텍스트 — 직전 상태

- main HEAD: FE Polish Bundle 1 머지 완료 후 상태 (사용자가 이 세션 전 `stage/fe-polish` → main squash merge 완료 전제)
- Bundle 1 결과: FE-A (Landing CTA + /dashboard redirect) + FE-B (/trading 모바일/빈 상태) + FE-C (shortcut help + draft scoping) 머지
- 110 FE tests green, lint 0/0
- ESLint `react-compiler` + `@tanstack/query/exhaustive-deps` error level
- 메모리 참조: `project_fe_polish_bundle1_option_c.md`, `project_sprint_fe_{a,b,c}_complete.md`, `feedback_merge_strategy_c_default.md`

## ★ 스킬 1 P0+P1 dogfood 검증 (이번 실측 핵심)

**Bundle 1 대비 측정 지표**:

| 지표                          | Bundle 1 (P0 전)        | Bundle 2 목표 (P0 후) |
| ----------------------------- | ----------------------- | --------------------- |
| Worker permission prompt 발생 | 다수 (사용자 수동 클릭) | **0건**               |
| 자율 실행 시간                | 25분                    | 25분 이하             |
| Evaluator iter=1 PASS 비율    | 3/3                     | 3/3 유지              |

**Orchestrator 기록 책임**: Phase 3 summary 에 "Worker permission prompt 발생 횟수" 1 line 필수 포함.

## 사전 Probe 5단계 (Iron Law)

Orchestrator 는 Phase 0 시작 **전** 자동 수행:

```bash
bash ~/.claude/skills/autonomous-parallel-sprints/scripts/preflight-probe.sh \
  /Users/woosung/project/agy-project/quant-bridge
```

기대 결과: **[1~4] + [3b] 전부 통과**. Probe #3b (worktree settings 상속) 는 스킬 1 P0 패치 후 신규 추가됨. `gh pr merge*` DENY 감지는 무시 (Option C 미사용).

**추가 사전 작업 (Probe #3b 통과 보장)**: `.claude/settings.local.json` 의 `allow` 배열에 아래 패턴이 없으면 추가:

```json
"Bash(echo * > *.status)",
"Bash(echo * > *.iteration)",
"Bash(echo * > *.pr)",
"Bash(echo * > /Users/woosung/project/agy-project/quant-bridge/.claude/plans/*)",
"Bash(tee -a /Users/woosung/project/agy-project/quant-bridge/.claude/plans/*)",
"Bash(git merge --squash *)",
"Bash(git push origin stage/*)",
"Bash(gh pr close *)",
"Bash(git push origin --delete *)"
```

JSON 유효성: `python3 -m json.tool .claude/settings.local.json`.

## 공통 엄수 제약 (전 스프린트)

- **LESSON-004**: `react-hooks/*` eslint-disable 금지
- **LESSON-005**: queryKey factory `xxxKeys.list(userId, ...)` + `makeXxxFetcher` CallExpression
- **LESSON-006**: render body `ref.current = v` 금지 → sync useEffect(deps 없음)
- **LESSON-007**: dev server/mcp-chrome orphan 정리
- TypeScript strict, `any` 금지
- `.ai/stacks/nextjs-shared.md §4` 반응형 규칙 (모바일 <768px overflow-x-auto wrapper)
- shadcn/ui 토큰 준수 · DESIGN.md 토큰
- Interaction 금지 (자율 실행). 머지 금지 (Worker).
- Worker 프롬프트 상단 `sig()` 헬퍼 **반드시** 사용 (P0 패치)

---

# Sprint FE-D — Chip-style tag input (Strategy Form)

## Scope

현재 Strategy 생성 3-step form 의 tags 입력은 comma-split 텍스트. 파워 유저 마찰 → Enter/Backspace 기반 chip UI 로 변경.

### 1) 신규 컴포넌트

`frontend/src/features/strategy/components/tag-input.tsx`

- Controlled prop: `value: string[]`, `onChange: (next: string[]) => void`, `placeholder?: string`
- 입력 interaction:
  - Enter: 현재 input text trim → 빈 문자열 아니고 중복 아니면 chip 추가 + input clear
  - `,` 또는 `Tab`: 동일 (Enter 와 같은 동작)
  - Backspace (input 비어 있을 때): 마지막 chip 제거
  - chip 클릭: 해당 chip `×` 버튼 노출 → click 시 제거
- UI: shadcn Badge (removable variant) + `<input>` inline. focus ring 토큰

### 2) Form 통합

`frontend/src/app/(dashboard)/strategies/new/**/step-*.tsx` (or wizard 관련 컴포넌트) 내 tags 필드를 TagInput 으로 교체:

- 기존 Zod schema `tags: z.array(z.string()).max(N)` 유지
- draft 저장 로직 (Sprint FE-C 의 draft userId scoping) 그대로 유지

### 3) Unit test

- `tag-input.test.tsx`: Enter/Backspace/comma 각각 + 중복 방지 + max length 초과 거부

### 파일

- `frontend/src/features/strategy/components/tag-input.tsx` (신규)
- `frontend/src/features/strategy/components/__tests__/tag-input.test.tsx` (신규)
- `frontend/src/app/(dashboard)/strategies/new/...` (기존 form step 중 tags 다루는 파일 1~2개)

## 브랜치

`feat/fe-d-chip-tag-input` · worktree `.claude/worktrees/feat+fe-d` · **base = stage/fe-polish-b2**

## Test

- `pnpm lint` / `pnpm tsc --noEmit` / `pnpm test -- --run` green
- `pnpm build` green
- Live smoke (Playwright MCP): `/strategies/new` tags step → Enter chip 추가 / comma chip 추가 / Backspace 마지막 제거 / 중복 차단. Console error 0, CPU < 80%

## PR

- `--base stage/fe-polish-b2 --head feat/fe-d-chip-tag-input`
- title: `feat(fe-d): Strategy form chip-style tag input`
- 예상 commit: 3~4개

---

# Sprint FE-E — Bottom sheet DeleteDialog (mobile <768px)

## Scope

현재 Strategy 삭제 확인 `DeleteDialog` 는 centered modal. 모바일에서 thumb-reach 불편 → <768px 에서 하단 시트 (bottom sheet) 로 자동 전환.

### 1) 반응형 전환

`frontend/src/features/strategy/components/delete-dialog.tsx` (기존 파일 수정):

- `useMediaQuery('(max-width: 767px)')` 또는 Tailwind `md:` breakpoint 기반
- 모바일 <768px: `Sheet` (shadcn `Sheet side="bottom"`) + drag handle
- 데스크톱 ≥768px: 기존 `Dialog` 유지
- 공통 body: 삭제 확인 copy + "취소" + "삭제" (destructive variant)

### 2) thumb-reach 우선순위

- 하단 시트 내부 버튼 순서: "취소" (위) → "삭제" (아래) — 주 동작이 아래에 오도록 (thumb 자연 위치)
- Esc / 바깥 탭 → close
- drag down 으로 dismiss 가능

### 3) Unit test

- `delete-dialog.test.tsx`: viewport width mock 변경 시 Sheet vs Dialog 렌더 분기. Confirm button click → onConfirm 호출.

### 파일

- `frontend/src/features/strategy/components/delete-dialog.tsx` (수정)
- `frontend/src/features/strategy/components/__tests__/delete-dialog.test.tsx` (수정 또는 신규)
- shadcn `Sheet` 컴포넌트 미설치 시 `pnpm dlx shadcn@latest add sheet`

## 브랜치

`feat/fe-e-delete-bottom-sheet` · worktree `.claude/worktrees/feat+fe-e` · **base = stage/fe-polish-b2**

## Test

- lint/tsc/test/build green
- Live smoke: `/strategies` 목록 → 삭제 버튼. 375px → bottom sheet 렌더 / 1024px → dialog 렌더 / Esc 닫힘. Console error 0

## PR

- `--base stage/fe-polish-b2 --head feat/fe-e-delete-bottom-sheet`
- title: `feat(fe-e): DeleteDialog 모바일 bottom sheet 전환 (<768px)`
- 예상 commit: 3~4개

---

# Sprint FE-F — Backtest run from edit page

## Scope

현재 `/strategies/[id]/edit` 에서 백테스트 실행으로 넘어가는 UX 부재. Edit header 에 "백테스트 실행" CTA 추가 → `/backtest?strategy_id=${id}` 쿼리 파라미터로 backtest 폼 자동 프리필.

### 1) Edit 페이지 CTA

`frontend/src/app/(dashboard)/strategies/[id]/edit/...` (header/toolbar 관련 컴포넌트):

- shadcn Button (variant="outline" or "secondary") + `Link href={\`/backtest?strategy_id=\${id}\`}`
- 위치: 페이지 헤더 우측, 기존 Save 버튼 옆 또는 별도 라인
- 아이콘: `<Play />` (lucide-react) — "백테스트 실행" 라벨

### 2) Backtest 페이지 searchParams 파싱

`frontend/src/app/(dashboard)/backtest/**/*.tsx` (기존 백테스트 form 페이지):

- 서버 컴포넌트면 `searchParams` prop 으로 `strategy_id` 수신 → initial form value 주입
- 클라이언트 form 이면 `useSearchParams()` 로 `strategy_id` 읽어 초기 select default 설정
- `strategy_id` 가 유효한지 (해당 사용자 소유 + 활성 상태) 는 form submit 시 BE 가 검증 (새 BE 엔드포인트 불필요)

### 3) Unit test

- edit page header 렌더 시 "백테스트 실행" 링크 href 가 `/backtest?strategy_id=${id}`
- backtest form: searchParams `strategy_id=abc` 주입 시 초기 value 가 `abc`

### 파일

- `frontend/src/app/(dashboard)/strategies/[id]/edit/...` (header 컴포넌트 수정)
- `frontend/src/app/(dashboard)/backtest/...` (form prefill 수정)
- 기존 테스트 파일 2개 수정 or 신규 2개 추가

## 브랜치

`feat/fe-f-edit-to-backtest` · worktree `.claude/worktrees/feat+fe-f` · **base = stage/fe-polish-b2**

## Test

- lint/tsc/test/build green
- Live smoke: `/strategies/[id]/edit` → "백테스트 실행" 클릭 → `/backtest?strategy_id=...` 이동. strategy 선택이 미리 선택됨. Console error 0

## PR

- `--base stage/fe-polish-b2 --head feat/fe-f-edit-to-backtest`
- title: `feat(fe-f): Edit 페이지 → Backtest 이동 CTA + strategy_id prefill`
- 예상 commit: 3~4개

---

## 독립성 매트릭스 (Planner 판정 참고)

| Sprint | 주 수정 디렉토리                                                                 | 파일 충돌 여부                     |
| ------ | -------------------------------------------------------------------------------- | ---------------------------------- |
| FE-D   | `features/strategy/components/tag-input.tsx` + `app/(dashboard)/strategies/new/` | —                                  |
| FE-E   | `features/strategy/components/delete-dialog.tsx`                                 | — (FE-D 의 tag-input 과 별개 파일) |
| FE-F   | `app/(dashboard)/strategies/[id]/edit/` + `app/(dashboard)/backtest/`            | — (FE-D 의 new 디렉토리와 별개)    |

**판정**: 3 sprint 는 파일 경로 충돌 0건. Bundle 1 과 동일 독립성 확보.

**하드 skip 금지 조건 (GATE 1)**: 위 3건 모두 해당 없음 — DB migration / 신규 envvar / 외부 API / Golden Rule 위반 / 반복 LESSON 모두 0건. GATE 1 자동 skip 가능 (Planner confidence ≥ 9 전제).

---

## Phase 0 절차 (Orchestrator)

1. `preflight-probe.sh` 실행 → [1~4] + [3b] 전부 통과 확인
2. `.claude/settings.local.json` 광역 allow 패턴 확인/추가 (이미 Bundle 1 에서 추가돼 있어야 함)
3. **Staging branch 생성**:
   ```bash
   cd /Users/woosung/project/agy-project/quant-bridge
   git checkout main && git pull origin main
   git checkout -b stage/fe-polish-b2
   git push -u origin stage/fe-polish-b2
   ```
4. **pnpm install** (Bundle 1 교훈 — repo root frontend/node_modules staleness 예방):
   ```bash
   cd /Users/woosung/project/agy-project/quant-bridge/frontend
   pnpm install --frozen-lockfile
   ```
5. `.claude/plans/fe-polish-bundle2-orchestration/` 생성 (tracker · signals · prompts · logs)
6. **Phase -1 Planner** (스킬 1 P1 패치):
   ```bash
   bash ~/.claude/skills/autonomous-parallel-sprints/scripts/planner.sh \
     docs/next-session-fe-polish-bundle2-autonomous.md \
     .claude/plans/fe-polish-bundle2-orchestration \
     fe-polish-b2 3
   ```
   → Agent tool 로 Planner subagent dispatch → 3 worker prompt 자동 생성 (`prompts/worker-{d,e,f}.prompt`)
7. Worker worktree 3개 **stage/fe-polish-b2 기준** 생성:
   ```bash
   git worktree add .claude/worktrees/feat+fe-d -b feat/fe-d-chip-tag-input stage/fe-polish-b2
   git worktree add .claude/worktrees/feat+fe-e -b feat/fe-e-delete-bottom-sheet stage/fe-polish-b2
   git worktree add .claude/worktrees/feat+fe-f -b feat/fe-f-edit-to-backtest stage/fe-polish-b2
   ```
8. 한 줄 출력: `"plan 작성 완료. Probe 1~4 + 3b OK. Planner 3 worker prompt 생성. stage/fe-polish-b2 생성됨. 'ok' 입력 시 worker 3개 kickoff 시작."`

## Phase 1 절차 (kickoff)

사용자 "ok" 수신 후:

```bash
for X in d e f; do
  bash ~/.claude/skills/autonomous-parallel-sprints/scripts/kickoff-worker.sh \
    /Users/woosung/project/agy-project/quant-bridge/.claude/worktrees/feat+fe-$X \
    /Users/woosung/project/agy-project/quant-bridge/.claude/plans/fe-polish-bundle2-orchestration/prompts/worker-$X.prompt \
    fe-$X
  sleep 15  # trust 다이얼로그 순차 처리
done
```

**P0 패치 확인**: 각 worker worktree `.claude/settings.local.json` 가 심링크로 존재하는지:

```bash
ls -la .claude/worktrees/feat+fe-d/.claude/settings.local.json
# → symbolic link → /Users/woosung/project/agy-project/quant-bridge/.claude/settings.local.json
```

## Phase 2 — Orchestrator 순차 머지 to stage/fe-polish-b2 (Option C)

각 워커 `pr_ready` 도달 시 **직렬 머지 (mutex)**:

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git fetch origin feat/fe-d-chip-tag-input
git checkout stage/fe-polish-b2
git pull origin stage/fe-polish-b2
git merge --squash origin/feat/fe-d-chip-tag-input
git commit -m "feat(fe-d): Strategy form chip-style tag input"
git push origin stage/fe-polish-b2

gh pr close <pr_d> --comment "Merged via local squash into stage/fe-polish-b2"
git push origin --delete feat/fe-d-chip-tag-input
```

N=3 반복 (fe-d, fe-e, fe-f). Conflict 시 해당 PR `blocked` + 사용자 수동 resolve 요청.

**Partial-complete 정책** (스킬 1 SKILL.md 규정):

- `pr_ready` 2개 + `blocked` 1개 → blocked 제외하고 나머지 머지 진행 + blocked 내용 Phase 3 요약에 포함
- `blocked` 2개 이상 → 전체 홀드 + 사용자 에스컬레이션

## Phase 3 — Cleanup + A→main 머지 안내 (사용자 수동)

자동 cleanup:

- 워커 worktree 3개 제거 (`git worktree remove --force`)
- 로컬 branch 삭제 (`git branch -D`)
- cmux ws close · orphan 정리 (`pkill -f next-server`, `pgrep -f mcp-chrome | xargs -r kill`)
- 메모리 3파일 (`project_sprint_fe_{d,e,f}_complete.md`) + MEMORY.md 인덱스
- `.claude/plans/fe-polish-bundle2-orchestration/summary.md` 최종화:
  - **★ Worker permission prompt 발생 횟수 기록** (P0+P1 dogfood 검증)
  - 3 squash SHA
  - CI 상태
  - 소요 시간 (Bundle 1: 25분 대비)
  - Evaluator iteration 수

**사용자에게 최종 보고 (A→main 머지 가이드 포함)**:

```
FE Polish Bundle 2 staging 머지 완료. main 은 자동화 touch 없음.
stage/fe-polish-b2 커밋: <SHA-D> <SHA-E> <SHA-F> (CI 상태: ...)

★ P0+P1 dogfood 실측:
- Worker permission prompt 발생: N건 (Bundle 1: M건)
- 자율 실행 시간: X분 (Bundle 1: 25분)
- Evaluator iter=1 PASS: 3/3

다음 단계 — 사용자 수동 (2~3분):
cd /Users/woosung/project/agy-project/quant-bridge
gh pr create --base main --head stage/fe-polish-b2 \
  --title "chore: FE Polish Bundle 2 (chip tag input + bottom sheet + edit-to-backtest)" \
  --body "포함: fe-d (chip tag input) + fe-e (bottom sheet delete) + fe-f (edit→backtest CTA). 각 sprint 는 stage/fe-polish-b2 에 squash merge 됨."

gh pr merge <new_pr_number> --squash --delete-branch
git checkout main && git pull origin main
```

**Rollback 명령 (만약 마음에 안 들면)**:

```
git branch -D stage/fe-polish-b2
git push origin --delete stage/fe-polish-b2
```

## 실패 대응 매트릭스

| 조건                            | 동작                                                               |
| ------------------------------- | ------------------------------------------------------------------ |
| lint/tsc/test 실패              | 3회 fix 후에도 실패 시 blocked                                     |
| Live smoke CPU > 80%            | 즉시 blocked (LESSON-004 재발 방지)                                |
| Evaluator 3회 FAIL              | blocked                                                            |
| Probe 실패 (#3b 포함)           | kickoff 금지, 원인 제시                                            |
| `git merge --squash` conflict   | 해당 PR `blocked` + 사용자 수동 resolve 가이드                     |
| staging CI red                  | 보고서에 CI 상태 명시, 사용자 A→main 판단 맡김                     |
| ★ Worker permission prompt 발생 | Phase 3 summary 에 **횟수 + 발생 지점** 필수 기록 (P0 패치 검증용) |

## Session summary (Phase 3 끝)

`.claude/plans/fe-polish-bundle2-orchestration/summary.md` — 3 staging 머지 결과 + commit SHA + 소요 + Evaluator iteration + **★ P0+P1 dogfood 지표** + A→main 수동 머지 명령 + rollback 명령.

--- PROMPT END ---

## 사용 방법

1. 새 Claude Code 세션을 `claude --permission-mode bypassPermissions` 로 시작
2. 맨 위 트리거 프롬프트 3줄 붙여넣기
3. Probe 통과 (1~4 + 3b) + Phase 0 (stage 브랜치 + Planner + worktree + scaffolding) 결과 확인 → `"ok"` 입력
4. 자리 비움 (~45~60분)
5. 깨어나서 summary 확인 (특히 **Worker permission prompt 발생 횟수**) + A→main 머지 명령 3개 수동 실행

## 예상 타임라인

- Probe + Phase 0 (Planner 포함): ~10~15분
- Phase 1 kickoff + 워커 실행: ~30~40분
- Phase 2 로컬 squash merge × 3 + staging CI: ~10분
- Phase 3 cleanup + 보고: ~5분
- **Claude 자율 실행 합계**: ~55~70분 (사용자 개입 `"ok"` 1회)
- **사용자 A→main 머지**: 2~3분 (터미널)

## ★ 성공 판정 기준 (P0+P1 dogfood)

Bundle 2 실측이 아래 지표를 달성하면 스킬 1 안정화 확인 → **스킬 2 (autonomous-sprint-cycle) 착수 준비 완료**:

- ✅ Worker permission prompt **0건**
- ✅ 자율 실행 시간 25분 이하 (Bundle 1 동급)
- ✅ Evaluator iter=1 PASS 3/3
- ✅ 사용자 interaction "ok" 1회

하나라도 미달 시: 스킬 1 추가 패치 → 재 dogfood.
