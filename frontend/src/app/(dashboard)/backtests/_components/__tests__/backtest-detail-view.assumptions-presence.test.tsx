// Sprint 50: AssumptionsCard 공통 lift-up 검증 — Tabs 외부에 1회만 렌더 (overview/stress-test 양쪽 진입 시 동일하게 표시, codex P1#3 / Surface Trust 보존).

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  BacktestDetail,
  BacktestProgressResponse,
} from "@/features/backtest/schemas";

// --- hooks mocks ---------------------------------------------------------

let progressStatus: BacktestProgressResponse["status"] | undefined = undefined;
let detailData: Partial<BacktestDetail> & { status: BacktestDetail["status"] };

vi.mock("@/features/backtest/hooks", () => ({
  useBacktest: () => ({
    data: detailData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
    error: null,
  }),
  useBacktestProgress: () => ({
    data: progressStatus
      ? {
          backtest_id: "x",
          status: progressStatus,
          started_at: null,
          completed_at: null,
          error: null,
          stale: false,
        }
      : undefined,
    refetch: vi.fn(),
  }),
  useBacktestTrades: () => ({
    data: { items: [], total: 0, limit: 200, offset: 0 },
    isLoading: false,
    isError: false,
    error: null,
  }),
  useCreateBacktest: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateBacktestShare: () => ({ mutate: vi.fn(), isPending: false }),
  useRevokeBacktestShare: () => ({ mutate: vi.fn(), isPending: false }),
  useStressTest: () => ({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
  }),
  useCreateMonteCarlo: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateWalkForward: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { BacktestDetailView } from "../backtest-detail-view";

const COMPLETED_DETAIL: BacktestDetail = {
  id: "abc12345-1111-1111-1111-111111111111",
  strategy_id: "11111111-1111-1111-1111-111111111111",
  symbol: "BTC/USDT",
  timeframe: "1h",
  period_start: "2026-01-01T00:00:00Z",
  period_end: "2026-02-01T00:00:00Z",
  status: "completed",
  created_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-02-01T00:00:00Z",
  initial_capital: 10000,
  // Sprint 50 — AssumptionsCard 렌더 조건: status=completed && metrics 둘 다 truthy
  metrics: {
    total_return: 0.1,
    annual_return_pct: 0.5,
    sharpe_ratio: 1.5,
    max_drawdown: 0.1,
    num_trades: 5,
  } as unknown as BacktestDetail["metrics"],
  equity_curve: null,
  config: null,
  error: null,
} as unknown as BacktestDetail;

beforeEach(() => {
  progressStatus = undefined;
  detailData = { ...COMPLETED_DETAIL };
});

describe("BacktestDetailView — AssumptionsCard 공통 lift-up (Sprint 50, codex P1#3)", () => {
  it("status=completed + metrics 시 AssumptionsCard 가 정확히 1회만 렌더 (Tabs 외부)", () => {
    render(<BacktestDetailView id="abc12345-1111-1111-1111-111111111111" />);
    // AssumptionsCard 의 unique label "초기 자본" 1회만 출현 = Tabs 외부 단독 위치
    const initialCapitalLabels = screen.getAllByText("초기 자본");
    expect(initialCapitalLabels).toHaveLength(1);
  });

  it("AssumptionsCard 가 모든 tab 진입 시에도 visible (default overview tab 기준)", () => {
    render(<BacktestDetailView id="abc12345-1111-1111-1111-111111111111" />);
    // 가정박스 5 항목 중 "포지션 모델" 도 표시되는지 (Surface Trust 보존)
    expect(screen.getByText("포지션 모델")).toBeInTheDocument();
    expect(screen.getByText("수수료")).toBeInTheDocument();
  });

  it("status≠completed 시 AssumptionsCard 미렌더 (running 상태)", () => {
    detailData = { ...COMPLETED_DETAIL, status: "running" };
    render(<BacktestDetailView id="abc12345-1111-1111-1111-111111111111" />);
    expect(screen.queryByText("초기 자본")).not.toBeInTheDocument();
  });
});
