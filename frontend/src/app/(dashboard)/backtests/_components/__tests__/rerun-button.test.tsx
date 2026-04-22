import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { BacktestDetail } from "@/features/backtest/schemas";

const mockMutate = vi.fn();
const mockPush = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

let pendingState = false;
let triggerSuccess = true;
let createdId = "new-backtest-id";
let mutationError: Error | null = null;

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: (opts: {
    onSuccess?: (r: { backtest_id: string }) => void;
    onError?: (e: Error) => void;
  }) => ({
    mutate: (...args: unknown[]) => {
      mockMutate(...args);
      if (mutationError) {
        opts.onError?.(mutationError);
        return;
      }
      if (triggerSuccess) {
        opts.onSuccess?.({ backtest_id: createdId });
      }
    },
    isPending: pendingState,
  }),
}));

import { RerunButton } from "../rerun-button";

const BACKTEST: BacktestDetail = {
  id: "old-id-1234-1234-1234-123456789012",
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
  mockMutate.mockClear();
  mockPush.mockClear();
  mockToastSuccess.mockClear();
  mockToastError.mockClear();
  pendingState = false;
  triggerSuccess = true;
  createdId = "new-backtest-id";
  mutationError = null;
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("RerunButton", () => {
  it("isEnabled=true (terminal 상태) 일 때 활성화된다", () => {
    render(<RerunButton backtest={BACKTEST} isEnabled={true} />);
    const btn = screen.getByRole("button", { name: /재실행/ });
    expect(btn).not.toBeDisabled();
  });

  it("isEnabled=false (running/queued/cancelling) 일 때 비활성화된다", () => {
    render(<RerunButton backtest={BACKTEST} isEnabled={false} />);
    const btn = screen.getByRole("button", { name: /재실행/ });
    expect(btn).toBeDisabled();
  });

  it("클릭 시 동일 파라미터로 mutate 호출 + 성공 시 router.push + toast.success", () => {
    render(<RerunButton backtest={BACKTEST} isEnabled={true} />);
    fireEvent.click(screen.getByRole("button", { name: /재실행/ }));

    expect(mockMutate).toHaveBeenCalledTimes(1);
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        strategy_id: BACKTEST.strategy_id,
        symbol: BACKTEST.symbol,
        timeframe: BACKTEST.timeframe,
        period_start: BACKTEST.period_start,
        period_end: BACKTEST.period_end,
        initial_capital: 10000,
      }),
    );
    expect(mockPush).toHaveBeenCalledWith("/backtests/new-backtest-id");
    expect(mockToastSuccess).toHaveBeenCalledWith("재실행 시작");
  });

  it("mutation 실패 시 toast.error 노출 + router.push 호출되지 않음", () => {
    mutationError = new Error("Network down");
    render(<RerunButton backtest={BACKTEST} isEnabled={true} />);
    fireEvent.click(screen.getByRole("button", { name: /재실행/ }));

    expect(mockMutate).toHaveBeenCalledTimes(1);
    expect(mockToastError).toHaveBeenCalledWith("재실행 실패: Network down");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("isPending=true 일 때 (mutation 진행 중) 비활성화된다", () => {
    pendingState = true;
    render(<RerunButton backtest={BACKTEST} isEnabled={true} />);
    const btn = screen.getByRole("button", { name: /재실행/ });
    expect(btn).toBeDisabled();
  });

  it("initial_capital 이 비유효 (0) 인 경우 mutate 호출 안 됨 + toast.error", () => {
    const broken = { ...BACKTEST, initial_capital: 0 } as unknown as BacktestDetail;
    render(<RerunButton backtest={broken} isEnabled={true} />);
    fireEvent.click(screen.getByRole("button", { name: /재실행/ }));

    expect(mockMutate).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith(
      expect.stringContaining("유효하지 않은 초기 자본"),
    );
  });
});
