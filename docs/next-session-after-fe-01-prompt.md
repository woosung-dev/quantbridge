# Sprint FE-02 시작 프롬프트 — Tech Debt & 가드레일 완성 (바이브 코딩 번들)

> 새 Claude Code 세션에서 이 파일 내용을 붙여넣거나, 아래 "--- PROMPT START ---" 블록만 복사. 또는 단 한 줄: `docs/next-session-after-fe-01-prompt.md 읽고 그대로 실행해줘`

---

## 내부 참고

Sprint FE-01 (TabParse 1질문 UX + LESSON-004 가드레일) 완료. FE tech debt가 가시화됐고 CI 가드레일 자동화가 일시 중단된 상태. 이걸 한 번에 정리하는 "tech debt 제로 + 가드레일 완성" 스프린트. UX 결정 불필요 → 바이브 코딩으로 단번에.

--- PROMPT START ---

# Sprint FE-02: FE Tech Debt & 가드레일 완성

## 컨텍스트 — 직전 세션 결과 (2026-04-19)

Sprint FE-01 완료. Main에 두 PR 머지됨:

- `44e0986` feat(fe-01): TabParse 1질문 UX + CPU 100% 수정 (#23)
- `941e942` chore(lesson-004): React hooks 가드레일 (#24)

**LESSON-004 사건**: `useEffect(() => setIndex(0), [result])` 패턴이 React Query 참조 흔들림 조건에서 CPU 100% 무한 루프 → 시스템 종료. iter-3에서 useEffect 제거 + `clampedIndex` render-time clamp. 3중 방어선 (ESLint error + CI grep + PR template) 설치됐지만 **자동 E2E/build 검증은 hotfix #4로 일시 disable**.

## 이 세션의 목표 — 한 번에 3건 번들

**Sprint FE-02 = A + B + E** (바이브 코딩, 총 ~6시간, UX 결정 0건)

| #     | 작업                                        | 산출물                                                                          |
| ----- | ------------------------------------------- | ------------------------------------------------------------------------------- |
| **A** | Clerk test key → CI build/e2e job 복원      | `.github/workflows/ci.yml` 복원 + repo secret 2개 등록                          |
| **B** | `@tanstack/query/exhaustive-deps` 7건 정리  | `hooks.ts` + `trading/hooks.ts` queryKey에 Clerk token 통합 + warn → error 격상 |
| **E** | `react-compiler` warn 해소 (`draft.ts` 1건) | debouncer 패턴 refactor 또는 명시적 allowlist                                   |

**완료 조건**: `pnpm lint` 0 errors 0 warnings + CI build + e2e job 자동 실행 + Clerk auth queryKey 통합. 이 스프린트 끝나면 FE tech debt 제로.

**C (source lift-up) + D (Backtest UI)는 별도 스프린트** (UX 결정 / scope 커서 번들 부적합).

## 시작 액션

### 0단계: 이전 세션 cleanup (Bash 셸 묶임으로 미완료)

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git checkout main && git pull origin main
git worktree prune
git branch -D sprint-fe-01-full-backup 2>/dev/null || true
git branch -D worktree-feat+sprint-fe-01-tabparse-1q 2>/dev/null || true
git branch -D feat/sprint-fe-01-tabparse-1q 2>/dev/null || true
git branch -D chore/lesson-004-guardrails 2>/dev/null || true
git fetch --prune origin
git branch --merged main | grep -vE '^\*|main|master' | xargs -r git branch -d
```

### 1단계: 워크트리 생성

```bash
# superpowers:using-git-worktrees 패턴
git worktree add .claude/worktrees/feat+sprint-fe02-techdebt -b feat/sprint-fe02-techdebt
cd .claude/worktrees/feat+sprint-fe02-techdebt
```

### 2단계: 메모리 조회

`project_sprint_fe01_complete.md` + `feedback_effect_ref_loop.md` 읽고 LESSON-004 맥락 + hooks 금기 패턴 재확인.

## 방법론 선택

**추천: 하이브리드 병렬** (메인 세션 A + 2 subagent 병렬 B/E). 총 ~3~4시간.

| 옵션               | 설명                                                           | 추천도 | 실시간                 |
| ------------------ | -------------------------------------------------------------- | ------ | ---------------------- |
| 1. 순차            | Vibe coding 흐름, 하나씩                                       | ★★★★   | ~6h                    |
| 2. 하이브리드 병렬 | A는 메인 (Clerk Dashboard human-gate), B/E는 subagent 2개 동시 | ★★★★★  | ~3~4h                  |
| 3. 완전 병렬       | 3 worktree + 3 subagent                                        | ★★★    | ~2.5h, 머지 오버헤드 ↑ |

### 방법론 A: 하이브리드 병렬 (추천) — `superpowers:dispatching-parallel-agents`

**Phase 1 — 플래닝 (10분)**:

- `superpowers:writing-plans` 로 단일 플랜 작성
- 플랜 파일: `docs/superpowers/plans/2026-04-19-sprint-fe02-techdebt.md`
- 3개 독립 Task 블록 명시 (파일 경계 분리):
  - **A (ci.yml + secret)**: 메인 세션 직접 실행
  - **B (queryKey 통합)**: `hooks.ts` + `trading/hooks.ts` + `strategyKeys/tradingKeys` factory
  - **E (draft.ts refactor)**: `draft.ts` 만
- `eslint.config.mjs` 의 rule 격상은 B/E 완료 후 **메인 세션이 일괄 적용** (충돌 회피)

**Phase 2 — 병렬 실행**:

**메인 세션** (human + Clerk Dashboard):

1. Clerk Dashboard → quantbridge-ci dev app 생성
2. `gh secret set CLERK_TEST_PUBLISHABLE_KEY` / `CLERK_TEST_SECRET_KEY`
3. `.github/workflows/ci.yml` hotfix #4 복원
4. `frontend/playwright.config.ts` 확인

**동시에, subagent 2개 dispatch** (`superpowers:dispatching-parallel-agents`):

- **Subagent 1 (B)**: general-purpose, isolation=worktree
  - 브랜치: `chore/query-keys-userid`
  - Task: hooks.ts/trading/hooks.ts queryKey에 `userId` 통합 + 기존 테스트 녹색 유지 + 새 테스트 추가
  - 금지: eslint.config.mjs 수정 (메인이 일괄 처리)
  - 리포트 형식: diff 파일 목록 + vitest 결과 + 주의사항

- **Subagent 2 (E)**: general-purpose, isolation=worktree
  - 브랜치: `chore/draft-debouncer-useref`
  - Task: draft.ts debouncer를 `useRef` 패턴으로 refactor + 기존 저장 동작 테스트
  - 금지: eslint.config.mjs 수정
  - 리포트 형식: diff + vitest + 주의사항

**Phase 3 — 수렴 (30분)**:

1. Subagent 1/2 리포트 수령 → 코드 검토 (actual diff 확인, trust-but-verify)
2. 두 브랜치를 메인 세션 브랜치 `feat/sprint-fe02-techdebt`에 cherry-pick 또는 merge
3. `eslint.config.mjs`에 `@tanstack/query/exhaustive-deps: "error"` + `react-compiler/react-compiler: "error"` 일괄 격상
4. `pnpm lint` → **0 errors 0 warnings** 확인
5. `pnpm test` 녹색 / `pnpm typecheck` clean
6. CI build + e2e job 복원 상태 확인
7. Playwright MCP Live smoke (TabParse walkthrough 5분)
8. `superpowers:finishing-a-development-branch` → 단일 PR (3건 번들)

### 방법론 B: 순차 (대안)

1. `superpowers:writing-plans` → 플랜
2. `superpowers:executing-plans` → T1~T8 순차 (A → B → E)
3. 각 commit마다 CPU 모니터링 + atomic commit
4. PR 생성

선택은 세션 시작 시 결정 (default: 하이브리드 병렬).

## 작업별 상세 가이드

### A: Clerk test key → CI 복원

**Step A1**: Clerk Dashboard 접속 (https://dashboard.clerk.com) → 신규 dev application 생성 (이름: "quantbridge-ci"). 또는 기존 dev instance (frank-goose-90 / stunning-chipmunk-35) 재활용.

**Step A2**: secret 등록

```bash
gh secret set CLERK_TEST_PUBLISHABLE_KEY --body "pk_test_xxx..."
gh secret set CLERK_TEST_SECRET_KEY --body "sk_test_xxx..."
```

**Step A3**: `.github/workflows/ci.yml`에서 PR #24 hotfix #4의 주석 영역을 복원:

- frontend job에 `pnpm build` step 재추가
- 별도 `e2e` job 재도입 (Playwright + chromium)
- env 참조: `${{ secrets.CLERK_TEST_PUBLISHABLE_KEY }}` / `${{ secrets.CLERK_TEST_SECRET_KEY }}`
- ci summary job의 needs 배열에 `e2e` 다시 포함

**Step A4**: `frontend/playwright.config.ts` webServer command를 `pnpm dev` 유지 (240s timeout). Clerk 실제 키라 초기화 성공 예상.

### B: query exhaustive-deps 정리 (Clerk getToken queryKey 통합)

**현재 패턴** (7건 모두):

```typescript
const { getToken } = useAuth();
return useQuery({
  queryKey: strategyKeys.list(), // ← getToken 누락
  queryFn: async () => {
    const token = await getToken();
    return listStrategies(token);
  },
});
```

**권장 전략**: `userId`를 queryKey에 포함 (token은 매번 새로 가져옴, userId가 바뀌면 cache invalidation)

```typescript
const { userId, getToken } = useAuth();
return useQuery({
  queryKey: strategyKeys.list(userId ?? "anon"),
  queryFn: async () => {
    const token = await getToken();
    return listStrategies(token);
  },
  enabled: !!userId,
});
```

**Step B1**: `strategyKeys` / `tradingKeys` 함수 시그니처에 `userId` 파라미터 추가 (queryKey factory pattern)

**Step B2**: 7건 호출부 일괄 refactor

**Step B3**: ESLint 규칙 warn → error 격상 (`frontend/eslint.config.mjs`)

**Step B4**: 기존 테스트 녹색 유지 확인

### E: draft.ts debouncer refactor

**현재** (`frontend/src/features/strategy/draft.ts:63~69`):

```typescript
useEffect(() => {
  const t = setTimeout(() => saveWizardDraft(draft), 500);
  return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [method, pineSource]);
```

**문제**: `draft` 는 dep에 없고 매 render 새 객체 → exhaustive-deps disable 필요 → react-compiler 최적화 불가.

**해결**: `useRef`로 최신 draft 참조 유지 + dep은 scalar만

```typescript
const draftRef = useRef(draft);
draftRef.current = draft; // render 시 참조 갱신

useEffect(() => {
  const t = setTimeout(() => saveWizardDraft(draftRef.current), 500);
  return () => clearTimeout(t);
}, [method, pineSource]);
// exhaustive-deps 통과 (ref는 stable)
```

**Step E1**: refactor + 기존 draft 저장 동작 테스트 (vitest)

**Step E2**: `react-compiler` 규칙 warn → error 격상

## 엄수 제약 (LESSON-004 이후)

- **hooks 변경 diff 에서 dev server 5분 live smoke 필수**. Activity Monitor / `top` 으로 CPU 확인
- **ESLint `react-hooks/*` disable 절대 금지** (B/E 작업 중에도 override 유혹 있음 — 패턴을 바꾸는 방향으로)
- useEffect dep는 **scalar 우선** (`[items.length]` > `[items]`)
- React Query `.data` / Zustand full store / RHF `watch()` / Zod `.parse()` 결과를 useEffect dep로 쓰지 말 것
- 선택지 2개↑ 제시 시 **별점 테이블로 추천도 필수**

## 완료 조건 체크리스트

- [ ] `pnpm lint` → **0 errors, 0 warnings** (이전 8 warnings 제거)
- [ ] `pnpm test` → 35+ green (기존 수 유지 or 증가)
- [ ] `pnpm typecheck` → clean
- [ ] CI 재활성화: `frontend job` build + 별도 `e2e` job 동작 + PR #24 hotfix 역복원
- [ ] Clerk Dashboard "quantbridge-ci" app 등록 + GitHub secret 2개 존재
- [ ] Live smoke: TabParse → Dialog walkthrough → save → PUT 200 OK + CPU 0% 유지
- [ ] PR 생성 + CI green + 리뷰어 수동 smoke 완료 체크박스 통과
- [ ] `.ai/project/lessons.md` 에 이번 스프린트의 새 lesson 추가 (있다면)

## 참조

- `.ai/project/lessons.md` LESSON-004 — 사고 전체 기록
- `docs/superpowers/plans/2026-04-19-sprint-fe-01-tabparse-1q.md` — FE-01 플랜
- `docs/ai-rules-prompt-react-hooks-safety.md` — ai-rules 전파 프롬프트 (별도 세션)
- PR #23 (`44e0986`) / PR #24 (`941e942`) — 구현 히스토리
- Memory: `project_sprint_fe01_complete.md`, `feedback_effect_ref_loop.md`

--- PROMPT END ---

## 사용 방법

### 한 줄로 시작 (가장 빠름)

```
docs/next-session-after-fe-01-prompt.md 읽고 그대로 실행해줘
```

### 전체 붙여넣기

위 "--- PROMPT START ---" 부터 "--- PROMPT END ---" 까지 복사 + 새 Claude Code 세션에 붙여넣기.

## 다음 스프린트 예고 (FE-03+)

이번 스프린트 (FE-02 tech debt) 완료 후:

| 번호              | 후보                                                                                           | 방법론                                                               | 예상 |
| ----------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ---- |
| **FE-03**         | Edit page source state 리프트업 (C) — TabCode ↔ TabParse 편집 버퍼 공유, "저장" 버튼 실제 동작 | brainstorming → writing-plans → plan-design-review → executing-plans | ~4h  |
| **FE-04 / BE-04** | Backtest UI MVP (D) — BE 이미 ready, UI만                                                      | office-hours → writing-plans                                         | ~8h+ |
| 기타              | UI/UX 디자인 체계 강화, mobile-first 반응형 재점검 등                                          | —                                                                    | —    |

C는 브레인스토밍 필수, D는 큰 스프린트라 각각 별도 세션.
