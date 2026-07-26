# W4 — Trade Analysis 방향별 승률/평균 PnL Breakdown

> **Session:** Sprint X1+X3, 2026-04-23 | **Worker:** 4 / 5
> **Branch:** `stage/x1-x3-indicator-ui`
> **TDD Mode:** **정석 TDD** — 계산 로직 (승률/평균) 을 포함하므로 unit 테스트 필수

---

## 1. Context

QuantBridge FE 의 Backtest 상세 페이지 "거래 분석" 탭 (`trade-analysis.tsx`, 136 lines) 은 전체 집계 (num_trades, win_rate, long_count, short_count, avg_win, avg_loss) 만 표시. 방향별 (롱/숏) 승률과 평균 PnL 을 분리한 정보가 없어 "롱이 강한지 숏이 강한지" 를 판별하기 어렵다.

**SL/TP breakdown 은 scope 에서 제외**: 현재 `TradeItem` 스키마 (backend) 에 `exit_reason` 필드가 없어 SL/TP 구분 정보가 없음. BE 스키마 확장은 별도 sprint follow-up. **이번 sprint 는 방향별 집계 + trades 데이터를 활용한 승률 breakdown 에 한정.**

**사용자 memory 제약 (LESSON-004)**: trades 데이터는 이미 `useBacktestTrades` 훅으로 fetch 됨. 새 계산 로직은 pure function + memoized 로 구성 — RQ 결과를 useEffect dep 로 쓰지 말 것.

---

## 2. Acceptance Criteria

### 정량

- [ ] 신규 유틸 `computeDirectionBreakdown(trades)` 단위 테스트 ≥ 5건: (a) 전체 롱 승리, (b) 전체 숏 승리, (c) 혼합, (d) 빈 배열, (e) 단일 trade
- [ ] `trade-analysis.tsx` 컴포넌트 테스트 ≥ 2건: (a) 롱/숏 breakdown section 렌더링, (b) 데이터 없을 때 기존 fallback 유지
- [ ] FE `pnpm test -- --run`, `pnpm tsc --noEmit`, `pnpm lint` clean
- [ ] 기존 TradeAnalysis 테스트 PASS (회귀 0)

### 정성

- [ ] 방향별 승률 계산: `win_count_long / total_long`, `win_count_short / total_short`
- [ ] 방향별 평균 PnL: `sum(pnl) / count` (Decimal 대응 — `Number(trade.pnl)` 변환 시 precision 손실 없도록 trade.pnl 이 string 임을 인지)
- [ ] 기존 "방향 분포" section 은 보존하되, 하단에 "방향별 성과" 새 section 추가
- [ ] `TradeAnalysisProps` 시그니처에 `trades?: TradeItem[]` 추가 (optional — 없으면 기존 동작)
- [ ] 부모 컴포넌트 (`backtest-detail-view.tsx`) 는 `trades.data?.items` 를 이미 fetch 중이므로 prop 전달만 추가

---

## 3. File Structure

**수정:**

- `frontend/src/app/(dashboard)/backtests/_components/trade-analysis.tsx` — breakdown section 추가
- `frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx` — `trades={trades.data?.items}` prop 전달 (1 라인)
- `frontend/src/features/backtest/utils.ts` — `computeDirectionBreakdown()` 유틸 추가

**신규:**

- `frontend/src/features/backtest/__tests__/direction-breakdown.test.ts` — util 단위 테스트
- `frontend/src/app/(dashboard)/backtests/_components/__tests__/trade-analysis.test.tsx` — 컴포넌트 테스트

---

## 4. TDD Tasks

### T1. Failing util test

**Step 1 — `direction-breakdown.test.ts`:**

```ts
import { describe, expect, it } from "vitest";

import type { TradeItem } from "@/features/backtest/schemas";
import { computeDirectionBreakdown } from "@/features/backtest/utils";

function mkTrade(
  overrides: Partial<TradeItem> & Pick<TradeItem, "direction" | "pnl">,
): TradeItem {
  return {
    trade_index: 0,
    direction: overrides.direction,
    status: "closed",
    entry_time: "2026-01-01T00:00:00Z",
    exit_time: "2026-01-01T01:00:00Z",
    entry_price: "100",
    exit_price: "101",
    size: "1",
    pnl: overrides.pnl,
    return_pct: "0",
    fees: "0",
    ...overrides,
  } as TradeItem;
}

describe("computeDirectionBreakdown", () => {
  it("returns zeros for empty trades", () => {
    const r = computeDirectionBreakdown([]);
    expect(r.long.count).toBe(0);
    expect(r.short.count).toBe(0);
    expect(r.long.winRate).toBe(0);
  });

  it("computes long-only breakdown", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "long", pnl: "100" }),
      mkTrade({ direction: "long", pnl: "-50" }),
      mkTrade({ direction: "long", pnl: "200" }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.count).toBe(3);
    expect(r.long.winCount).toBe(2);
    expect(r.long.winRate).toBeCloseTo(2 / 3, 4);
    expect(r.long.avgPnl).toBeCloseTo(250 / 3, 2);
    expect(r.short.count).toBe(0);
  });

  it("computes short-only breakdown", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "short", pnl: "150" }),
      mkTrade({ direction: "short", pnl: "150" }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.short.count).toBe(2);
    expect(r.short.winRate).toBe(1);
    expect(r.short.avgPnl).toBe(150);
  });

  it("computes mixed breakdown", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "long", pnl: "100" }),
      mkTrade({ direction: "short", pnl: "-30" }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.count).toBe(1);
    expect(r.short.count).toBe(1);
    expect(r.long.winRate).toBe(1);
    expect(r.short.winRate).toBe(0);
  });

  it("handles single trade win", () => {
    const trades: TradeItem[] = [mkTrade({ direction: "long", pnl: "1" })];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.winRate).toBe(1);
    expect(r.long.avgPnl).toBe(1);
  });
});
```

**Step 2 — 실패 확인:**

```bash
cd frontend && pnpm test -- --run direction-breakdown
```

Expected: FAIL — `computeDirectionBreakdown` import 불가.

### T2. Util 구현

**Step 3 — `frontend/src/features/backtest/utils.ts` 하단에 추가:**

```ts
import type { TradeItem } from "./schemas";

export interface DirectionStats {
  count: number;
  winCount: number;
  winRate: number; // 0..1
  avgPnl: number; // 소수점 2 자리 표시용 number
  totalPnl: number;
}

export interface DirectionBreakdown {
  long: DirectionStats;
  short: DirectionStats;
}

function emptyStats(): DirectionStats {
  return { count: 0, winCount: 0, winRate: 0, avgPnl: 0, totalPnl: 0 };
}

/**
 * 거래 목록을 방향(long/short)별로 집계.
 *
 * - 승리 판정: `Number(trade.pnl) > 0`
 * - pnl / return_pct 은 서버에서 string 으로 직렬화되므로 parse 시 Number
 * - 빈 배열 / 단일 방향 / 혼합 모두 안전.
 */
export function computeDirectionBreakdown(
  trades: readonly TradeItem[],
): DirectionBreakdown {
  const long = emptyStats();
  const short = emptyStats();

  for (const t of trades) {
    const bucket = t.direction === "long" ? long : short;
    const pnl = Number(t.pnl) || 0;
    bucket.count += 1;
    bucket.totalPnl += pnl;
    if (pnl > 0) bucket.winCount += 1;
  }

  long.winRate = long.count > 0 ? long.winCount / long.count : 0;
  short.winRate = short.count > 0 ? short.winCount / short.count : 0;
  long.avgPnl = long.count > 0 ? long.totalPnl / long.count : 0;
  short.avgPnl = short.count > 0 ? short.totalPnl / short.count : 0;

  return { long, short };
}
```

**Step 4 — util 테스트 녹색:**

```bash
cd frontend && pnpm test -- --run direction-breakdown
```

Expected: 5/5 PASS.

### T3. TradeAnalysis 컴포넌트 확장

**Step 5 — `trade-analysis.tsx` 수정:**

```tsx
"use client";

import { useMemo } from "react";

import { cn } from "@/lib/utils";
import {
  computeDirectionBreakdown,
  type DirectionBreakdown,
} from "@/features/backtest/utils";
import type {
  BacktestMetricsOut,
  TradeItem,
} from "@/features/backtest/schemas";

interface TradeAnalysisProps {
  metrics: BacktestMetricsOut;
  trades?: readonly TradeItem[];
}

export function TradeAnalysis({ metrics, trades }: TradeAnalysisProps) {
  const { num_trades, win_rate, long_count, short_count, avg_win, avg_loss } =
    metrics;
  const winCount = Math.round(win_rate * num_trades);
  const lossCount = num_trades - winCount;
  const winPct = num_trades > 0 ? (winCount / num_trades) * 100 : 0;
  const maxAbsAvg = Math.max(Math.abs(avg_win ?? 0), Math.abs(avg_loss ?? 0));

  // 방향별 breakdown — trades 가 있을 때만 계산 (useMemo — pure)
  const breakdown = useMemo<DirectionBreakdown | null>(() => {
    if (!trades || trades.length === 0) return null;
    return computeDirectionBreakdown(trades);
  }, [trades]);

  return (
    <div className="space-y-8">
      {/* 방향 분포 (기존) */}
      <section>
        <SectionTitle>방향 분포</SectionTitle>
        <div className="flex flex-wrap gap-3">
          <DirectionBadge label="롱" value={long_count} />
          <DirectionBadge label="숏" value={short_count} />
          <DirectionBadge label="전체" value={num_trades} />
        </div>
      </section>

      {/* 방향별 성과 (신규) */}
      {breakdown && (breakdown.long.count > 0 || breakdown.short.count > 0) && (
        <section>
          <SectionTitle>방향별 성과</SectionTitle>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <DirectionStatsCard
              label="롱"
              stats={breakdown.long}
              color="green"
            />
            <DirectionStatsCard
              label="숏"
              stats={breakdown.short}
              color="red"
            />
          </div>
        </section>
      )}

      {/* 승/패 비율 (기존) */}
      <section>
        <SectionTitle>승/패 비율</SectionTitle>
        <div className="flex items-center gap-3 text-sm">
          <span className="w-14 text-right font-medium text-green-500">
            {winCount}건
          </span>
          <div className="h-4 flex-1 overflow-hidden rounded-full bg-[color:var(--muted)]">
            <div
              className="h-full rounded-full bg-green-500 transition-all duration-300"
              style={{ width: `${winPct}%` }}
            />
          </div>
          <span className="w-14 font-medium text-red-500">{lossCount}건</span>
        </div>
        <p className="mt-1 text-center text-xs text-[color:var(--text-muted)]">
          승률 {winPct.toFixed(1)}% · 패률 {(100 - winPct).toFixed(1)}%
        </p>
      </section>

      {/* 평균 수익 vs 손실 (기존) */}
      {avg_win != null && avg_loss != null ? (
        <section>
          <SectionTitle>평균 수익 vs 손실</SectionTitle>
          <div className="space-y-3">
            <RatioBar
              label="평균 수익"
              value={avg_win}
              max={maxAbsAvg}
              colorClass="bg-green-500"
            />
            <RatioBar
              label="평균 손실"
              value={Math.abs(avg_loss)}
              max={maxAbsAvg}
              colorClass="bg-red-500"
            />
          </div>
        </section>
      ) : (
        <p className="text-sm text-[color:var(--text-muted)]">
          평균 수익/손실 데이터가 없습니다 (이전 버전 백테스트).
        </p>
      )}
    </div>
  );
}

// ---- 신규 서브컴포넌트 -------------------------------------------------

import type { DirectionStats } from "@/features/backtest/utils";

function DirectionStatsCard({
  label,
  stats,
  color,
}: {
  label: string;
  stats: DirectionStats;
  color: "green" | "red";
}) {
  const colorClass = color === "green" ? "text-green-500" : "text-red-500";
  if (stats.count === 0) {
    return (
      <div className="rounded-md border border-[color:var(--border)] px-4 py-3">
        <p className={cn("text-xs font-semibold uppercase", colorClass)}>
          {label}
        </p>
        <p className="mt-1 text-sm text-[color:var(--text-muted)]">거래 없음</p>
      </div>
    );
  }
  return (
    <div className="rounded-md border border-[color:var(--border)] px-4 py-3">
      <p className={cn("text-xs font-semibold uppercase", colorClass)}>
        {label} · {stats.count}건
      </p>
      <dl className="mt-2 space-y-1 text-sm">
        <div className="flex justify-between">
          <dt className="text-[color:var(--text-muted)]">승률</dt>
          <dd className="font-mono">{(stats.winRate * 100).toFixed(1)}%</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-[color:var(--text-muted)]">평균 PnL</dt>
          <dd className="font-mono">
            {stats.avgPnl >= 0 ? "+" : ""}
            {stats.avgPnl.toFixed(2)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

// (기존 SectionTitle / DirectionBadge / RatioBar 그대로 유지)
```

**Step 6 — 부모 컴포넌트 1 라인 수정:**

`backtest-detail-view.tsx` 의 TradeAnalysis 사용 부분:

```tsx
<TabsContent value="analysis" className="mt-4">
  <TradeAnalysis metrics={bt.metrics} trades={trades.data?.items} />
</TabsContent>
```

### T4. 컴포넌트 테스트

**Step 7 — `trade-analysis.test.tsx`:**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestMetricsOut,
  TradeItem,
} from "@/features/backtest/schemas";
import { TradeAnalysis } from "../trade-analysis";

const METRICS: BacktestMetricsOut = {
  total_return_pct: 0.1,
  sharpe_ratio: 1.5,
  max_drawdown_pct: -0.05,
  num_trades: 3,
  win_rate: 0.667,
  long_count: 2,
  short_count: 1,
  avg_win: 100,
  avg_loss: -30,
} as unknown as BacktestMetricsOut;

describe("TradeAnalysis", () => {
  it("renders existing sections without trades", () => {
    render(<TradeAnalysis metrics={METRICS} />);
    expect(screen.getByText("방향 분포")).toBeInTheDocument();
    expect(screen.getByText("승/패 비율")).toBeInTheDocument();
    expect(screen.queryByText("방향별 성과")).not.toBeInTheDocument();
  });

  it("renders direction breakdown when trades provided", () => {
    const trades: TradeItem[] = [
      {
        trade_index: 0,
        direction: "long",
        status: "closed",
        entry_time: "2026-01-01T00:00:00Z",
        exit_time: "2026-01-01T01:00:00Z",
        entry_price: "100",
        exit_price: "110",
        size: "1",
        pnl: "10",
        return_pct: "0.1",
        fees: "0",
      } as TradeItem,
    ];
    render(<TradeAnalysis metrics={METRICS} trades={trades} />);
    expect(screen.getByText("방향별 성과")).toBeInTheDocument();
    expect(screen.getByText(/롱 · 1건/)).toBeInTheDocument();
  });
});
```

**Step 8 — 녹색 확인:**

```bash
cd frontend && pnpm test -- --run trade-analysis direction-breakdown
cd frontend && pnpm tsc --noEmit && pnpm lint
```

Expected: 모두 PASS/clean.

### T5. Worker-side codex review

```bash
codex exec --sandbox read-only "Review git diff for TradeAnalysis direction breakdown. Check: (1) computeDirectionBreakdown pure + no side effects, (2) TradeAnalysis trades prop optional backward-compat, (3) useMemo dep is [trades] stable ref — LESSON-004 compliant, (4) TypeScript strict: no any, (5) Tailwind v4 class conventions, (6) empty/single/mixed edge cases covered."
```

출력 → `docs/superpowers/reviews/2026-04-23-x1x3-w4-codex-self.md`.

### T6. Stage push

```bash
git add frontend/src/features/backtest/utils.ts frontend/src/features/backtest/__tests__/direction-breakdown.test.ts frontend/src/app/\(dashboard\)/backtests/_components/trade-analysis.tsx frontend/src/app/\(dashboard\)/backtests/_components/__tests__/trade-analysis.test.tsx frontend/src/app/\(dashboard\)/backtests/_components/backtest-detail-view.tsx docs/superpowers/reviews/2026-04-23-x1x3-w4-codex-self.md
git commit -m "feat(backtest): Trade Analysis direction breakdown (long/short win rate + avg PnL) (W4)"
git push origin stage/x1-x3-indicator-ui
```

---

## 5. Edge Cases 필수 커버

- 빈 trades → 기존 동작 (breakdown section 미렌더)
- 단일 trade → 해당 방향만 렌더, 반대 방향은 "거래 없음"
- trade.pnl 이 "0" (손익 0) → winCount 에 포함 안 됨 (pnl > 0 엄격)
- trade.pnl 이 NaN 문자열 → `Number() || 0` 으로 0 처리
- trades prop 이 undefined (hooks.ts enabled:false 상태) → 기존 동작 유지
- LESSON-004: useMemo dep=[trades] 만, RQ result object 를 직접 dep 로 쓰지 않음

---

## 6. 3-Evaluator 공용 질문

1. AC 정량 (5 util + 2 component + tsc/lint) 실제 달성?
2. spurious PASS: mkTrade 헬퍼가 실제 schema 와 일치하는가?
3. TDD: FAIL → PASS 전환 evidence?
4. 회귀: 기존 TradeAnalysis 섹션 (방향 분포 / 승패 / 평균) 레이아웃/동작 변경?
5. edge: 빈/단일/혼합/NaN/undefined?
6. memory 규칙 (LESSON-004): trades 를 useEffect dep 로 쓰지 않음, useMemo 만?
7. GO / GO_WITH_FIX / MAJOR_REVISION / NO_GO + 신뢰도 1-10

---

## 7. Verification

```bash
cd frontend && pnpm test -- --run
cd frontend && pnpm tsc --noEmit
cd frontend && pnpm lint
# Live: /backtests/<completed-id> → "거래 분석" 탭 → 방향별 성과 section 확인
```
