// DetailedResultsSection (심화 분석) — 수익 구조/벤치마킹/월별 수익률 3카드 + waterfall 잠금
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  BacktestMetricsOut,
  EquityPoint,
  TradeItem,
} from "@/features/backtest/schemas";

import { DetailedResultsSection } from "@/features/backtest/components/report/detailed-results-section";

const METRICS = {
  total_return: 0.2,
  sharpe_ratio: 1.154,
  max_drawdown: -0.1,
  win_rate: 0.6,
  num_trades: 10,
  monthly_returns: [["2026-01", 0.05]],
} as unknown as BacktestMetricsOut;

const EQUITY: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 12000 },
];
const BH: EquityPoint[] = [
  { timestamp: "2026-01-01T00:00:00Z", value: 10000 },
  { timestamp: "2026-01-02T00:00:00Z", value: 11000 },
];

const TRADES: TradeItem[] = [
  {
    trade_index: 0,
    direction: "long",
    status: "closed",
    entry_time: "2026-01-01T00:00:00Z",
    exit_time: "2026-01-02T00:00:00Z",
    entry_price: 100,
    exit_price: 120,
    size: 1,
    pnl: 2000,
    return_pct: 0.2,
    fees: 5,
  } as TradeItem,
];

describe("DetailedResultsSection (심화 분석)", () => {
  it("수익 구조/벤치마킹/월별 수익률 3카드 시맨틱 구조", () => {
    const { container } = render(
      <DetailedResultsSection
        metrics={METRICS}
        equityCurve={EQUITY}
        buyAndHoldCurve={BH}
        initialCapital={10000}
        trades={TRADES}
      />,
    );
    expect(container.querySelectorAll(".card")).toHaveLength(3);
    expect(screen.getByText("수익 구조")).toBeInTheDocument();
    expect(screen.getByText("벤치마킹")).toBeInTheDocument();
    expect(screen.getByText("월별 수익률")).toBeInTheDocument();
  });

  it("trades 없음(profitStructure null) → waterfall 잠금 empty state", () => {
    render(
      <DetailedResultsSection
        metrics={METRICS}
        equityCurve={EQUITY}
        buyAndHoldCurve={null}
        initialCapital={10000}
      />,
    );
    expect(screen.getByTestId("profit-waterfall-locked")).toBeInTheDocument();
    expect(
      screen.getByText("수익 구조 데이터가 없는 구 백테스트입니다"),
    ).toBeInTheDocument();
  });
});
