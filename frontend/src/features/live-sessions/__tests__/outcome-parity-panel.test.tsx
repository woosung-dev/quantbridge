import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { OutcomeParityResponse, OutcomeParityScope } from "../schemas";

const useLiveSessionOutcomeParityMock = vi.hoisted(() => vi.fn());

vi.mock("../hooks", () => ({
  useLiveSessionOutcomeParity: useLiveSessionOutcomeParityMock,
}));

import { OutcomeParityPanel } from "../components/outcome-parity-panel";

const SESSION_ID = "00000000-0000-4000-a000-000000000001";

const COMPLETE_SCOPE: OutcomeParityScope = {
  matched_count: 12,
  expected_gross: "999.99",
  actual_net: "5.50",
  decomposable_count: 8,
  decomposable_expected_gross: "10.00",
  execution_gap: "-1.25",
  cost: "-3.25",
  decomposable_actual_net: "5.50",
  actual_gross: "8.75",
  round_trip_notional: "2000",
  effective_cost_pct_per_leg: "0.0558",
  effective_cost_pct_round_trip: "0.1116",
  edge_pct_round_trip: "0.55",
  cost_to_edge_ratio: "0.590909090909090909",
  undecomposed_count: 4,
  undecomposed_net: "1.50",
  expected_only_count: 7,
  expected_only_gross: "20",
  expected_only_pending_count: 2,
  expected_only_failed_count: 3,
  expected_only_dispatched_count: 2,
  actual_only_count: 2,
  actual_only_net: "-4",
  ledger_only_count: 1,
  ledger_only_net: "-0.75",
  match_coverage_pct: "28.169014084507042253521126760",
  decomposition_coverage_pct: "66.66666666666666666666666667",
  sample_n: 12,
  sample_mean_net: "0.458333333333333333",
  sample_sd_net: "1.2",
  sample_required_n: 30,
  sample_sufficient: false,
};

const SUFFICIENT_SCOPE: OutcomeParityScope = {
  ...COMPLETE_SCOPE,
  sample_n: 30,
  sample_required_n: 30,
  sample_sufficient: true,
};

function responseWith(
  session: OutcomeParityScope = COMPLETE_SCOPE,
  strategy: OutcomeParityScope = COMPLETE_SCOPE,
  overrides: Partial<
    Pick<OutcomeParityResponse, "ledger_supported" | "strategy_session_count" | "unattributed_count">
  > = {},
): OutcomeParityResponse {
  return {
    session_id: SESSION_ID,
    session,
    strategy,
    unattributed_count: 3,
    ledger_supported: true,
    strategy_session_count: 2,
    assumption: {
      source: "house_default",
      taker_fee_pct: "0.1",
      slippage_pct: "0.05",
      maker_fee_pct: "0.02",
      implied_round_trip_pct: "0.3",
    },
    ...overrides,
  };
}

function renderLoaded(data = responseWith()) {
  useLiveSessionOutcomeParityMock.mockReturnValue({
    data,
    isError: false,
    isLoading: false,
    refetch: vi.fn(),
  });
  return render(<OutcomeParityPanel sessionId={SESSION_ID} />);
}

afterEach(() => {
  useLiveSessionOutcomeParityMock.mockReset();
});

describe("OutcomeParityPanel", () => {
  it("워터폴 첫 값은 전 관측 합이 아닌 decomposable_expected_gross를 쓴다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-waterfall-expected")).toHaveTextContent(
      "10.00",
    );
    expect(screen.getByTestId("outcome-parity-session-expected-gross-total")).toHaveTextContent(
      "999.99",
    );
  });

  it("매칭이 없어도 대조 밖 버킷과 매칭 커버리지를 표시한다", () => {
    const unmatched: OutcomeParityScope = {
      ...COMPLETE_SCOPE,
      matched_count: 0,
      decomposable_count: 0,
      decomposable_expected_gross: null,
      execution_gap: null,
      cost: null,
      decomposable_actual_net: null,
      actual_gross: null,
      round_trip_notional: null,
      effective_cost_pct_per_leg: null,
      effective_cost_pct_round_trip: null,
      undecomposed_count: 0,
      undecomposed_net: "0",
      expected_only_count: 51,
      expected_only_pending_count: 17,
      expected_only_failed_count: 17,
      expected_only_dispatched_count: 17,
      actual_only_count: 0,
      ledger_only_count: 0,
      ledger_only_net: "0",
      match_coverage_pct: "0",
      decomposition_coverage_pct: null,
      sample_n: 0,
      sample_mean_net: null,
      sample_sd_net: null,
      sample_required_n: null,
      sample_sufficient: false,
    };

    renderLoaded(responseWith(unmatched, unmatched));

    expect(screen.getByTestId("outcome-parity-unmatched-warning")).toHaveTextContent(
      "대조된 청산은 없고 미확정만 51건 있습니다.",
    );
    expect(screen.getByTestId("outcome-parity-session-expected-only-count")).toHaveTextContent(
      "51건",
    );
    expect(screen.getByTestId("outcome-parity-session-coverage")).toHaveTextContent("0.00%");
  });

  it("매칭과 모든 버킷이 비면 기존 빈 상태를 표시한다", () => {
    const empty: OutcomeParityScope = {
      ...COMPLETE_SCOPE,
      matched_count: 0,
      decomposable_count: 0,
      undecomposed_count: 0,
      undecomposed_net: "0",
      expected_only_count: 0,
      expected_only_gross: "0",
      expected_only_pending_count: 0,
      expected_only_failed_count: 0,
      expected_only_dispatched_count: 0,
      actual_only_count: 0,
      actual_only_net: "0",
      ledger_only_count: 0,
      ledger_only_net: "0",
      match_coverage_pct: null,
      decomposition_coverage_pct: null,
    };

    renderLoaded(responseWith(empty, empty, { unattributed_count: 0 }));

    expect(screen.getByTestId("outcome-parity-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("outcome-parity-panel")).not.toBeInTheDocument();
  });

  it("비용 분해 불가 매칭은 커버리지 밖 관측에 넣지 않는다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-undecomposed-count")).toHaveTextContent(
      "4건",
    );
    expect(
      within(screen.getByTestId("outcome-parity-session-outside-coverage")).queryByText(
        "매칭됐으나 비용 분해 불가",
      ),
    ).not.toBeInTheDocument();
  });

  it("원장에만 있는 청산을 별도 버킷으로 표시한다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-ledger-only-count")).toHaveTextContent(
      "1건",
    );
    expect(screen.getByTestId("outcome-parity-session-outside-coverage")).toHaveTextContent(
      "거래소 네이티브 TP/SL 등 로컬 주문 없이 실행된 청산입니다",
    );
  });

  it("비용 분해 커버리지가 0이면 워터폴의 반영 표본을 경고한다", () => {
    const undecomposed: OutcomeParityScope = {
      ...COMPLETE_SCOPE,
      decomposable_count: 0,
      decomposable_expected_gross: null,
      execution_gap: null,
      cost: null,
      decomposable_actual_net: null,
      actual_gross: null,
      round_trip_notional: null,
      effective_cost_pct_per_leg: null,
      effective_cost_pct_round_trip: null,
      undecomposed_count: 12,
      undecomposed_net: "5.50",
      decomposition_coverage_pct: "0",
    };

    renderLoaded(responseWith(undecomposed, undecomposed));

    expect(screen.getByTestId("outcome-parity-session-decomposition-coverage")).toHaveTextContent(
      "0.00%",
    );
    expect(screen.getByTestId("outcome-parity-session-waterfall-note")).toHaveTextContent(
      "이 막대는 매칭 12건 중 0건만 반영합니다.",
    );
  });

  it("낮은 매칭 커버리지만 경고 톤으로 표시한다", () => {
    const highCoverage: OutcomeParityScope = {
      ...COMPLETE_SCOPE,
      match_coverage_pct: "95",
    };

    renderLoaded(responseWith(COMPLETE_SCOPE, highCoverage));

    expect(screen.getByTestId("outcome-parity-session-coverage")).toHaveClass(
      "text-[color:var(--warning)]",
    );
    expect(screen.getByTestId("outcome-parity-strategy-coverage")).not.toHaveClass(
      "text-[color:var(--warning)]",
    );
  });

  it("0으로 표현된 순손익에 이익 색을 붙이지 않는다", () => {
    const zeroNet: OutcomeParityScope = {
      ...COMPLETE_SCOPE,
      actual_net: "0.00",
    };

    renderLoaded(responseWith(zeroNet, zeroNet));

    expect(screen.getByTestId("outcome-parity-session-actual-net-total")).toHaveClass(
      "text-foreground",
    );
    expect(screen.getByTestId("outcome-parity-session-actual-net-total")).not.toHaveClass(
      "text-bullish",
    );
  });

  it("1% 이상 퍼센트는 표시 계층에서 소수 둘째 자리까지 반올림한다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-coverage")).toHaveTextContent("28.17%");
  });

  it("1% 미만 비용률은 유효숫자를 보존하고 비교 블록은 왕복 값을 쓴다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-effective-cost-pct-per-leg")).toHaveTextContent(
      "0.0558%",
    );
    expect(
      screen.getByTestId("outcome-parity-session-effective-cost-pct-round-trip"),
    ).toHaveTextContent("0.1116%");
    expect(screen.getByTestId("outcome-parity-session-assumption-compare")).toHaveTextContent(
      "0.1116%",
    );
  });

  it("표본 게이트가 열리면 엣지율과 비용 엣지 배수를 표시한다", () => {
    renderLoaded(responseWith(SUFFICIENT_SCOPE, SUFFICIENT_SCOPE));

    expect(screen.getByTestId("outcome-parity-session-edge-pct-round-trip")).toHaveTextContent(
      "0.5500%",
    );
    expect(screen.getByTestId("outcome-parity-session-cost-to-edge-ratio")).toHaveTextContent(
      "0.590909090909090909",
    );
  });

  it("표본 게이트가 닫히면 엣지율과 비용 엣지 배수를 표시하지 않는다", () => {
    renderLoaded();

    expect(screen.queryByTestId("outcome-parity-session-edge-pct-round-trip")).not.toBeInTheDocument();
    expect(screen.queryByTestId("outcome-parity-session-cost-to-edge-ratio")).not.toBeInTheDocument();
  });

  it("분해 가능한 거래소 gross를 워터폴 근처에 표시한다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-actual-gross")).toHaveTextContent("8.75");
  });

  it("원장 미지원 거래소는 워터폴 대신 비용 분해 불가 안내를 표시한다", () => {
    renderLoaded(responseWith(COMPLETE_SCOPE, COMPLETE_SCOPE, { ledger_supported: false }));

    expect(screen.queryByTestId("outcome-parity-session-waterfall")).not.toBeInTheDocument();
    expect(screen.getByTestId("outcome-parity-session-ledger-unsupported-message")).toHaveTextContent(
      "이 거래소는 청산 원장 적재가 아직 지원되지 않아 비용 분해를 할 수 없습니다.",
    );
  });

  it("계정 원장 진단과 전략 세션 수를 스코프 밖에서 표시한다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-account-diagnostic")).toHaveTextContent(
      "미귀속 원장 행 (계정 전체, 기간 무관): 3건",
    );
    expect(screen.getByTestId("outcome-parity-strategy-scope-badge")).toHaveTextContent("세션 2건");
  });

  it("엔진 기본 가정이 사용자의 백테스트 설정이 아님과 maker 수수료를 고지한다", () => {
    renderLoaded();

    expect(screen.getByText(/귀하의 백테스트 설정이 아닙니다/)).toBeInTheDocument();
    expect(screen.getByTestId("outcome-parity-assumption-maker-fee")).toHaveTextContent(
      "0.0200%",
    );
    expect(screen.getByText(/TP 지정가 청산은 maker 수수료라 이 왕복 가정은 과대계상입니다/)).toBeInTheDocument();
  });
});
