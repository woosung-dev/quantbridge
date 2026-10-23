import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BacktestDetailView } from "../backtest-detail-view";
import { TradeDetailShell } from "../trades/trade-detail-shell";
import { BacktestDetailSchema } from "../../schemas";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  legacy: vi.fn(() => ({ data: { name: "기존 Pine 전략" } })),
  uid: "user-a",
}));
vi.mock("@/lib/api-client", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("@/hooks/use-auth-ctx", () => ({
  useAuthCtx: () => ({ uid: mocks.uid, getToken: async () => mocks.uid }),
}));
vi.mock("@/features/strategy/hooks", () => ({ useStrategy: mocks.legacy }));
vi.mock("../rerun-button", () => ({ RerunButton: () => null }));
vi.mock("../share-button", () => ({ ShareButton: () => null }));
vi.mock("../trades/trade-detail-table", () => ({ TradeDetailTable: () => null }));
vi.mock("../trades/trade-stats-strip", () => ({ TradeStatsStrip: () => null }));

const ID = "11111111-1111-4111-8111-111111111111";
const BACKTEST = BacktestDetailSchema.parse({
  id: "22222222-2222-4222-8222-222222222222",
  strategy_id: ID,
  symbol: "BTC/USDT",
  timeframe: "1h",
  period_start: "2026-01-01T00:00:00Z",
  period_end: "2026-02-01T00:00:00Z",
  status: "completed",
  completed_at: "2026-02-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  initial_capital: "10000",
  config: { execution_policy: "code_v1" },
});
let detail = BACKTEST;
vi.mock("@/features/backtest/hooks", () => ({
  useBacktest: () => ({ data: detail, refetch: vi.fn() }),
  useBacktestProgress: () => ({ data: undefined }),
  useAllBacktestTrades: () => ({ data: { items: [], total: 0 } }),
}));

function codeResponse(name: string) {
  return {
    id: ID,
    name,
    description: null,
    symbol: "BTC/USDT",
    timeframe: "1h",
    is_archived: false,
    settings: null,
    version: {
      id: "33333333-3333-4333-8333-333333333333",
      schema_version: 1,
      execution_policy: "code_v1",
      language: "typescript",
      source_code: "manual source",
      warmup_bars: 200,
      params: {},
      provenance: {},
      source_hash: "a".repeat(64),
      execution_hash: "b".repeat(64),
      created_at: "2026-01-01T00:00:00Z",
    },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  detail = BACKTEST;
  mocks.uid = "user-a";
  mocks.apiFetch.mockImplementation(async (_path, options) => codeResponse(options.token));
});

describe("코드 백테스트 결과에서 전략으로 이동", () => {
  it.each([
    [BacktestDetailView, "report-strategy-chip"],
    [TradeDetailShell, "trades-strategy-chip"],
  ] as const)("두 결과 화면이 코드 조회·작업공간 링크를 사용한다: %s", async (View, testId) => {
    const client = new QueryClient();
    const { rerender } = render(
      <QueryClientProvider client={client}>
        <View id={BACKTEST.id} />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(screen.getByTestId(testId)).toHaveTextContent("user-a"));
    expect(screen.getByTestId(testId)).toHaveAttribute("href", `/strategies/code?strategy=${ID}`);
    expect(mocks.apiFetch).toHaveBeenCalledWith(`/api/v1/strategies/code/${ID}`, {
      token: "user-a",
    });
    expect(mocks.legacy).not.toHaveBeenCalled();

    mocks.uid = "user-b";
    rerender(
      <QueryClientProvider client={client}>
        <View id={BACKTEST.id} />
      </QueryClientProvider>,
    );
    expect(screen.getByTestId(testId)).not.toHaveTextContent("user-a");
    await waitFor(() => expect(screen.getByTestId(testId)).toHaveTextContent("user-b"));
  });

  it("기존 Pine 결과는 기존 조회·편집기를 유지한다", () => {
    detail = { ...BACKTEST, config: null };
    render(<BacktestDetailView id={BACKTEST.id} />);
    expect(screen.getByTestId("report-strategy-chip")).toHaveTextContent("기존 Pine 전략");
    expect(screen.getByTestId("report-strategy-chip")).toHaveAttribute(
      "href",
      `/strategies/${ID}/edit`,
    );
    expect(mocks.legacy).toHaveBeenCalledWith(ID);
    expect(mocks.apiFetch).not.toHaveBeenCalled();
  });
});
