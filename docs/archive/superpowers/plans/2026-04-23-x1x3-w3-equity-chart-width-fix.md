# W3 — EquityChart `width(-1)` Warning 제거

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 3 / 5
> **Branch:** `stage/x1-x3-indicator-ui`
> **TDD Mode:** **test + impl 동시 허용** — pure UI 렌더링 (no hooks/state/effect 로직 변경)

---

## 1. Context

QuantBridge 는 Next.js 16 FE + FastAPI BE 의 퀀트 플랫폼. backtest 상세 페이지 (`/backtests/[id]`) 는 `recharts` 기반 `EquityChart` 를 사용한다.

**현재 공백**: 브라우저 콘솔에 `Warning: width(-1) and height(256) ... ResponsiveContainer` 가 뜬다. 원인은 `ResponsiveContainer` 가 부모 `div` 의 width=0 상태에서 첫 렌더링되는 시점. 이후 resize 로 복구되나 경고가 남음.

**사용자 memory 제약 (LESSON-004)**: useEffect + RQ/Zustand unstable dep 금지. ResizeObserver 사용 시 stable ref 로 한정.

---

## 2. Acceptance Criteria

### 정량

- [ ] Playwright 시나리오: `/backtests/<id>` 로 직접 navigate → 첫 페인트 시점부터 console warning "width(-1)" **0건**
- [ ] FE vitest: `EquityChart` 렌더링 테스트 ≥ 1건 (mount 후 컨테이너 width 0 가정에서 crash 없음)
- [ ] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` 모두 clean
- [ ] 기존 equity 데이터 렌더링 회귀 0 (기존 테스트 PASS)

### 정성

- [ ] ResponsiveContainer 를 감싸는 wrapper 에 **명시적 width** (예: `w-full` + inline `style={{ width: "100%" }}`) 또는 mount 후 조건부 렌더링
- [ ] useEffect 의존 배열에 RQ/Zustand 불안정 참조 금지 — primitive dep 만
- [ ] shadcn/ui v4 + Tailwind v4 관례 유지 (inline style 은 최소화, className 우선)

---

## 3. File Structure

**수정:**

- `frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx` — ResponsiveContainer 안정화

**신규:**

- `frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx` — mount 테스트

---

## 4. TDD Tasks

### T1. Failing test (mount 시 crash/warning 가드)

**Step 1 — vitest 테스트 생성:**

```tsx
// frontend/src/app/(dashboard)/backtests/_components/__tests__/equity-chart.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { EquityPoint } from "@/features/backtest/schemas";
import { EquityChart } from "../equity-chart";

const POINTS: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 10200 },
  { timestamp: "2026-01-03T00:00:00Z", value: 10500 },
];

describe("EquityChart", () => {
  it("renders empty state when no points", () => {
    render(<EquityChart points={[]} />);
    expect(screen.getByText(/Equity 데이터가 없습니다/)).toBeInTheDocument();
  });

  it("mounts without recharts width(-1) warning", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<EquityChart points={POINTS} />);

    const w = warnSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    const e = errSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && /width\(-1\)/.test(a)),
    );
    expect(w || e).toBe(false);

    warnSpy.mockRestore();
    errSpy.mockRestore();
  });
});
```

**Step 2 — 실패 확인 (warning 여부는 환경 의존적이므로 최소한 render crash 없음을 검증):**

```bash
cd frontend && pnpm test -- --run equity-chart.test
```

Expected: 가능하면 FAIL 또는 render crash; 적어도 smoke 형태로 돌아감 (완전 FAIL 이 아니어도 mount 보장).

### T2. ResponsiveContainer 안정화 구현

**Step 3 — `equity-chart.tsx` 수정** (핵심 아이디어: min-width inline + 부모 컨테이너에 `w-full` 보장 + mount gate):

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { EquityPoint } from "@/features/backtest/schemas";
import {
  downsampleEquity,
  formatCurrency,
  formatDate,
} from "@/features/backtest/utils";

interface EquityChartProps {
  points: readonly EquityPoint[];
  maxPoints?: number;
}

interface ChartDatum {
  ts: number;
  value: number;
  label: string;
}

export function EquityChart({ points, maxPoints = 1000 }: EquityChartProps) {
  const data = useMemo<ChartDatum[]>(() => {
    const sampled = downsampleEquity(points, maxPoints);
    return sampled.map((p) => ({
      ts: new Date(p.timestamp).getTime(),
      value: p.value,
      label: formatDate(p.timestamp),
    }));
  }, [points, maxPoints]);

  // mount gate — ResponsiveContainer 가 width=0 로 첫 렌더링되는 것을 회피.
  // CSR only 환경에서만 실제 차트 마운트.
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []); // primitive-only dep array — LESSON-004 준수

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Equity 데이터가 없습니다
      </div>
    );
  }

  if (!isMounted) {
    return <div className="h-64 w-full" aria-busy="true" />;
  }

  return (
    <div className="h-64 w-full" style={{ minWidth: 0 }}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart
          data={data}
          margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={32} />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => formatCurrency(v, 0)}
            width={80}
          />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? formatCurrency(value) : String(value)
            }
            labelFormatter={(label) => (label == null ? "" : String(label))}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="currentColor"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**근거:**

- `useState(false) + useEffect(() => setIsMounted(true), [])` 패턴은 Next.js SSR hydration 이후에만 ResponsiveContainer 를 mount → 첫 페인트 시 width=0 회피
- primitive-only dep `[]` → LESSON-004 위반 없음
- `minWidth={0}` (recharts prop) 는 defensive 하게 추가
- `aria-busy="true"` placeholder 는 동일 크기 (`h-64 w-full`) 를 유지해 layout shift 방지

**Step 4 — 녹색 확인:**

```bash
cd frontend && pnpm test -- --run equity-chart.test
cd frontend && pnpm tsc --noEmit
cd frontend && pnpm lint
```

Expected: 모두 clean.

### T3. Playwright live smoke (선택 — 조건 충족 시)

FE worker 환경에서 dev 서버 mount 가능하면:

```bash
cd frontend && pnpm dev &
# 백그라운드 3~5초 대기 후
# Playwright MCP 로 navigate → console 모니터
```

Worker 환경에서 `pnpm dev` 가 안 되면 이 step 스킵 가능. Phase 4 합류 단계에서 orchestrator 가 Playwright 로 최종 검증.

### T4. Worker-side codex review 1-pass

```bash
codex exec --sandbox read-only "Review git diff for equity-chart width(-1) fix. Check: (1) useEffect dep array is primitive-only per LESSON-004, (2) no RQ/Zustand unstable ref in dep, (3) SSR-safe (no window access before mount), (4) layout shift minimized (placeholder same size), (5) recharts ResponsiveContainer usage idiomatic."
```

출력 → `docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md`.

### T5. Stage push

```bash
git add frontend/src/app/\(dashboard\)/backtests/_components/equity-chart.tsx frontend/src/app/\(dashboard\)/backtests/_components/__tests__/equity-chart.test.tsx docs/superpowers/reviews/2026-04-23-x1x3-w3-codex-self.md
git commit -m "fix(backtest): EquityChart width(-1) warning via mount gate (W3)"
git push origin stage/x1-x3-indicator-ui
```

---

## 5. Edge Cases 필수 커버

- data.length === 0 → 기존 "Equity 데이터가 없습니다" 분기 유지
- SSR pre-hydration → placeholder div (aria-busy) 만 렌더, ResponsiveContainer 금지
- props.points 변경 (이미 resize 완료 후 재-render) → data useMemo + mount gate 유지
- 매우 큰 points (maxPoints=1000 초과) → downsampleEquity 로 샘플링 (기존 로직)

---

## 6. 3-Evaluator 공용 질문

1. AC 정량 (warning 0건 + vitest + tsc/lint) 실제 달성?
2. spurious PASS: console.warn spy 가 실제 warning 을 잡을 수 있는 환경인가? (jsdom 에서 recharts 가 warning 을 emit 하는지 확인)
3. TDD: 실패 테스트 → 녹색 전환 evidence?
4. 회귀: 기존 equity 데이터 렌더링 / downsampleEquity / Tooltip 포매팅 semantic drift?
5. edge: 0 data / SSR hydration / 매우 많은 points / resize 후 re-render?
6. **LESSON-004** 위반: useEffect dep 에 unstable RQ/Zustand 참조 없음?
7. GO / GO_WITH_FIX / MAJOR_REVISION / NO_GO + 신뢰도 1-10

---

## 7. Verification

```bash
cd frontend && pnpm test -- --run
cd frontend && pnpm tsc --noEmit
cd frontend && pnpm lint
# Live: pnpm dev → /backtests/<id> console open → warning 0건
```
