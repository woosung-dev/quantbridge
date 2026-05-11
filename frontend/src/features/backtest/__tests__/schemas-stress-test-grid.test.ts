// Sprint 52 BL-224 — Cost Assumption + Param Stability schemas superRefine 검증
// FE schema 가 BE `stress_test/schemas.py:144-164,212-227` grid validator 와 동일 제약 검증.

import { describe, expect, it } from "vitest";

import {
  CostAssumptionParamsSchema,
  ParamStabilityParamsSchema,
} from "../schemas";

describe("CostAssumptionParamsSchema (Sprint 52 BL-224 superRefine)", () => {
  it("happy path — fees + slippage 2 key 3x3 grid PASS", () => {
    const parsed = CostAssumptionParamsSchema.parse({
      param_grid: {
        fees: ["0.001", "0.002", "0.003"],
        slippage: ["0.0005", "0.001", "0.0015"],
      },
    });
    expect(Object.keys(parsed.param_grid)).toHaveLength(2);
  });

  it("3 key reject (exactly 2 keys)", () => {
    expect(() =>
      CostAssumptionParamsSchema.parse({
        param_grid: {
          fees: ["0.001"],
          slippage: ["0.0005"],
          extra: ["1"],
        },
      }),
    ).toThrow(/exactly 2 keys/);
  });

  it("non-fees/slippage key reject (allowedKeys subset)", () => {
    expect(() =>
      CostAssumptionParamsSchema.parse({
        param_grid: {
          fees: ["0.001"],
          leverage: ["1.0"],
        },
      }),
    ).toThrow(/subset.*fees.*slippage/i);
  });

  it("non-empty values 강제", () => {
    expect(() =>
      CostAssumptionParamsSchema.parse({
        param_grid: {
          fees: [],
          slippage: ["0.0005"],
        },
      }),
    ).toThrow(/must not be empty/);
  });

  it("4x3 = 12 cell reject (≤9 cell)", () => {
    expect(() =>
      CostAssumptionParamsSchema.parse({
        param_grid: {
          fees: ["0.001", "0.002", "0.003", "0.004"],
          slippage: ["0.0005", "0.001", "0.0015"],
        },
      }),
    ).toThrow(/exceeds 9/);
  });

  it("NaN string reject (finite Decimal 강제)", () => {
    expect(() =>
      CostAssumptionParamsSchema.parse({
        param_grid: {
          fees: ["0.001", "NaN"],
          slippage: ["0.0005"],
        },
      }),
    ).toThrow(/finite Decimal/);
  });

  it("Infinity string reject", () => {
    expect(() =>
      CostAssumptionParamsSchema.parse({
        param_grid: {
          fees: ["0.001", "Infinity"],
          slippage: ["0.0005"],
        },
      }),
    ).toThrow(/finite Decimal/);
  });

  it("empty string reject", () => {
    expect(() =>
      CostAssumptionParamsSchema.parse({
        param_grid: {
          fees: ["0.001", ""],
          slippage: ["0.0005"],
        },
      }),
    ).toThrow(/finite Decimal/);
  });
});

describe("ParamStabilityParamsSchema (Sprint 52 BL-224 superRefine)", () => {
  it("happy path — 2 arbitrary var_name 3x3 grid PASS", () => {
    const parsed = ParamStabilityParamsSchema.parse({
      param_grid: {
        emaPeriod: ["10", "20", "30"],
        stopLossPct: ["1.0", "2.0", "3.0"],
      },
    });
    expect(Object.keys(parsed.param_grid)).toHaveLength(2);
  });

  it("1 key reject (exactly 2 keys — single axis 차단)", () => {
    expect(() =>
      ParamStabilityParamsSchema.parse({
        param_grid: {
          emaPeriod: ["10", "20"],
        },
      }),
    ).toThrow(/exactly 2 keys/);
  });

  it("3 key reject", () => {
    expect(() =>
      ParamStabilityParamsSchema.parse({
        param_grid: {
          emaPeriod: ["10"],
          stopLossPct: ["1.0"],
          extra: ["1"],
        },
      }),
    ).toThrow(/exactly 2 keys/);
  });

  it("non-empty values 강제", () => {
    expect(() =>
      ParamStabilityParamsSchema.parse({
        param_grid: {
          emaPeriod: [],
          stopLossPct: ["1.0"],
        },
      }),
    ).toThrow(/must not be empty/);
  });

  it("4x3 = 12 cell reject (≤9 cell)", () => {
    expect(() =>
      ParamStabilityParamsSchema.parse({
        param_grid: {
          emaPeriod: ["10", "20", "30", "40"],
          stopLossPct: ["1.0", "2.0", "3.0"],
        },
      }),
    ).toThrow(/exceeds 9/);
  });

  it("NaN reject (finite Decimal 강제)", () => {
    expect(() =>
      ParamStabilityParamsSchema.parse({
        param_grid: {
          emaPeriod: ["NaN", "10"],
          stopLossPct: ["1.0"],
        },
      }),
    ).toThrow(/finite Decimal/);
  });

  it("Infinity reject", () => {
    expect(() =>
      ParamStabilityParamsSchema.parse({
        param_grid: {
          emaPeriod: ["10"],
          stopLossPct: ["1.0", "Infinity"],
        },
      }),
    ).toThrow(/finite Decimal/);
  });

  it("empty string reject", () => {
    expect(() =>
      ParamStabilityParamsSchema.parse({
        param_grid: {
          emaPeriod: ["10", ""],
          stopLossPct: ["1.0"],
        },
      }),
    ).toThrow(/finite Decimal/);
  });

  it("var_name 자유 (BE 가 InputDecl cross-check) — allowedKeys 제약 없음", () => {
    // BE 가 var_name 검증 → FE 는 통과시킴.
    const parsed = ParamStabilityParamsSchema.parse({
      param_grid: {
        anyVarName: ["1", "2"],
        otherVar: ["3.5", "4.5"],
      },
    });
    expect(Object.keys(parsed.param_grid)).toEqual(["anyVarName", "otherVar"]);
  });
});
