import { describe, expect, it } from "vitest";

import type { TradeItem } from "@/features/backtest/schemas";

import {
  __test_only__,
  MARKER_LIMIT,
  deriveTradeMarkers,
} from "../marker-layer";

const { formatPriceShort, formatReturnPctShort, COLORS } = __test_only__;

// --- fixtures -------------------------------------------------------------

function makeTrade(overrides: Partial<TradeItem> = {}): TradeItem {
  return {
    trade_index: 1,
    direction: "long",
    status: "closed",
    entry_time: "2026-01-01T12:00:00Z",
    exit_time: "2026-01-01T18:00:00Z",
    entry_price: 100,
    exit_price: 110,
    size: 1,
    pnl: 10,
    return_pct: 0.1,
    fees: 0.1,
    ...overrides,
  };
}

// --- deriveTradeMarkers ---------------------------------------------------

describe("deriveTradeMarkers (Sprint 32-C BL-171)", () => {
  it("returns empty array for undefined / empty trades", () => {
    expect(deriveTradeMarkers(undefined)).toEqual([]);
    expect(deriveTradeMarkers([])).toEqual([]);
  });

  it("emits entry + exit markers for closed long trade", () => {
    const trade = makeTrade({
      direction: "long",
      status: "closed",
      entry_price: 100,
      pnl: 10,
      return_pct: 0.1,
    });

    const markers = deriveTradeMarkers([trade]);
    expect(markers).toHaveLength(2);

    const entry = markers[0]!;
    const exit = markers[1]!;

    // entry = arrowUp green, position belowBar.
    expect(entry.shape).toBe("arrowUp");
    expect(entry.color).toBe(COLORS.longEntry);
    expect(entry.position).toBe("belowBar");
    expect(entry.text).toBe("L $100.00");

    // exit = circle, win → green, position inBar.
    expect(exit.shape).toBe("circle");
    expect(exit.color).toBe(COLORS.longExitWin);
    expect(exit.position).toBe("inBar");
    expect(exit.text).toBe("+10.00%");
  });

  it("emits entry + exit markers for closed short trade", () => {
    const trade = makeTrade({
      direction: "short",
      status: "closed",
      entry_price: 200,
      pnl: 5,
      return_pct: 0.025,
    });

    const markers = deriveTradeMarkers([trade]);
    expect(markers).toHaveLength(2);

    const entry = markers[0]!;
    const exit = markers[1]!;

    // entry = arrowDown red, position aboveBar.
    expect(entry.shape).toBe("arrowDown");
    expect(entry.color).toBe(COLORS.shortEntry);
    expect(entry.position).toBe("aboveBar");
    expect(entry.text).toBe("S $200.00");

    // exit = circle, win → green, position inBar.
    expect(exit.shape).toBe("circle");
    expect(exit.color).toBe(COLORS.shortExitWin);
    expect(exit.text).toBe("+2.50%");
  });

  it("colors exit red when PnL <= 0 (loss case)", () => {
    const longLoss = makeTrade({
      direction: "long",
      pnl: -5,
      return_pct: -0.05,
    });
    const shortLoss = makeTrade({
      direction: "short",
      pnl: -5,
      return_pct: -0.05,
    });

    const longMarkers = deriveTradeMarkers([longLoss]);
    const shortMarkers = deriveTradeMarkers([shortLoss]);

    expect(longMarkers[1]!.color).toBe(COLORS.longExitLoss);
    expect(shortMarkers[1]!.color).toBe(COLORS.shortExitLoss);

    // text 부호 = "-" 시작.
    expect(longMarkers[1]!.text).toBe("-5.00%");
    expect(shortMarkers[1]!.text).toBe("-5.00%");
  });

  it("emits only entry marker for open trade (no exit)", () => {
    const open = makeTrade({
      status: "open",
      exit_time: null,
      exit_price: null,
    });

    const markers = deriveTradeMarkers([open]);
    expect(markers).toHaveLength(1);
    expect(markers[0]!.shape).toBe("arrowUp");
  });

  it("caps markers at MARKER_LIMIT", () => {
    // MARKER_LIMIT = 200. 250 closed trades → 200 trades * 2 markers (entry+exit) = 400.
    const trades: TradeItem[] = [];
    for (let i = 0; i < 250; i += 1) {
      trades.push(
        makeTrade({
          trade_index: i,
          entry_time: new Date(2026, 0, 1, i % 24).toISOString(),
          exit_time: new Date(2026, 0, 1, (i % 24) + 1).toISOString(),
        }),
      );
    }
    const markers = deriveTradeMarkers(trades);
    expect(markers.length).toBe(MARKER_LIMIT * 2);
  });

  it("uses entry_price formatting (BTC large vs small)", () => {
    const btc = makeTrade({ direction: "long", entry_price: 67890 });
    const small = makeTrade({ direction: "long", entry_price: 0.5432 });

    const btcMarkers = deriveTradeMarkers([btc]);
    const smallMarkers = deriveTradeMarkers([small]);

    expect(btcMarkers[0]!.text).toBe("L $67,890");
    expect(smallMarkers[0]!.text).toBe("L $0.5432");
  });
});

// --- format helpers (sanity) ----------------------------------------------

describe("formatPriceShort (Sprint 32-C BL-171)", () => {
  it("returns dash for non-finite", () => {
    expect(formatPriceShort(Number.NaN)).toBe("—");
    expect(formatPriceShort(Number.POSITIVE_INFINITY)).toBe("—");
  });

  it("formats large prices with thousands separator (no decimals)", () => {
    expect(formatPriceShort(67890.123)).toBe("$67,890");
    expect(formatPriceShort(1500)).toBe("$1,500");
  });

  it("formats medium prices with 2 decimals", () => {
    expect(formatPriceShort(123.456)).toBe("$123.46");
    expect(formatPriceShort(1)).toBe("$1.00");
  });

  it("formats small prices with 4 decimals", () => {
    expect(formatPriceShort(0.5432)).toBe("$0.5432");
    expect(formatPriceShort(0.001)).toBe("$0.0010");
  });
});

describe("formatReturnPctShort (Sprint 32-C BL-171)", () => {
  it("returns dash for non-finite", () => {
    expect(formatReturnPctShort(Number.NaN)).toBe("—");
  });

  it("formats positive with + sign", () => {
    expect(formatReturnPctShort(0.0123)).toBe("+1.23%");
    expect(formatReturnPctShort(1)).toBe("+100.00%");
  });

  it("formats negative without extra sign (Number toFixed already includes -)", () => {
    expect(formatReturnPctShort(-0.0123)).toBe("-1.23%");
  });

  it("formats zero with + sign", () => {
    expect(formatReturnPctShort(0)).toBe("+0.00%");
  });
});
