# Sprint FE-C — Keyboard shortcut help + draft userId scoping

- **Branch**: `feat/fe-c-shortcut-help-draft-scope` (base: `stage/fe-polish`)
- **Worker**: autonomous, PR base = `stage/fe-polish`, no merge
- **Scope SSOT**: `docs/next-session-fe-polish-autonomous.md § # Sprint FE-C`
- **Rules**: LESSON-004/005/006, TS strict, Next 16 App Router

---

## Context

- Current `frontend/src/features/strategy/draft.ts` exposes `loadWizardDraft()` / `saveWizardDraft()` / `clearWizardDraft()` / `useAutoSaveDraft()` with **fixed key** `"sprint7c:strategy-wizard-draft:v1"` — draft leaks across Clerk accounts on the same device.
- Only call site: `frontend/src/app/(dashboard)/strategies/new/page.tsx`.
- `useAuth()` (`@clerk/nextjs`) already wired throughout `features/{strategy,backtest,trading}/hooks.ts` — `userId: string | null`.
- `(dashboard)/layout.tsx` wraps all authed pages; Clerk protects via `proxy.ts`.
- No existing `useKeyboardShortcut` hook; previous sprints only used local `onKeyDown` on specific controls (e.g. textarea Cmd+Enter).
- `components/ui/dialog.tsx` is Base UI Dialog (`@base-ui/react/dialog`), exports `Dialog/DialogContent/Header/Title/Description/Footer`. `Esc` close is built-in.

## Goal

1. **Global `?` keyboard shortcut** opens a help dialog listing the 4 supported shortcuts. Must ignore `?` when user is typing in `input` / `textarea` / `contentEditable`.
2. **Per-user localStorage scoping** for the new-strategy wizard draft — key format becomes `sprint7c:strategy-wizard-draft:v1:<userId>`; best-effort cleanup of the previous user's draft on userId transition.

## Non-goals

- New global shortcuts beyond the 4 already documented (⌘+S, ⌘+Enter, ?, Esc).
- Migrating old unscoped drafts — stale plain-key rows are simply orphaned (low volume, 30-day TTL on the old schema).
- Refactoring the pre-existing `eslint-disable react-hooks/set-state-in-effect` on the draft restore mount effect (out of scope; no functional change required).

---

## Implementation

### Step 1 — `components/shortcut-help-dialog.tsx` (new)

Client component. Owns both the global `?` listener **and** the Dialog UI (single source of truth for open state).

Key points:

- `"use client"` directive.
- `const [open, setOpen] = useState(false)`.
- `useEffect` adds a `document.addEventListener("keydown", handler)` and returns a cleanup that removes it. **Empty deps array** — listener installed once per mount.
- `handler(event: KeyboardEvent)`:
  - Ignore if `event.defaultPrevented` or `event.isComposing` or `event.repeat`.
  - Ignore if any modifier (ctrl/meta/alt) is down (we only want plain `?`).
  - Determine focus target via `document.activeElement` (plus traverse into shadow roots if ever relevant — not needed today). Focus guard returns early if the element is an `input`, `textarea`, or has `isContentEditable === true`.
  - `if (event.key === "?")` → `event.preventDefault()` + `setOpen(true)`.
- Render `<Dialog open={open} onOpenChange={setOpen}>` with a small table listing the 4 shortcuts.
- Esc handling comes free from Base UI Dialog — no extra work.
- TypeScript: the function component returns `React.JSX.Element`; no `any`.

Shortcut list UI — plain `<ul>` or `<dl>` with `<kbd>` elements; no new dependency. Strings in Korean to match the existing UI voice.

### Step 2 — Mount in `(dashboard)/layout.tsx`

`app/(dashboard)/layout.tsx` becomes effectively client-hosting via its child. But layout today has no `"use client"` — we keep it server-side. The new dialog component is a client island, which Next automatically lifts.

Mount as a sibling of `<DashboardShell>{children}</DashboardShell>`:

```tsx
<DashboardShell>{children}</DashboardShell>
<ShortcutHelpDialog />
```

This puts the shortcut listener on every authed route but not on the public landing / auth pages.

### Step 3 — `features/strategy/draft.ts` — userId-scoped key

1. Add helper `draftKeyFor(userId: string): string` → `` `sprint7c:strategy-wizard-draft:v1:${userId}` ``. Keep the top-level `DRAFT_KEY_PREFIX` and `DRAFT_KEY_VERSION_PREFIX = "sprint7c:strategy-wizard-draft:v1"` constant for tests and for cross-user cleanup.
2. Update signatures:
   - `loadWizardDraft(userId: string | null): WizardDraft | null` — returns `null` if `userId` is nil.
   - `saveWizardDraft(userId: string | null, draft): void` — no-op on nil userId.
   - `clearWizardDraft(userId: string | null): void` — no-op on nil userId.
   - `useAutoSaveDraft(userId: string | null, draft): void` — internal effect uses `userId` in the debounce deps so that a user swap triggers one trailing save for the new key (no leak into old user).
3. Add `clearOtherUsersDrafts(currentUserId: string | null): void` — iterates `window.localStorage` keys, matches prefix `sprint7c:strategy-wizard-draft:v1:`, removes any whose suffix !== current userId. Used on userId transition.
4. `useAutoSaveDraft` also watches userId change via a sync effect; when `previousUserId !== currentUserId` and both are non-null, call `clearWizardDraft(previousUserId)`. This is the "cleanup on Clerk userId change" spec. Implement via a `prevUserIdRef` that's updated in a sync `useEffect` (no deps) after each commit (LESSON-006-safe — ref write inside effect, not render body).
5. SSR guard stays (`typeof window !== "undefined"`).

### Step 4 — `app/(dashboard)/strategies/new/page.tsx`

- Import `useAuth` from `@clerk/nextjs`.
- `const { userId } = useAuth();`
- Replace call sites:
  - `loadWizardDraft()` → `loadWizardDraft(userId)`
  - `useAutoSaveDraft({ ... })` → `useAutoSaveDraft(userId, { ... })`
  - `clearWizardDraft()` → `clearWizardDraft(userId)` (twice — success + discard).
- Mount effect also gains a call to `clearOtherUsersDrafts(userId)` to wipe leftovers from prior sessions.

### Step 5 — Tests

Two new test files plus updates to the existing draft test:

1. `frontend/src/components/__tests__/shortcut-help-dialog.test.tsx`
   - `?` key fires → dialog opens.
   - `?` key while an `<input>` has focus → dialog stays closed, `?` not prevented.
   - `?` key while an element with `contentEditable` has focus → dialog stays closed.
   - `Esc` while open → dialog closes (Base UI default; verify via assertion).
   - Listener cleanup: unmount component, dispatch `?`, no re-open (dialog dom gone).
2. `frontend/src/features/strategy/__tests__/draft.test.ts` — **extend**, don't break existing cases:
   - Update `baseDraft` usage to pass `userId: "user_A"`.
   - Add: keys are scoped — after `saveWizardDraft("user_A", ...)`, `localStorage` has `sprint7c:strategy-wizard-draft:v1:user_A`.
   - Add: `loadWizardDraft("user_B")` returns null when only user_A saved.
   - Add: `clearOtherUsersDrafts("user_B")` wipes user_A's key but preserves user_B's.
   - Add: userId transition via `useAutoSaveDraft` — rerender with new userId and confirm that the previous user's key is cleared within one tick.
   - Edge: `loadWizardDraft(null)` returns null without throwing.

### Step 6 — Self-verification & live smoke

Per SSOT §5, run lint/tsc/test/build, then Playwright-MCP smoke scenarios a–d. Signals (`c.status`, `c.iteration`, `c.pr`) follow the orchestration protocol.

### Step 7 — Evaluator + PR

On PASS, push branch and `gh pr create --base stage/fe-polish` with the SSOT-mandated title/body. Never merge.

---

## Risk & mitigations

| Risk                                                                 | Mitigation                                                                                                          |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `?` shortcut intercepts typing in rich-text editors we may add later | `contentEditable` guard + modifier key guard; listener targeted to `document` not a specific element                |
| React StrictMode double-mount re-registers listener → double toggle  | cleanup returns inside `useEffect` — idempotent remove; modifier guard prevents runaway                             |
| userId `null` (sign-out) race right before save                      | helpers are no-ops on nil userId; test covers it                                                                    |
| Existing drafts under old unscoped key become invisible              | acceptable per Non-goals — stale entries expire via 30-day TTL path if we ever re-introduce read; no data loss risk |
| LESSON-006 (ref during render)                                       | `prevUserIdRef` is written only inside a sync `useEffect`                                                           |
| LESSON-004 (eslint-disable react-hooks/\*)                           | avoid entirely in new code; leave the pre-existing disable in `page.tsx` mount effect untouched (unrelated scope)   |

## File-level diff summary

- **new** `frontend/src/components/shortcut-help-dialog.tsx`
- **new** `frontend/src/components/__tests__/shortcut-help-dialog.test.tsx`
- **mod** `frontend/src/app/(dashboard)/layout.tsx` — mount the dialog
- **mod** `frontend/src/features/strategy/draft.ts` — userId-scoped key + cross-user cleanup
- **mod** `frontend/src/features/strategy/__tests__/draft.test.ts` — scope + cleanup cases
- **mod** `frontend/src/app/(dashboard)/strategies/new/page.tsx` — thread `userId` through

## Success criteria

- lint 0/0, `tsc --noEmit` clean, `vitest --run` green (new cases included), `pnpm build` green.
- Playwright smoke a–d all pass; console error 0; CPU <80%.
- Evaluator cold-start PASS.
- PR created to `stage/fe-polish` with conventional title.
