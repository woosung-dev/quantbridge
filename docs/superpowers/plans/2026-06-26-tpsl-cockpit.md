# 모바일 트레이딩 콕핏 polish + PnL surfacing 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**TDD 모드: 혼합.** pure util / hooks 도입 = 정석 TDD (test 먼저 RED → impl → GREEN). pure UI 표현(props + tone class, effect 없음) = test+impl 동시.

**Goal:** demo-safe 모바일 트레이딩 콕핏에서 세션별 실현손익(PnL)을 한눈에 보이게 surfacing 하고 반응형 polish 를 더한다 (신규 BE API 0).

**Architecture:** 기존 `useLiveSessionState` hook 을 재사용해 세션 리스트 각 행에 실현손익 배지를 노출(React Query 캐시가 detail 패널과 queryKey 공유 → 추가 네트워크 0). 순수 포맷 헬퍼 `formatRealizedPnl` 로 부호·색조(tone)를 SSOT 화하고 detail 패널·list 배지가 공유한다.

**Tech Stack:** Next.js 16 (App Router) · TypeScript strict · Tailwind v4 · React Query · vitest + @testing-library/react.

## 사전 발견 (grounding 정정)

- **BL-356~359 모바일 터치타겟 ≥44pt 는 이미 main 에서 해소됨** (Sprint 62 PR #290 `36bb4e0`). `date-preset-pills.tsx`(BL-356 `h-11 md:h-8`) / `strategy-table.tsx`(BL-357) / `dashboard-header.tsx` UserButton(BL-358 `size-11 min-w-11`) / `exchange-accounts-panel.tsx` 삭제버튼(BL-359 `size-11 md:size-auto`) 전부 Sprint 62 T-2 주석과 함께 적용 완료. → **재수정 금지(surgical changes). 검증만.**
- 기존 테이블은 전부 `overflow-x-auto` + `min-w-[Npx]` 래퍼 보유 (orders/exchange-accounts/events). KPI hero 는 `grid-cols-2 md:grid-cols-4` 반응형 완비. → 추가 작업 불필요, 검증만.
- 실제 잔여 gap = **세션별 PnL 이 detail 패널을 탭해야만 보임** (모바일 glanceable 부재) + detail 패널 PnL 이 부호·색조 없는 raw string.

## Global Constraints

- demo-only. 신규 BE API 0 (기존 hook/API 만 재사용). 신규 Celery task 0. migration 0.
- 신규 파일 첫줄 한국어 역할주석. 사고/문서 한국어, 네이밍/커밋 영어. Korean 문장 종결 `.`(콜론 금지).
- TypeScript strict, `any` 금지. react-hooks ESLint disable 금지 (LESSON-004). useEffect dep 에 RQ/Zustand/RHF/Zod 결과 직접 사용 금지 (LESSON-006). React Query = queryKey factory + userId 첫 인자 (LESSON-005).
- 커밋 trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **★ 명시적 defer:** 긴급 flatten/전량청산 버튼 구현 금지 (close-all BE 엔드포인트 부재 = cross-domain, Wave0 disjoint 위반).

---

### Task 1: `formatRealizedPnl` 순수 포맷 헬퍼 (정석 TDD)

**Files:**
- Modify: `frontend/src/features/live-sessions/utils.ts`
- Test: `frontend/src/features/live-sessions/__tests__/format-realized-pnl.test.ts` (Create)

**Interfaces:**
- Produces:
  - `type PnlTone = "profit" | "loss" | "flat"`
  - `interface RealizedPnlDisplay { text: string; tone: PnlTone }`
  - `function formatRealizedPnl(raw: string): RealizedPnlDisplay` — BE Decimal-as-string 입력. 양수 → `+`prefix·tone "profit", 음수 → 그대로(부호 포함)·tone "loss", 0 → `0`·tone "flat". 파싱 불가(NaN) → raw 그대로·tone "flat".

- [ ] **Step 1: 실패 테스트 작성**

```typescript
// 실현손익 string → 부호·tone 포맷 헬퍼 단위 테스트.
import { describe, it, expect } from "vitest";
import { formatRealizedPnl } from "../utils";

describe("formatRealizedPnl", () => {
  it("양수 → + prefix + profit tone", () => {
    expect(formatRealizedPnl("12.34")).toEqual({ text: "+12.34", tone: "profit" });
  });
  it("음수 → 부호 보존 + loss tone", () => {
    expect(formatRealizedPnl("-5.5")).toEqual({ text: "-5.5", tone: "loss" });
  });
  it("0 → flat tone, prefix 없음", () => {
    expect(formatRealizedPnl("0")).toEqual({ text: "0", tone: "flat" });
  });
  it("파싱 불가 → raw 보존 + flat tone", () => {
    expect(formatRealizedPnl("n/a")).toEqual({ text: "n/a", tone: "flat" });
  });
  it("precision 보존 — 원본 string 유지(부동소수 재포맷 안 함)", () => {
    expect(formatRealizedPnl("0.000000001")).toEqual({
      text: "+0.000000001",
      tone: "profit",
    });
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && pnpm test -- --run src/features/live-sessions/__tests__/format-realized-pnl.test.ts`
Expected: FAIL — `formatRealizedPnl is not a function`.

- [ ] **Step 3: 최소 구현** (`utils.ts` 끝에 추가)

```typescript
// ── 실현손익 표시 포맷 (Wave0 cockpit — 부호·tone SSOT) ──────────────────
// BE Decimal-as-string 입력. precision 보존 위해 원본 string 유지 (재포맷 X),
// 부호 판정만 Number 로. detail 패널 + list 배지가 공유.

export type PnlTone = "profit" | "loss" | "flat";

export interface RealizedPnlDisplay {
  text: string;
  tone: PnlTone;
}

export function formatRealizedPnl(raw: string): RealizedPnlDisplay {
  const n = Number(raw);
  if (!Number.isFinite(n) || n === 0) {
    return { text: raw, tone: "flat" };
  }
  if (n > 0) {
    return { text: `+${raw}`, tone: "profit" };
  }
  return { text: raw, tone: "loss" };
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && pnpm test -- --run src/features/live-sessions/__tests__/format-realized-pnl.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/features/live-sessions/utils.ts frontend/src/features/live-sessions/__tests__/format-realized-pnl.test.ts
git commit -m "feat(live-sessions): formatRealizedPnl sign+tone SSOT helper"
```

---

### Task 2: detail 패널 Realized PnL 부호·색조 적용 (pure UI — test+impl 동시)

**Files:**
- Modify: `frontend/src/features/live-sessions/components/live-session-detail.tsx`
- Test: `frontend/src/features/live-sessions/components/__tests__/live-session-detail.test.tsx:291-307` (기존 assertion 갱신)

**Interfaces:**
- Consumes: `formatRealizedPnl` (Task 1).

- [ ] **Step 1: import 추가** (`live-session-detail.tsx` 상단 utils import 에 합류)

```typescript
import {
  buildActivityTimeline,
  buildActivityTimelineWithEquity,
  formatRealizedPnl,
} from "../utils";
```

- [ ] **Step 2: Realized PnL `<dd>` 교체** (현재 line 69-74 블록)

```tsx
<div>
  <dt className="text-muted-foreground">Realized PnL</dt>
  <dd className="font-mono">
    {stateLoading ? (
      "…"
    ) : (
      <PnlValue raw={state?.total_realized_pnl ?? "0"} />
    )}
  </dd>
</div>
```

- [ ] **Step 3: `PnlValue` presentational 컴포넌트 추가** (파일 하단, `LiveSessionDetail` 함수 뒤)

```tsx
// 실현손익 값 — 부호 + tone 색조 (profit=success / loss=destructive / flat=muted).
function PnlValue({ raw }: { raw: string }) {
  const { text, tone } = formatRealizedPnl(raw);
  const toneClass =
    tone === "profit"
      ? "text-[color:var(--success)]"
      : tone === "loss"
        ? "text-[color:var(--destructive)]"
        : "text-[color:var(--foreground)]";
  return <span className={toneClass}>{text}</span>;
}
```

- [ ] **Step 4: 기존 테스트 assertion 갱신** (`live-session-detail.test.tsx`, "session 메타" 테스트의 PnL assertion)

기존:
```typescript
    expect(screen.getByText("98.76")).toBeInTheDocument();
```
교체 (양수 → `+` prefix 반영):
```typescript
    // Wave0 cockpit: 양수 PnL 은 + prefix + success tone 으로 표시.
    expect(screen.getByText("+98.76")).toBeInTheDocument();
```

- [ ] **Step 5: 테스트 실행**

Run: `cd frontend && pnpm test -- --run src/features/live-sessions/components/__tests__/live-session-detail.test.tsx`
Expected: PASS (5 tests — PnL assertion 갱신 반영).

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/features/live-sessions/components/live-session-detail.tsx frontend/src/features/live-sessions/components/__tests__/live-session-detail.test.tsx
git commit -m "feat(live-sessions): sign+tone Realized PnL in detail panel"
```

---

### Task 3: 세션 리스트 행에 PnL 배지 surfacing (정석 TDD — hooks 도입)

**Files:**
- Modify: `frontend/src/features/live-sessions/components/live-session-list.tsx`
- Test: `frontend/src/features/live-sessions/components/__tests__/live-session-list-pnl.test.tsx` (Create)

**Interfaces:**
- Consumes: `useLiveSessionState(sessionId, isActive)` (기존 hook) + `formatRealizedPnl` (Task 1).
- 설계: 리스트 `<li>` 안의 자식 컴포넌트 `SessionPnlBadge` 가 hook 을 호출(루프 안 hook 호출 금지 → 자식 컴포넌트 top-level). queryKey 는 `liveSessionKeys.state(uid, sessionId)` 로 detail 패널과 동일 → RQ 캐시 공유, 추가 네트워크 0. is_active 세션만 리스트에 표시되므로 항상 enabled.

- [ ] **Step 1: 실패 테스트 작성** (state mock 으로 PnL 배지 렌더 검증)

```typescript
// 세션 리스트 PnL 배지 — useLiveSessionState 재사용 surfacing 검증.
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LiveSession, LiveSignalState } from "../../schemas";
import { LiveSessionList } from "../live-session-list";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "test-user", getToken: async () => "test-token" }),
}));

const stateMock = vi.fn();
const listMock = vi.fn();
vi.mock("../../api", () => ({
  getLiveSessionState: (...a: unknown[]) => stateMock(...a),
  listLiveSessions: (...a: unknown[]) => listMock(...a),
  listLiveSessionEvents: vi.fn(),
  registerLiveSession: vi.fn(),
  deactivateLiveSession: vi.fn(),
}));

const SESSION: LiveSession = {
  id: "00000000-0000-0000-0000-0000000000aa",
  user_id: "00000000-0000-0000-0000-0000000000bb",
  strategy_id: "00000000-0000-0000-0000-0000000000cc",
  exchange_account_id: "00000000-0000-0000-0000-0000000000dd",
  symbol: "BTCUSDT",
  interval: "5m",
  is_active: true,
  last_evaluated_bar_time: null,
  created_at: "2026-05-01T11:00:00Z",
  deactivated_at: null,
};

const STATE: LiveSignalState = {
  session_id: SESSION.id,
  schema_version: 1,
  last_strategy_state_report: {},
  last_open_trades_snapshot: {},
  total_closed_trades: 3,
  total_realized_pnl: "42.5",
  equity_curve: [],
  updated_at: "2026-05-01T12:00:00Z",
};

function renderWith(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("LiveSessionList PnL 배지 (Wave0 cockpit surfacing)", () => {
  beforeEach(() => {
    stateMock.mockReset();
    listMock.mockReset();
    listMock.mockResolvedValue({ items: [SESSION], total: 1 });
    stateMock.mockResolvedValue(STATE);
  });

  it("활성 세션 행에 부호·tone PnL 배지 표시", async () => {
    renderWith(<LiveSessionList />);
    // 양수 PnL 은 + prefix.
    expect(await screen.findByText("+42.5")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && pnpm test -- --run src/features/live-sessions/components/__tests__/live-session-list-pnl.test.tsx`
Expected: FAIL — `+42.5` 텍스트 없음 (배지 미구현).

- [ ] **Step 3: `SessionPnlBadge` 자식 컴포넌트 추가 + 리스트 행에 배치**

`live-session-list.tsx` import 에 추가:
```typescript
import { useDeactivateLiveSession, useLiveSessionState, useLiveSessions } from "../hooks";
import { formatRealizedPnl } from "../utils";
```

`<li>` 안 `<button>` 의 메타 `<p>` 아래(button 닫힘 직전)에 배지 삽입. 현재 button 블록(line 96-105)을:
```tsx
            <button
              type="button"
              onClick={() => onSelect?.(s)}
              className="text-left"
            >
              <span className="block font-medium">{s.symbol}</span>
              <p className="text-xs text-muted-foreground">
                {s.interval} · created: {new Date(s.created_at).toLocaleString()}
              </p>
              <SessionPnlBadge sessionId={s.id} isActive={s.is_active} />
            </button>
```

파일 하단(컴포넌트 밖)에 자식 컴포넌트 추가:
```tsx
// 세션별 실현손익 배지 — useLiveSessionState 재사용(queryKey 공유 → 추가 네트워크 0).
// 리스트는 is_active 세션만 표시하므로 항상 enabled. LESSON-004: primitive dep 전달.
function SessionPnlBadge({
  sessionId,
  isActive,
}: {
  sessionId: string;
  isActive: boolean;
}) {
  const { data: state, isLoading } = useLiveSessionState(sessionId, isActive);
  if (isLoading || !state) {
    return null;
  }
  const { text, tone } = formatRealizedPnl(state.total_realized_pnl);
  const toneClass =
    tone === "profit"
      ? "text-[color:var(--success)]"
      : tone === "loss"
        ? "text-[color:var(--destructive)]"
        : "text-muted-foreground";
  return (
    <p className="mt-1 flex items-center gap-2 font-mono text-xs">
      <span className="text-muted-foreground">PnL</span>
      <span className={toneClass}>{text}</span>
      <span className="text-muted-foreground">
        · {state.total_closed_trades} 청산
      </span>
    </p>
  );
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && pnpm test -- --run src/features/live-sessions/components/__tests__/live-session-list-pnl.test.tsx`
Expected: PASS (1 test).

- [ ] **Step 5: 기존 list 회귀 확인**

Run: `cd frontend && pnpm test -- --run src/features/live-sessions`
Expected: PASS (기존 live-session-list-state / detail 테스트 회귀 0).

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/features/live-sessions/components/live-session-list.tsx frontend/src/features/live-sessions/components/__tests__/live-session-list-pnl.test.tsx
git commit -m "feat(live-sessions): per-session PnL badge in list (mobile surfacing)"
```

---

### Task 4: 트레이딩 페이지 반응형 padding polish (pure UI)

**Files:**
- Modify: `frontend/src/app/(dashboard)/trading/page.tsx:20`

- [ ] **Step 1: 페이지 래퍼 padding 모바일 축소**

기존:
```tsx
    <div className="mx-auto max-w-[1200px] space-y-6 px-6 py-8">
```
교체 (모바일 px-4 → sm 이상 px-6, 세로도 모바일 축소):
```tsx
    <div className="mx-auto max-w-[1200px] space-y-6 px-4 py-6 sm:px-6 sm:py-8">
```

- [ ] **Step 2: 빌드/타입 확인**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 에러 0.

- [ ] **Step 3: 커밋**

```bash
git add "frontend/src/app/(dashboard)/trading/page.tsx"
git commit -m "polish(trading): responsive page padding (mobile px-4 → sm px-6)"
```

---

### Task 5: 전체 self-verify + dev smoke

- [ ] **Step 1: 전체 게이트**

Run: `cd frontend && pnpm lint && pnpm tsc --noEmit && pnpm test -- --run && pnpm build`
Expected: lint clean · tsc 0 err · 전체 vitest PASS · build 성공.

- [ ] **Step 2: dev smoke (375px viewport, CPU 모니터)**

`pnpm dev &` → sleep 20 → Playwright MCP navigate `/trading` (375px) → CPU 6 샘플 중 80% 초과 0건 확인 → `pkill -f next-server`.

- [ ] **Step 3: 결과를 signal/로그에 기록 후 Evaluator 게이트로 진행.**

## Self-Review

- **Spec coverage:** BL-356~359(이미 해소 → 검증) · PnL/세션상태 모바일 surfacing(Task 1-3) · 반응형 polish(Task 4) · 테이블 overflow(기존 완비, 검증) · flatten 버튼(defer 준수). ✅
- **Placeholder scan:** 모든 step 에 실제 코드/명령 포함. ✅
- **Type consistency:** `RealizedPnlDisplay { text, tone }` / `PnlTone` Task 1 정의 → Task 2/3 동일 사용. `useLiveSessionState(sessionId, isActive)` 기존 시그니처 일치. ✅
