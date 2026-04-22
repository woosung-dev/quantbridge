# W5 — Backtest "재실행" 버튼

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 5 / 5
> **Branch:** `stage/x1-x3-indicator-ui`
> **TDD Mode:** **정석 TDD** — mutation 호출 + navigation 라우팅, side-effect 있음

---

## 1. Context

QuantBridge backtest 상세 페이지 (`/backtests/[id]`) 에 동일 파라미터로 다시 실행하는 버튼이 없다. dogfood 시 같은 전략/심볼/기간 조합을 반복 실행할 때 매번 `/backtests/new` 폼을 다시 채워야 함.

**기존 자산:**

- `useCreateBacktest` 훅 (`hooks.ts:164`) — 이미 존재, `BacktestForm` 에서 사용 중
- `BacktestDetail` 스키마 — `strategy_id`, `symbol`, `timeframe`, `period_start`, `period_end`, `initial_capital` 모두 포함
- shadcn/ui `Button` + sonner toast (기존 사용)

**구현 방향:** 상세 페이지 헤더에 "재실행" 버튼 → 클릭 시 현재 backtest 의 파라미터 그대로 `useCreateBacktest.mutate()` → 성공 시 `router.push("/backtests/<new-id>")` + toast.

**사용자 memory 제약 (LESSON-004)**: useEffect 사용 금지 (router.push 는 click handler 안에서 호출).

---

## 2. Acceptance Criteria

### 정량

- [ ] `backtest-detail-view.tsx` 헤더에 "재실행" 버튼 1개 (`completed | failed | cancelled` 상태에서만 활성화 — 진행 중인 backtest 는 disabled)
- [ ] 클릭 → `useCreateBacktest.mutate()` 호출 → onSuccess 시 `router.push("/backtests/<created.backtest_id>")` + sonner toast "재실행 시작"
- [ ] 버튼 컴포넌트 테스트 ≥ 3건: (a) terminal 상태에서 활성화, (b) running 상태에서 disabled, (c) 클릭 시 mutate 호출 (mock)
- [ ] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` clean

### 정성

- [ ] mutation pending 동안 버튼 비활성 + spinner (Lucide `Loader2` 또는 기존 패턴)
- [ ] 에러 시 sonner toast 로 노출 ("재실행 실패: <message>")
- [ ] 부모 컴포넌트는 `useRouter` 와 `useCreateBacktest` 만 추가 — 새 store/effect 금지
- [ ] CTA 위치: 헤더 우측 (← 목록 링크 옆) — 기존 레이아웃 응집도 유지

---

## 3. File Structure

**수정:**

- `frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx` — 헤더에 재실행 버튼 + handler

**신규:**

- `frontend/src/app/(dashboard)/backtests/_components/__tests__/rerun-button.test.tsx` — 버튼 단위 테스트
- (선택) `frontend/src/app/(dashboard)/backtests/_components/rerun-button.tsx` — 별도 컴포넌트로 분리하면 테스트 단순화

---

## 4. TDD Tasks

### T1. RerunButton 컴포넌트 분리

**Step 1 — `rerun-button.tsx` 신규 생성:**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { Loader2, RefreshCcw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useCreateBacktest } from "@/features/backtest/hooks";
import type { BacktestDetail } from "@/features/backtest/schemas";

interface RerunButtonProps {
  backtest: BacktestDetail;
  /** 진행 중(queued/running/cancelling)일 때는 false */
  isEnabled: boolean;
}

export function RerunButton({ backtest, isEnabled }: RerunButtonProps) {
  const router = useRouter();
  const create = useCreateBacktest({
    onSuccess: (created) => {
      toast.success("재실행 시작");
      router.push(`/backtests/${created.backtest_id}`);
    },
    onError: (err) => {
      toast.error(`재실행 실패: ${err.message}`);
    },
  });

  const handleClick = () => {
    create.mutate({
      strategy_id: backtest.strategy_id,
      symbol: backtest.symbol,
      timeframe: backtest.timeframe as never, // schema enum guard
      period_start: backtest.period_start,
      period_end: backtest.period_end,
      initial_capital: Number(backtest.initial_capital),
    });
  };

  const isPending = create.isPending;
  const isDisabled = !isEnabled || isPending;

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleClick}
      disabled={isDisabled}
      aria-label="동일 파라미터로 재실행"
    >
      {isPending ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <RefreshCcw className="mr-2 h-4 w-4" />
      )}
      재실행
    </Button>
  );
}
```

**Step 2 — 테스트 신규:**

```tsx
// frontend/src/app/(dashboard)/backtests/_components/__tests__/rerun-button.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BacktestDetail } from "@/features/backtest/schemas";
import { RerunButton } from "../rerun-button";

const mockMutate = vi.fn();
const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: (opts: {
    onSuccess?: (r: { backtest_id: string }) => void;
  }) => ({
    mutate: (...args: unknown[]) => {
      mockMutate(...args);
      opts.onSuccess?.({ backtest_id: "new-id" });
    },
    isPending: false,
  }),
}));

const BACKTEST: BacktestDetail = {
  id: "old-id",
  strategy_id: "11111111-1111-1111-1111-111111111111",
  symbol: "BTC/USDT",
  timeframe: "1h",
  period_start: "2026-01-01T00:00:00Z",
  period_end: "2026-02-01T00:00:00Z",
  status: "completed",
  created_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-02-01T00:00:00Z",
  initial_capital: "10000",
  metrics: null,
  equity_curve: null,
  error: null,
} as BacktestDetail;

describe("RerunButton", () => {
  it("is enabled in terminal state", () => {
    render(<RerunButton backtest={BACKTEST} isEnabled={true} />);
    const btn = screen.getByRole("button", { name: /재실행/ });
    expect(btn).not.toBeDisabled();
  });

  it("is disabled when isEnabled=false (running etc.)", () => {
    render(<RerunButton backtest={BACKTEST} isEnabled={false} />);
    expect(screen.getByRole("button", { name: /재실행/ })).toBeDisabled();
  });

  it("triggers mutate with the same params and navigates on success", () => {
    mockMutate.mockClear();
    mockPush.mockClear();
    render(<RerunButton backtest={BACKTEST} isEnabled={true} />);
    fireEvent.click(screen.getByRole("button", { name: /재실행/ }));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        strategy_id: BACKTEST.strategy_id,
        symbol: BACKTEST.symbol,
        timeframe: BACKTEST.timeframe,
        period_start: BACKTEST.period_start,
        period_end: BACKTEST.period_end,
        initial_capital: 10000,
      }),
    );
    expect(mockPush).toHaveBeenCalledWith("/backtests/new-id");
  });
});
```

**Step 3 — 실패 확인:**

```bash
cd frontend && pnpm test -- --run rerun-button
```

Expected: FAIL — `RerunButton` import 불가 (또는 컴포넌트 없음).

### T2. BacktestDetailView 헤더에 통합

**Step 4 — `backtest-detail-view.tsx` 수정** (헤더 부분만):

```tsx
import { RerunButton } from "./rerun-button";

// ... in component body:
const TERMINAL = (s?: string) =>
  s === "completed" || s === "failed" || s === "cancelled";

// header JSX (existing):
<header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
  <div>
    <div className="flex items-center gap-2">
      <h1 className="font-display text-2xl font-bold">
        {bt.symbol} · {bt.timeframe}
      </h1>
      <BacktestStatusBadge status={effectiveStatus} />
    </div>
    <p className="text-sm text-muted-foreground">
      {formatDate(bt.period_start)} → {formatDate(bt.period_end)}
    </p>
  </div>
  <div className="flex items-center gap-3">
    <RerunButton backtest={bt} isEnabled={TERMINAL(effectiveStatus)} />
    <Link
      href="/backtests"
      className="text-sm text-muted-foreground hover:text-foreground"
    >
      ← 목록
    </Link>
  </div>
</header>;
```

**Step 5 — 테스트 녹색 + 회귀 검증:**

```bash
cd frontend && pnpm test -- --run
cd frontend && pnpm tsc --noEmit
cd frontend && pnpm lint
```

Expected: 모두 PASS / clean.

### T3. Worker-side codex review

```bash
codex exec --sandbox read-only "Review git diff for RerunButton + BacktestDetailView integration. Check: (1) no useEffect added per LESSON-004, (2) router.push only inside click handler, (3) toast on both success/error, (4) disabled state covers running/queued/cancelling, (5) initial_capital string→number conversion safe (decimalString in schema), (6) hooks.ts unchanged (reuse useCreateBacktest)."
```

출력 → `docs/superpowers/reviews/2026-04-23-x1x3-w5-codex-self.md`.

### T4. Stage push

```bash
git add frontend/src/app/\(dashboard\)/backtests/_components/rerun-button.tsx frontend/src/app/\(dashboard\)/backtests/_components/__tests__/rerun-button.test.tsx frontend/src/app/\(dashboard\)/backtests/_components/backtest-detail-view.tsx docs/superpowers/reviews/2026-04-23-x1x3-w5-codex-self.md
git commit -m "feat(backtest): re-run button in detail header (W5)"
git push origin stage/x1-x3-indicator-ui
```

---

## 5. Edge Cases 필수 커버

- 진행 중 (queued/running/cancelling) → 버튼 disabled + tooltip 가능 (선택)
- 완료/실패/취소 (terminal) → 활성화
- 클릭 후 mutation pending → spinner + disabled
- mutation 성공 → router.push + toast.success → 새 detail 페이지에서 자동 폴링 시작
- mutation 실패 → toast.error, 버튼 다시 활성화
- BacktestDetail.initial_capital 이 매우 큰 string ("99999999.99999999") → Number() 변환 시 precision 손실 가능 — 단, schema 가 `.positive().refine(Number.isFinite)` 으로 finite 보장
- hooks.ts 의 `useCreateBacktest` 시그니처 변경 시 → 컴파일 에러로 즉각 노출 (no silent fallback)

---

## 6. 3-Evaluator 공용 질문

1. AC 정량 (3 unit tests + 헤더 integration + tsc/lint) 실제 달성?
2. spurious PASS: mock 이 너무 헐겁지 않은가? (mutate args 검증 포함됨)
3. TDD: FAIL → PASS 전환 evidence?
4. 회귀: 기존 헤더 (← 목록) / Tabs / 상태 분기 변경?
5. edge: terminal / running / pending mutation / error toast / 큰 initial_capital?
6. memory 규칙 (LESSON-004): useEffect 추가 없음? router.push 가 effect 안에서 호출되지 않음?
7. GO / GO_WITH_FIX / MAJOR_REVISION / NO_GO + 신뢰도 1-10

---

## 7. Verification

```bash
cd frontend && pnpm test -- --run
cd frontend && pnpm tsc --noEmit
cd frontend && pnpm lint
# Live: /backtests/<completed-id> → 헤더 "재실행" 클릭 → 새 backtest 페이지로 navigate
```
