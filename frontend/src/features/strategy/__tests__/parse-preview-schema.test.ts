// Sprint 7b: ParsePreviewResponse.functions_used Zod round-trip 검증.

import { describe, expect, it } from "vitest";

import { ParsePreviewResponseSchema } from "../schemas";

describe("ParsePreviewResponseSchema", () => {
  it("parses functions_used from BE response", () => {
    const raw = {
      status: "ok",
      pine_version: "v5",
      warnings: [],
      errors: [],
      entry_count: 3,
      exit_count: 2,
      functions_used: ["strategy.entry", "ta.crossover", "ta.ema"],
    };
    const parsed = ParsePreviewResponseSchema.parse(raw);
    expect(parsed.functions_used).toEqual([
      "strategy.entry",
      "ta.crossover",
      "ta.ema",
    ]);
  });

  it("defaults functions_used to empty array when omitted", () => {
    const raw = {
      status: "error",
      pine_version: "v5",
      errors: [{ code: "LexError", message: "boom", line: null }],
    };
    const parsed = ParsePreviewResponseSchema.parse(raw);
    expect(parsed.functions_used).toEqual([]);
    expect(parsed.warnings).toEqual([]);
  });
});
