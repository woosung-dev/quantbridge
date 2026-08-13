// TradeAnalyticsSection — KPI 4 + 거래 분포 donut 카운트 + 빈 상태 검증
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestMetricsOut,
  TradeItem,
} from "@/features/backtest/schemas";

import { TradeAnalyticsSection } from "@/app/(dashboard)/backtests/_components/report/trade-analytics-section";

const METRICS = {
  total_return: 0.1,
  sharpe_ratio: 1,
  max_drawdown: -0.05,
  win_rate: 0.5,
  num_trades: 4,
  avg_trade_abs: 12.5,
  avg_trade_pct: 0.005,
  avg_bars_in_trade: 1.5,
  largest_win_abs: 100,
  largest_loss_abs: -40,
  best_trade_pct: 0.04,
  worst_trade_pct: -0.02,
  avg_win: 0.03,
  avg_loss: -0.015,
} as unknown as BacktestMetricsOut;

function trade(idx: number, pnl: number): TradeItem {
  return {
    trade_index: idx,
    direction: "long",
    status: "closed",
    entry_time: "2026-01-01T00:00:00Z",
    exit_time: "2026-01-02T00:00:00Z",
    entry_price: 100,
    exit_price: 101,
    size: 1,
    pnl,
    return_pct: pnl / 100,
    fees: 0,
  } as unknown as TradeItem;
}

describe("TradeAnalyticsSection", () => {
  it("KPI 4종 + 거래 분포 donut 카운트 렌더", () => {
    render(
      <TradeAnalyticsSection
        metrics={METRICS}
        trades={[trade(0, 10), trade(1, -5), trade(2, 0), trade(3, 8)]}
      />,
    );
    expect(screen.getByText("평균 PnL")).toBeInTheDocument();
    expect(screen.getByText("+12.50 USDT")).toBeInTheDocument();
    expect(screen.getByText("평균 거래 바수")).toBeInTheDocument();
    expect(screen.getByText("1.5")).toBeInTheDocument();
    expect(screen.getByText("최대 수익 거래")).toBeInTheDocument();
    expect(screen.getByText("+100.00 USDT")).toBeInTheDocument();
    expect(screen.getByText("최대 손실 거래")).toBeInTheDocument();
    expect(screen.getByText("-40.00 USDT")).toBeInTheDocument();
    // donut 범례: 승 2 / 패 1 / 손익분기 1, 중앙 총 거래 4
    expect(screen.getByText("2 거래")).toBeInTheDocument();
    expect(screen.getAllByText("1 거래")).toHaveLength(2);
    expect(screen.getByText("총 거래")).toBeInTheDocument();
  });

  it("거래 0건 → 분포/도넛 빈 상태", () => {
    render(<TradeAnalyticsSection metrics={{ ...METRICS, num_trades: 0 }} trades={[]} />);
    expect(screen.getByTestId("pnl-distribution-empty")).toBeInTheDocument();
    expect(screen.getByTestId("trade-outcome-donut-empty")).toBeInTheDocument();
  });
});
