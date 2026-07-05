// BacktestReportShell — IA 골격 (스트립 + 히어로 차트 + 섹션 탭 존재/순서) 검증
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BacktestDetail } from "@/features/backtest/schemas";

vi.mock("@/features/backtest/hooks", () => ({
  useAllBacktestTrades: () => ({
    data: { items: [], total: 0, truncated: false },
    isLoading: false,
    isError: false,
    error: null,
  }),
  useBacktest: () => ({ data: undefined, isLoading: false, isError: false }),
  useBacktests: () => ({ data: undefined, isLoading: false, isError: false }),
  useStressTest: () => ({ data: undefined, isLoading: false, isError: false, error: null }),
  useCreateMonteCarlo: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateWalkForward: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateCostAssumption: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateParamStability: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/components/charts/trading-chart", () => ({
  TradingChart: () => <div data-testid="mock-trading-chart" />,
}));

import { BacktestReportShell } from "../backtest-report-shell";

const BT = {
  id: "11111111-2222-3333-4444-555555555555",
  strategy_id: "s",
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2025-01-01T00:00:00Z",
  period_end: "2026-07-05T00:00:00Z",
  status: "completed",
  created_at: "2026-07-05T00:00:00Z",
  completed_at: "2026-07-05T00:00:00Z",
  initial_capital: 1000000,
  error: null,
  config: null,
  metrics: {
    total_return: 0.189,
    sharpe_ratio: 1.154,
    max_drawdown: -0.0252,
    win_rate: 0.9898,
    num_trades: 295,
    profit_factor: 21.3,
  },
  equity_curve: [
    { timestamp: "2025-01-01T00:00:00Z", value: 1000000 },
    { timestamp: "2025-01-02T00:00:00Z", value: 1010000 },
  ],
} as unknown as BacktestDetail;

describe("BacktestReportShell", () => {
  it("KeyStatsStrip + PerformanceChart + 섹션 탭 4종이 순서대로 존재", () => {
    render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    expect(screen.getByTestId("key-stats-strip")).toBeInTheDocument();
    expect(screen.getByTestId("performance-chart")).toBeInTheDocument();
    const tabs = screen.getAllByRole("tab");
    // 히어로 차트 내부의 기간 탭(1M/3M/6M/전체) 뒤에 섹션 탭 4종.
    const labels = tabs.map((t) => t.textContent);
    const sectionLabels = ["상세 결과", "거래 분석", "거래 목록", "스트레스 테스트"];
    for (const label of sectionLabels) {
      expect(labels).toContain(label);
    }
    // 순서 보존 확인 (섹션 탭 상대 순서).
    const idx = sectionLabels.map((l) => labels.indexOf(l));
    expect([...idx].sort((a, b) => a - b)).toEqual(idx);
  });

  it("metrics 없으면 null 렌더 (방어)", () => {
    const { container } = render(
      <BacktestReportShell
        backtest={{ ...BT, metrics: null } as unknown as BacktestDetail}
        currentId={BT.id}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
