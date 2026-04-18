import { describe, expect, it } from "vitest";
import { buildParseSteps } from "../parse-dialog-steps";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

const emptyResponse: ParsePreviewResponse = {
  status: "ok",
  pine_version: "v5",
  warnings: [],
  errors: [],
  entry_count: 0,
  exit_count: 0,
  functions_used: [],
};

describe("buildParseSteps", () => {
  it("returns intro + final when nothing to show", () => {
    const steps = buildParseSteps(emptyResponse);
    expect(steps).toHaveLength(2);
    expect(steps[0]?.kind).toBe("intro");
    expect(steps[1]?.kind).toBe("final");
  });

  it("orders steps error -> warning -> function", () => {
    const steps = buildParseSteps({
      ...emptyResponse,
      status: "error",
      errors: [{ code: "syntax", message: "bad", line: 12 }],
      warnings: ["duplicate strategy.exit calls at lines [5, 9]"],
      functions_used: ["ta.rsi"],
    });
    expect(steps.map((s) => s.kind)).toEqual([
      "intro",
      "error",
      "warning",
      "function",
      "final",
    ]);
  });

  it("caps function steps at 14 and flags overflow", () => {
    const many = Array.from({ length: 20 }, (_, i) => `fn.${i}`);
    const steps = buildParseSteps({ ...emptyResponse, functions_used: many });
    const functionSteps = steps.filter((s) => s.kind === "function");
    expect(functionSteps).toHaveLength(14);
    const final = steps.at(-1);
    expect(final?.kind).toBe("final");
    if (final?.kind === "final") {
      expect(final.hiddenFunctionCount).toBe(6);
    }
  });

  it("prioritizes known stdlib functions before unknown ones under the cap", () => {
    const unknowns = Array.from({ length: 15 }, (_, i) => `my.fn_${i}`);
    const knowns = ["ta.rsi", "strategy.entry"];
    const steps = buildParseSteps({
      ...emptyResponse,
      functions_used: [...unknowns, ...knowns],
    });
    const functionStepNames = steps
      .filter(
        (s): s is Extract<typeof s, { kind: "function" }> => s.kind === "function",
      )
      .map((s) => s.name);
    expect(functionStepNames.slice(0, 2)).toEqual(["ta.rsi", "strategy.entry"]);
    expect(functionStepNames).toHaveLength(14);
  });

  it("final.canSave is false when status is error", () => {
    const steps = buildParseSteps({ ...emptyResponse, status: "error" });
    const final = steps.at(-1);
    if (final?.kind !== "final") throw new Error("unreachable");
    expect(final.canSave).toBe(false);
  });

  it("final.canSave is true when status is ok", () => {
    const steps = buildParseSteps(emptyResponse);
    const final = steps.at(-1);
    if (final?.kind !== "final") throw new Error("unreachable");
    expect(final.canSave).toBe(true);
  });
});
