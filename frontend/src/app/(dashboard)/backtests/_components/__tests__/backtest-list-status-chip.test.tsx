// BacktestList 상태 표시 — C 디자인 이식(S5) 후. 옛 progress-cell/KPI-pulse 는 C 상태 칩으로
// 교체됐다(backtest-list-progress-cell.test.tsx 대체). 상태별 칩 라벨이 올바른지 검증한다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BacktestList } from "@/app/(dashboard)/backtests/_components/backtest-list";
import type { BacktestStatus } from "@/features/backtest/schemas";

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

function renderWith(status: BacktestStatus, id = "00000000-0000-4000-8000-000000000a01") {
  mockUseBacktests.mockReturnValue({
    data: { items: [{ ...baseItem, id, status }], total: 1, limit: 20, offset: 0 },
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
}

describe("BacktestList — C 상태 칩 (S5 이식)", () => {
  afterEach(() => {
    cleanup();
    mockUseBacktests.mockReset();
  });

  // 상태 → 행에 표시되는 칩 라벨.
  const cases: ReadonlyArray<[BacktestStatus, string]> = [
    ["completed", "완료"],
    ["running", "실행 중"],
    ["queued", "대기"],
    ["failed", "실패"],
    ["cancelled", "취소됨"],
  ];

  for (const [status, label] of cases) {
    it(`${status} 행은 "${label}" 칩을 표시한다`, () => {
      renderWith(status, `00000000-0000-4000-8000-0000000000${status.length}0`);
      const row = screen.getByTestId(
        `backtest-row-00000000-0000-4000-8000-0000000000${status.length}0`,
      );
      expect(within(row).getByText(label)).toBeInTheDocument();
    });
  }

  it("상태 필터 탭과 runs-summary 요약이 함께 렌더된다", () => {
    renderWith("completed");
    // 필터 탭 (전체 + 상태 5종)
    expect(screen.getByTestId("backtest-filter-all")).toBeInTheDocument();
    expect(screen.getByTestId("backtest-filter-completed")).toBeInTheDocument();
    // runs-summary 의 완료 카운트 (mono span) — 완료 1건
    expect(screen.getByText("실행 목록")).toBeInTheDocument();
  });
});
