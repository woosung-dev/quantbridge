// C13 진짜 OOS — WalkForwardParamsSchema optimizer spec parity + result 신규 필드 검증.

import { describe, expect, it } from "vitest";

import type { ParamSpace } from "@/features/optimizer/schemas";

import { WalkForwardParamsSchema, WalkForwardResultSchema } from "../schemas";

// param_space 는 옵티마이저 run 에서 온 검증완료 객체 — FE 는 passthrough, BE 가 재검증.
const PARAM_SPACE = {
  schema_version: 1,
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  max_evaluations: 9,
  parameters: { emaPeriod: { kind: "integer", min: 5, max: 10, step: 5 } },
} as unknown as ParamSpace;

describe("WalkForwardParamsSchema optimizer spec (WFO)", () => {
  it("optimizer_param_space + optimizer_kind 수용", () => {
    const parsed = WalkForwardParamsSchema.parse({
      train_bars: 100,
      test_bars: 50,
      optimizer_param_space: PARAM_SPACE,
      optimizer_kind: "grid_search",
    });
    expect(parsed.optimizer_param_space).toBeDefined();
    expect(parsed.optimizer_kind).toBe("grid_search");
  });

  it("plain (spec 없음) 통과 — 회귀 0", () => {
    const parsed = WalkForwardParamsSchema.parse({
      train_bars: 100,
      test_bars: 50,
    });
    expect(parsed.optimizer_param_space).toBeUndefined();
    expect(parsed.optimizer_kind).toBeUndefined();
  });
});

const BASE_RESULT = {
  folds: [
    {
      fold_index: 0,
      train_start: "2026-01-01T00:00:00+00:00",
      train_end: "2026-02-01T00:00:00+00:00",
      test_start: "2026-02-01T00:00:00+00:00",
      test_end: "2026-03-01T00:00:00+00:00",
      in_sample_return: "0.2",
      out_of_sample_return: "0.05",
      oos_sharpe: "0.4",
      num_trades_oos: 5,
    },
  ],
  aggregate_oos_return: "0.05",
  degradation_ratio: "4.0",
  valid_positive_regime: true,
  total_possible_folds: 1,
  was_truncated: false,
};

describe("WalkForwardResultSchema WFO 필드", () => {
  it("reoptimized_per_fold + degenerate_folds_skipped + selected_params 파싱", () => {
    const parsed = WalkForwardResultSchema.parse({
      ...BASE_RESULT,
      reoptimized_per_fold: true,
      degenerate_folds_skipped: 2,
      folds: [{ ...BASE_RESULT.folds[0], selected_params: { emaPeriod: "7" } }],
    });
    expect(parsed.reoptimized_per_fold).toBe(true);
    expect(parsed.degenerate_folds_skipped).toBe(2);
    expect(parsed.folds[0]?.selected_params).toEqual({ emaPeriod: "7" });
  });

  it("구버전 result (신규 필드 없음) → 기본값 — 회귀 0", () => {
    const parsed = WalkForwardResultSchema.parse(BASE_RESULT);
    expect(parsed.reoptimized_per_fold).toBe(false);
    expect(parsed.degenerate_folds_skipped).toBe(0);
    expect(parsed.folds[0]?.selected_params ?? null).toBeNull();
  });
});
