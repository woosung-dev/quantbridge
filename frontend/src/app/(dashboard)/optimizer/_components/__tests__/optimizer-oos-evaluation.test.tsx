// C13 진짜 OOS — OptimizerOosEvaluation: CTA → optimizer spec(param_space+kind) WFO submit.

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StressTestDetail } from "@/features/backtest/schemas";
import type { ParamSpace } from "@/features/optimizer/schemas";

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

const PARAM_SPACE = {
  schema_version: 1,
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  max_evaluations: 9,
  parameters: { emaPeriod: { kind: "integer", min: 5, max: 10, step: 5 } },
} as unknown as ParamSpace;

function walkForwardDetail(
  status: StressTestDetail["status"],
  { skipped = 0 }: { skipped?: number } = {},
): StressTestDetail {
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
                selected_params: { emaPeriod: "7" },
              },
            ],
            aggregate_oos_return: 0.05,
            degradation_ratio: "4.0",
            valid_positive_regime: true,
            total_possible_folds: 1,
            was_truncated: false,
            reoptimized_per_fold: true,
            degenerate_folds_skipped: skipped,
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

function renderOos(sectionNum = "04") {
  return render(
    <OptimizerOosEvaluation
      backtestId={BACKTEST_ID}
      paramSpace={PARAM_SPACE}
      kind="grid_search"
      sectionNum={sectionNum}
    />,
  );
}

beforeEach(() => {
  wfMutation = { mutate: vi.fn(), isPending: false };
  lastWfOpts = null;
  stressData = undefined;
});

describe("OptimizerOosEvaluation (true WFO)", () => {
  it("CTA + 진짜 WFO 정직 고지 렌더", () => {
    renderOos();
    expect(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    ).toBeInTheDocument();
    // 섹션 번호는 페이지 조립부가 주입 — grid 는 03 파라미터 안정성 뒤라 04 (중복 03 회귀 방지).
    expect(screen.getByText("04")).toBeInTheDocument();
    // 진짜 out-of-sample 고지 (낙관 경고 X).
    expect(screen.getByText(/진짜 out-of-sample/)).toBeInTheDocument();
    expect(screen.getByText(/in-sample.*재최적화/)).toBeInTheDocument();
    // 구 fixed-param 낙관 고지는 제거됨.
    expect(screen.queryByText(/fold별 재최적화 아님/)).not.toBeInTheDocument();
  });

  it("CTA 클릭 시 optimizer_param_space + optimizer_kind 로 WFO submit", () => {
    renderOos();
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
        optimizer_kind: "grid_search",
      },
    });
    expect(arg.params.optimizer_param_space).toEqual(PARAM_SPACE);
    expect(arg.params.best_params).toBeUndefined();
  });

  it("completed → 재최적화 뱃지 + WalkForwardBarChart 임베드", () => {
    stressData = walkForwardDetail("completed");
    renderOos();
    fireEvent.click(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    );
    act(() => {
      lastWfOpts?.onSuccess?.({ stress_test_id: STRESS_ID });
    });
    expect(screen.getByText(/각 fold 재최적화됨/)).toBeInTheDocument();
    expect(screen.getByText(/Degradation ratio/)).toBeInTheDocument();
    // fold별 재최적화 파라미터 노출 (drift = fragility 정직 신호).
    expect(screen.getByText(/emaPeriod=7/)).toBeInTheDocument();
  });

  it("degenerate_folds_skipped > 0 → fragility 경고 노출", () => {
    stressData = walkForwardDetail("completed", { skipped: 2 });
    renderOos();
    fireEvent.click(
      screen.getByRole("button", { name: /Walk-Forward OOS 검증/ }),
    );
    act(() => {
      lastWfOpts?.onSuccess?.({ stress_test_id: STRESS_ID });
    });
    expect(screen.getByText(/2.*fold.*제외/)).toBeInTheDocument();
  });

  it("running 상태에서 CTA disabled", () => {
    stressData = walkForwardDetail("running");
    renderOos();
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
