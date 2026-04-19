# Sprint FE-03 (C) — Edit page 편집 버퍼 state lift-up

**Date:** 2026-04-19
**Branch:** `feat/sprint-fe03-edit-lift-up`
**Worktree:** `.claude/worktrees/feat+sprint-fe03`
**Scope source:** `docs/next-session-sprint-bcd-autonomous.md` § `# Sprint FE-03 (C)`

## 문제 정의

- `/strategies/[id]/edit` TabCode 의 Monaco editor 와 TabParse 의 preview query 가 서로 독립 local state 로 `pineSource` 를 소유 → 편집 내용이 TabParse 에 반영되지 않음.
- 페이지 header 에 **저장 버튼이 없음** — 사용자 편집은 persist 되지 않음.
- 탭 close / route change 시 경고 없음 → 저장 안 된 편집 유실 위험.

## 해결 (사전 fix된 baseline)

### Scope 5개

1. **Zustand 도메인 store** — `frontend/src/features/strategy/edit-store.ts`
   - State: `pineSource: string`, `lastSavedAt: Date | null`, `serverSnapshot: string`, `strategyId: string | null`
   - Computed: `isDirty` = `pineSource !== serverSnapshot` (store selector 로 제공 — `selectIsDirty`)
   - Actions: `setPineSource(s)`, `resetDirty()`, `markSaved(savedAt)`, `loadServerSnapshot(strategyId, pineSource)`
2. **TabCode** — Monaco `onChange` → `setPineSource` 직접 연결 (debounce 없음). 내부 `useState` 제거.
3. **TabParse** — `useEditStore(s => s.pineSource)` 구독, 500ms debounce 후 `usePreviewParse(debounced)` 재호출.
4. **Save 버튼** — `EditorView` header 우측, `isDirty` 시 enabled, 클릭 시 `useUpdateStrategy` mutation → `onSuccess` 시 `markSaved(new Date())` + `loadServerSnapshot` 업데이트 + sonner toast.
5. **Unload 경고** — `isDirty` true 시 `beforeunload` 이벤트로 `event.preventDefault()` + `returnValue` 세팅.

### 엄수 제약

- **LESSON-004**: `react-hooks/*` eslint-disable 절대 금지. useEffect dep 에 RQ/Zustand/RHF/Zod 결과 **직접 사용 금지** (선택자는 scalar, 개별 primitive 만).
- **LESSON-005**: queryKey factory 는 `strategyKeys.list(userId, ...)` 패턴 그대로. 신규 factory 추가 없음 (기존 `parsePreview` 재사용).
- **LESSON-006**: render body 에서 `ref.current = ` 대입 금지. debounce 는 `useRef` + sync useEffect(deps 없음) 패턴 (`draft.ts` 기존 패턴 그대로 복제).
- **Zustand scalar selector**: `useEditStore(s => s.pineSource)` 만. 객체 selector (`s => ({...})`) / 전체 store dep 금지.
- **TypeScript strict**, `any` 금지.

## 구현 단계 (TDD)

### Step 1. Zustand store + 단위 테스트

파일: `frontend/src/features/strategy/edit-store.ts`, `frontend/src/features/strategy/__tests__/edit-store.test.ts`

```ts
interface EditState {
  strategyId: string | null;
  pineSource: string;
  serverSnapshot: string;
  lastSavedAt: Date | null;
  setPineSource: (s: string) => void;
  loadServerSnapshot: (strategyId: string, pineSource: string) => void;
  markSaved: (savedAt: Date) => void;
  resetDirty: () => void;
}
```

Selectors (모듈 top-level):

- `selectPineSource = (s: EditState) => s.pineSource`
- `selectIsDirty = (s: EditState) => s.pineSource !== s.serverSnapshot`
- `selectLastSavedAt = (s: EditState) => s.lastSavedAt`

Tests:

- 초기값 확인
- `loadServerSnapshot` → `isDirty=false`
- `setPineSource` (서버 다른 값) → `isDirty=true`
- `setPineSource` (서버 같은 값 복귀) → `isDirty=false`
- `markSaved` 이후 `lastSavedAt` 갱신
- `resetDirty` 는 `pineSource = serverSnapshot` 으로 되돌림

### Step 2. TabCode 수정

`useState(strategy.pine_source)` 제거. Monaco `onChange` → `setPineSource`. 초기화는 `EditorView` 에서 `loadServerSnapshot` 호출 후 mount.
`dirty` / `update` 블록 제거 (저장은 header 에서).
internal manual parse (⌘+Enter) 는 현재 `source` 대신 store 값 사용.

### Step 3. TabParse 수정

`useEditStore(s => s.pineSource)` 로 구독. 500ms debounce (draft.ts 패턴) → debounced value 를 `usePreviewParse` 에 전달. 저장 로직은 header 로 이관되므로 `handleSave` 는 header 위치로 lift-up. Dialog onSave 는 header 버튼과 동일한 mutation 사용.

### Step 4. EditorView 수정

`loadServerSnapshot(id, strategy.pine_source)` 를 strategy fetch 완료 시 1회 실행. Header 에 Save 버튼 추가 (`isDirty` 시 enabled). Unload 경고 effect 추가.

### Step 5. 테스트

- `edit-store.test.ts` (Step 1)
- `tab-code.test.tsx` — Monaco onChange → store.pineSource update (기존 test 가 있다면 확장, 없으면 신규)
- `tab-parse.test.tsx` — store pineSource change → debounce → preview parse 재호출
- `editor-view.test.tsx` — unload warning + save flow

### Step 6. Self-verify

```bash
cd frontend
pnpm lint        # 0/0
pnpm tsc --noEmit
pnpm test -- --run
pnpm build       # Clerk env
```

Live smoke: `pnpm dev` + Playwright MCP navigate to `/strategies/<id>/edit` + 60s CPU 샘플링 (> 80% 샘플 0건 확인).

### Step 7. Evaluator dispatch

isolation=worktree, subagent_type=superpowers:code-reviewer (없으면 general-purpose). 최대 3 iteration.

### Step 8. PR 생성

`signals/c.status=pr_ready`, `signals/c.pr=<번호>`.

## Out of scope

- Auto-save (사용자 타이핑 중 자동 저장) — 수동 저장 버튼만.
- Route change 내부 경고 (Next.js `router.push` 은 `beforeunload` 트리거 안 함) — MVP 에서는 browser tab close 만 커버.
- 서버 rollback / optimistic update — 단순 mutation → invalidate.

## 결과물

- 신규: `edit-store.ts` + `edit-store.test.ts`
- 수정: `editor-view.tsx`, `tab-code.tsx`, `tab-parse.tsx`
- 예상 commit 5~6개: store, tab-code lift, tab-parse 구독, header save + unload, tests, 통합.
