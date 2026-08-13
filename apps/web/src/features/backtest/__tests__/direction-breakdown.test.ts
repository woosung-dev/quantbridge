// W4 Sprint X1+X3: 방향(long/short)별 승률·평균 PnL breakdown 단위 테스트.

import { describe, expect, it } from "vitest";

import type { TradeItem } from "../schemas";
import { computeDirectionBreakdown } from "../utils";

// schema 와 일치하는 trade fixture. pnl 등은 decimalString → number 로 transform 된 후의
// 형태를 그대로 사용 (BE → FE 파싱 직후 시점).
function mkTrade(
  overrides: Pick<TradeItem, "direction" | "pnl"> & Partial<TradeItem>,
): TradeItem {
  return {
    trade_index: 0,
    status: "closed",
    entry_time: "2026-01-01T00:00:00Z",
    exit_time: "2026-01-01T01:00:00Z",
    entry_price: 100,
    exit_price: 101,
    size: 1,
    return_pct: 0,
    fees: 0,
    ...overrides,
  };
}

describe("computeDirectionBreakdown", () => {
  it("returns zeros for empty trades", () => {
    const r = computeDirectionBreakdown([]);
    expect(r.long.count).toBe(0);
    expect(r.short.count).toBe(0);
    expect(r.long.winRate).toBe(0);
    expect(r.short.winRate).toBe(0);
    expect(r.long.avgPnl).toBe(0);
    expect(r.short.avgPnl).toBe(0);
  });

  it("computes long-only breakdown (2 wins / 1 loss)", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "long", pnl: 100 }),
      mkTrade({ direction: "long", pnl: -50 }),
      mkTrade({ direction: "long", pnl: 200 }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.count).toBe(3);
    expect(r.long.winCount).toBe(2);
    expect(r.long.winRate).toBeCloseTo(2 / 3, 4);
    expect(r.long.avgPnl).toBeCloseTo(250 / 3, 2);
    expect(r.long.totalPnl).toBe(250);
    expect(r.short.count).toBe(0);
  });

  it("computes short-only breakdown (all wins)", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "short", pnl: 150 }),
      mkTrade({ direction: "short", pnl: 150 }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.short.count).toBe(2);
    expect(r.short.winRate).toBe(1);
    expect(r.short.avgPnl).toBe(150);
    expect(r.long.count).toBe(0);
  });

  it("computes mixed breakdown", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "long", pnl: 100 }),
      mkTrade({ direction: "short", pnl: -30 }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.count).toBe(1);
    expect(r.short.count).toBe(1);
    expect(r.long.winRate).toBe(1);
    expect(r.short.winRate).toBe(0);
    expect(r.long.avgPnl).toBe(100);
    expect(r.short.avgPnl).toBe(-30);
  });

  it("handles single trade win", () => {
    const trades: TradeItem[] = [mkTrade({ direction: "long", pnl: 1 })];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.winRate).toBe(1);
    expect(r.long.avgPnl).toBe(1);
    expect(r.long.count).toBe(1);
    expect(r.long.winCount).toBe(1);
  });

  it("treats pnl=0 as non-win (strict > 0)", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "long", pnl: 0 }),
      mkTrade({ direction: "long", pnl: 10 }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.count).toBe(2);
    expect(r.long.winCount).toBe(1);
    expect(r.long.winRate).toBe(0.5);
    expect(r.long.avgPnl).toBe(5);
  });

  it("handles non-finite pnl as 0 (NaN/Infinity guard)", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "long", pnl: Number.NaN }),
      mkTrade({ direction: "long", pnl: 20 }),
    ];
    const r = computeDirectionBreakdown(trades);
    expect(r.long.count).toBe(2);
    expect(r.long.winCount).toBe(1); // NaN → 0 → not > 0
    expect(r.long.totalPnl).toBe(20);
    expect(r.long.avgPnl).toBe(10);
  });
});
