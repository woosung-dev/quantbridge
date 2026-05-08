// BacktestList 표 행 — Sprint 43 W7 진행률 cell 통합 검증.
// running/queued/cancelling 행은 기간 cell 대신 RunningProgressBar.
// completed/failed/cancelled 행은 기간 표시 그대로.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BacktestList } from "@/app/(dashboard)/backtests/_components/backtest-list";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/backtests",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "user-1", getToken: async () => "test-token" }),
}));

const mockUseBacktests = vi.fn();
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: (...args: unknown[]) => mockUseBacktests(...args),
}));

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

const baseItem = {
  strategy_id: "00000000-0000-4000-8000-000000000111",
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2026-01-01T00:00:00Z",
  period_end: "2026-02-01T00:00:00Z",
  created_at: "2026-02-02T00:00:00Z",
  completed_at: "2026-02-02T00:05:00Z",
};

describe("BacktestList — Sprint 43 W7 진행률 cell", () => {
  afterEach(() => {
    cleanup();
    mockUseBacktests.mockReset();
  });

  it("running 행은 기간 cell 대신 RunningProgressBar 표시", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          { ...baseItem, id: "00000000-0000-4000-8000-000000000a01", status: "running" as const },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <QueryClientProvider client={makeQc()}>
        <BacktestList />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("running-progress-bar")).toBeInTheDocument();
    expect(screen.getByTestId("running-progress-bar")).toHaveTextContent("실행 중…");
  });

  it("queued 행은 pulse dot + '대기 중…' 라벨 표시", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          { ...baseItem, id: "00000000-0000-4000-8000-000000000a02", status: "queued" as const },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <QueryClientProvider client={makeQc()}>
        <BacktestList />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("queued-pulse")).toBeInTheDocument();
  });

  it("completed 행은 RunningProgressBar 미표시 (기간 텍스트 그대로)", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          {
            ...baseItem,
            id: "00000000-0000-4000-8000-000000000a03",
            status: "completed" as const,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <QueryClientProvider client={makeQc()}>
        <BacktestList />
      </QueryClientProvider>,
    );

    expect(screen.queryByTestId("running-progress-bar")).not.toBeInTheDocument();
    expect(screen.queryByTestId("queued-pulse")).not.toBeInTheDocument();
  });

  it("실행 중 KPI 카드는 pulse animation 적용 (counts.running > 0)", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          { ...baseItem, id: "00000000-0000-4000-8000-000000000a04", status: "running" as const },
          { ...baseItem, id: "00000000-0000-4000-8000-000000000a05", status: "queued" as const },
        ],
        total: 2,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <QueryClientProvider client={makeQc()}>
        <BacktestList />
      </QueryClientProvider>,
    );

    const runningKpi = screen.getByTestId("kpi-card-실행-중");
    expect(runningKpi).toBeInTheDocument();
    // queued 1건 보조 라벨
    expect(runningKpi).toHaveTextContent("대기 1건 포함");
  });
});
