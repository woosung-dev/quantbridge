import { describe, expect, it } from "vitest";
import { buildParseSteps, FUNCTION_CAP } from "../parse-dialog-steps";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

const emptyResponse: ParsePreviewResponse = {
  status: "ok",
  pine_version: "v5",
  warnings: [],
  errors: [],
  entry_count: 0,
  exit_count: 0,
  functions_used: [],
  unsupported_builtins: [],
  is_runnable: true,
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
  unsupported_builtins: [],
  is_runnable: true,
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

  // T-B: status="unsupported" path (coverage 0 in initial suite)
  it("final.canSave is false when status is unsupported", () => {
    const steps = buildParseSteps({ ...emptyResponse, status: "unsupported" });
    const final = steps.at(-1);
    if (final?.kind !== "final") throw new Error("unreachable");
    expect(final.canSave).toBe(false);
    // intro + final only (0 errors/warnings/fns)
    expect(steps).toHaveLength(2);
  });

  // T-E: functions_used 중복 엔트리 → 중복 step 생성 (current behavior pinning)
  it("keeps duplicate function names as separate steps (no dedupe)", () => {
    const steps = buildParseSteps({
      ...emptyResponse,
      functions_used: ["ta.rsi", "ta.rsi", "ta.sma"],
  unsupported_builtins: [],
  is_runnable: true,
    });
    const names = steps
      .filter((s): s is Extract<typeof s, { kind: "function" }> => s.kind === "function")
      .map((s) => s.name);
    expect(names).toEqual(["ta.rsi", "ta.rsi", "ta.sma"]);
  });

  // T-E: 빈 문자열 / whitespace 엔트리 — unknown 그룹으로 분류, fallback 설명 적용
  it("handles empty-string and whitespace function names via fallback describe", () => {
    const steps = buildParseSteps({
      ...emptyResponse,
      functions_used: ["", "  ", "ta.rsi"],
  unsupported_builtins: [],
  is_runnable: true,
    });
    const fnSteps = steps.filter(
      (s): s is Extract<typeof s, { kind: "function" }> => s.kind === "function",
    );
    // stdlib 우선 — ta.rsi 먼저, 그 다음 unknown ("" + "  ")
    expect(fnSteps[0]?.name).toBe("ta.rsi");
    expect(fnSteps).toHaveLength(3);
    // fallback이 non-empty purpose 반환하는지 확인 (blank UI 방지 pin)
    for (const s of fnSteps) {
      expect(s.description.purpose.length).toBeGreaterThan(0);
    }
  });

  // T-F: FUNCTION_CAP export + boundary regression guard
  it("exposes FUNCTION_CAP=14 and produces exactly CAP function steps at boundary", () => {
    expect(FUNCTION_CAP).toBe(14);
    const exactly = Array.from({ length: FUNCTION_CAP }, (_, i) => `u.fn_${i}`);
    const steps = buildParseSteps({ ...emptyResponse, functions_used: exactly });
    const fnSteps = steps.filter((s) => s.kind === "function");
    expect(fnSteps).toHaveLength(FUNCTION_CAP);
    const final = steps.at(-1);
    if (final?.kind !== "final") throw new Error("unreachable");
    expect(final.hiddenFunctionCount).toBe(0);
  });
});
