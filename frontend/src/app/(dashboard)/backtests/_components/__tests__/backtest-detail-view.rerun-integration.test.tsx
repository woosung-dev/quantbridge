// W5 통합 테스트: BacktestDetailView 헤더의 RerunButton 이 effectiveStatus
// 에 따라 올바르게 enable/disable 되는지 직접 검증. codex review 보완.

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
  // Sprint 41 Worker H — ShareButton 이 detail-view 헤더에 추가됨. share hook 도 mock.
  useCreateBacktestShare: () => ({ mutate: vi.fn(), isPending: false }),
  useRevokeBacktestShare: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// BacktestDetailView import must come AFTER vi.mock calls
import { BacktestDetailView } from "../backtest-detail-view";

const BASE_DETAIL: BacktestDetail = {
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
  metrics: null,
  equity_curve: null,
  error: null,
} as unknown as BacktestDetail;

beforeEach(() => {
  progressStatus = undefined;
  detailData = { ...BASE_DETAIL };
});

describe("BacktestDetailView — RerunButton 연결", () => {
  it.each(["queued", "running", "cancelling"] as const)(
    "effectiveStatus=%s 이면 재실행 버튼이 비활성화",
    (status) => {
      detailData = { ...BASE_DETAIL, status };
      progressStatus = status;
      render(<BacktestDetailView id="abc" />);
      const btn = screen.getByRole("button", { name: /재실행/ });
      expect(btn).toBeDisabled();
    },
  );

  it.each(["completed", "failed", "cancelled"] as const)(
    "effectiveStatus=%s 이면 재실행 버튼이 활성화",
    (status) => {
      detailData = { ...BASE_DETAIL, status };
      progressStatus = status;
      render(<BacktestDetailView id="abc" />);
      const btn = screen.getByRole("button", { name: /재실행/ });
      expect(btn).not.toBeDisabled();
    },
  );

  // 부모가 effectiveStatus = progress.data?.status ?? bt.status 를 쓰는지
  // 검증하기 위한 상충 케이스 (codex review 보완). detail 과 progress 가
  // 다를 때 progress 가 우선 — 만약 부모가 bt.status 만 보면 실패.
  it("detail.status=completed 인데 progress.status=running 이면 비활성화 (progress 우선)", () => {
    detailData = { ...BASE_DETAIL, status: "completed" };
    progressStatus = "running";
    render(<BacktestDetailView id="abc" />);
    const btn = screen.getByRole("button", { name: /재실행/ });
    expect(btn).toBeDisabled();
  });

  it("detail.status=running 인데 progress.status=completed 이면 활성화 (progress 우선)", () => {
    detailData = { ...BASE_DETAIL, status: "running" };
    progressStatus = "completed";
    render(<BacktestDetailView id="abc" />);
    const btn = screen.getByRole("button", { name: /재실행/ });
    expect(btn).not.toBeDisabled();
  });
});
