import { render, screen } from "@testing-library/react";
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
  effective_cost_pct: "0.1625",
  undecomposed_count: 4,
  undecomposed_net: "1.50",
  expected_only_count: 7,
  expected_only_gross: "20",
  actual_only_count: 2,
  actual_only_net: "-4",
  unattributed_count: 3,
  coverage_pct: "28.00",
  sample_n: 12,
  sample_mean_net: "0.458333333333333333",
  sample_sd_net: "1.2",
  sample_required_n: 8,
  sample_sufficient: true,
};

function responseWith(
  session: OutcomeParityScope = COMPLETE_SCOPE,
  strategy: OutcomeParityScope = COMPLETE_SCOPE,
): OutcomeParityResponse {
  return {
    session_id: SESSION_ID,
    session,
    strategy,
    assumption: {
      source: "house_default",
      taker_fee_pct: "0.1",
      slippage_pct: "0.05",
      maker_fee_pct: "0.02",
      implied_round_trip_pct: "0.3",
    },
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

  it("표본이 부족하면 성과 지표 대신 현재와 필요 표본 수를 보여준다", () => {
    const insufficient: OutcomeParityScope = {
      ...COMPLETE_SCOPE,
      sample_n: 4,
      sample_mean_net: "0.88",
      sample_sd_net: "0.12",
      sample_required_n: 10,
      sample_sufficient: false,
    };

    renderLoaded(responseWith(insufficient, insufficient));

    expect(screen.queryByText("표본 평균 순손익")).not.toBeInTheDocument();
    expect(screen.getAllByText("현재 표본 4건, 필요 표본 10건.")).toHaveLength(2);
  });

  it("표본이 충분하면 표본 기반 성과 지표를 보여준다", () => {
    renderLoaded();

    expect(screen.getAllByText("표본 평균 순손익")).toHaveLength(2);
    expect(screen.queryByText(/성과 비율을 표시하지 않습니다/)).not.toBeInTheDocument();
  });

  it("엔진만 청산 버킷을 숨기지 않는다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-expected-only-count")).toHaveTextContent(
      "7건",
    );
  });

  it("대조 커버리지를 표시한다", () => {
    renderLoaded();

    expect(screen.getByTestId("outcome-parity-session-coverage")).toHaveTextContent("28.00%");
  });

  it("비용 가정이 사용자의 백테스트 설정과 다를 수 있음을 고지한다", () => {
    renderLoaded();

    expect(screen.getByText(/백테스트 설정과 다를 수 있습니다/)).toBeInTheDocument();
  });
});
