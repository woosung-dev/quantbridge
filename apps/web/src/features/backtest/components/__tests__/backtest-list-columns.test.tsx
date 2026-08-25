// 백테스트 목록의 성과 열과 미청산 부기를 검증한다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BacktestList } from "@/features/backtest/components/backtest-list";

let queryString = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
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

const item = {
  id: "00000000-0000-4000-8000-000000000001",
  strategy_id: "00000000-0000-4000-8000-000000000111",
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2026-01-01T00:00:00Z",
  period_end: "2026-02-01T00:00:00Z",
  status: "completed" as const,
  created_at: "2026-02-02T00:00:00Z",
  completed_at: "2026-02-02T00:05:00Z",
};

function renderList() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <BacktestList />
    </QueryClientProvider>,
  );
}

describe("BacktestList 성과 열", () => {
  afterEach(() => {
    cleanup();
    queryString = "";
    mockUseBacktests.mockReset();
    mockUseStrategies.mockReset();
  });

  it("11개 열과 성과 숫자, 미청산 부기를 렌더한다", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          {
            ...item,
            metrics_summary: {
              total_return: 0.1234,
              net_profit_abs: 12,
              sharpe_ratio: 1.5,
              sharpe_convention: "tv_monthly_rfr2",
              max_drawdown: -0.04,
              num_trades: 1234,
              total_open_trades: 1,
            },
          },
        ],
        total: 1,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseStrategies.mockReturnValue({
      data: { items: [{ id: item.strategy_id, name: "MA 전략" }] },
    });

    renderList();

    const table = screen.getByRole("table", { name: /백테스트 실행 목록/ });
    expect(within(table).getAllByRole("columnheader")).toHaveLength(11);
    const row = screen.getByTestId(`backtest-row-${item.id}`);
    expect(within(row).getByText("12.34%")).toBeInTheDocument();
    expect(within(row).getByText("-4.00%")).toBeInTheDocument();
    expect(within(row).getByText("1.50")).toBeInTheDocument();
    expect(within(row).getByTitle("무위험 2%/년 · 월간 수익률 기준")).toHaveTextContent("1.50");
    expect(within(row).getByText("1,234")).toBeInTheDocument();
    expect(within(row).getByText("미청산 포함")).toBeInTheDocument();
  });

  it("metrics_summary 가 null 이면 성과 네 칸을 무데이터 사유와 함께 렌더한다", () => {
    mockUseBacktests.mockReturnValue({
      data: { items: [{ ...item, metrics_summary: null }], total: 1 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseStrategies.mockReturnValue({ data: { items: [] } });

    renderList();

    const row = screen.getByTestId(`backtest-row-${item.id}`);
    expect(
      within(row).getAllByTitle("아직 끝나지 않은 실행은 수익률을 채우지 않습니다."),
    ).toHaveLength(4);
  });

  it("구 기준과 산출 불가 샤프의 사유를 표시하고 혼합 정렬을 고지한다", () => {
    queryString = "order_by=sharpe_ratio&order=desc";
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          {
            ...item,
            metrics_summary: {
              total_return: 0.1234,
              net_profit_abs: 12,
              sharpe_ratio: 1.5,
              max_drawdown: -0.04,
              num_trades: 1234,
              total_open_trades: 0,
            },
          },
          {
            ...item,
            id: "00000000-0000-4000-8000-000000000002",
            metrics_summary: {
              total_return: 0.1,
              net_profit_abs: 10,
              sharpe_ratio: 0,
              sharpe_convention: "unavailable",
              max_drawdown: -0.02,
              num_trades: 10,
              total_open_trades: 0,
            },
          },
        ],
        total: 2,
      },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseStrategies.mockReturnValue({ data: { items: [] } });

    renderList();

    expect(
      screen.getByTitle("구 기준(봉 수익률 · 무위험 0%) - 현재 기준과 비교 불가"),
    ).toHaveTextContent("1.50");
    expect(screen.getByTitle("변동이 없거나 기간이 짧아 산출되지 않았습니다")).toHaveTextContent(
      "—",
    );
    expect(screen.getByTestId("backtest-sharpe-sort-notice")).toHaveTextContent(
      "구 기준 샤프는 현재 기준과 비교할 수 없어 정렬 시 비교 가능한 결과 뒤로 분리됩니다.",
    );
  });

  // BL-822 — 목록의 거래 수 칸은 **완료 거래**(summary 는 JSONB closed 카운트)다.
  // 상세는 미청산까지 포함한 「거래 수」를 보여 주므로, 여기에 미청산 건수를 적어 두
  // 화면의 숫자가 더해서 맞는 것이 보이게 한다.
  it("거래 수 칸에 미청산 건수를 부기한다", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          {
            ...item,
            metrics_summary: {
              total_return: 0.1234,
              net_profit_abs: 12,
              sharpe_ratio: 1.5,
              max_drawdown: -0.04,
              num_trades: 12,
              total_open_trades: 1,
            },
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

    renderList();

    const row = screen.getByTestId(`backtest-row-${item.id}`);
    expect(within(row).getByText("12")).toBeInTheDocument();
    expect(within(row).getByText("미청산 1")).toBeInTheDocument();
    // 열 이름도 값과 같은 뜻이어야 한다 — 상세의 「총 거래 수」(13)와 다른 수이므로.
    const table = screen.getByRole("table", { name: /백테스트 실행 목록/ });
    expect(within(table).getByRole("button", { name: "완료 거래 기준 정렬" })).toBeInTheDocument();
    expect(within(table).queryByText("거래 수")).toBeNull();
  });

  it("음성 대조 — 미청산 0건이면 부기가 붙지 않는다", () => {
    mockUseBacktests.mockReturnValue({
      data: {
        items: [
          {
            ...item,
            metrics_summary: {
              total_return: 0.1234,
              net_profit_abs: 12,
              sharpe_ratio: 1.5,
              max_drawdown: -0.04,
              num_trades: 12,
              total_open_trades: 0,
            },
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

    renderList();

    const row = screen.getByTestId(`backtest-row-${item.id}`);
    expect(within(row).queryByText(/미청산/)).toBeNull();
  });
});
