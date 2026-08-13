// BacktestList 상태 표시 + 4상태 렌더 — C 디자인 이식(S5) 후. 옛 progress-cell/KPI-pulse UI 는
// C 상태 칩으로 교체됐다(backtest-list-progress-cell.test.tsx 대체). 검증 대상 넷.
//   1. 상태별 칩 라벨이 S4 용어 SSOT(BACKTEST_STATUS_LABEL)와 일치한다.
//   2. 무데이터 셀 — 아직 끝나지 않은 실행(대기/실행 중)은 종료 시각이 없어 EMPTY_CELL 로 표기된다.
//   3. 스켈레톤 / 에러(role="alert" + 엔드포인트 + 재시도) / 빈 상태가 실제로 렌더된다.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BacktestList } from "@/app/(dashboard)/backtests/_components/backtest-list";
import { BACKTEST_STATUS_LABEL } from "@/features/backtest/labels";
import type { BacktestStatus } from "@/features/backtest/schemas";
import { EMPTY_CELL } from "@/lib/labels";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/backtests",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "user-1", getToken: async () => "test-token" }),
}));

const mockUseBacktests = vi.fn();
const mockUseStrategies = vi.fn();
vi.mock("@/features/backtest/hooks", () => ({
  useBacktests: (...args: unknown[]) => mockUseBacktests(...args),
}));
vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: (...args: unknown[]) => mockUseStrategies(...args),
}));

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

const baseItem = {
  id: "00000000-0000-4000-8000-000000000a01",
  strategy_id: "00000000-0000-4000-8000-000000000111",
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2026-01-01T00:00:00Z",
  period_end: "2026-02-01T00:00:00Z",
  status: "completed" as BacktestStatus,
  created_at: "2026-02-02T00:00:00Z",
  completed_at: "2026-02-02T00:05:00Z" as string | null,
};

beforeEach(() => {
  mockUseStrategies.mockReturnValue({ data: { items: [] } });
});

function renderList(overrides: Partial<typeof baseItem> = {}, listOverrides: Record<string, unknown> = {}) {
  mockUseBacktests.mockReturnValue({
    data: { items: [{ ...baseItem, ...overrides }], total: 1, limit: 20, offset: 0 },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...listOverrides,
  });
  render(
    <QueryClientProvider client={makeQc()}>
      <BacktestList />
    </QueryClientProvider>,
  );
}

describe("BacktestList — C 상태 칩 + 4상태 렌더 (S5 이식)", () => {
  afterEach(() => {
    cleanup();
    mockUseBacktests.mockReset();
    mockUseStrategies.mockReset();
  });

  // 상태 → 행에 표시되는 칩 라벨 (SSOT 파생 — 하드코딩 드리프트 방지).
  const statuses: readonly BacktestStatus[] = [
    "completed",
    "running",
    "queued",
    "failed",
    "cancelled",
    "cancelling",
  ];

  for (const status of statuses) {
    it(`${status} 행은 SSOT 라벨 "${BACKTEST_STATUS_LABEL[status].label}" 칩을 표시한다`, () => {
      renderList({ id: `00000000-0000-4000-8000-0000000000${status.length}0`, status });
      const row = screen.getByTestId(
        `backtest-row-00000000-0000-4000-8000-0000000000${status.length}0`,
      );
      expect(within(row).getByText(BACKTEST_STATUS_LABEL[status].label)).toBeInTheDocument();
    });
  }

  it("무데이터 셀 — 아직 끝나지 않은(queued) 실행은 성과를 EMPTY_CELL 로 표기한다", () => {
    renderList({ status: "queued", completed_at: null });
    const row = screen.getByTestId("backtest-row-00000000-0000-4000-8000-000000000a01");
    expect(within(row).getAllByText(EMPTY_CELL).length).toBeGreaterThanOrEqual(4);
  });

  it("스켈레톤 — isLoading 이면 aria-hidden 스켈레톤 표가 렌더된다", () => {
    mockUseBacktests.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    render(
      <QueryClientProvider client={makeQc()}>
        <BacktestList />
      </QueryClientProvider>,
    );
    expect(screen.getByTestId("backtest-skeleton")).toBeInTheDocument();
  });

  it("에러 — isError 이면 role=alert + 엔드포인트 + 다시 시도 버튼이 렌더된다", () => {
    const refetch = vi.fn();
    mockUseBacktests.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("boom"),
      refetch,
    });
    render(
      <QueryClientProvider client={makeQc()}>
        <BacktestList />
      </QueryClientProvider>,
    );
    const box = screen.getByRole("alert");
    expect(box).toHaveAttribute("data-testid", "backtest-error");
    expect(within(box).getByText("boom")).toBeInTheDocument();
    expect(within(box).getByText("GET /api/v1/backtests")).toBeInTheDocument();
    expect(within(box).getByRole("button", { name: /다시 시도/ })).toBeInTheDocument();
  });

  it("빈 상태 — 데이터 0건이면 첫 백테스트 안내가 렌더된다", () => {
    mockUseBacktests.mockReturnValue({
      data: { items: [], total: 0, limit: 20, offset: 0 },
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
    expect(screen.getByTestId("backtest-empty")).toBeInTheDocument();
    expect(screen.getByText("첫 백테스트를 시작하세요")).toBeInTheDocument();
  });
});
