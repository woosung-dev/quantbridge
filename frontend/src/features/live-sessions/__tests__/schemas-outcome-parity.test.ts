import { describe, expect, it } from "vitest";

import { OutcomeParityResponseSchema } from "../schemas";

const sessionId = "00000000-0000-4000-a000-000000000001";

const nullScope = {
  matched_count: 1,
  expected_gross: "123.456789123456789",
  actual_net: "120.000000000000001",
  decomposable_count: 0,
  decomposable_expected_gross: null,
  execution_gap: null,
  cost: null,
  decomposable_actual_net: null,
  actual_gross: null,
  round_trip_notional: null,
  effective_cost_pct_per_leg: null,
  effective_cost_pct_round_trip: null,
  edge_pct_round_trip: null,
  cost_to_edge_ratio: null,
  undecomposed_count: 1,
  undecomposed_net: "120.000000000000001",
  expected_only_count: 2,
  expected_only_gross: "4.5",
  expected_only_pending_count: 1,
  expected_only_failed_count: 1,
  expected_only_dispatched_count: 0,
  actual_only_count: 3,
  actual_only_net: "-2.5",
  ledger_only_count: 0,
  ledger_only_net: "0",
  match_coverage_pct: null,
  decomposition_coverage_pct: null,
  sample_n: 1,
  sample_mean_net: null,
  sample_sd_net: null,
  sample_required_n: null,
  sample_sufficient: false,
};

describe("OutcomeParityResponseSchema", () => {
  it("nullable Decimal 필드는 null을 보존하고 숫자 Decimal은 문자열로 유지한다", () => {
    const parsed = OutcomeParityResponseSchema.parse({
      session_id: sessionId,
      session: nullScope,
      strategy: nullScope,
      unattributed_count: 4,
      ledger_supported: true,
      strategy_session_count: 2,
      assumption: {
        source: "house_default",
        taker_fee_pct: "0.1",
        slippage_pct: "0.05",
        maker_fee_pct: "0.02",
        implied_round_trip_pct: "0.3",
      },
    });

    expect(parsed.session.decomposable_expected_gross).toBeNull();
    expect(parsed.session.sample_required_n).toBeNull();
    expect(parsed.session.edge_pct_round_trip).toBeNull();
    expect(parsed.session.expected_gross).toBe("123.456789123456789");
    expect(typeof parsed.session.actual_net).toBe("string");
    expect(parsed.unattributed_count).toBe(4);
    expect(parsed.strategy_session_count).toBe(2);
    expect(typeof parsed.assumption.implied_round_trip_pct).toBe("string");
  });
});
