// form-schemas 단위 테스트 — row 검증 규칙 + rowsToParameters + buildCreateRunBody 런타임 검증.

import { describe, expect, it } from "vitest";

import {
  BayesianRowSchema,
  buildCreateRunBody,
  GeneticRowSchema,
  GridParameterRowSchema,
  rowsToParameters,
} from "../form-schemas";

const BASE = {
  backtest_id: "3f9c1a52-1111-4222-8333-944455556666",
  objective_metric: "sharpe_ratio" as const,
  direction: "maximize" as const,
  max_evaluations: 9,
};

describe("row 스키마", () => {
  it("grid integer row — 문자열 입력을 숫자로 coerce", () => {
    const parsed = GridParameterRowSchema.parse({
      var_name: "length",
      kind: "integer",
      min: "10",
      max: "30",
      step: "5",
    });
    expect(parsed).toEqual({
      var_name: "length",
      kind: "integer",
      min: 10,
      max: 30,
      step: 5,
    });
  });

  it("bayesian row — min >= max 거부", () => {
    const res = BayesianRowSchema.safeParse({
      var_name: "x",
      min: "30",
      max: "5",
      prior: "uniform",
      log_scale: false,
    });
    expect(res.success).toBe(false);
  });

  it("bayesian row — log_uniform 인데 min <= 0 거부", () => {
    const res = BayesianRowSchema.safeParse({
      var_name: "x",
      min: "0",
      max: "5",
      prior: "log_uniform",
      log_scale: false,
    });
    expect(res.success).toBe(false);
  });

  it("genetic row — min > max 거부, min == max 허용", () => {
    expect(
      GeneticRowSchema.safeParse({
        var_name: "x",
        kind: "integer",
        min: "9",
        max: "5",
        step: "1",
      }).success,
    ).toBe(false);
    expect(
      GeneticRowSchema.safeParse({
        var_name: "x",
        kind: "integer",
        min: "5",
        max: "5",
        step: "1",
      }).success,
    ).toBe(true);
  });
});

describe("rowsToParameters", () => {
  it("빈 var_name row 는 skip", () => {
    const out = rowsToParameters(
      [
        { var_name: "a", v: 1 },
        { var_name: "", v: 2 },
      ],
      (row) => ({ v: row.v }),
    );
    expect(Object.keys(out)).toEqual(["a"]);
  });
});

describe("buildCreateRunBody", () => {
  it("정상 조합 — 원본 shape 그대로 반환 (스키마 default 미주입)", () => {
    const body = buildCreateRunBody({
      kind: "grid_search",
      schemaVersion: 1,
      base: BASE,
      parameters: { length: { kind: "integer", min: 10, max: 30, step: 5 } },
    });
    expect(body.param_space).not.toHaveProperty("genetic_selection_method");
    expect(body.kind).toBe("grid_search");
  });

  it("스키마 위반 조합(잘못된 kind 필드) — 제출 전 throw", () => {
    expect(() =>
      buildCreateRunBody({
        kind: "grid_search",
        schemaVersion: 1,
        base: BASE,
        parameters: { length: { kind: "nope" } },
      }),
    ).toThrow();
  });
});
