# Sprint FE-E — DeleteDialog 모바일 Bottom Sheet 전환 (<768px)

- Base: `stage/fe-polish-b2`
- Branch: `feat/fe-e-delete-bottom-sheet`
- Worktree: `.claude/worktrees/feat+fe-e`
- Strategy: Option C (Worker 는 PR 생성까지만, 머지는 Orchestrator)

## Scope

현재 `DeleteDialog`(2-phase: confirm / archive-fallback)는 센터 모달로만 렌더된다. 모바일(<768px) 에서 thumb-reach가 나쁘므로 하단 시트로 자동 전환.

실제 파일 경로: `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/delete-dialog.tsx` (SSOT 의 `features/strategy/components/` 서술은 레거시 표현; 실제 위치가 정답).

## 결정 · 제약

- 프로젝트는 `@base-ui/react` 기반이며 기존 `Dialog`는 base-ui 의 `DialogPrimitive` 위에 구현되어 있다. `shadcn add sheet` 는 radix 기반 Sheet 를 가져와 `button.tsx` overwrite 프롬프트를 띄우므로 **사용하지 않는다**.
- 대신 `Sheet` 컴포넌트를 base-ui `Dialog` 프리미티브 위에 직접 구성한다 (기존 `dialog.tsx` 패턴 그대로). 이 방식이 shadcn 생태계에서 허용되는 "컴포넌트 소유" 원칙과 일치하며, 기존 Dialog와 접근성 동작(ESC / backdrop click / focus trap)이 완전히 동일해진다.
- Drag-down dismiss: shadcn radix-sheet 기본 동작에도 drag-to-dismiss 는 없다. 이 스프린트의 허용 범위(LOC 최소)로 drag 핸들은 **시각적 afformance** 로만 제공 (thumbnail bar). Esc / 바깥 탭 / Close 버튼 dismiss 는 base-ui 기본 동작으로 커버.
- Viewport breakpoint: `(max-width: 767px)` → Sheet, `≥768px` → Dialog.
- SSR-safe: `useMediaQuery` 훅 초기값 `undefined`, mount 후 첫 렌더에서 결정. 서버 HTML 과 hydration mismatch 방지를 위해 마운트 전에는 기본값 Dialog 을 렌더.

## 변경 파일

1. **신규** `frontend/src/hooks/use-media-query.ts`
   - `useMediaQuery(query: string): boolean | undefined` (mount 전 undefined)
   - `window.matchMedia` 구독 · cleanup
   - SSR 가드

2. **신규** `frontend/src/components/ui/sheet.tsx`
   - base-ui `Dialog` 기반 컴포넌트 family: `Sheet`, `SheetContent`, `SheetHeader`, `SheetFooter`, `SheetTitle`, `SheetDescription`
   - `SheetContent`: `fixed inset-x-0 bottom-0 rounded-t-xl border-t p-4 pb-[env(safe-area-inset-bottom)]` + slide-in/out-to-bottom 애니메이션 + 상단 drag handle (`h-1 w-12 rounded-full bg-muted mx-auto mb-3`)

3. **수정** `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/delete-dialog.tsx`
   - `useMediaQuery("(max-width: 767px)")` 로 모바일 여부 판정
   - 모바일(true): `<Sheet> ... <SheetContent>` 사용, 버튼 컬럼 배치 (취소 위 · 삭제 아래)
   - 데스크톱(false|undefined): 기존 `<Dialog><DialogContent>` 유지
   - 2-phase (confirm / archive-fallback) 두 phase 모두 분기 적용
   - `onDone`/`onArchived`/`onOpenChange` 기존 prop 인터페이스 변경 없음

4. **신규** `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/__tests__/delete-dialog.test.tsx`
   - `window.matchMedia` mock helper (matches: boolean toggle)
   - <768px: Sheet 렌더 (drag handle 보임 / `data-slot="sheet-content"`)
   - ≥768px: Dialog 렌더 (`data-slot="dialog-content"`)
   - 삭제 버튼 클릭 → `useDeleteStrategy` mutate 호출 검증 (hook mock)
   - Phase 2 (`archive-fallback`) 렌더 분기 검증 — 모바일에서도 Sheet 로 렌더
   - SSR 초기(undefined) 상태: Dialog fallback 렌더

## Self-verify

```bash
cd frontend
pnpm lint          # 0/0
pnpm tsc --noEmit
pnpm test -- --run
pnpm build
# Live smoke: 375x667 → Sheet, 1024x768 → Dialog, Esc dismiss, CPU <80%
```

## Evaluator

`superpowers:code-reviewer` subagent · isolation=worktree · cold start 재현 · scope checklist + policy zero-tolerance.

## PR

`gh pr create --base stage/fe-polish-b2 --head feat/fe-e-delete-bottom-sheet` (Worker 는 생성까지만).

## 실패/블록 조건

- Evaluator 3회 FAIL → `sig status blocked`
- self-verify 3회 fix 후에도 red → blocked
- Live smoke CPU > 80% (LESSON-004 재발) → blocked
- base-ui Sheet 구현 중 타입/접근성 deep issue (base-ui Dialog 인터페이스 변경 등) → blocked
