// HIGH-1 (Evaluator gate 2): grid(schema_version=1) param_space 가 BE 직렬화 형태(v2 필드=null)로
// 재파싱 가능해야 함. BE ParamSpace.model_dump(mode="json") 는 v2 필드를 null 로 내보내므로,
// FE 가 이를 reject 하면 옵티마이저 run-detail(getOptimizationRun hard parse) 로드 실패 →
// grid optimizer(기본) run detail + 그 안의 WFO OOS CTA 가 전부 unreachable. (BL-350/354 family)

import { describe, expect, it } from "vitest";

import { OptimizationRunResponseSchema, ParamSpaceSchema } from "../schemas";

// BE ParamSpace.model_dump(mode="json") 가 grid run 에 대해 내보내는 실제 형태.
const BE_GRID_PARAM_SPACE = {
  schema_version: 1,
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  max_evaluations: 9,
  parameters: { emaPeriod: { kind: "integer", min: 5, max: 10, step: 5 } },
  bayesian_n_initial_random: null,
  bayesian_acquisition: null,
  population_size: null,
  n_generations: null,
  mutation_rate: null,
  crossover_rate: null,
  genetic_selection_method: null,
};

describe("ParamSpaceSchema grid round-trip (BE null v2 fields)", () => {
  it("grid param_space (v2 필드 null) 재파싱 통과", () => {
    const parsed = ParamSpaceSchema.parse(BE_GRID_PARAM_SPACE);
    expect(parsed.schema_version).toBe(1);
    expect(parsed.objective_metric).toBe("sharpe_ratio");
  });

  it("grid OptimizationRunResponse 로드 통과 (run-detail 페이지)", () => {
    const run = {
      id: "11111111-1111-4111-8111-111111111111",
      user_id: "22222222-2222-4222-8222-222222222222",
      backtest_id: "33333333-3333-4333-8333-333333333333",
      kind: "grid_search",
      status: "completed",
      param_space: BE_GRID_PARAM_SPACE,
      result: null,
      error_message: null,
      created_at: "2026-03-01T00:00:00+00:00",
      started_at: "2026-03-01T00:00:00+00:00",
      completed_at: "2026-03-01T00:01:00+00:00",
    };
    expect(() => OptimizationRunResponseSchema.parse(run)).not.toThrow();
  });

  it("schema_version=1 에 실제 v2 값(비-null) 들어오면 여전히 reject", () => {
    expect(() =>
      ParamSpaceSchema.parse({
        ...BE_GRID_PARAM_SPACE,
        population_size: 10, // 실제 v2 값 → schema_version=1 금지 유지
      }),
    ).toThrow();
  });
});
