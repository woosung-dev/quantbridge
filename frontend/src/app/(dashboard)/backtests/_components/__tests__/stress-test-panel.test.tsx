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
let lastMcOpts: Opts;
let _lastWfOpts: Opts;
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
  lastMcOpts = null;
  _lastWfOpts = null;
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
