// C13 — OptimizerOosEvaluation: CTA 클릭 → best_params 주입 walk-forward submit → 결과 임베드.

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StressTestDetail } from "@/features/backtest/schemas";

interface MutationMock {
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
}
type Opts = { onSuccess?: (r: { stress_test_id: string }) => void } | null;

let wfMutation: MutationMock;
let lastWfOpts: Opts;
let stressData: StressTestDetail | undefined;

vi.mock("@/features/backtest/hooks", () => ({
  useCreateWalkForward: (opts: Opts) => {
    lastWfOpts = opts;
    return wfMutation;
  },
  useStressTest: () => ({
    data: stressData,
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

// import AFTER mocks
import { OptimizerOosEvaluation } from "../optimizer-oos-evaluation";

const BACKTEST_ID = "abc12345-1111-4111-8111-111111111111";
const STRESS_ID = "11111111-1111-4111-8111-111111111111";

function walkForwardDetail(status: StressTestDetail["status"]): StressTestDetail {
  return {
    id: STRESS_ID,
    backtest_id: BACKTEST_ID,
    kind: "walk_forward",
    status,
    params: {},
    monte_carlo_result: null,
    walk_forward_result:
      status === "completed"
        ? {
            folds: [
              {
                fold_index: 0,
                train_start: "2026-01-01T00:00:00+00:00",
                train_end: "2026-02-01T00:00:00+00:00",
                test_start: "2026-02-01T00:00:00+00:00",
                test_end: "2026-03-01T00:00:00+00:00",
                in_sample_return: 0.2,
                out_of_sample_return: 0.05,
                oos_sharpe: 0.4,
                num_trades_oos: 5,
              },
            ],
            aggregate_oos_return: 0.05,
            degradation_ratio: "4.0",
            valid_positive_regime: true,
            total_possible_folds: 1,
            was_truncated: false,
          }
        : null,
    cost_assumption_result: null,
    param_stability_result: null,
    error: null,
    created_at: "2026-03-01T00:00:00+00:00",
    started_at: "2026-03-01T00:00:00+00:00",
    completed_at: status === "completed" ? "2026-03-01T00:01:00+00:00" : null,
  };
}

beforeEach(() => {
  wfMutation = { mutate: vi.fn(), isPending: false };
  lastWfOpts = null;
  stressData = undefined;
});

describe("OptimizerOosEvaluation", () => {
  it("CTA + 정직 라벨(과최적 경고) 렌더", () => {
    render(
      <OptimizerOosEvaluation backtestId={BACKTEST_ID} bestParams={{ ema: 20 }} />,
    );
    expect(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/IS≫OOS/)).toBeInTheDocument();
  });

  it("정직 고지: fold별 재최적화 아님 + OOS 가 파라미터 선택 기간과 겹쳐 낙관 가능 경고", () => {
    render(
      <OptimizerOosEvaluation backtestId={BACKTEST_ID} bestParams={{ ema: 20 }} />,
    );
    expect(screen.getByText(/fold별 재최적화 아님/)).toBeInTheDocument();
    expect(
      screen.getByText(/진짜 out-of-sample 보다 낙관적/),
    ).toBeInTheDocument();
  });

  it("CTA 클릭 시 best_params + backtest_id 로 walk-forward submit", () => {
    render(
      <OptimizerOosEvaluation
        backtestId={BACKTEST_ID}
        bestParams={{ ema: 20, sl: 2.5 }}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    );
    expect(wfMutation.mutate).toHaveBeenCalledTimes(1);
    const arg = wfMutation.mutate.mock.calls[0]?.[0];
    expect(arg).toMatchObject({
      backtest_id: BACKTEST_ID,
      params: {
        train_bars: 500,
        test_bars: 100,
        step_bars: 100,
        max_folds: 20,
        best_params: { ema: 20, sl: 2.5 },
      },
    });
  });

  it("completed → WalkForwardBarChart(degradation 텍스트) 임베드", () => {
    stressData = walkForwardDetail("completed");
    render(
      <OptimizerOosEvaluation backtestId={BACKTEST_ID} bestParams={{ ema: 20 }} />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    );
    act(() => {
      lastWfOpts?.onSuccess?.({ stress_test_id: STRESS_ID });
    });
    expect(screen.getByText(/Degradation ratio/)).toBeInTheDocument();
  });

  it("running 상태에서 CTA disabled", () => {
    stressData = walkForwardDetail("running");
    render(
      <OptimizerOosEvaluation backtestId={BACKTEST_ID} bestParams={{ ema: 20 }} />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    );
    act(() => {
      lastWfOpts?.onSuccess?.({ stress_test_id: STRESS_ID });
    });
    expect(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    ).toBeDisabled();
  });
});
