// BacktestReportShell — 자식에게 넘기는 파생 배열의 identity 가 재렌더에도 유지되는지 고정한다.
// ★종전엔 buy_and_hold 변환 배열과 로딩 중 `trades ?? []` 를 렌더마다 새로 만들어, 부모가 다시
//   그려질 때마다 자식 memo(B&H 범위 · 초과수익 · 분포) 가 무효가 되고 차트 시리즈가 다시 꽂혔다.
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BacktestDetail } from "@/features/backtest/schemas";

const detailedProps = vi.hoisted(() => [] as Array<Record<string, unknown>>);
const analyticsProps = vi.hoisted(() => [] as Array<Record<string, unknown>>);

vi.mock("@/features/backtest/hooks", () => ({
  // 로딩 중 — data 없음. 셸은 trades 자리에 기본값을 넘긴다.
  useAllBacktestTrades: () => ({
    data: undefined,
    isLoading: true,
    isError: false,
    error: null,
  }),
}));

vi.mock("@/features/backtest/components/report/detailed-results-section", () => ({
  DetailedResultsSection: (props: Record<string, unknown>) => {
    detailedProps.push(props);
    return null;
  },
}));
vi.mock("@/features/backtest/components/report/trade-analytics-section", () => ({
  TradeAnalyticsSection: (props: Record<string, unknown>) => {
    analyticsProps.push(props);
    return null;
  },
}));
vi.mock("@/features/backtest/components/report/performance-chart", () => ({
  PerformanceChart: () => null,
}));
vi.mock("@/features/backtest/components/report/metric-groups-section", () => ({
  MetricGroupsSection: () => null,
}));
vi.mock("@/features/backtest/components/stress-test-panel", () => ({
  StressTestPanel: () => null,
}));

import { BacktestReportShell } from "@/features/backtest/components/report/backtest-report-shell";

const BT = {
  id: "11111111-2222-3333-4444-555555555555",
  strategy_id: "s",
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2025-01-01T00:00:00Z",
  period_end: "2025-01-03T00:00:00Z",
  status: "completed",
  created_at: "2025-01-03T00:00:00Z",
  completed_at: "2025-01-03T00:00:00Z",
  initial_capital: 1000,
  error: null,
  config: null,
  metrics: {
    total_return: 0.1,
    sharpe_ratio: 1,
    max_drawdown: -0.05,
    win_rate: 0.5,
    num_trades: 2,
    profit_factor: 1.5,
    buy_and_hold_curve: [
      ["2025-01-01T00:00:00Z", 1000],
      ["2025-01-02T00:00:00Z", 1050],
    ],
  },
  equity_curve: [
    { timestamp: "2025-01-01T00:00:00Z", value: 1000 },
    { timestamp: "2025-01-02T00:00:00Z", value: 1100 },
  ],
} as unknown as BacktestDetail;

describe("BacktestReportShell — 파생 배열 identity", () => {
  it("같은 backtest 로 재렌더하면 B&H 곡선과 빈 trades 기본값이 같은 참조다", () => {
    detailedProps.length = 0;
    analyticsProps.length = 0;

    const { rerender } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    rerender(<BacktestReportShell backtest={BT} currentId={BT.id} />);

    expect(detailedProps).toHaveLength(2);
    const [first, second] = detailedProps;
    expect(first?.buyAndHoldCurve).toEqual([
      { timestamp: "2025-01-01T00:00:00Z", value: 1000 },
      { timestamp: "2025-01-02T00:00:00Z", value: 1050 },
    ]);
    expect(second?.buyAndHoldCurve).toBe(first?.buyAndHoldCurve);

    expect(analyticsProps).toHaveLength(2);
    expect(analyticsProps[0]?.trades).toEqual([]);
    expect(analyticsProps[1]?.trades).toBe(analyticsProps[0]?.trades);
  });
});
