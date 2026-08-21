// Phase C: StressTestPanel — 버튼 클릭 → mutation 호출 + activeStressTestId 설정 → detail 표시.

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StressTestDetail, StressTestSummary } from "@/features/backtest/schemas";

// --- hooks mocks ---------------------------------------------------------

interface MutationMock {
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
}
type Opts = { onSuccess?: (r: { stress_test_id: string }) => void } | null;

let mcMutation: MutationMock;
let wfMutation: MutationMock;
let caMutation: MutationMock;
let psMutation: MutationMock;
let lastMcOpts: Opts;
let _lastWfOpts: Opts;
let _lastCaOpts: Opts;
let lastPsOpts: Opts;
let stressData: StressTestDetail | undefined;
let historyItems: StressTestSummary[] | undefined;
// [BL-414] 서버가 보고하는 전체 건수. 표의 잘림 고지를 재려면 items.length 와 갈라야 한다.
let historyTotal: number | undefined;
let requestedStressTestId: string | null | undefined;

// [BL-414] 이력 목록 헬퍼 — BE 는 created_at 내림차순으로 준다.
function makeSummary(
  over: Partial<StressTestSummary> & Pick<StressTestSummary, "id">,
): StressTestSummary {
  return {
    backtest_id: "abc12345-1111-4111-8111-111111111111",
    kind: "monte_carlo",
    status: "completed",
    created_at: "2026-04-24T00:00:00+00:00",
    completed_at: "2026-04-24T00:01:00+00:00",
    headline_metric: { key: "max_drawdown_p95", value: "-0.12" },
    ...over,
  };
}

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
  useCreateParamStability: (opts: Opts) => {
    lastPsOpts = opts;
    return psMutation;
  },
  useStressTestHistory: () => ({
    data:
      historyItems === undefined
        ? undefined
        : {
            items: historyItems,
            total: historyTotal ?? historyItems.length,
            limit: 20,
            offset: 0,
          },
    isLoading: false,
    isError: false,
  }),
  useStressTest: (id: string | null) => {
    requestedStressTestId = id;
    return {
      data: stressData,
      isLoading: false,
      isError: false,
      error: null,
    };
  },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// import AFTER mocks
import { StressTestPanel } from "@/features/backtest/components/stress-test-panel";
import { DEFAULT_FEES_PCT, DEFAULT_SLIPPAGE_PCT } from "@/features/backtest/cost-defaults";

beforeEach(() => {
  mcMutation = { mutate: vi.fn(), isPending: false };
  wfMutation = { mutate: vi.fn(), isPending: false };
  caMutation = { mutate: vi.fn(), isPending: false };
  psMutation = { mutate: vi.fn(), isPending: false };
  lastMcOpts = null;
  _lastWfOpts = null;
  _lastCaOpts = null;
  lastPsOpts = null;
  stressData = undefined;
  historyItems = undefined;
  historyTotal = undefined;
  requestedStressTestId = undefined;
});

describe("StressTestPanel", () => {
  it("renders run buttons and initial empty-state hint", () => {
    render(<StressTestPanel backtestId="abc" />);
    expect(screen.getByRole("button", { name: /Monte Carlo/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Walk-Forward/ })).toBeInTheDocument();
    expect(screen.getByText(/스트레스 테스트를 실행하세요/)).toBeInTheDocument();
  });

  it("스트레스 테스트가 없으면 빈 패널을 렌더한다", () => {
    historyItems = [];

    render(<StressTestPanel backtestId="abc" />);

    expect(requestedStressTestId).toBeNull();
    expect(screen.getByText(/스트레스 테스트를 실행하세요/)).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: /Cost Assumption/ }));
    expect(caMutation.mutate).toHaveBeenCalledTimes(1);
    const arg = caMutation.mutate.mock.calls[0]?.[0];
    expect(arg.backtest_id).toBe("abc12345-1111-4111-8111-111111111111");
    expect(arg.params.param_grid.fees).toHaveLength(3);
    expect(arg.params.param_grid.slippage).toHaveLength(3);
  });

  // ★[BL-730 / codex Standards-5] — 기본값을 넣느라 **보수적 상단을 지우지 않았다**.
  //   종전 격자의 상단(fees 0.002 · slippage 0.001)은 과거 실행과의 비교 기준이라
  //   유지해야 한다. 「기본값 포함」과 「상단 보존」은 양립 가능하므로 둘 다 단언한다.
  it("BL-730: 격자가 종전 상단(0.002 / 0.001)을 유지한다", () => {
    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(screen.getByRole("button", { name: /Cost Assumption/ }));
    const grid = caMutation.mutate.mock.calls[0]?.[0].params.param_grid;
    expect(grid.fees).toContain("0.002");
    expect(grid.slippage).toContain("0.001");
  });

  // ★[BL-730] — 값이 아니라 **계약**을 잰다. 종전 케이스는 격자 리터럴 6개를 그대로 베껴
  //   단언했는데, 그래서 격자 최저점이 실제 기본값(0.00055/0.00014)보다 낮아도 초록이었다.
  //   기본값이 격자 밖이면 「지금 설정으로 돌리면 어떻게 되나」를 이 패널로 재현할 수 없다.
  //   상수를 import 해서 재므로 기본값이 또 바뀌어도 이 계약은 살아 있다.
  it("BL-730: 비용 민감도 격자에 **현재 기본값**이 들어 있다", () => {
    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(screen.getByRole("button", { name: /Cost Assumption/ }));
    const grid = caMutation.mutate.mock.calls[0]?.[0].params.param_grid;
    expect(grid.fees).toContain(String(DEFAULT_FEES_PCT));
    expect(grid.slippage).toContain(String(DEFAULT_SLIPPAGE_PCT));
    // ★민감도 격자는 **서로 다른 3점**이어야 한다 — [base, base, base] 도 위 두 단언을
    //   통과하는데 그건 민감도를 전혀 재지 않는다 (2026-08-15 codex Standards-6).
    expect(new Set(grid.fees).size).toBe(3);
    expect(new Set(grid.slippage).size).toBe(3);
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
    expect(screen.getByLabelText("Monte Carlo 요약 통계")).toBeInTheDocument();
    expect(screen.getByText(/CI 95% 하한/)).toBeInTheDocument();
    expect(screen.getByText(/MDD p95/)).toBeInTheDocument();
    // fan chart 도 같이 렌더 (책임 분리 유지 검증).
    // jsdom 환경 → placeholder branch (aria-busy="true"). 존재만 확인.
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("리로드 시 최신 스트레스 테스트 결과를 렌더한다", () => {
    const latestStressTest = makeSummary({
      id: "11111111-1111-4111-8111-111111111111",
    });
    historyItems = [latestStressTest];
    stressData = {
      id: latestStressTest.id,
      backtest_id: latestStressTest.backtest_id,
      kind: "monte_carlo",
      status: "completed",
      params: {},
      monte_carlo_result: {
        samples: 1000,
        ci_lower_95: 9500,
        ci_upper_95: 11000,
        median_final_equity: 10500,
        max_drawdown_mean: -0.05,
        max_drawdown_p95: -0.12,
        equity_percentiles: {},
      },
      walk_forward_result: null,
      error: null,
      created_at: latestStressTest.created_at,
      started_at: latestStressTest.created_at,
      completed_at: latestStressTest.completed_at,
    };

    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);

    expect(requestedStressTestId).toBe(latestStressTest.id);
    expect(screen.getByLabelText("Monte Carlo 요약 통계")).toBeInTheDocument();
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

  // Sprint 52 BL-223 — Param Stability wire-up
  it("Param Stability 버튼 클릭 시 form toggle + 제출 시 psMutation.mutate 호출", () => {
    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    // 초기 form 미표시
    expect(screen.queryByTestId("param-stability-form")).not.toBeInTheDocument();
    // 버튼 클릭 → form 표시
    fireEvent.click(screen.getByRole("button", { name: "Param Stability 실행" }));
    expect(screen.getByTestId("param-stability-form")).toBeInTheDocument();
    // form 제출 → mutation 호출
    fireEvent.click(screen.getByRole("button", { name: "Param Stability 실행" }));
    // 첫 번째는 panel 버튼이지만 form 내부 submit 버튼도 같은 라벨 → 같은 form 의 submit 버튼이 호출됨
    // 정확한 검증: 4 개 button (panel 4 + form 2 = 6) 중 form submit 만 mutation 호출
    expect(psMutation.mutate).toHaveBeenCalled();
    const payload = psMutation.mutate.mock.calls[0]?.[0] as {
      backtest_id: string;
      params: { param_grid: Record<string, string[]> };
    };
    expect(payload.backtest_id).toBe("abc12345-1111-4111-8111-111111111111");
    expect(Object.keys(payload.params.param_grid)).toEqual(["emaPeriod", "stopLossPct"]);
  });

  it("psMutation onSuccess → activeStressTestId 설정 + form 자동 닫힘", () => {
    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(screen.getByRole("button", { name: "Param Stability 실행" }));
    expect(screen.getByTestId("param-stability-form")).toBeInTheDocument();

    act(() => {
      lastPsOpts?.onSuccess?.({
        stress_test_id: "22222222-2222-4222-8222-222222222222",
      });
    });
    // form 자동 닫힘 + 버튼 라벨 "실행" 으로 복귀
    expect(screen.queryByTestId("param-stability-form")).not.toBeInTheDocument();
  });

  it("param_stability completed → ParamStabilityHeatmap 분기 렌더", () => {
    stressData = {
      id: "22222222-2222-4222-8222-222222222222",
      backtest_id: "abc12345-1111-4111-8111-111111111111",
      kind: "param_stability",
      status: "completed",
      params: {},
      monte_carlo_result: null,
      walk_forward_result: null,
      cost_assumption_result: null,
      param_stability_result: {
        param1_name: "emaPeriod",
        param2_name: "stopLossPct",
        param1_values: ["10", "20", "30"],
        param2_values: ["1.0", "2.0", "3.0"],
        cells: Array.from({ length: 9 }, () => ({
          param1_value: "10",
          param2_value: "1.0",
          sharpe: "0.5",
          total_return: "0.05",
          max_drawdown: "-0.02",
          num_trades: 10,
          is_degenerate: false,
        })),
      },
      error: null,
      created_at: "2026-05-11T00:00:00+00:00",
      started_at: "2026-05-11T00:00:00+00:00",
      completed_at: "2026-05-11T00:01:00+00:00",
    };

    render(<StressTestPanel backtestId="abc12345-1111-4111-8111-111111111111" />);
    fireEvent.click(screen.getByRole("button", { name: "Param Stability 실행" }));
    act(() => {
      lastPsOpts?.onSuccess?.({
        stress_test_id: "22222222-2222-4222-8222-222222222222",
      });
    });

    // heatmap 의 axis 변수명 노출 검증
    expect(screen.getAllByText(/emaPeriod/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/stopLossPct/).length).toBeGreaterThan(0);
  });
});

// [BL-414] 이력 표. ★패널을 통해 렌더한다 — 표 컴포넌트에 props 를 직접 넣어 재면
// "패널이 이력 훅 대신 최신 1건 훅을 쓴다" 는 변이가 red 를 못 낸다 (AGENTS.md §10 의무 2).
describe("StressTestPanel — 스트레스 테스트 이력 ([BL-414])", () => {
  const BACKTEST_ID = "abc12345-1111-4111-8111-111111111111";

  it("이력이 2건이면 2행이 보인다", () => {
    historyItems = [
      makeSummary({
        id: "11111111-1111-4111-8111-111111111111",
        kind: "walk_forward",
        headline_metric: { key: "degradation_ratio", value: "0.42" },
      }),
      makeSummary({ id: "11111111-1111-4111-8111-111111111112" }),
    ];

    render(<StressTestPanel backtestId={BACKTEST_ID} />);

    expect(screen.getAllByTestId("stress-test-history-row")).toHaveLength(2);
    // 종류가 행마다 구분돼 보인다 — 안 그러면 이력 목록이 무의미하다.
    expect(screen.getByText("워크포워드")).toBeInTheDocument();
    expect(screen.getByText("몬테카를로")).toBeInTheDocument();
  });

  it("이력이 0건이면 그렇게 말한다", () => {
    historyItems = [];

    render(<StressTestPanel backtestId={BACKTEST_ID} />);

    expect(screen.queryAllByTestId("stress-test-history-row")).toHaveLength(0);
    expect(screen.getByText(/아직 실행한 스트레스 테스트가 없습니다/)).toBeInTheDocument();
  });

  // ★[BL-465] — "없음" 과 "0" 을 같게 렌더하면 화면이 거짓말을 한다. 실패한 실행의
  //   지표 칸은 0 이 아니라 빈칸이어야 하고, 상태는 "실패" 로 보여야 한다.
  it("FAILED 행은 상태가 보이고 지표 칸이 0 이 아니라 빈칸이다", () => {
    historyItems = [
      makeSummary({
        id: "11111111-1111-4111-8111-111111111113",
        status: "failed",
        headline_metric: null,
      }),
    ];

    render(<StressTestPanel backtestId={BACKTEST_ID} />);

    expect(screen.getByText("실패")).toBeInTheDocument();
    const metricCell = screen.getByTestId("stress-test-history-metric");
    expect(metricCell).toHaveTextContent("—");
    expect(metricCell.textContent).not.toMatch(/0/);
  });

  it("행을 고르면 그 실행의 상세를 요청한다", () => {
    const older = "11111111-1111-4111-8111-111111111114";
    historyItems = [
      makeSummary({ id: "11111111-1111-4111-8111-111111111115" }),
      makeSummary({ id: older }),
    ];

    render(<StressTestPanel backtestId={BACKTEST_ID} />);

    // 기본값은 최신(items[0]) 이다.
    expect(requestedStressTestId).toBe("11111111-1111-4111-8111-111111111115");

    const rows = screen.getAllByTestId("stress-test-history-row");
    const olderRow = rows[1];
    expect(olderRow).toBeDefined();
    fireEvent.click(
      within(olderRow as HTMLElement).getByRole("button", {
        name: "이 실행 결과 보기",
      }),
    );

    expect(requestedStressTestId).toBe(older);
  });
});

// ── [BL-414] codex 적대 리뷰 처분 (2026-08-17) ────────────────────────────────
describe("StressTestPanel — 이력 1페이지 상한과 지표 표기 ([BL-414] codex P1·P2)", () => {
  const BACKTEST_ID = "abc12345-1111-4111-8111-111111111111";

  it("P1: 전체가 1페이지보다 많으면 잘렸다고 고지한다", () => {
    historyItems = [
      makeSummary({ id: "11111111-1111-4111-8111-111111111201" }),
      makeSummary({ id: "11111111-1111-4111-8111-111111111202" }),
    ];
    historyTotal = 21; // 서버에는 21건, 화면에는 2건

    render(<StressTestPanel backtestId={BACKTEST_ID} />);

    const notice = screen.getByTestId("stress-test-history-truncated");
    expect(notice).toHaveTextContent("최근 2건만 표시합니다 (전체 21건).");
  });

  it("P1 음성 대조: 전체가 화면과 같으면 고지가 없다", () => {
    historyItems = [
      makeSummary({ id: "11111111-1111-4111-8111-111111111203" }),
      makeSummary({ id: "11111111-1111-4111-8111-111111111204" }),
    ];
    historyTotal = 2;

    render(<StressTestPanel backtestId={BACKTEST_ID} />);

    expect(screen.queryByTestId("stress-test-history-truncated")).not.toBeInTheDocument();
  });

  it("P2: 열화 비율이 Infinity 면 ∞ 로 그리고 무데이터(—)와 구분한다", () => {
    historyItems = [
      makeSummary({
        id: "11111111-1111-4111-8111-111111111205",
        kind: "walk_forward",
        headline_metric: { key: "degradation_ratio", value: "Infinity" },
      }),
      makeSummary({
        id: "11111111-1111-4111-8111-111111111206",
        kind: "walk_forward",
        status: "failed",
        headline_metric: null,
      }),
    ];

    render(<StressTestPanel backtestId={BACKTEST_ID} />);

    const cells = screen.getAllByTestId("stress-test-history-metric");
    expect(cells[0]).toHaveTextContent("∞");
    // ★같은 열의 무데이터 행과 같게 그리면 안 된다.
    expect(cells[0]).not.toHaveTextContent("—");
    expect(cells[1]).toHaveTextContent("—");
    expect(cells[1]).not.toHaveTextContent("∞");
  });
});
