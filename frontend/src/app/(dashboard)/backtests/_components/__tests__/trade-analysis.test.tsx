// W4 Sprint X1+X3: TradeAnalysis 방향별 성과 section 렌더링 테스트.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestMetricsOut,
  TradeItem,
} from "@/features/backtest/schemas";

import { TradeAnalysis } from "../trade-analysis";

// schema 와 일치하는 metrics fixture (decimalString → number transform 후).
const METRICS: BacktestMetricsOut = {
  total_return: 0.1,
  sharpe_ratio: 1.5,
  max_drawdown: -0.05,
  win_rate: 0.667,
  num_trades: 3,
  long_count: 2,
  short_count: 1,
  avg_win: 100,
  avg_loss: -30,
  sortino_ratio: null,
  calmar_ratio: null,
  profit_factor: null,
};

function mkTrade(
  overrides: Pick<TradeItem, "direction" | "pnl"> & Partial<TradeItem>,
): TradeItem {
  return {
    trade_index: 0,
    status: "closed",
    entry_time: "2026-01-01T00:00:00Z",
    exit_time: "2026-01-01T01:00:00Z",
    entry_price: 100,
    exit_price: 110,
    size: 1,
    return_pct: 0,
    fees: 0,
    ...overrides,
  };
}

describe("TradeAnalysis", () => {
  it("renders existing sections without trades prop (regression guard)", () => {
    render(<TradeAnalysis metrics={METRICS} />);
    expect(screen.getByText("방향 분포")).toBeInTheDocument();
    expect(screen.getByText("승/패 비율")).toBeInTheDocument();
    expect(screen.getByText("평균 수익 vs 손실")).toBeInTheDocument();
    expect(screen.queryByText("방향별 성과")).not.toBeInTheDocument();
  });

  it("renders existing sections with empty trades array (no breakdown)", () => {
    render(<TradeAnalysis metrics={METRICS} trades={[]} />);
    expect(screen.getByText("방향 분포")).toBeInTheDocument();
    expect(screen.queryByText("방향별 성과")).not.toBeInTheDocument();
  });

  it("renders direction breakdown when trades provided", () => {
    const trades: TradeItem[] = [
      mkTrade({ direction: "long", pnl: 10 }),
      mkTrade({ direction: "long", pnl: -5 }),
      mkTrade({ direction: "short", pnl: 20 }),
    ];
    render(<TradeAnalysis metrics={METRICS} trades={trades} />);
    expect(screen.getByText("방향별 성과")).toBeInTheDocument();
    expect(screen.getByText(/롱 · 2건/)).toBeInTheDocument();
    expect(screen.getByText(/숏 · 1건/)).toBeInTheDocument();
    // 롱 승률 1/2 = 50.0%, 숏 승률 1/1 = 100.0%
    expect(screen.getByText("50.0%")).toBeInTheDocument();
    expect(screen.getByText("100.0%")).toBeInTheDocument();
  });

  it("renders single-direction breakdown with empty other side", () => {
    const trades: TradeItem[] = [mkTrade({ direction: "long", pnl: 50 })];
    render(<TradeAnalysis metrics={METRICS} trades={trades} />);
    expect(screen.getByText("방향별 성과")).toBeInTheDocument();
    expect(screen.getByText(/롱 · 1건/)).toBeInTheDocument();
    expect(screen.getByText("거래 없음")).toBeInTheDocument(); // short 카드
  });
});
