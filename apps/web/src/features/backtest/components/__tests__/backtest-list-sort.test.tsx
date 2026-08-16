// 백테스트 목록의 서버 정렬 URL 상태와 접근성 표기를 검증한다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BacktestList } from "@/features/backtest/components/backtest-list";

const replace = vi.fn();
let queryString = "";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/backtests",
  useSearchParams: () => new URLSearchParams(queryString),
}));

const mockUseBacktests = vi.fn();
const mockUseStrategies = vi.fn();
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: (...args: unknown[]) => mockUseBacktests(...args),
}));
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: (...args: unknown[]) => mockUseStrategies(...args),
}));

function renderList() {
  mockUseBacktests.mockReturnValue({
    data: {
      items: [
        {
          id: "00000000-0000-4000-8000-000000000001",
          strategy_id: "00000000-0000-4000-8000-000000000111",
          symbol: "BTCUSDT",
          timeframe: "1h",
          period_start: "2026-01-01T00:00:00Z",
          period_end: "2026-02-01T00:00:00Z",
          status: "completed",
          created_at: "2026-02-02T00:00:00Z",
          completed_at: "2026-02-02T00:05:00Z",
          metrics_summary: null,
        },
      ],
      total: 1,
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  });
  mockUseStrategies.mockReturnValue({ data: { items: [] } });
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <BacktestList />
    </QueryClientProvider>,
  );
}

describe("BacktestList 서버 정렬", () => {
  afterEach(() => {
    cleanup();
    queryString = "";
    replace.mockReset();
    mockUseBacktests.mockReset();
    mockUseStrategies.mockReset();
  });

  it("정렬 헤더 클릭은 order_by/order URL을 갱신하고 활성 th만 aria-sort를 가진다", () => {
    renderList();

    expect(screen.getByRole("columnheader", { name: /실행 시각/ })).toHaveAttribute("aria-sort", "descending");
    fireEvent.click(screen.getByRole("button", { name: "수익률 기준 정렬" }));
    expect(replace).toHaveBeenCalledWith("/backtests?order_by=total_return&order=desc");

    cleanup();
    queryString = "order_by=total_return&order=desc";
    renderList();
    expect(screen.getByRole("columnheader", { name: /수익률/ })).toHaveAttribute("aria-sort", "descending");
    expect(screen.getByRole("columnheader", { name: /실행 시각/ })).not.toHaveAttribute("aria-sort");
    fireEvent.click(screen.getByRole("button", { name: "수익률 기준 정렬" }));
    expect(replace).toHaveBeenLastCalledWith("/backtests?order_by=total_return&order=asc");
  });
});
