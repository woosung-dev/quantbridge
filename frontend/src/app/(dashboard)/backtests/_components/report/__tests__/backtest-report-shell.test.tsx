// BacktestReportShell — variant-c 번호 섹션 IA (01~10) 존재/순서 + metrics null 방어 검증
import { render, screen, within } from "@testing-library/react";
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
  useLatestStressTest: () => ({ data: undefined }),
  useCreateMonteCarlo: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateWalkForward: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateCostAssumption: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateParamStability: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/components/charts/trading-chart", () => ({
  TradingChart: () => <div data-testid="mock-trading-chart" />,
}));

import { BacktestReportShell } from "@/app/(dashboard)/backtests/_components/report/backtest-report-shell";

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

describe("BacktestReportShell (variant-c 번호 섹션 IA)", () => {
  it("핵심 섹션 프리미티브(요약/차트/지표/거래/다음 단계)가 시맨틱 클래스로 렌더", () => {
    render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    expect(screen.getByTestId("backtest-report-shell")).toBeInTheDocument();
    expect(screen.getByTestId("key-stats-strip")).toBeInTheDocument();
    expect(screen.getByTestId("performance-chart")).toBeInTheDocument();
    expect(screen.getByTestId("metric-groups-section")).toBeInTheDocument();
    expect(screen.getByTestId("report-next-steps")).toBeInTheDocument();
  });

  it("01~10 아이브로 번호가 순서대로 존재 (상단→하단 단일 스크롤)", () => {
    const { container } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    const nums = Array.from(container.querySelectorAll(".eyebrow .num")).map(
      (el) => el.textContent,
    );
    expect(nums).toEqual([
      "01",
      "02",
      "03",
      "04",
      "05",
      "06",
      "07",
      "08",
      "09",
      "10",
    ]);
  });

  it("실행 조건 섹션에 AssumptionsCard(초기 자본) 가 1회만 렌더", () => {
    render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    expect(screen.getAllByText("초기 자본")).toHaveLength(1);
  });

  it("스트레스 테스트 섹션 앵커 id 가 CTA 링크와 일치", () => {
    const { container } = render(<BacktestReportShell backtest={BT} currentId={BT.id} />);
    expect(container.querySelector("#stress-test")).not.toBeNull();
    const cta = screen.getByTestId("report-next-steps");
    expect(within(cta).getByText("스트레스 테스트 열기").getAttribute("href")).toBe(
      "#stress-test",
    );
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
