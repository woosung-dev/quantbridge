// BacktestList — codex review P2 fix (Sprint 41-B2).
// hasMorePages (data.total > items.length) 시 status 필터 chip(전체 제외) 비활성 + 안내 노출.

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

function makeItem(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    strategy_id: "00000000-0000-4000-8000-000000000111",
    symbol: "BTCUSDT",
    timeframe: "1h",
    period_start: "2026-01-01T00:00:00Z",
    period_end: "2026-02-01T00:00:00Z",
    status: "completed" as const,
    created_at: "2026-02-02T00:00:00Z",
    completed_at: "2026-02-02T00:05:00Z",
    ...overrides,
  };
}

describe("BacktestList — Sprint 41-B2 hasMorePages filter UX", () => {
  afterEach(() => {
    cleanup();
    mockUseBacktests.mockReset();
  });

  it("total <= items.length (현재 페이지에 모든 데이터) → 전 chip 활성 + 안내 미표시", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [makeItem()],
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

    expect(
      screen.queryByTestId("backtest-filter-notice"),
    ).not.toBeInTheDocument();
    // '완료' chip 은 활성 (disabled 아님)
    const completedChip = screen.getByTestId("backtest-filter-completed");
    expect(completedChip).not.toBeDisabled();
    expect(completedChip.getAttribute("aria-disabled")).not.toBe("true");
  });

  it("total > items.length (페이지 한 개만 fetch) → '전체' 제외 chip 비활성 + 안내 노출", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [makeItem(), makeItem({ id: "00000000-0000-4000-8000-000000000002" })],
        total: 50, // 50 > 2 → hasMorePages
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

    // 안내 노출
    const notice = screen.getByTestId("backtest-filter-notice");
    expect(notice).toBeInTheDocument();
    expect(notice).toHaveTextContent(/현재 페이지\(20건\)만 필터/);
    expect(notice).toHaveTextContent(/Beta 에 서버 필터/);

    // '전체' chip 은 활성, 나머지는 비활성
    const allChip = screen.getByTestId("backtest-filter-all");
    expect(allChip).not.toBeDisabled();

    const completedChip = screen.getByTestId("backtest-filter-completed");
    expect(completedChip).toBeDisabled();
    expect(completedChip.getAttribute("aria-disabled")).toBe("true");

    const failedChip = screen.getByTestId("backtest-filter-failed");
    expect(failedChip).toBeDisabled();
  });

  it("KPI '총 건수' 는 BE total 그대로 노출 (페이지 슬라이스 아님)", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [makeItem()],
        total: 50,
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

    // total=50 KPI 카드
    expect(screen.getByText("50")).toBeInTheDocument();
  });
});
