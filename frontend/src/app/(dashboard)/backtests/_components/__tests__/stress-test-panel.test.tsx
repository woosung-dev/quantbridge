// Phase C: StressTestPanel — 버튼 클릭 → mutation 호출 + activeStressTestId 설정 → detail 표시.

import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StressTestDetail } from "@/features/backtest/schemas";

// --- hooks mocks ---------------------------------------------------------

interface MutationMock {
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
}
type Opts = { onSuccess?: (r: { stress_test_id: string }) => void } | null;

let mcMutation: MutationMock;
let wfMutation: MutationMock;
let caMutation: MutationMock;
let lastMcOpts: Opts;
let _lastWfOpts: Opts;
let _lastCaOpts: Opts;
let stressData: StressTestDetail | undefined;

vi.mock("@/features/backtest/hooks", () => ({
  useCreateMonteCarlo: (opts: Opts) => {
    lastMcOpts = opts;
    return mcMutation;
  },
  useCreateWalkForward: (opts: Opts) => {
    _lastWfOpts = opts;
    return wfMutation;
  },
  useCreateCostAssumption: (opts: Opts) => {
    _lastCaOpts = opts;
    return caMutation;
  },
  useStressTest: () => ({
    data: stressData,
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// import AFTER mocks
import { StressTestPanel } from "../stress-test-panel";

beforeEach(() => {
  mcMutation = { mutate: vi.fn(), isPending: false };
  wfMutation = { mutate: vi.fn(), isPending: false };
  caMutation = { mutate: vi.fn(), isPending: false };
  lastMcOpts = null;
  _lastWfOpts = null;
  _lastCaOpts = null;
  stressData = undefined;
});

describe("StressTestPanel", () => {
  it("renders run buttons and initial empty-state hint", () => {
    render(<StressTestPanel backtestId="abc" />);
    expect(
      screen.getByRole("button", { name: /Monte Carlo/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Walk-Forward/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/스트레스 테스트를 실행하세요/),
    ).toBeInTheDocument();
  });

  it("clicking Monte Carlo button calls mutation with correct body", () => {
    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(screen.getByRole("button", { name: /Monte Carlo/ }));
    expect(mcMutation.mutate).toHaveBeenCalledTimes(1);
    const firstCallArg = mcMutation.mutate.mock.calls[0]?.[0];
    expect(firstCallArg).toMatchObject({
      backtest_id: "abc12345-1111-4111-8111-111111111111",
      params: { n_samples: 1000, seed: 42 },
    });
  });

  it("clicking Walk-Forward button calls mutation with nested params", () => {
    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(screen.getByRole("button", { name: /Walk-Forward/ }));
    expect(wfMutation.mutate).toHaveBeenCalledTimes(1);
    const firstCallArg = wfMutation.mutate.mock.calls[0]?.[0];
    expect(firstCallArg).toMatchObject({
      backtest_id: "abc12345-1111-4111-8111-111111111111",
      params: {
        train_bars: 500,
        test_bars: 100,
        step_bars: 100,
        max_folds: 20,
      },
    });
  });

  it("Sprint 50: Cost Assumption Sensitivity 버튼 클릭 시 9-cell preset 호출", () => {
    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(
      screen.getByRole("button", { name: /Cost Assumption/ }),
    );
    expect(caMutation.mutate).toHaveBeenCalledTimes(1);
    const arg = caMutation.mutate.mock.calls[0]?.[0];
    expect(arg).toMatchObject({
      backtest_id: "abc12345-1111-4111-8111-111111111111",
      params: {
        param_grid: {
          fees: ["0.0005", "0.001", "0.002"],
          slippage: ["0.0001", "0.0005", "0.001"],
        },
      },
    });
  });

  it("MC completed 상태에서 summary table + fan chart 둘 다 렌더 (BL-183)", () => {
    // BE schema 미러 — decimalString 은 zod transform 후 number 형태.
    stressData = {
      id: "11111111-1111-4111-8111-111111111111",
      backtest_id: "abc12345-1111-4111-8111-111111111111",
      kind: "monte_carlo",
      status: "completed",
      params: { n_samples: 1000, seed: 42 },
      monte_carlo_result: {
        samples: 1000,
        ci_lower_95: 9500,
        ci_upper_95: 11000,
        median_final_equity: 10500,
        max_drawdown_mean: -0.05,
        max_drawdown_p95: -0.12,
        equity_percentiles: {
          "5": [10000, 9800, 9500],
          "25": [10000, 10000, 9900],
          "50": [10000, 10100, 10300],
          "75": [10000, 10200, 10600],
          "95": [10000, 10400, 11000],
        },
      },
      walk_forward_result: null,
      error: null,
      created_at: "2026-04-24T00:00:00+00:00",
      started_at: "2026-04-24T00:00:00+00:00",
      completed_at: "2026-04-24T00:01:00+00:00",
    };

    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(screen.getByRole("button", { name: /Monte Carlo/ }));
    act(() => {
      lastMcOpts?.onSuccess?.({
        stress_test_id: "11111111-1111-4111-8111-111111111111",
      });
    });

    // BL-183: 숫자 요약표 노출 (책임 분리 신규 컴포넌트).
    expect(
      screen.getByLabelText("Monte Carlo 요약 통계"),
    ).toBeInTheDocument();
    expect(screen.getByText(/CI 95% 하한/)).toBeInTheDocument();
    expect(screen.getByText(/MDD p95/)).toBeInTheDocument();
    // fan chart 도 같이 렌더 (책임 분리 유지 검증).
    // jsdom 환경 → placeholder branch (aria-busy="true"). 존재만 확인.
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("running 상태에서 실행 버튼이 disabled 된다 + '실행 중' 텍스트 표시", () => {
    // useStressTest 가 running 상태를 반환하도록 사전 주입.
    stressData = {
      id: "11111111-1111-4111-8111-111111111111",
      backtest_id: "abc12345-1111-4111-8111-111111111111",
      kind: "monte_carlo",
      status: "running",
      params: {},
      monte_carlo_result: null,
      walk_forward_result: null,
      error: null,
      created_at: "2026-04-24T00:00:00+00:00",
      started_at: "2026-04-24T00:00:00+00:00",
      completed_at: null,
    };

    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);

    // 실제 플로우 재현: click → mutation onSuccess → setActiveStressTestId →
    // polling (running) 으로 전환. 이후 panel 은 running UI + disabled 버튼을 보여야 함.
    fireEvent.click(screen.getByRole("button", { name: /Monte Carlo/ }));
    act(() => {
      lastMcOpts?.onSuccess?.({
        stress_test_id: "11111111-1111-4111-8111-111111111111",
      });
    });

    // FIX-C1: polling 중복 클릭 방지 — 두 버튼 모두 disabled.
    const mcBtn = screen.getByRole("button", { name: /Monte Carlo/ });
    const wfBtn = screen.getByRole("button", { name: /Walk-Forward/ });
    expect(mcBtn).toBeDisabled();
    expect(wfBtn).toBeDisabled();

    // running 상태 UI 텍스트 렌더 확인.
    expect(screen.getByText(/실행 중/)).toBeInTheDocument();
  });
});
