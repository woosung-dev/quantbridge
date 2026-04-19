// Sprint FE-04: Backtest Zod schemas — BE Decimal→str 직렬화에 대한 transform 검증.

import { describe, expect, it } from "vitest";

import {
  BacktestDetailSchema,
  BacktestMetricsOutSchema,
  CreateBacktestRequestSchema,
  EquityPointSchema,
  TradeItemSchema,
} from "../schemas";

describe("EquityPointSchema", () => {
  it("transforms decimal string value into finite number", () => {
    const parsed = EquityPointSchema.parse({
      timestamp: "2024-01-01T00:00:00+00:00",
      value: "10500.123456",
    });
    expect(parsed.value).toBeCloseTo(10500.123456, 6);
    expect(Number.isFinite(parsed.value)).toBe(true);
  });

  it("rejects NaN decimal string", () => {
    expect(() =>
      EquityPointSchema.parse({
        timestamp: "2024-01-01T00:00:00+00:00",
        value: "not-a-number",
      }),
    ).toThrow();
  });
});

describe("BacktestMetricsOutSchema", () => {
  it("converts all decimal fields to number", () => {
    const parsed = BacktestMetricsOutSchema.parse({
      total_return: "0.234",
      sharpe_ratio: "1.8",
      max_drawdown: "-0.12",
      win_rate: "0.55",
      num_trades: 42,
    });
    expect(parsed.total_return).toBeCloseTo(0.234, 6);
    expect(parsed.sharpe_ratio).toBeCloseTo(1.8, 6);
    expect(parsed.max_drawdown).toBeCloseTo(-0.12, 6);
    expect(parsed.win_rate).toBeCloseTo(0.55, 6);
    expect(parsed.num_trades).toBe(42);
  });
});

describe("TradeItemSchema", () => {
  it("parses closed trade with nullable exit fields", () => {
    const parsed = TradeItemSchema.parse({
      trade_index: 0,
      direction: "long",
      status: "closed",
      entry_time: "2024-01-01T00:00:00+00:00",
      exit_time: "2024-01-02T00:00:00+00:00",
      entry_price: "100.0",
      exit_price: "110.0",
      size: "1.5",
      pnl: "15.0",
      return_pct: "0.10",
      fees: "0.15",
    });
    expect(parsed.entry_price).toBe(100);
    expect(parsed.exit_price).toBe(110);
  });

  it("accepts open trade with null exit fields", () => {
    const parsed = TradeItemSchema.parse({
      trade_index: 1,
      direction: "short",
      status: "open",
      entry_time: "2024-01-01T00:00:00+00:00",
      exit_time: null,
      entry_price: "50",
      exit_price: null,
      size: "2",
      pnl: "0",
      return_pct: "0",
      fees: "0",
    });
    expect(parsed.exit_price).toBeNull();
    expect(parsed.exit_time).toBeNull();
  });
});

describe("BacktestDetailSchema", () => {
  it("parses completed detail with metrics + equity_curve", () => {
    const raw = {
      id: "11111111-1111-4111-8111-111111111111",
      strategy_id: "22222222-2222-4222-8222-222222222222",
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "2024-01-01T00:00:00+00:00",
      period_end: "2024-01-31T00:00:00+00:00",
      status: "completed",
      created_at: "2024-02-01T00:00:00+00:00",
      completed_at: "2024-02-01T00:05:00+00:00",
      initial_capital: "10000.0",
      metrics: {
        total_return: "0.3",
        sharpe_ratio: "2.1",
        max_drawdown: "-0.08",
        win_rate: "0.6",
        num_trades: 15,
      },
      equity_curve: [
        { timestamp: "2024-01-01T00:00:00+00:00", value: "10000" },
        { timestamp: "2024-01-02T00:00:00+00:00", value: "10100" },
      ],
      error: null,
    };
    const parsed = BacktestDetailSchema.parse(raw);
    expect(parsed.initial_capital).toBe(10000);
    expect(parsed.metrics?.total_return).toBeCloseTo(0.3, 6);
    expect(parsed.equity_curve?.length).toBe(2);
    expect(parsed.equity_curve?.[0]?.value).toBe(10000);
  });
});

describe("CreateBacktestRequestSchema", () => {
  const valid = {
    strategy_id: "11111111-1111-4111-8111-111111111111",
    symbol: "BTC/USDT",
    timeframe: "1h" as const,
    period_start: "2024-01-01T00:00:00+00:00",
    period_end: "2024-01-31T00:00:00+00:00",
    initial_capital: 10000,
  };

  it("accepts valid request", () => {
    expect(() => CreateBacktestRequestSchema.parse(valid)).not.toThrow();
  });

  it("rejects period_end <= period_start", () => {
    expect(() =>
      CreateBacktestRequestSchema.parse({
        ...valid,
        period_end: valid.period_start,
      }),
    ).toThrow();
  });

  it("rejects non-finite initial_capital (Infinity)", () => {
    expect(() =>
      CreateBacktestRequestSchema.parse({
        ...valid,
        initial_capital: Number.POSITIVE_INFINITY,
      }),
    ).toThrow();
  });

  it("rejects non-positive initial_capital", () => {
    expect(() =>
      CreateBacktestRequestSchema.parse({
        ...valid,
        initial_capital: 0,
      }),
    ).toThrow();
  });

  it("rejects symbol under 3 chars", () => {
    expect(() =>
      CreateBacktestRequestSchema.parse({ ...valid, symbol: "BT" }),
    ).toThrow();
  });
});
