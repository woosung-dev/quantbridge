// Sprint 51 BL-220 — Param Stability Zod schema parse test (codex G.0 P1#6).
// FE schema 가 BE StressTestKindSchema/ParamStabilityResultSchema 와 정합.

import { describe, expect, it } from "vitest";

import {
  CreateParamStabilityRequestSchema,
  ParamStabilityCellSchema,
  ParamStabilityResultSchema,
  StressTestKindSchema,
} from "../schemas";

describe("StressTestKindSchema (Sprint 51)", () => {
  it("'param_stability' enum value 허용", () => {
    expect(StressTestKindSchema.parse("param_stability")).toBe(
      "param_stability",
    );
  });

  it("invalid kind reject", () => {
    expect(() => StressTestKindSchema.parse("unknown_kind")).toThrow();
  });
});

describe("ParamStabilityCellSchema", () => {
  it("9-cell round-trip parse (BE str → FE str)", () => {
    const cell = {
      param1_value: "10",
      param2_value: "1.0",
      sharpe: "1.23",
      total_return: "0.15",
      max_drawdown: "-0.05",
      num_trades: 10,
      is_degenerate: false,
    };
    const parsed = ParamStabilityCellSchema.parse(cell);
    expect(parsed.param1_value).toBe("10");
    expect(parsed.sharpe).toBe("1.23");
    expect(parsed.num_trades).toBe(10);
    expect(parsed.is_degenerate).toBe(false);
  });

  it("degenerate cell — sharpe=null 허용", () => {
    const cell = {
      param1_value: "10",
      param2_value: "1.0",
      sharpe: null,
      total_return: "0",
      max_drawdown: "0",
      num_trades: 0,
      is_degenerate: true,
    };
    const parsed = ParamStabilityCellSchema.parse(cell);
    expect(parsed.sharpe).toBeNull();
    expect(parsed.is_degenerate).toBe(true);
  });
});

describe("ParamStabilityResultSchema", () => {
  it("9-cell result round-trip", () => {
    const result = {
      param1_name: "emaPeriod",
      param2_name: "stopLossPct",
      param1_values: ["10", "20", "30"],
      param2_values: ["1.0", "2.0", "3.0"],
      cells: Array.from({ length: 9 }, (_, i) => ({
        param1_value: String(i),
        param2_value: String(i),
        sharpe: "1.5",
        total_return: "0.05",
        max_drawdown: "-0.02",
        num_trades: 10,
        is_degenerate: false,
      })),
    };
    const parsed = ParamStabilityResultSchema.parse(result);
    expect(parsed.cells).toHaveLength(9);
    expect(parsed.param1_name).toBe("emaPeriod");
  });
});

describe("CreateParamStabilityRequestSchema", () => {
  it("9-cell grid request round-trip", () => {
    const req = {
      backtest_id: "550e8400-e29b-41d4-a716-446655440000",
      params: {
        param_grid: {
          emaPeriod: ["10", "20", "30"],
          stopLossPct: ["1.0", "2.0", "3.0"],
        },
      },
    };
    const parsed = CreateParamStabilityRequestSchema.parse(req);
    expect(parsed.backtest_id).toBe("550e8400-e29b-41d4-a716-446655440000");
    expect(Object.keys(parsed.params.param_grid)).toHaveLength(2);
  });

  it("invalid backtest_id (non-UUID) reject", () => {
    expect(() =>
      CreateParamStabilityRequestSchema.parse({
        backtest_id: "not-a-uuid",
        params: { param_grid: { x: ["1"], y: ["2"] } },
      }),
    ).toThrow();
  });
});
